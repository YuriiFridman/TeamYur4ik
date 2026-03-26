import asyncio
import json
import logging
import websockets
from websockets.server import WebSocketServerProtocol
from typing import Dict, Optional, Set
from dataclasses import dataclass, field

import config
import database
import auth
from voice_relay import VoiceRelay

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ClientConnection:
    """Represents a single connected WebSocket client and its current state."""
    websocket: WebSocketServerProtocol
    user_id: Optional[int] = None
    username: Optional[str] = None
    current_channel_id: Optional[int] = None
    server_id: Optional[int] = None
    is_muted: bool = False
    is_deafened: bool = False


# Global state: maps user_id -> ClientConnection for all currently connected users
connected_clients: Dict[int, ClientConnection] = {}
voice_relay = VoiceRelay()


# ---------------------------------------------------------------------------
# Helper send functions
# ---------------------------------------------------------------------------

async def send_response(ws, action: str, success: bool, data: dict = None):
    """Send a response message back to the requesting client."""
    msg = {"type": "response", "action": action, "success": success, "data": data or {}}
    await ws.send(json.dumps(msg))


async def send_event(ws, event: str, data: dict = None):
    """Push a server-initiated event to a client."""
    msg = {"type": "event", "event": event, "data": data or {}}
    await ws.send(json.dumps(msg))


async def broadcast_to_channel(channel_id: int, event_type: str, data: dict, exclude: int = None):
    """Broadcast an event to every client currently joined to channel_id."""
    for uid, client in list(connected_clients.items()):
        if client.current_channel_id == channel_id and uid != exclude:
            try:
                await send_event(client.websocket, event_type, data)
            except Exception as e:
                logger.error(f"Error broadcasting to channel {channel_id}: {e}")


async def broadcast_to_server(server_id: int, event_type: str, data: dict, exclude: int = None):
    """Broadcast an event to every client currently in server_id."""
    for uid, client in list(connected_clients.items()):
        if client.server_id == server_id and uid != exclude:
            try:
                await send_event(client.websocket, event_type, data)
            except Exception as e:
                logger.error(f"Error broadcasting to server {server_id}: {e}")


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------

async def handle_login(client: ClientConnection, data: dict) -> bool:
    """Authenticate a user by JWT token or username/password.

    Token-based auth is used by the persistent NetworkClient session: the
    client obtains a token during the initial (LoginWorker) connection and
    then authenticates all subsequent reconnections with that token so the
    user's password never has to be stored client-side.
    """
    # --- Token-based authentication (preferred for reconnection) ---
    token_str = data.get("token", "")
    if token_str:
        token_data = auth.verify_token(token_str)
        if token_data:
            client.user_id = token_data["user_id"]
            client.username = token_data["username"]
            connected_clients[client.user_id] = client
            await send_response(
                client.websocket, "login", True,
                {"token": token_str,
                 "user_id": client.user_id,
                 "username": client.username}
            )
            return True
        else:
            await send_response(client.websocket, "login", False,
                                {"error": "Token expired or invalid"})
            return False

    # --- Username + password authentication ---
    username = data.get("username", "")
    password = data.get("password", "")
    user = database.authenticate_user(username, password)
    if user:
        token = auth.create_token(user["id"], user["username"])
        client.user_id = user["id"]
        client.username = user["username"]
        connected_clients[user["id"]] = client
        await send_response(
            client.websocket, "login", True,
            {"token": token, "user_id": user["id"], "username": user["username"]}
        )
        return True
    else:
        await send_response(client.websocket, "login", False,
                            {"error": "Invalid username or password"})
        return False


async def handle_register(client: ClientConnection, data: dict):
    """Register a new user account."""
    user_id = database.register_user(
        data.get("username", ""),
        data.get("password", ""),
        data.get("email")
    )
    if user_id:
        await send_response(client.websocket, "register", True,
                            {"message": "Registration successful"})
    else:
        await send_response(client.websocket, "register", False,
                            {"error": "Username already taken or invalid"})


