"""
Unit tests for server/database.py

Uses a fresh in-memory SQLite database for every test so tests
are fully isolated and never touch the production DB file.
"""
import sys
import os
import pytest

# Make the server package importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

# Redirect the database to an in-memory SQLite DB before importing anything
import config as _cfg
_cfg.DATABASE_URL = ":memory:"

import database


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch, tmp_path):
    """
    Before each test: point the database module at a brand-new temp file
    and create all tables.  This guarantees isolation between tests.
    """
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(_cfg, "DATABASE_URL", db_path)
    # Patch the module-level get_connection so it always uses the patched URL
    import importlib
    importlib.reload(database)
    database.create_tables()
    yield
    # Cleanup is automatic – tmp_path is removed by pytest


# ---------------------------------------------------------------------------
# User registration and authentication
# ---------------------------------------------------------------------------

class TestUserRegistration:
    def test_register_new_user_returns_id(self):
        uid = database.register_user("alice", "password123")
        assert isinstance(uid, int)
        assert uid > 0

    def test_register_duplicate_username_returns_none(self):
        database.register_user("bob", "pass1")
        result = database.register_user("bob", "pass2")
        assert result is None

    def test_register_empty_username_returns_none(self):
        assert database.register_user("", "password") is None

    def test_register_empty_password_returns_none(self):
        assert database.register_user("charlie", "") is None


class TestUserAuthentication:
    def test_correct_credentials_return_user(self):
        database.register_user("diana", "secret")
        user = database.authenticate_user("diana", "secret")
        assert user is not None
        assert user["username"] == "diana"

    def test_wrong_password_returns_none(self):
        database.register_user("eve", "correct")
        assert database.authenticate_user("eve", "wrong") is None

    def test_unknown_user_returns_none(self):
        assert database.authenticate_user("nobody", "pass") is None


# ---------------------------------------------------------------------------
# Servers
# ---------------------------------------------------------------------------

class TestServers:
    def _setup_user(self, name="owner", pw="pw"):
        uid = database.register_user(name, pw)
        return uid

    def test_create_server_returns_id(self):
        uid = self._setup_user()
        sid = database.create_server("MyServer", uid)
        assert isinstance(sid, int) and sid > 0

    def test_get_servers_empty_before_join(self):
        uid = self._setup_user()
        database.create_server("Orphan", uid)
        # User hasn't joined yet → list should be empty
        servers = database.get_servers(uid)
        assert servers == []

    def test_get_servers_after_join(self):
        uid = self._setup_user()
        sid = database.create_server("Joined", uid)
        database.join_server(sid, uid)
        servers = database.get_servers(uid)
        assert len(servers) == 1
        assert servers[0]["name"] == "Joined"

    def test_join_server_idempotent(self):
        uid = self._setup_user()
        sid = database.create_server("S", uid)
        database.join_server(sid, uid)
        database.join_server(sid, uid)  # should not raise
        assert len(database.get_server_members(sid)) == 1

    def test_delete_server_cascades(self):
        uid = self._setup_user()
        sid = database.create_server("ToDelete", uid)
        database.join_server(sid, uid)
        chid = database.create_channel(sid, "general", "text")
        database.save_message(chid, uid, "hello")
        database.delete_server(sid)
        # After deletion the server should not appear in member's server list
        assert database.get_servers(uid) == []
        # Channels should be gone
        assert database.get_channels(sid) == []


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------

class TestChannels:
    def _setup(self):
        uid = database.register_user("owner", "pw")
        sid = database.create_server("S", uid)
        database.join_server(sid, uid)
        return uid, sid

    def test_create_text_channel(self):
        uid, sid = self._setup()
        cid = database.create_channel(sid, "general", "text")
        channels = database.get_channels(sid)
        assert len(channels) == 1
        assert channels[0]["name"] == "general"
        assert channels[0]["type"] == "text"

    def test_create_voice_channel(self):
        uid, sid = self._setup()
        database.create_channel(sid, "Voice", "voice")
        channels = database.get_channels(sid)
        assert channels[0]["type"] == "voice"

    def test_delete_channel(self):
        uid, sid = self._setup()
        cid = database.create_channel(sid, "temp", "text")
        database.delete_channel(cid)
        assert database.get_channels(sid) == []

    def test_rename_channel(self):
        uid, sid = self._setup()
        cid = database.create_channel(sid, "old-name", "text")
        database.rename_channel(cid, "new-name")
        channels = database.get_channels(sid)
        assert channels[0]["name"] == "new-name"

    def test_delete_channel_removes_messages(self):
        uid, sid = self._setup()
        cid = database.create_channel(sid, "chat", "text")
        database.save_message(cid, uid, "bye")
        database.delete_channel(cid)
        # Messages for the deleted channel should be gone
        assert database.get_message_history(cid) == []


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

