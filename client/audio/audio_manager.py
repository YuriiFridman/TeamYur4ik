import logging
import struct
import sys
import threading
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import PyAudio; fall back gracefully if not available.
# On Windows, missing native DLLs raise OSError (not ImportError),
# so we catch both here.
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except (ImportError, OSError):
    PYAUDIO_AVAILABLE = False
    logger.warning("PyAudio not available. Audio features disabled.")

# Try to import opuslib; fall back to raw PCM if not available.
# On Windows, missing native DLLs raise OSError (not ImportError).
try:
    import opuslib
    OPUS_AVAILABLE = True
except (ImportError, OSError):
    OPUS_AVAILABLE = False
    logger.warning("opuslib not available. Using raw PCM audio.")

# Audio constants
SAMPLE_RATE = 48000          # Hz – standard for Opus
CHANNELS = 1                 # Mono capture/playback
FRAME_DURATION_MS = 20       # 20 ms per frame (Opus requirement)
CHUNK_SIZE = SAMPLE_RATE * FRAME_DURATION_MS // 1000  # = 960 samples per frame


class AudioManager:
    """
    Manages audio capture and playback for the TeamYur4ik client.

    Supports two transmission modes:
      - 'vad'  : Voice Activity Detection – transmits frames above an RMS threshold.
      - 'ptt'  : Push-to-Talk – transmits only while ptt_active is True.

    Uses Opus encoding/decoding when opuslib is available; falls back to raw 16-bit PCM.
    Capture runs in a background daemon thread; all public methods are thread-safe.
    """

    def __init__(self):
        # PyAudio instance (None if unavailable or import failed)
        self._pa: Optional[object] = None
        # Device indices (None = let PyAudio pick the system default)
        self._input_device_index: Optional[int] = None
        self._output_device_index: Optional[int] = None
        # Capture thread and cooperative-stop event
        self._capture_thread: Optional[threading.Thread] = None
        self._stop_capture = threading.Event()
        # Transmission mode: 'vad', 'ptt', or 'mute'
        self._mode: str = "vad"
        # RMS amplitude threshold for VAD (normalised 0.0 – 1.0)
        self._vad_threshold: float = 0.01
        # Push-to-talk key name (used by the UI layer; stored here for settings sync)
        self._ptt_key: str = "space"
        # True while the PTT button is held
        self._ptt_active: bool = False
        # Lock guarding all mutable state accessed from both UI and capture threads
        self._lock = threading.Lock()
        # Callback invoked with encoded audio bytes when a frame should be transmitted
        self.on_audio_captured: Optional[Callable[[bytes], None]] = None

        # Persistent output stream – opened once and reused to avoid the
        # per-frame open/close overhead that causes audio glitches and high CPU usage.
        self._output_stream: Optional[object] = None
        self._output_lock = threading.Lock()

        # Opus encoder/decoder handles (None if opuslib unavailable)
        self._encoder = None
        self._decoder = None

        # --- Initialise PyAudio ---
        if PYAUDIO_AVAILABLE:
            try:
                self._pa = pyaudio.PyAudio()
                logger.info("PyAudio initialised successfully")
            except Exception as e:
                logger.error(f"Failed to initialise PyAudio: {e}")
                self._pa = None

        # --- Initialise Opus ---
        if OPUS_AVAILABLE:
            try:
                self._encoder = opuslib.Encoder(SAMPLE_RATE, CHANNELS,
                                                opuslib.APPLICATION_VOIP)
                self._decoder = opuslib.Decoder(SAMPLE_RATE, CHANNELS)
                logger.info("Opus encoder/decoder initialised")
            except Exception as e:
                logger.error(f"Failed to initialise Opus: {e}")
                self._encoder = None
                self._decoder = None

    # -------------------------------------------------------------------------
    # Capture control
    # -------------------------------------------------------------------------

    def start_capture(self):
        """Start capturing microphone audio in a background daemon thread."""
        if self._capture_thread and self._capture_thread.is_alive():
            logger.debug("Capture already running; ignoring start_capture()")
            return
        if not self._pa:
            logger.warning("Cannot start capture: PyAudio is not available")
            return
        self._stop_capture.clear()
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
            name="AudioCaptureThread"
        )
        self._capture_thread.start()
        logger.info("Audio capture started")

    def stop_capture(self):
        """Signal the capture thread to stop and block until it exits (max 2 s)."""
        self._stop_capture.set()
        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None
        logger.info("Audio capture stopped")

    def _capture_loop(self):
        """
        Background thread body.
        Opens a PyAudio input stream and continuously reads 20 ms frames.
        Applies VAD / PTT gating before invoking on_audio_captured.
        """
        try:
            stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
                input_device_index=self._input_device_index,
            )
        except Exception as e:
            logger.error(f"Failed to open input stream: {e}")
            return

        logger.debug("Capture loop started")
        try:
            while not self._stop_capture.is_set():
                try:
                    # exception_on_overflow=False prevents crashes on buffer overrun
                    raw = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                except Exception as e:
                    logger.error(f"Error reading from microphone: {e}")
                    break

                # Read shared state atomically
                with self._lock:
                    mode = self._mode
                    ptt_active = self._ptt_active
                    threshold = self._vad_threshold

                # Determine whether this frame should be transmitted
                should_send = False
                if mode == "vad":
                    rms = self._calculate_rms(raw)
                    should_send = rms >= threshold
                elif mode == "ptt":
                    should_send = ptt_active
                # mode == 'mute' → should_send stays False

                if should_send and self.on_audio_captured:
                    audio_data = self._encode(raw)
                    if audio_data:
                        self.on_audio_captured(audio_data)
        finally:
            stream.stop_stream()
            stream.close()
            logger.debug("Capture loop ended")

    # -------------------------------------------------------------------------
    # Playback
    # -------------------------------------------------------------------------

    def play_audio(self, data: bytes):
        """
        Decode incoming audio bytes and write them to the persistent output stream.
        The stream is opened lazily on the first call and reused for all subsequent frames,
        avoiding the per-frame open/close overhead that caused audio glitches.
        """
        if not self._pa:
            return
        pcm = self._decode(data)
        if not pcm:
            return
        with self._output_lock:
            try:
                # Open the persistent stream if it is not yet open or was closed
                if self._output_stream is None or not self._output_stream.is_active():
                    self._output_stream = self._pa.open(
                        format=pyaudio.paInt16,
                        channels=CHANNELS,
                        rate=SAMPLE_RATE,
                        output=True,
                        frames_per_buffer=CHUNK_SIZE,
                        output_device_index=self._output_device_index,
                    )
                self._output_stream.write(pcm)
            except Exception as e:
                logger.error(f"Error playing audio: {e}")
                # Close the broken stream so the next call re-opens it cleanly
                if self._output_stream:
                    try:
                        self._output_stream.close()
                    except Exception:
                        pass
                    self._output_stream = None

    # -------------------------------------------------------------------------
    # Encode / decode helpers
    # -------------------------------------------------------------------------

    def _encode(self, pcm: bytes) -> Optional[bytes]:
        """Encode raw 16-bit PCM to Opus; returns raw PCM if Opus is unavailable."""
        if self._encoder:
            try:
                return self._encoder.encode(pcm, CHUNK_SIZE)
            except Exception as e:
                logger.error(f"Opus encode error: {e}")
        return pcm  # raw PCM fallback

    def _decode(self, data: bytes) -> Optional[bytes]:
        """Decode Opus bytes to raw 16-bit PCM; returns raw bytes if Opus is unavailable."""
        if self._decoder:
            try:
                return self._decoder.decode(data, CHUNK_SIZE)
            except Exception as e:
                logger.error(f"Opus decode error: {e}")
        return data  # raw PCM fallback

    # -------------------------------------------------------------------------
    # VAD helper
    # -------------------------------------------------------------------------

    def _calculate_rms(self, data: bytes) -> float:
        """
        Calculate normalised RMS of a 16-bit little-endian PCM buffer.
        Returns a value in the range [0.0, 1.0].
        """
        if len(data) < 2:
            return 0.0
        n = len(data) // 2
        samples = struct.unpack(f"<{n}h", data[:n * 2])
        rms = (sum(s * s for s in samples) / n) ** 0.5
        # Normalise: max int16 amplitude is 32768
        return rms / 32768.0

    # -------------------------------------------------------------------------
    # Configuration setters
    # -------------------------------------------------------------------------

    def set_mode(self, mode: str):
        """Set transmission mode: 'vad', 'ptt', or 'mute'."""
        with self._lock:
            self._mode = mode
        logger.debug(f"Audio mode set to: {mode}")

    def set_vad_threshold(self, val: float):
        """Set the VAD RMS threshold (clamped to [0.0, 1.0])."""
        with self._lock:
            self._vad_threshold = max(0.0, min(1.0, val))

    def set_ptt_key(self, key: str):
        """Store the push-to-talk key name (consumed by the UI layer)."""
        with self._lock:
            self._ptt_key = key

    @property
    def ptt_active(self) -> bool:
        """True while the PTT button is being held down."""
        return self._ptt_active

    @ptt_active.setter
    def ptt_active(self, value: bool):
        with self._lock:
            self._ptt_active = value

    def set_input_device(self, index: int):
        """Select the microphone device by PyAudio device index."""
        with self._lock:
            self._input_device_index = index

    def set_output_device(self, index: int):
        """Select the speaker/headphone device by PyAudio device index."""
        with self._lock:
            self._output_device_index = index

    def get_devices(self) -> Dict[str, List[str]]:
        """
        Enumerate all available audio devices.
        Returns {'input': [name, ...], 'output': [name, ...]}.
        """
        result: Dict[str, List[str]] = {"input": [], "output": []}
        if not self._pa:
            return result
        try:
            for i in range(self._pa.get_device_count()):
                info = self._pa.get_device_info_by_index(i)
                name = info.get("name", f"Device {i}")
                # Fix encoding: PyAudio on Windows returns device names in the
                # system ANSI code page but Python may decode them as Latin-1.
                # Re-encode to Latin-1 then decode with the preferred encoding.
                if sys.platform == "win32":
                    try:
                        import locale as _locale
                        enc = _locale.getpreferredencoding(False) or "utf-8"
                        name = name.encode("latin-1").decode(enc, errors="replace")
                    except (UnicodeEncodeError, UnicodeDecodeError, LookupError):
                        pass
                if info.get("maxInputChannels", 0) > 0:
                    result["input"].append(name)
                if info.get("maxOutputChannels", 0) > 0:
                    result["output"].append(name)
        except Exception as e:
            logger.error(f"Error enumerating audio devices: {e}")
        return result

    def __del__(self):
        """Ensure the capture thread, output stream, and PyAudio are cleaned up on GC."""
        self.stop_capture()
        # Close the persistent output stream if it is still open
        with self._output_lock:
            if self._output_stream:
                try:
                    self._output_stream.stop_stream()
                    self._output_stream.close()
                except Exception:
                    pass
                self._output_stream = None
        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