async def handle_get_servers(client: ClientConnection, data: dict):
    """Return all servers that the current user belongs to."""
    servers = database.get_servers(client.user_id)
    await send_response(client.websocket, "get_servers", True, {"servers": servers})


async def handle_create_server(client: ClientConnection, data: dict):
    """Create a new server with a default text and voice channel."""
    name = data.get("name", "").strip()
    if not name:
        await send_response(client.websocket, "create_server", False,
                            {"error": "Server name required"})
        return
    server_id = database.create_server(name, client.user_id)
    # Creator automatically joins and becomes admin
    database.join_server(server_id, client.user_id)
    database.set_user_role(server_id, client.user_id, "admin")
    # Provision default channels
    database.create_channel(server_id, "general", "text")
    database.create_channel(server_id, "General Voice", "voice")
    await send_response(client.websocket, "create_server", True,
                        {"server_id": server_id, "name": name})


async def handle_join_server(client: ClientConnection, data: dict):
    """Join an existing server and receive its channel/member list."""
    server_id = data.get("server_id")
    if not server_id:
        await send_response(client.websocket, "join_server", False,
                            {"error": "server_id required"})
        return
    if database.is_banned(server_id, client.user_id):
        await send_response(client.websocket, "join_server", False,
                            {"error": "You are banned from this server"})
        return
    database.join_server(server_id, client.user_id)
    client.server_id = server_id
    channels = database.get_channels(server_id)
    members = database.get_server_members(server_id)
    await send_response(client.websocket, "join_server", True,
                        {"channels": channels, "members": members})
    await broadcast_to_server(
        server_id, "user_joined_server",
        {"user_id": client.user_id, "username": client.username},
        exclude=client.user_id
    )


async def handle_leave_server(client: ClientConnection, data: dict):
    """Leave the current server and clean up channel membership."""
    server_id = client.server_id
    if client.current_channel_id:
        await broadcast_to_channel(
            client.current_channel_id, "user_left_channel",
            {"user_id": client.user_id, "username": client.username}
        )
        client.current_channel_id = None
    client.server_id = None
    if server_id:
        await broadcast_to_server(
            server_id, "user_left_server",
            {"user_id": client.user_id, "username": client.username}
        )
    await send_response(client.websocket, "leave_server", True, {})


async def handle_join_channel(client: ClientConnection, data: dict):
    """Join a channel; automatically leaves the previous one and sends message history."""
    channel_id = data.get("channel_id")
    if not channel_id:
        await send_response(client.websocket, "join_channel", False,
                            {"error": "channel_id required"})
        return
    # Notify old channel that this user is leaving
    if client.current_channel_id and client.current_channel_id != channel_id:
        await broadcast_to_channel(
            client.current_channel_id, "user_left_channel",
            {"user_id": client.user_id, "username": client.username}
        )
    client.current_channel_id = channel_id
    history = database.get_message_history(channel_id)
    await send_response(client.websocket, "join_channel", True,
                        {"channel_id": channel_id, "history": history})
    await broadcast_to_channel(
        channel_id, "user_joined_channel",
        {"user_id": client.user_id, "username": client.username},
        exclude=client.user_id
    )


async def handle_leave_channel(client: ClientConnection, data: dict):
    """Leave the current channel."""
    channel_id = client.current_channel_id
    if channel_id:
        await broadcast_to_channel(
            channel_id, "user_left_channel",
            {"user_id": client.user_id, "username": client.username}
        )
    client.current_channel_id = None
    await send_response(client.websocket, "leave_channel", True, {})


async def handle_send_message(client: ClientConnection, data: dict):
    """Save a text message and broadcast it to all users in the channel."""
    channel_id = data.get("channel_id") or client.current_channel_id
    content = data.get("content", "").strip()
    if not channel_id or not content:
        await send_response(client.websocket, "send_message", False,
                            {"error": "channel_id and content required"})
        return
    msg_id = database.save_message(channel_id, client.user_id, content)
    msg_data = {
        "id": msg_id,
        "channel_id": channel_id,
        "user_id": client.user_id,
        "username": client.username,
        "content": content
    }
    await broadcast_to_channel(channel_id, "new_message", msg_data)
    await send_response(client.websocket, "send_message", True, msg_data)