class TestMessages:
    def _setup(self):
        uid = database.register_user("user", "pw")
        sid = database.create_server("S", uid)
        database.join_server(sid, uid)
        cid = database.create_channel(sid, "general", "text")
        return uid, sid, cid

    def test_save_message_returns_id(self):
        uid, sid, cid = self._setup()
        mid = database.save_message(cid, uid, "Hello!")
        assert isinstance(mid, int) and mid > 0

    def test_get_message_history_order(self):
        uid, sid, cid = self._setup()
        database.save_message(cid, uid, "first")
        database.save_message(cid, uid, "second")
        history = database.get_message_history(cid)
        assert len(history) == 2
        # Both messages must be present; order is oldest-first by id
        contents = [m["content"] for m in history]
        assert "first" in contents
        assert "second" in contents
        # The row saved first must have a lower id, so it appears first
        ids = [m["id"] for m in history]
        assert ids[0] < ids[1]

    def test_message_history_respects_limit(self):
        uid, sid, cid = self._setup()
        for i in range(10):
            database.save_message(cid, uid, f"msg{i}")
        assert len(database.get_message_history(cid, limit=5)) == 5

    def test_message_history_contains_username(self):
        uid, sid, cid = self._setup()
        database.save_message(cid, uid, "test msg")
        history = database.get_message_history(cid)
        assert history[0]["username"] == "user"


# ---------------------------------------------------------------------------
# Roles and permissions
# ---------------------------------------------------------------------------

class TestRoles:
    def _setup_two_users(self):
        uid1 = database.register_user("admin_user", "pw")
        uid2 = database.register_user("member_user", "pw")
        sid = database.create_server("S", uid1)
        database.join_server(sid, uid1)
        database.join_server(sid, uid2)
        return uid1, uid2, sid

    def test_default_role_is_member(self):
        uid1, uid2, sid = self._setup_two_users()
        assert database.get_user_role(sid, uid2) == "member"

    def test_set_role_admin(self):
        uid1, uid2, sid = self._setup_two_users()
        database.set_user_role(sid, uid1, "admin")
        assert database.get_user_role(sid, uid1) == "admin"

    def test_set_role_moderator(self):
        uid1, uid2, sid = self._setup_two_users()
        database.set_user_role(sid, uid2, "moderator")
        assert database.get_user_role(sid, uid2) == "moderator"

    def test_get_user_role_unknown_user_defaults_to_member(self):
        uid1, uid2, sid = self._setup_two_users()
        assert database.get_user_role(sid, 99999) == "member"


# ---------------------------------------------------------------------------
# Bans
# ---------------------------------------------------------------------------

class TestBans:
    def _setup(self):
        uid1 = database.register_user("admin_b", "pw")
        uid2 = database.register_user("banned_b", "pw")
        sid = database.create_server("S", uid1)
        database.join_server(sid, uid1)
        database.join_server(sid, uid2)
        return uid1, uid2, sid

    def test_ban_user(self):
        uid1, uid2, sid = self._setup()
        database.ban_user(sid, uid2, uid1, "spam")
        assert database.is_banned(sid, uid2) is True

    def test_unban_user(self):
        uid1, uid2, sid = self._setup()
        database.ban_user(sid, uid2, uid1)
        database.unban_user(sid, uid2)
        assert database.is_banned(sid, uid2) is False

    def test_is_banned_false_by_default(self):
        uid1, uid2, sid = self._setup()
        assert database.is_banned(sid, uid2) is False

    def test_get_bans_returns_list(self):
        uid1, uid2, sid = self._setup()
        database.ban_user(sid, uid2, uid1, "reason")
        bans = database.get_bans(sid)
        assert len(bans) == 1
        assert bans[0]["username"] == "banned_b"


# ---------------------------------------------------------------------------
# Kick
# ---------------------------------------------------------------------------

class TestKick:
    def test_kick_removes_from_members(self):
        uid1 = database.register_user("admin_k", "pw")
        uid2 = database.register_user("target_k", "pw")
        sid = database.create_server("S", uid1)
        database.join_server(sid, uid1)
        database.join_server(sid, uid2)
        database.kick_user(sid, uid2)
        members = database.get_server_members(sid)
        ids = [m["id"] for m in members]
        assert uid2 not in ids
