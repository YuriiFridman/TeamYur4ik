import sqlite3
import bcrypt
import logging
from typing import Optional, List, Dict, Any

import config

logger = logging.getLogger(__name__)


def get_connection():
    """Return a new SQLite connection with Row factory for dict-like access."""
    conn = sqlite3.connect(config.DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    """Create all database tables if they do not already exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                avatar_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                owner_id INTEGER NOT NULL,
                icon_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'text',
                is_private INTEGER DEFAULT 0,
                password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers(id)
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (channel_id) REFERENCES channels(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS server_members (
                server_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (server_id, user_id),
                FOREIGN KEY (server_id) REFERENCES servers(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS bans (
                server_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                banned_by INTEGER NOT NULL,
                reason TEXT,
                banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (server_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS channel_mutes (
                channel_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                muted_by INTEGER NOT NULL,
                PRIMARY KEY (channel_id, user_id)
            );
        """)
        conn.commit()
    logger.info("Database tables created")


def register_user(username: str, password: str, email: str = None) -> Optional[int]:
    """
    Register a new user with a bcrypt-hashed password.
    Returns the new user_id, or None if the username is already taken or input is invalid.
    """
    if not username or not password:
        return None
    try:
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
                (username, password_hash, email)
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        logger.warning(f"Username '{username}' already taken")
        return None
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        return None


def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """
    Verify username and password.
    Returns dict with 'id' and 'username' on success, or None on failure.
    """
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,)
            ).fetchone()
            if row and bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
                return {"id": row["id"], "username": row["username"]}
        return None
    except Exception as e:
        logger.error(f"Error authenticating user: {e}")
        return None


def get_servers(user_id: int) -> List[Dict]:
    """Return all servers that user_id is a member of."""
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT s.id, s.name, s.owner_id, s.icon_url FROM servers s
                   JOIN server_members sm ON s.id = sm.server_id
                   WHERE sm.user_id = ?""",
                (user_id,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error getting servers: {e}")
        return []


def create_server(name: str, owner_id: int) -> int:
    """Create a new server and return its id."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO servers (name, owner_id) VALUES (?, ?)",
            (name, owner_id)
        )
        conn.commit()
        return cursor.lastrowid


def create_channel(
    server_id: int,
    name: str,
    type: str = 'text',
    is_private: int = 0,
    password: str = None
) -> int:
    """
    Create a channel in server_id.
    Hashes channel password with bcrypt if provided.
    Returns new channel id.
    """
    password_hash = None
    if password:
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO channels (server_id, name, type, is_private, password_hash) VALUES (?, ?, ?, ?, ?)",
            (server_id, name, type, is_private, password_hash)
        )
        conn.commit()
        return cursor.lastrowid


def get_channels(server_id: int) -> List[Dict]:
    """Return all channels for server_id (excludes password hashes)."""
    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, server_id, name, type, is_private FROM channels WHERE server_id = ? ORDER BY id",
                (server_id,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error getting channels: {e}")
        return []


def save_message(channel_id: int, user_id: int, content: str) -> int:
    """Persist a chat message and return its id."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO messages (channel_id, user_id, content) VALUES (?, ?, ?)",
            (channel_id, user_id, content)
        )
        conn.commit()
        return cursor.lastrowid


def get_message_history(channel_id: int, limit: int = 50) -> List[Dict]:
    """
    Return the most recent `limit` messages for channel_id,
    ordered oldest-first for display purposes.
    """
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT m.id, m.channel_id, m.user_id, u.username, m.content, m.created_at
                   FROM messages m JOIN users u ON m.user_id = u.id
                   WHERE m.channel_id = ? ORDER BY m.created_at DESC LIMIT ?""",
                (channel_id, limit)
            ).fetchall()
            # Reverse so oldest message appears first in the chat window
            return list(reversed([dict(r) for r in rows]))
    except Exception as e:
        logger.error(f"Error getting message history: {e}")
        return []


def ban_user(server_id: int, user_id: int, banned_by: int, reason: str = None):
    """Insert or replace a ban record for user_id in server_id."""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO bans (server_id, user_id, banned_by, reason) VALUES (?, ?, ?, ?)",
                (server_id, user_id, banned_by, reason)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error banning user: {e}")


def is_banned(server_id: int, user_id: int) -> bool:
    """Return True if user_id has an active ban in server_id."""
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM bans WHERE server_id = ? AND user_id = ?",
                (server_id, user_id)
            ).fetchone()
            return row is not None
    except Exception as e:
        logger.error(f"Error checking ban: {e}")
        return False


def get_user_role(server_id: int, user_id: int) -> str:
    """Return the role string for user_id in server_id, defaulting to 'member'."""
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT role FROM server_members WHERE server_id = ? AND user_id = ?",
                (server_id, user_id)
            ).fetchone()
            return row["role"] if row else "member"
    except Exception as e:
        logger.error(f"Error getting user role: {e}")
        return "member"


def set_user_role(server_id: int, user_id: int, role: str):
    """Update the role for user_id in server_id."""
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE server_members SET role = ? WHERE server_id = ? AND user_id = ?",
                (role, server_id, user_id)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error setting user role: {e}")


def get_server_members(server_id: int) -> List[Dict]:
    """Return list of member dicts (id, username, role) for server_id."""
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT u.id, u.username, sm.role FROM server_members sm
                   JOIN users u ON sm.user_id = u.id
                   WHERE sm.server_id = ?""",
                (server_id,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error getting server members: {e}")
        return []


def kick_user(server_id: int, user_id: int):
    """Remove user_id from server_id's member list."""
    try:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM server_members WHERE server_id = ? AND user_id = ?",
                (server_id, user_id)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error kicking user: {e}")


def delete_channel(channel_id: int):
    """Delete a channel and all its messages."""
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM messages WHERE channel_id = ?", (channel_id,))
            conn.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
            conn.commit()
    except Exception as e:
        logger.error(f"Error deleting channel: {e}")


def delete_server(server_id: int):
    """
    Delete a server and cascade-delete all related data:
    members, bans, channel messages, channels, and the server record itself.
    """
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM server_members WHERE server_id = ?", (server_id,))
            conn.execute("DELETE FROM bans WHERE server_id = ?", (server_id,))
            # Delete all messages in every channel of this server using a single subquery
            conn.execute(
                "DELETE FROM messages WHERE channel_id IN "
                "(SELECT id FROM channels WHERE server_id = ?)",
                (server_id,),
            )
            conn.execute("DELETE FROM channels WHERE server_id = ?", (server_id,))
            conn.execute("DELETE FROM servers WHERE id = ?", (server_id,))
            conn.commit()
    except Exception as e:
        logger.error(f"Error deleting server: {e}")


def join_server(server_id: int, user_id: int):
    """Add user_id as a member of server_id (silently ignored if already a member)."""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO server_members (server_id, user_id) VALUES (?, ?)",
                (server_id, user_id)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error joining server: {e}")


def get_bans(server_id: int) -> List[Dict]:
    """Return all active ban records for server_id, including the banned username."""
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT b.server_id, b.user_id, u.username, b.reason, b.banned_at
                   FROM bans b JOIN users u ON b.user_id = u.id
                   WHERE b.server_id = ?""",
                (server_id,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error getting bans: {e}")
        return []


def unban_user(server_id: int, user_id: int):
    """Remove the ban for user_id in server_id."""
    try:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM bans WHERE server_id = ? AND user_id = ?",
                (server_id, user_id)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error unbanning user: {e}")