async def handle_get_history(client: ClientConnection, data: dict):
    """Return message history for a channel."""
    channel_id = data.get("channel_id") or client.current_channel_id
    limit = data.get("limit", 50)
    history = database.get_message_history(channel_id, limit)
    await send_response(client.websocket, "get_history", True, {"history": history})


async def handle_kick_user(client: ClientConnection, data: dict):
    """Kick a user from the server (requires admin or moderator role)."""
    server_id = client.server_id
    target_id = data.get("user_id")
    role = database.get_user_role(server_id, client.user_id)
    if role not in ("admin", "moderator"):
        await send_response(client.websocket, "kick_user", False,
                            {"error": "Insufficient permissions"})
        return
    database.kick_user(server_id, target_id)
    # Notify the kicked user directly if they are online
    if target_id in connected_clients:
        target = connected_clients[target_id]
        await send_event(target.websocket, "kicked", {"server_id": server_id})
        target.server_id = None
        target.current_channel_id = None
    await broadcast_to_server(server_id, "user_kicked", {"user_id": target_id})
    await send_response(client.websocket, "kick_user", True, {})


async def handle_ban_user(client: ClientConnection, data: dict):
    """Ban a user from the server, then kick them if online (requires admin or moderator)."""
    server_id = client.server_id
    target_id = data.get("user_id")
    reason = data.get("reason", "")
    role = database.get_user_role(server_id, client.user_id)
    if role not in ("admin", "moderator"):
        await send_response(client.websocket, "ban_user", False,
                            {"error": "Insufficient permissions"})
        return
    database.ban_user(server_id, target_id, client.user_id, reason)
    database.kick_user(server_id, target_id)
    if target_id in connected_clients:
        target = connected_clients[target_id]
        await send_event(target.websocket, "banned", {"server_id": server_id, "reason": reason})
        target.server_id = None
        target.current_channel_id = None
    await broadcast_to_server(server_id, "user_banned", {"user_id": target_id})
    await send_response(client.websocket, "ban_user", True, {})


async def handle_mute_user(client: ClientConnection, data: dict):
    """Server-side mute: set is_muted flag on target and send muted event."""
    target_id = data.get("user_id")
    if target_id in connected_clients:
        connected_clients[target_id].is_muted = True
        await send_event(connected_clients[target_id].websocket, "muted", {})
    await send_response(client.websocket, "mute_user", True, {})


async def handle_set_role(client: ClientConnection, data: dict):
    """Change a user's role in the current server (admin only)."""
    server_id = client.server_id
    target_id = data.get("user_id")
    new_role = data.get("role", "member")
    role = database.get_user_role(server_id, client.user_id)
    if role != "admin":
        await send_response(client.websocket, "set_role", False,
                            {"error": "Only admins can set roles"})
        return
    database.set_user_role(server_id, target_id, new_role)
    await broadcast_to_server(server_id, "role_updated",
                               {"user_id": target_id, "role": new_role})
    await send_response(client.websocket, "set_role", True, {})


async def handle_create_channel(client: ClientConnection, data: dict):
    """Create a new channel in the current server (requires admin or moderator)."""
    server_id = client.server_id
    name = data.get("name", "").strip()
    ch_type = data.get("type", "text")
    is_private = data.get("is_private", 0)
    password = data.get("password")
    role = database.get_user_role(server_id, client.user_id)
    if role not in ("admin", "moderator"):
        await send_response(client.websocket, "create_channel", False,
                            {"error": "Insufficient permissions"})
        return
    ch_id = database.create_channel(server_id, name, ch_type, is_private, password)
    ch_data = {"id": ch_id, "name": name, "type": ch_type, "is_private": is_private}
    await broadcast_to_server(server_id, "channel_created", ch_data)
    await send_response(client.websocket, "create_channel", True, ch_data)


