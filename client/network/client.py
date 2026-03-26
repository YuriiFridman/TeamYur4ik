import asyncio
import json
import logging
import socket
import struct
import threading
from typing import Callable, Dict, Optional

import websockets

logger = logging.getLogger(__name__)


class NetworkClient:
    """
    Manages the WebSocket connection (text commands) and UDP socket (voice).

    The asyncio event loop runs in a dedicated background thread so the Qt UI
    thread is never blocked.  Automatic exponential-backoff reconnection is
    built in for the WebSocket connection.
    """

    def __init__(self):
        self._host: Optional[str] = None
        self._ws_port: int = 8765
        self._voice_port: int = 9000
        self._token: Optional[str] = None
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._udp_socket: Optional[socket.socket] = None
        self._running: bool = False
        # Reconnection back-off parameters
        self._reconnect_delay: float = 1.0
        self._max_reconnect_delay: float = 30.0
        # Registered event callbacks: event_name -> callable(data)
        self.on_event: Dict[str, Callable] = {}
        # Called when the WebSocket connection is established
        self.on_connected: Optional[Callable] = None
        # Called when permanently disconnected (running == False)
        self.on_disconnected: Optional[Callable] = None

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def connect(self, host: str, ws_port: int, voice_port: int, token: str):
        """
        Begin connecting to the server.
        Starts the asyncio event loop in a background thread and opens a
        UDP socket for voice traffic.
        """
        self._host = host
        self._ws_port = ws_port
        self._voice_port = voice_port
        self._token = token
        self._running = True
        self._reconnect_delay = 1.0
        # UDP socket for voice – connectionless, so no handshake needed
        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Run the asyncio loop in a daemon thread so it dies with the process
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="NetworkThread"
        )
        self._thread.start()

    def send_command(self, action: str, data: dict = None):
        """
        Queue a WebSocket command on the network thread.
        Thread-safe: can be called from the Qt UI thread.
        """
        if self._loop and self._ws and self._running:
            msg = json.dumps({"type": "action", "action": action, "data": data or {}})
            asyncio.run_coroutine_threadsafe(self._ws.send(msg), self._loop)

    def send_voice(self, channel_id: int, audio_data: bytes):
        """
        Send a voice UDP packet to the relay server.
        Packet format: [4-byte big-endian channel_id] + encoded audio bytes.
        """
        if self._udp_socket and self._host and self._running:
            try:
                packet = struct.pack(">I", channel_id) + audio_data
                self._udp_socket.sendto(packet, (self._host, self._voice_port))
            except Exception as e:
                logger.error(f"Error sending voice packet: {e}")

    def disconnect(self):
        """
        Initiate a clean disconnect.
        Closes the WebSocket and UDP socket, then stops the event loop.
        """
        self._running = False
        if self._loop and self._ws:
            asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)
        if self._udp_socket:
            self._udp_socket.close()
            self._udp_socket = None
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

    # -------------------------------------------------------------------------
    # Internal asyncio machinery (runs in background thread)
    # -------------------------------------------------------------------------

    def _run_loop(self):
        """Entry point for the background network thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connection_loop())

    async def _connection_loop(self):
        """
        Outer reconnection loop.
        Keeps trying to connect until self._running is False,
        using exponential back-off between attempts.
        """
        while self._running:
            try:
                uri = f"ws://{self._host}:{self._ws_port}"
                logger.info(f"Connecting to {uri}")
                async with websockets.connect(uri) as ws:
                    self._ws = ws
                    self._reconnect_delay = 1.0  # reset back-off on successful connect
                    if self.on_connected:
                        self.on_connected()
                    await self._receive_loop(ws)
            except (websockets.exceptions.ConnectionClosed,
                    OSError, ConnectionRefusedError) as e:
                logger.warning(f"Connection lost: {e}")
                self._ws = None
                if not self._running:
                    break
                logger.info(f"Reconnecting in {self._reconnect_delay:.1f}s…")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self._max_reconnect_delay
                )
            except Exception as e:
                logger.error(f"Unexpected connection error: {e}", exc_info=True)
                if not self._running:
                    break
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self._max_reconnect_delay
                )

        if self.on_disconnected:
            self.on_disconnected()

    async def _receive_loop(self, ws):
        """
        Inner message-receive loop for a single WebSocket connection.
        Dispatches incoming messages to the registered on_event callbacks.
        """
        async for raw in ws:
            try:
                msg = json.loads(raw)
                msg_type = msg.get("type")
                if msg_type == "event":
                    # Server-pushed event (e.g. new_message, user_joined_channel)
                    event_name = msg.get("event")
                    data = msg.get("data", {})
                    cb = self.on_event.get(event_name)
                    if cb:
                        cb(data)
                elif msg_type == "response":
                    # Response to a command we sent (keyed as "response_<action>")
                    action = msg.get("action")
                    cb = self.on_event.get(f"response_{action}")
                    if cb:
                        cb(msg)
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
