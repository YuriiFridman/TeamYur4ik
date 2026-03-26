"""
Unit tests for server/voice_relay.py — VoiceRelayProtocol logic.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from voice_relay import VoiceRelayProtocol


class FakeTransport:
    """Capture sendto() calls for assertions."""
    def __init__(self):
        self.sent: list = []

    def sendto(self, data: bytes, addr):
        self.sent.append((data, addr))


@pytest.fixture
def relay():
    proto = VoiceRelayProtocol()
    proto.transport = FakeTransport()
    return proto


class TestVoiceRelayProtocol:
    def test_register_client(self, relay):
        relay.register_client(("127.0.0.1", 5000), 1)
        assert relay._client_channels[("127.0.0.1", 5000)] == 1
        assert ("127.0.0.1", 5000) in relay._channel_clients[1]

    def test_unregister_client(self, relay):
        addr = ("127.0.0.1", 5001)
        relay.register_client(addr, 2)
        relay.unregister_client(addr)
        assert addr not in relay._client_channels
        # Empty channel set is cleaned up
        assert 2 not in relay._channel_clients

    def test_relay_packet_to_peer(self, relay):
        addr1 = ("127.0.0.1", 6001)
        addr2 = ("127.0.0.1", 6002)
        relay.register_client(addr1, 1)
        relay.register_client(addr2, 1)
        # addr1 sends a packet
        import struct
        data = struct.pack(">I", 1) + b"opus_audio_data"
        relay.datagram_received(data, addr1)
        # addr2 should have received it
        assert len(relay.transport.sent) == 1
        assert relay.transport.sent[0][1] == addr2

    def test_no_relay_to_self(self, relay):
        addr = ("127.0.0.1", 7001)
        relay.register_client(addr, 1)
        import struct
        data = struct.pack(">I", 1) + b"audio"
        relay.datagram_received(data, addr)
        assert relay.transport.sent == []

    def test_short_packet_ignored(self, relay):
        relay.datagram_received(b"\x00\x00", ("127.0.0.1", 8000))
        # No crash, nothing sent
        assert relay.transport.sent == []

    def test_channel_change_re_registers(self, relay):
        addr = ("127.0.0.1", 9001)
        relay.register_client(addr, 1)
        relay.register_client(addr, 2)
        assert relay._client_channels[addr] == 2
        assert addr not in relay._channel_clients.get(1, set())
        assert addr in relay._channel_clients[2]

    def test_multiple_peers_in_channel(self, relay):
        addrs = [("127.0.0.1", 5000 + i) for i in range(4)]
        for a in addrs:
            relay.register_client(a, 10)
        import struct
        data = struct.pack(">I", 10) + b"audio"
        relay.datagram_received(data, addrs[0])
        # Should relay to the other 3 peers
        assert len(relay.transport.sent) == 3
        recipients = {s[1] for s in relay.transport.sent}
        assert addrs[0] not in recipients
        for a in addrs[1:]:
            assert a in recipients