async def handle_delete_channel(client: ClientConnection, data: dict):
    """Delete a channel and its messages (requires admin or moderator)."""
    server_id = client.server_id
    channel_id = data.get("channel_id")
    role = database.get_user_role(server_id, client.user_id)
    if role not in ("admin", "moderator"):
        await send_response(client.websocket, "delete_channel", False,
                            {"error": "Insufficient permissions"})
        return
    database.delete_channel(channel_id)
    await broadcast_to_server(server_id, "channel_deleted", {"channel_id": channel_id})
    await send_response(client.websocket, "delete_channel", True, {})


async def handle_delete_server(client: ClientConnection, data: dict):
    """Delete the entire server and notify all connected members (admin only)."""
    server_id = client.server_id
    role = database.get_user_role(server_id, client.user_id)
    if role != "admin":
        await send_response(client.websocket, "delete_server", False,
                            {"error": "Only admins can delete servers"})
        return
    await broadcast_to_server(server_id, "server_deleted", {"server_id": server_id})
    # Clear server state for all connected members
    for uid, c in list(connected_clients.items()):
        if c.server_id == server_id:
            c.server_id = None
            c.current_channel_id = None
    database.delete_server(server_id)
    await send_response(client.websocket, "delete_server", True, {})


async def handle_rename_channel(client: ClientConnection, data: dict):
    """Rename an existing channel (requires admin or moderator)."""
    server_id = client.server_id
    channel_id = data.get("channel_id")
    new_name = data.get("name", "").strip()
    if not channel_id or not new_name:
        await send_response(client.websocket, "rename_channel", False,
                            {"error": "channel_id and name required"})
        return
    role = database.get_user_role(server_id, client.user_id)
    if role not in ("admin", "moderator"):
        await send_response(client.websocket, "rename_channel", False,
                            {"error": "Insufficient permissions"})
        return
    database.rename_channel(channel_id, new_name)
    await broadcast_to_server(server_id, "channel_renamed",
                               {"channel_id": channel_id, "name": new_name})
    await send_response(client.websocket, "rename_channel", True,
                        {"channel_id": channel_id, "name": new_name})


async def handle_get_channels_admin(client: ClientConnection, data: dict):
    """Return all channels for a server (admin panel use)."""
    server_id = data.get("server_id") or client.server_id
    if not server_id:
        await send_response(client.websocket, "get_channels", False,
                            {"error": "server_id required"})
        return
    channels = database.get_channels(server_id)
    await send_response(client.websocket, "get_channels", True, {"channels": channels})


async def handle_get_members(client: ClientConnection, data: dict):
    """Return all members for a server (admin panel use)."""
    server_id = data.get("server_id") or client.server_id
    if not server_id:
        await send_response(client.websocket, "get_members", False,
                            {"error": "server_id required"})
        return
    members = database.get_server_members(server_id)
    await send_response(client.websocket, "get_members", True, {"members": members})


async def handle_get_bans(client: ClientConnection, data: dict):
    """Return the ban list for a server (admin panel use)."""
    server_id = data.get("server_id") or client.server_id
    if not server_id:
        await send_response(client.websocket, "get_bans", False,
                            {"error": "server_id required"})
        return
    bans = database.get_bans(server_id)
    await send_response(client.websocket, "get_bans", True, {"bans": bans})


async def handle_unban_user(client: ClientConnection, data: dict):
    """Remove a ban from server (requires admin or moderator)."""
    server_id = client.server_id
    target_id = data.get("user_id")
    role = database.get_user_role(server_id, client.user_id)
    if role not in ("admin", "moderator"):
        await send_response(client.websocket, "unban_user", False,
                            {"error": "Insufficient permissions"})
        return
    database.unban_user(server_id, target_id)
    await send_response(client.websocket, "unban_user", True, {})


