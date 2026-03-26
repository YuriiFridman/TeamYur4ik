"""
Unit tests for client-side modules that do NOT require a display.

Tests cover:
  - Localization manager
  - NetworkClient (stub/mock) state
  - AudioManager graceful degradation when PyAudio is absent
"""
import sys
import os
import json
import pytest

# Make client packages importable
CLIENT_DIR = os.path.join(os.path.dirname(__file__), "..", "client")
sys.path.insert(0, CLIENT_DIR)


# ---------------------------------------------------------------------------
# Localization
# ---------------------------------------------------------------------------

class TestLocalization:
    def test_get_english_key(self):
        from localization import loc
        loc.set_locale("en")
        assert loc.get("login") == "Login"

    def test_get_russian_key(self):
        from localization import loc
        loc.set_locale("ru")
        result = loc.get("login")
        loc.set_locale("en")  # restore for other tests
        assert result == "Войти"

    def test_missing_key_returns_key_name(self):
        from localization import loc
        loc.set_locale("en")
        assert loc.get("this_key_does_not_exist") == "this_key_does_not_exist"

    def test_set_locale_invalid_does_not_crash(self):
        from localization import loc
        loc.set_locale("xx")   # unsupported locale → silently ignored
        # should fall back to English for any key
        assert loc.get("send") == "Send"

    def test_get_locale(self):
        from localization import loc
        loc.set_locale("en")
        assert loc.get_locale() == "en"
        loc.set_locale("ru")
        assert loc.get_locale() == "ru"
        loc.set_locale("en")


# ---------------------------------------------------------------------------
# AudioManager — graceful degradation without hardware
# ---------------------------------------------------------------------------

class TestAudioManagerNoPyAudio:
    """AudioManager must not crash when PyAudio is unavailable."""

    def _make_stub(self):
        """Create a minimal AudioManager stub with all attributes needed by __del__."""
        import threading
        import audio.audio_manager as am
        mgr = am.AudioManager.__new__(am.AudioManager)
        mgr._pa = None
        mgr._capture_thread = None
        mgr._stop_capture = threading.Event()
        mgr._output_stream = None
        mgr._output_lock = threading.Lock()
        mgr._input_device_index = None
        mgr._output_device_index = None
        mgr._mode = "vad"
        mgr._vad_threshold = 0.01
        mgr._ptt_key = "space"
        mgr._ptt_active = False
        mgr._lock = threading.Lock()
        mgr._encoder = None
        mgr._decoder = None
        mgr.on_audio_captured = None
        return mgr

    def test_get_devices_without_pyaudio(self, monkeypatch):
        import audio.audio_manager as am
        monkeypatch.setattr(am, "PYAUDIO_AVAILABLE", False)
        mgr = self._make_stub()
        devices = mgr.get_devices()
        assert devices == {"input": [], "output": []}

    def test_start_capture_without_pyaudio(self, monkeypatch):
        import audio.audio_manager as am
        monkeypatch.setattr(am, "PYAUDIO_AVAILABLE", False)
        mgr = self._make_stub()
        # Should return silently without raising
        mgr.start_capture()

    def test_play_audio_without_pyaudio(self, monkeypatch):
        import audio.audio_manager as am
        monkeypatch.setattr(am, "PYAUDIO_AVAILABLE", False)
        mgr = self._make_stub()
        # Should return silently
        mgr.play_audio(b"fake_audio_data")


# ---------------------------------------------------------------------------
# AudioManager VAD helper
# ---------------------------------------------------------------------------

class TestAudioManagerVAD:
    def _make_stub(self):
        import threading
        import audio.audio_manager as am
        mgr = am.AudioManager.__new__(am.AudioManager)
        mgr._pa = None
        mgr._capture_thread = None
        mgr._stop_capture = threading.Event()
        mgr._output_stream = None
        mgr._output_lock = threading.Lock()
        mgr._lock = threading.Lock()
        mgr._encoder = None
        mgr._decoder = None
        mgr.on_audio_captured = None
        return mgr

    def test_rms_silence_is_zero(self):
        import struct
        import audio.audio_manager as am
        mgr = self._make_stub()
        # All-zero PCM → RMS = 0
        data = struct.pack("<960h", *([0] * 960))
        assert mgr._calculate_rms(data) == 0.0

    def test_rms_max_signal_near_one(self):
        import struct
        import audio.audio_manager as am
        mgr = self._make_stub()
        # Maximum positive value for int16
        data = struct.pack("<960h", *([32767] * 960))
        rms = mgr._calculate_rms(data)
        assert 0.99 < rms <= 1.0

    def test_rms_short_buffer_returns_zero(self):
        import audio.audio_manager as am
        mgr = self._make_stub()
        assert mgr._calculate_rms(b"\x01") == 0.0


# ---------------------------------------------------------------------------
# NetworkClient state machine
# ---------------------------------------------------------------------------

class TestNetworkClientState:
    def test_initial_state(self):
        from network.client import NetworkClient
        nc = NetworkClient()
        assert nc._host is None
        assert nc._ws is None
        assert nc._running is False
        assert isinstance(nc.on_event, dict)

    def test_send_command_before_connect_does_not_raise(self):
        from network.client import NetworkClient
        nc = NetworkClient()
        # Should silently ignore – no WebSocket, not running
        nc.send_command("login", {"username": "x"})

    def test_send_voice_before_connect_does_not_raise(self):
        from network.client import NetworkClient
        nc = NetworkClient()
        nc.send_voice(1, b"audio")

    def test_disconnect_before_connect_does_not_raise(self):
        from network.client import NetworkClient
        nc = NetworkClient()
        nc.disconnect()
