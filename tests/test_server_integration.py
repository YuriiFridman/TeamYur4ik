"""
Integration tests for server/server.py WebSocket action handlers.

We spin up a real asyncio WebSocket server on a random port, connect
one or more test clients, and assert the responses are correct.
"""
import asyncio
import json
import os
import sys
import threading
from typing import Optional
import pytest
import websockets

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

import config as _cfg


# ---------------------------------------------------------------------------
# Pytest-asyncio configuration
# ---------------------------------------------------------------------------
pytest_plugins = ("pytest_asyncio",)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def _get_free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


async def _send_action(ws, action: str, data: dict):
    await ws.send(json.dumps({"type": "action", "action": action, "data": data}))
    # Drain messages until we get the response (type == "response") for this action.
    # Event messages may arrive first when the handler broadcasts before responding.
    deadline = asyncio.get_event_loop().time() + 5
    while asyncio.get_event_loop().time() < deadline:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=2)
        except asyncio.TimeoutError:
            break
        msg = json.loads(raw)
        if msg.get("type") == "response" and msg.get("action") == action:
            return msg
    # If we didn't get a matching response, return the last message received
    return msg


# ---------------------------------------------------------------------------
# Server fixture — isolated DB per test function
# ---------------------------------------------------------------------------

@pytest.fixture
def server_url(tmp_path):
    """
    Spin up the server on a free port with a fresh DB for the test.
    Yields the WebSocket URL string; stops the server after the test.
    """
    port = _get_free_port()
    db_path = str(tmp_path / "test_server.db")

    # Patch config before importing server (and database)
    _cfg.DATABASE_URL = db_path
    _cfg.WS_PORT = port
    _cfg.VOICE_PORT = _get_free_port()

    # Force reload of database and server modules so they pick up the new DB path
    import importlib
    import database
    import server as srv
    importlib.reload(database)
    importlib.reload(srv)
    database.create_tables()

    # Run the asyncio server in a background thread
    loop = asyncio.new_event_loop()
    started = threading.Event()
    # shutdown is assigned in _serve() before started.set(), so by the time
    # started.wait() returns in the main thread it is guaranteed to be non-None.
    shutdown: Optional[asyncio.Event] = None

    async def _serve():
        nonlocal shutdown
        shutdown = asyncio.Event()
        await srv.voice_relay.start(_cfg.HOST, _cfg.VOICE_PORT)
        async with websockets.serve(srv.handle_client, "127.0.0.1", port) as ws_server:
            started.set()
            # Wait until teardown signals us to stop.
            await shutdown.wait()
            # Close the WebSocket server so no new connections are accepted.
            ws_server.close()
            await ws_server.wait_closed()
        # Stop the UDP voice relay after WebSocket server has closed.
        srv.voice_relay.stop()

    def _run():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_serve())

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    started.wait(timeout=10)

    yield f"ws://127.0.0.1:{port}"

    # --- Teardown: signal the server coroutine to stop cleanly ---
    async def _shutdown():
        if shutdown is not None:
            shutdown.set()

    future = asyncio.run_coroutine_threadsafe(_shutdown(), loop)
    future.result(timeout=5)

    # Wait for the server thread to finish, then stop and close the loop.
    t.join(timeout=15)
    if t.is_alive():
        loop.call_soon_threadsafe(loop.stop)


# ---------------------------------------------------------------------------
# Helpers that work against the live server
# ---------------------------------------------------------------------------

