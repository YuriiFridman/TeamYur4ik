import asyncio
import struct
import logging
from typing import Dict, Set, Optional, Tuple

logger = logging.getLogger(__name__)


class VoiceRelayProtocol(asyncio.DatagramProtocol):
    """
    UDP datagram protocol for relaying voice packets between clients in the same channel.
    Packet format: [4 bytes channel_id (big-endian uint32)] [remaining bytes: Opus audio data]
    """

    def __init__(self):
        self.transport: Optional[asyncio.DatagramTransport] = None
        # Maps client address tuple -> channel_id they are currently broadcasting in
        self._client_channels: Dict[Tuple, int] = {}
        # Maps channel_id -> set of client address tuples in that channel
        self._channel_clients: Dict[int, Set[Tuple]] = {}

    def connection_made(self, transport: asyncio.DatagramTransport):
        self.transport = transport
        logger.info("VoiceRelay UDP socket opened")

    def datagram_received(self, data: bytes, addr: Tuple):
        """
        Called for every incoming UDP datagram.
        Parse the 4-byte channel_id header, register the sender if needed,
        then relay the full packet to every other peer in the same channel.
        """
        # Need at least 4 bytes for the channel_id header
        if len(data) < 4:
            return

        channel_id = struct.unpack(">I", data[:4])[0]

        # Auto-register (or re-register) the client whenever its channel changes
        if addr not in self._client_channels or self._client_channels[addr] != channel_id:
            self.register_client(addr, channel_id)

        # Relay raw packet (header + audio) to every other client in the same channel
        peers = self._channel_clients.get(channel_id, set())
        for peer_addr in peers:
            if peer_addr != addr:
                try:
                    self.transport.sendto(data, peer_addr)
                except Exception as e:
                    logger.error(f"Error relaying voice to {peer_addr}: {e}")

    def error_received(self, exc: Exception):
        logger.error(f"VoiceRelay error: {exc}")

    def connection_lost(self, exc):
        logger.info("VoiceRelay UDP socket closed")

    def register_client(self, addr: Tuple, channel_id: int):
        """
        Move (or add) addr to channel_id, cleaning up any previous channel membership.
        """
        # Remove from old channel first so stale membership is cleaned up
        self.unregister_client(addr)
        self._client_channels[addr] = channel_id
        if channel_id not in self._channel_clients:
            self._channel_clients[channel_id] = set()
        self._channel_clients[channel_id].add(addr)
        logger.debug(f"Registered {addr} in voice channel {channel_id}")

    def unregister_client(self, addr: Tuple):
        """Remove addr from whichever voice channel it currently belongs to."""
        if addr in self._client_channels:
            old_channel = self._client_channels.pop(addr)
            if old_channel in self._channel_clients:
                self._channel_clients[old_channel].discard(addr)
                # Clean up empty channel sets to avoid memory leaks
                if not self._channel_clients[old_channel]:
                    del self._channel_clients[old_channel]
            logger.debug(f"Unregistered {addr} from voice channels")


class VoiceRelay:
    """High-level manager for the UDP voice relay server."""

    def __init__(self):
        self._protocol: Optional[VoiceRelayProtocol] = None
        self._transport: Optional[asyncio.DatagramTransport] = None

    async def start(self, host: str, port: int):
        """Bind the UDP socket and start listening for voice datagrams."""
        loop = asyncio.get_event_loop()
        self._transport, self._protocol = await loop.create_datagram_endpoint(
            VoiceRelayProtocol,
            local_addr=(host, port)
        )
        logger.info(f"VoiceRelay listening on UDP {host}:{port}")

    def stop(self):
        """Close the UDP socket."""
        if self._transport:
            self._transport.close()
            logger.info("VoiceRelay stopped")

    def register_client(self, addr: Tuple, channel_id: int):
        """Manually register a client address in a voice channel."""
        if self._protocol:
            self._protocol.register_client(addr, channel_id)

    def unregister_client(self, addr: Tuple):
        """Manually remove a client address from all voice channels."""
        if self._protocol:
            self._protocol.unregister_client(addr)
