import sys
import os
import json
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

sys.path.insert(0, os.path.dirname(__file__))

from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from ui.settings_dialog import SettingsDialog
from ui.styles import get_style
from ui.admin_panel import AdminPanel
from network.client import NetworkClient
from audio.audio_manager import AudioManager
from localization import loc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SETTINGS_FILE = Path.home() / ".teamyur4ik" / "settings.json"


def load_settings() -> dict:
    """Load persisted user settings; return defaults on any failure."""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
    return {"theme": "dark", "language": "en"}


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TeamYur4ik")

    settings = load_settings()
    loc.set_locale(settings.get("language", "en"))
    app.setStyleSheet(get_style(settings.get("theme", "dark")))

    login_window = LoginWindow()
    login_window.show()

    # Mutable shared state (avoids closure-capture issues with plain variables)
    state = {
        "network": None,
        "audio": None,
        "main_window": None,
        "current_server_id": None,
        "current_channel_id": None,
    }

    def on_login_successful(token: str, host: str, ws_port: int,
                            voice_port: int, username: str):
        login_window.hide()

        network = NetworkClient()
        audio = AudioManager()
        state["network"] = network
        state["audio"] = audio

        main_win = MainWindow(username=username)
        state["main_window"] = main_win

        # ── Server event handlers ──────────────────────────────────────────────

        def on_new_message(data):
            QTimer.singleShot(0, lambda: main_win.add_message(data))

        def on_user_joined_channel(data):
            QTimer.singleShot(0, lambda: main_win.add_user(data))

        def on_user_left_channel(data):
            uid = data.get("user_id")
            QTimer.singleShot(0, lambda: main_win.update_user_status(uid, False))

        def on_user_joined_server(data):
            QTimer.singleShot(0, lambda: main_win.add_user(data))

        def on_user_left_server(data):
            uid = data.get("user_id")
            QTimer.singleShot(0, lambda: main_win.update_user_status(uid, False))

        def on_channel_created(data):
            QTimer.singleShot(0, lambda: main_win.add_channel(data))

        def on_channel_deleted(_data):
            # Simplest safe approach: clear channels and let the user re-join the server
            QTimer.singleShot(0, lambda: main_win.clear_channels())

        def on_kicked(_data):
            QTimer.singleShot(0, lambda: (
                main_win.set_status(loc.get("disconnected")),
                main_win.close()
            ))

        def on_banned(data):
            reason = data.get("reason", "")
            QTimer.singleShot(0, lambda: (
                main_win.set_status(f"Banned: {reason}"),
                main_win.close()
            ))

        def on_muted(_data):
            QTimer.singleShot(0, lambda: audio.set_mode("mute"))

        def on_user_offline(data):
            uid = data.get("user_id")
            QTimer.singleShot(0, lambda: main_win.update_user_status(uid, False))

        # ── WebSocket connection callbacks ────────────────────────────────────

        def on_connected():
            # After WebSocket is up, authenticate with our JWT token
            network.send_command("login", {"username": username, "token": token,
                                           "password": ""})

        def on_disconnected():
            QTimer.singleShot(0, lambda: (main_win.close(), login_window.show()))

        # ── Response handlers ─────────────────────────────────────────────────

        def on_response_get_servers(msg):
            if msg.get("success"):
                servers = msg.get("data", {}).get("servers", [])
                QTimer.singleShot(0, lambda: [main_win.add_server(s) for s in servers])

        def on_response_join_server(msg):
            if msg.get("success"):
                data = msg.get("data", {})
                channels = data.get("channels", [])
                members = data.get("members", [])
                def update():
                    main_win.clear_channels()
                    main_win.clear_users()
                    for ch in channels:
                        main_win.add_channel(ch)
                    for m in members:
                        main_win.add_user(m)
                QTimer.singleShot(0, update)

        def on_response_join_channel(msg):
            if msg.get("success"):
                data = msg.get("data", {})
                history = data.get("history", [])
                channel_id = data.get("channel_id")
                state["current_channel_id"] = channel_id
                def update():
                    main_win.clear_messages()
                    for m in history:
                        main_win.add_message(m)
                QTimer.singleShot(0, update)

        def on_response_create_server(msg):
            if msg.get("success"):
                data = msg.get("data", {})
                server_id = data.get("server_id")
                name = data.get("name", "")
                state["current_server_id"] = server_id
                def _add():
                    main_win.add_server({"id": server_id, "name": name})
                    main_win.set_current_server(name)
                QTimer.singleShot(0, _add)
                # Send join_server in the next event-loop tick after the
                # add_server update has been processed by Qt, so that
                # on_response_join_server can safely update the UI.
                QTimer.singleShot(50, lambda: network.send_command(
                    "join_server", {"server_id": server_id}
                ))

        def on_response_login(msg):
            if msg.get("success"):
                # Once logged in, fetch the server list
                QTimer.singleShot(500, lambda: network.send_command("get_servers", {}))

        # ── Register callbacks ─────────────────────────────────────────────────

        network.on_event["new_message"]          = on_new_message
        network.on_event["user_joined_channel"]  = on_user_joined_channel
        network.on_event["user_left_channel"]    = on_user_left_channel
        network.on_event["user_joined_server"]   = on_user_joined_server
        network.on_event["user_left_server"]     = on_user_left_server
        network.on_event["user_offline"]         = on_user_offline
        network.on_event["channel_created"]      = on_channel_created
        network.on_event["channel_deleted"]      = on_channel_deleted
        network.on_event["kicked"]               = on_kicked
        network.on_event["banned"]               = on_banned
        network.on_event["muted"]                = on_muted
        network.on_event["response_get_servers"] = on_response_get_servers
        network.on_event["response_join_server"] = on_response_join_server
        network.on_event["response_join_channel"]= on_response_join_channel
        network.on_event["response_login"]       = on_response_login
        network.on_event["response_create_server"] = on_response_create_server
        network.on_connected    = on_connected
        network.on_disconnected = on_disconnected

        # ── Main window signal connections ────────────────────────────────────

        def on_join_channel(channel_id: int):
            state["current_channel_id"] = channel_id
            network.send_command("join_channel", {"channel_id": channel_id})

        def on_send_message(content: str):
            channel_id = state["current_channel_id"]
            if channel_id:
                network.send_command("send_message",
                                     {"channel_id": channel_id, "content": content})

        def on_join_server(server_id: int):
            state["current_server_id"] = server_id
            network.send_command("join_server", {"server_id": server_id})

        def on_create_server(name: str):
            network.send_command("create_server", {"name": name})

        def on_disconnect():
            network.disconnect()
            main_win.close()
            login_window.show()

        def on_settings():
            dlg = SettingsDialog(audio, main_win)
            dlg.exec()
            new_settings = load_settings()
            loc.set_locale(new_settings.get("language", "en"))
            app.setStyleSheet(get_style(new_settings.get("theme", "dark")))

        def on_mic_toggled(muted: bool):
            if muted:
                audio.stop_capture()
            else:
                audio.start_capture()

        def on_kick_user(user_id: int):
            network.send_command("kick_user", {"user_id": user_id})

        def on_ban_user(user_id: int):
            network.send_command("ban_user", {"user_id": user_id})

        def on_mute_user(user_id: int):
            network.send_command("mute_user", {"user_id": user_id})

        def on_set_role(user_id: int, role: str):
            network.send_command("set_role", {"user_id": user_id, "role": role})

        def on_create_channel(name: str, ch_type: str):
            server_id = state["current_server_id"]
            if server_id:
                network.send_command("create_channel", {
                    "server_id": server_id,
                    "name": name,
                    "type": ch_type,
                    "is_private": 0,
                })

        def on_admin_panel():
            server_id = state["current_server_id"]
            panel = AdminPanel(network_client=network,
                               server_id=server_id,
                               parent=main_win)

            # Temporary response handlers scoped to this panel instance
            def _on_get_channels(msg):
                if msg.get("success"):
                    chs = msg.get("data", {}).get("channels", [])
                    QTimer.singleShot(0, lambda: panel.populate_channels(chs))

            def _on_get_members(msg):
                if msg.get("success"):
                    mbs = msg.get("data", {}).get("members", [])
                    QTimer.singleShot(0, lambda: panel.populate_members(mbs))

            def _on_get_bans(msg):
                if msg.get("success"):
                    bns = msg.get("data", {}).get("bans", [])
                    QTimer.singleShot(0, lambda: panel.populate_bans(bns))

            # Save and replace callbacks
            _saved_callbacks = {
                k: network.on_event.get(k)
                for k in ("response_get_channels",
                          "response_get_members",
                          "response_get_bans")
            }
            network.on_event["response_get_channels"] = _on_get_channels
            network.on_event["response_get_members"]  = _on_get_members
            network.on_event["response_get_bans"]     = _on_get_bans

            panel.refresh()
            panel.exec()

            # Restore previous callbacks
            for k, v in _saved_callbacks.items():
                if v is not None:
                    network.on_event[k] = v
                else:
                    network.on_event.pop(k, None)

        main_win.join_channel_requested.connect(on_join_channel)
        main_win.send_message_requested.connect(on_send_message)
        main_win.join_server_requested.connect(on_join_server)
        main_win.create_server_requested.connect(on_create_server)
        main_win.create_channel_requested.connect(on_create_channel)
        main_win.disconnect_requested.connect(on_disconnect)
        main_win.settings_requested.connect(on_settings)
        main_win.admin_panel_requested.connect(on_admin_panel)
        main_win.mic_toggled.connect(on_mic_toggled)
        main_win.kick_user_requested.connect(on_kick_user)
        main_win.ban_user_requested.connect(on_ban_user)
        main_win.mute_user_requested.connect(on_mute_user)
        main_win.set_role_requested.connect(on_set_role)

        # ── Audio capture → voice UDP ──────────────────────────────────────────

        def on_audio_captured(data: bytes):
            channel_id = state["current_channel_id"]
            if channel_id:
                network.send_voice(channel_id, data)

        audio.on_audio_captured = on_audio_captured

        # ── Start network connection ───────────────────────────────────────────
        network.connect(host, ws_port, voice_port, token)

        # ── Apply saved audio settings ─────────────────────────────────────────
        input_dev = settings.get("input_device")
        output_dev = settings.get("output_device")
        if input_dev is not None:
            audio.set_input_device(input_dev)
        if output_dev is not None:
            audio.set_output_device(output_dev)
        audio.set_vad_threshold(settings.get("vad_threshold", 0.01))
        audio.set_mode(settings.get("audio_mode", "vad"))
        audio.start_capture()

        main_win.show()

    login_window.login_successful.connect(on_login_successful)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