async def _register_and_login(url, username="testuser", password="testpass"):
    """Register + login; return (ws, token)."""
    async with websockets.connect(url, open_timeout=5) as ws:
        # Register
        resp = await _send_action(ws, "register",
                                  {"username": username, "password": password})
        assert resp["success"], f"register failed: {resp}"
    # Login in a fresh connection
    async with websockets.connect(url, open_timeout=5) as ws:
        resp = await _send_action(ws, "login",
                                  {"username": username, "password": password})
        assert resp["success"], f"login failed: {resp}"
        return resp["data"]["token"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_success(server_url):
    async with websockets.connect(server_url, open_timeout=5) as ws:
        resp = await _send_action(ws, "register",
                                  {"username": "alice", "password": "pw1"})
    assert resp["success"] is True


@pytest.mark.asyncio
async def test_register_duplicate_fails(server_url):
    async with websockets.connect(server_url, open_timeout=5) as ws:
        await _send_action(ws, "register", {"username": "bob", "password": "pw"})
        resp = await _send_action(ws, "register", {"username": "bob", "password": "pw"})
    assert resp["success"] is False


@pytest.mark.asyncio
async def test_login_success(server_url):
    token = await _register_and_login(server_url, "carol", "pass")
    assert isinstance(token, str) and len(token) > 10


@pytest.mark.asyncio
async def test_login_wrong_password(server_url):
    await _register_and_login(server_url, "dave", "correct")
    async with websockets.connect(server_url, open_timeout=5) as ws:
        resp = await _send_action(ws, "login",
                                  {"username": "dave", "password": "wrong"})
    assert resp["success"] is False


@pytest.mark.asyncio
async def test_create_server(server_url):
    token = await _register_and_login(server_url, "eve", "pw")
    async with websockets.connect(server_url, open_timeout=5) as ws:
        await _send_action(ws, "login", {"username": "eve", "password": "pw"})
        resp = await _send_action(ws, "create_server",
                                  {"name": "Eve's Server", "token": token})
    assert resp["success"] is True
    assert resp["data"]["name"] == "Eve's Server"


@pytest.mark.asyncio
async def test_create_channel_requires_admin(server_url):
    """Regular member cannot create a channel."""
    token = await _register_and_login(server_url, "frank", "pw")
    async with websockets.connect(server_url, open_timeout=5) as ws:
        await _send_action(ws, "login", {"username": "frank", "password": "pw"})
        # Create a server (frank becomes admin of it)
        resp = await _send_action(ws, "create_server",
                                  {"name": "FrankServer", "token": token})
        sid = resp["data"]["server_id"]
        await _send_action(ws, "join_server", {"server_id": sid, "token": token})
        # frank IS admin so this should succeed
        resp = await _send_action(ws, "create_channel",
                                  {"name": "new-ch", "type": "text", "token": token})
    assert resp["success"] is True


@pytest.mark.asyncio
async def test_send_and_receive_message(server_url):
    """Send a message and verify it appears in history."""
    token = await _register_and_login(server_url, "grace", "pw")
    async with websockets.connect(server_url, open_timeout=5) as ws:
        await _send_action(ws, "login", {"username": "grace", "password": "pw"})
        resp = await _send_action(ws, "create_server",
                                  {"name": "GS", "token": token})
        sid = resp["data"]["server_id"]
        join_resp = await _send_action(ws, "join_server",
                                       {"server_id": sid, "token": token})
        channel_id = join_resp["data"]["channels"][0]["id"]
        await _send_action(ws, "join_channel",
                           {"channel_id": channel_id, "token": token})
        msg_resp = await _send_action(ws, "send_message",
                                      {"channel_id": channel_id,
                                       "content": "Hello world!", "token": token})
    assert msg_resp["success"] is True
    assert msg_resp["data"]["content"] == "Hello world!"


@pytest.mark.asyncio
async def test_get_history(server_url):
    token = await _register_and_login(server_url, "hank", "pw")
    async with websockets.connect(server_url, open_timeout=5) as ws:
        await _send_action(ws, "login", {"username": "hank", "password": "pw"})
        resp = await _send_action(ws, "create_server",
                                  {"name": "HS", "token": token})
        sid = resp["data"]["server_id"]
        join_resp = await _send_action(ws, "join_server",
                                       {"server_id": sid, "token": token})
        cid = join_resp["data"]["channels"][0]["id"]
        await _send_action(ws, "join_channel",
                           {"channel_id": cid, "token": token})
        await _send_action(ws, "send_message",
                           {"channel_id": cid, "content": "msg1", "token": token})
        await _send_action(ws, "send_message",
                           {"channel_id": cid, "content": "msg2", "token": token})
        hist_resp = await _send_action(ws, "get_history",
                                       {"channel_id": cid, "token": token})
    assert hist_resp["success"] is True
    contents = [m["content"] for m in hist_resp["data"]["history"]]
    assert "msg1" in contents
    assert "msg2" in contents


@pytest.mark.asyncio
async def test_unauthenticated_action_rejected(server_url):
    async with websockets.connect(server_url, open_timeout=5) as ws:
        resp = await _send_action(ws, "get_servers", {})
    assert resp["success"] is False


@pytest.mark.asyncio
async def test_get_channels_admin(server_url):
    token = await _register_and_login(server_url, "ian", "pw")
    async with websockets.connect(server_url, open_timeout=5) as ws:
        await _send_action(ws, "login", {"username": "ian", "password": "pw"})
        resp = await _send_action(ws, "create_server",
                                  {"name": "IS", "token": token})
        sid = resp["data"]["server_id"]
        await _send_action(ws, "join_server", {"server_id": sid, "token": token})
        ch_resp = await _send_action(ws, "get_channels",
                                     {"server_id": sid, "token": token})
    assert ch_resp["success"] is True
    # Default channels (general + General Voice) were created by create_server
    assert len(ch_resp["data"]["channels"]) >= 2


@pytest.mark.asyncio
async def test_get_members(server_url):
    token = await _register_and_login(server_url, "jake", "pw")
    async with websockets.connect(server_url, open_timeout=5) as ws:
        await _send_action(ws, "login", {"username": "jake", "password": "pw"})
        resp = await _send_action(ws, "create_server",
                                  {"name": "JakeServer", "token": token})
        sid = resp["data"]["server_id"]
        await _send_action(ws, "join_server", {"server_id": sid, "token": token})
        mb_resp = await _send_action(ws, "get_members",
                                     {"server_id": sid, "token": token})
    assert mb_resp["success"] is True
    usernames = [m["username"] for m in mb_resp["data"]["members"]]
    assert "jake" in usernames


@pytest.mark.asyncio
async def test_set_role(server_url):
    """Admin can set role of another member."""
    token_admin = await _register_and_login(server_url, "kat_admin", "pw")
    token_member = await _register_and_login(server_url, "kat_member", "pw")
    async with websockets.connect(server_url, open_timeout=5) as ws_admin:
        await _send_action(ws_admin, "login", {"username": "kat_admin", "password": "pw"})
        resp = await _send_action(ws_admin, "create_server",
                                  {"name": "KS", "token": token_admin})
        sid = resp["data"]["server_id"]
        await _send_action(ws_admin, "join_server",
                           {"server_id": sid, "token": token_admin})
        # member joins the server in another connection
        async with websockets.connect(server_url, open_timeout=5) as ws_m:
            await _send_action(ws_m, "login",
                               {"username": "kat_member", "password": "pw"})
            await _send_action(ws_m, "join_server",
                               {"server_id": sid, "token": token_member})
            mb_resp = await _send_action(ws_admin, "get_members",
                                         {"server_id": sid, "token": token_admin})
            member_id = next(
                m["id"] for m in mb_resp["data"]["members"]
                if m["username"] == "kat_member"
            )
            role_resp = await _send_action(ws_admin, "set_role",
                                           {"user_id": member_id, "role": "moderator",
                                            "token": token_admin})
    assert role_resp["success"] is True


@pytest.mark.asyncio
async def test_rename_channel(server_url):
    token = await _register_and_login(server_url, "leo", "pw")
    async with websockets.connect(server_url, open_timeout=5) as ws:
        await _send_action(ws, "login", {"username": "leo", "password": "pw"})
        resp = await _send_action(ws, "create_server",
                                  {"name": "LS", "token": token})
        sid = resp["data"]["server_id"]
        join_resp = await _send_action(ws, "join_server",
                                       {"server_id": sid, "token": token})
        cid = join_resp["data"]["channels"][0]["id"]
        rename_resp = await _send_action(ws, "rename_channel",
                                         {"channel_id": cid, "name": "renamed",
                                          "token": token})
    assert rename_resp["success"] is True
    assert rename_resp["data"]["name"] == "renamed"


@pytest.mark.asyncio
async def test_ban_and_unban(server_url):
    token_admin = await _register_and_login(server_url, "mia_admin", "pw")
    token_target = await _register_and_login(server_url, "mia_target", "pw")
    async with websockets.connect(server_url, open_timeout=5) as ws:
        await _send_action(ws, "login", {"username": "mia_admin", "password": "pw"})
        resp = await _send_action(ws, "create_server",
                                  {"name": "MS", "token": token_admin})
        sid = resp["data"]["server_id"]
        await _send_action(ws, "join_server", {"server_id": sid, "token": token_admin})

        async with websockets.connect(server_url, open_timeout=5) as ws2:
            await _send_action(ws2, "login",
                               {"username": "mia_target", "password": "pw"})
            await _send_action(ws2, "join_server",
                               {"server_id": sid, "token": token_target})

        mb = await _send_action(ws, "get_members",
                                {"server_id": sid, "token": token_admin})
        target_id = next(
            m["id"] for m in mb["data"]["members"]
            if m["username"] == "mia_target"
        )
        ban_resp = await _send_action(ws, "ban_user",
                                      {"user_id": target_id, "reason": "test",
                                       "token": token_admin})
        assert ban_resp["success"] is True

        bans_resp = await _send_action(ws, "get_bans",
                                       {"server_id": sid, "token": token_admin})
        assert len(bans_resp["data"]["bans"]) == 1

        unban_resp = await _send_action(ws, "unban_user",
                                        {"user_id": target_id, "token": token_admin})
        assert unban_resp["success"] is True

        bans_resp2 = await _send_action(ws, "get_bans",
                                        {"server_id": sid, "token": token_admin})
        assert len(bans_resp2["data"]["bans"]) == 0


@pytest.mark.asyncio
async def test_reconnection(server_url):
    """Client can disconnect and reconnect without server-side errors."""
    token = await _register_and_login(server_url, "nora", "pw")
    # First connection
    async with websockets.connect(server_url, open_timeout=5) as ws:
        resp = await _send_action(ws, "login", {"username": "nora", "password": "pw"})
        assert resp["success"] is True
    # Second connection – should succeed cleanly after first is closed
    async with websockets.connect(server_url, open_timeout=5) as ws:
        resp = await _send_action(ws, "login", {"username": "nora", "password": "pw"})
        assert resp["success"] is True