# Map action strings to their handler coroutines
ACTION_HANDLERS = {
    "login": handle_login,
    "register": handle_register,
    "get_servers": handle_get_servers,
    "create_server": handle_create_server,
    "join_server": handle_join_server,
    "leave_server": handle_leave_server,
    "join_channel": handle_join_channel,
    "leave_channel": handle_leave_channel,
    "send_message": handle_send_message,
    "get_history": handle_get_history,
    "kick_user": handle_kick_user,
    "ban_user": handle_ban_user,
    "mute_user": handle_mute_user,
    "set_role": handle_set_role,
    "create_channel": handle_create_channel,
    "delete_channel": handle_delete_channel,
    "rename_channel": handle_rename_channel,
    "delete_server": handle_delete_server,
    "get_channels": handle_get_channels_admin,
    "get_members": handle_get_members,
    "get_bans": handle_get_bans,
    "unban_user": handle_unban_user,
}


# ---------------------------------------------------------------------------
# WebSocket connection handler
# ---------------------------------------------------------------------------

async def handle_client(websocket: WebSocketServerProtocol):
    """
    Main per-client coroutine.
    Reads incoming messages in a loop, dispatches to action handlers,
    and cleans up on disconnect.
    """
    client = ClientConnection(websocket=websocket)
    logger.info(f"New connection from {websocket.remote_address}")
    try:
        async for raw_msg in websocket:
            try:
                msg = json.loads(raw_msg)
            except json.JSONDecodeError:
                await send_response(websocket, "error", False, {"error": "Invalid JSON"})
                continue

            msg_type = msg.get("type")
            if msg_type == "action":
                action = msg.get("action")
                data = msg.get("data", {})

                # Actions other than login/register require an authenticated session.
                # Validate the JWT token on every request to enforce session expiry.
                if action not in ("login", "register"):
                    token = data.get("token")
                    if token:
                        token_data = auth.verify_token(token)
                        if token_data:
                            # Refresh in-memory identity from the token on each request
                            client.user_id = token_data["user_id"]
                            client.username = token_data["username"]
                            connected_clients[client.user_id] = client
                        else:
                            await send_response(websocket, action, False,
                                                {"error": "Token expired or invalid"})
                            continue
                    elif not client.user_id:
                        await send_response(websocket, action, False,
                                            {"error": "Not authenticated"})
                        continue

                handler = ACTION_HANDLERS.get(action)
                if handler:
                    try:
                        await handler(client, data)
                    except Exception as e:
                        logger.error(f"Error handling action {action}: {e}", exc_info=True)
                        await send_response(websocket, action, False,
                                            {"error": "Internal server error"})
                else:
                    await send_response(websocket, action, False,
                                        {"error": f"Unknown action: {action}"})

    except websockets.exceptions.ConnectionClosedOK:
        logger.info(f"Client {client.username} disconnected normally")
    except websockets.exceptions.ConnectionClosedError as e:
        logger.warning(f"Client {client.username} disconnected with error: {e}")
    except Exception as e:
        logger.error(f"Unhandled error for client {client.username}: {e}", exc_info=True)
    finally:
        # Clean up global state on disconnect
        if client.user_id and client.user_id in connected_clients:
            del connected_clients[client.user_id]
        if client.current_channel_id:
            await broadcast_to_channel(
                client.current_channel_id, "user_left_channel",
                {"user_id": client.user_id, "username": client.username}
            )
        if client.server_id:
            await broadcast_to_server(
                client.server_id, "user_offline",
                {"user_id": client.user_id, "username": client.username}
            )
        logger.info(f"Cleaned up connection for {client.username}")


async def main():
    """Entry point: initialise DB, start voice relay, then serve WebSocket connections."""
    database.create_tables()
    logger.info(f"Starting TeamYur4ik server on ws://{config.HOST}:{config.WS_PORT}")
    await voice_relay.start(config.HOST, config.VOICE_PORT)
    async with websockets.serve(handle_client, config.HOST, config.WS_PORT):
        logger.info("Server is running. Press Ctrl+C to stop.")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
