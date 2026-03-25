import logging
import os
import sys
from typing import Dict, Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QLineEdit, QPushButton, QLabel, QSplitter,
    QMenu, QInputDialog, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QIcon, QFont, QAction

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from localization import loc

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main 3-panel Discord/TeamSpeak-like window.

    Left panel  : server icon list + add-server button
    Middle panel: server name, channel tree (text/voice), user list
    Right panel : top bar, chat area, message input + send button
    Bottom bar  : mic, deafen, PTT, settings buttons + username label
    """

    # ── Signals ────────────────────────────────────────────────────────────────
    join_channel_requested  = pyqtSignal(int)           # channel_id
    send_message_requested  = pyqtSignal(str)           # message content
    join_server_requested   = pyqtSignal(int)           # server_id
    create_server_requested = pyqtSignal(str)           # server name
    leave_channel_requested = pyqtSignal()
    mic_toggled             = pyqtSignal(bool)          # True = muted
    deafen_toggled          = pyqtSignal(bool)          # True = deafened
    disconnect_requested    = pyqtSignal()
    settings_requested      = pyqtSignal()
    admin_panel_requested   = pyqtSignal()
    kick_user_requested     = pyqtSignal(int)           # user_id
    ban_user_requested      = pyqtSignal(int)           # user_id
    mute_user_requested     = pyqtSignal(int)           # user_id
    set_role_requested      = pyqtSignal(int, str)      # user_id, role

    def __init__(self, username: str = ""):
        super().__init__()
        self._username = username
        self._is_muted = False
        self._is_deafened = False
        # Maps user_id (int) -> QListWidgetItem so we can update status
        self._user_items: Dict[int, QListWidgetItem] = {}
        # Maps server_id (int) -> QListWidgetItem
        self._server_items: Dict[int, QListWidgetItem] = {}
        self.setWindowTitle(loc.get("app_name"))
        self.setMinimumSize(900, 600)
        self._setup_ui()

    # -------------------------------------------------------------------------
    # UI construction
    # -------------------------------------------------------------------------

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left: server list panel (~64 px) ──────────────────────────────────
        server_panel = QWidget()
        server_panel.setFixedWidth(68)
        server_panel.setObjectName("server_panel")
        sp_layout = QVBoxLayout(server_panel)
        sp_layout.setContentsMargins(8, 8, 8, 8)
        sp_layout.setSpacing(4)

        self._server_list = QListWidget()
        self._server_list.setObjectName("server_list")
        self._server_list.setIconSize(QSize(40, 40))
        self._server_list.setFixedWidth(52)
        self._server_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._server_list.itemClicked.connect(self._on_server_clicked)
        sp_layout.addWidget(self._server_list)

        add_server_btn = QPushButton("+")
        add_server_btn.setObjectName("icon_btn")
        add_server_btn.setFixedSize(40, 40)
        add_server_btn.setToolTip(loc.get("create_server"))
        add_server_btn.clicked.connect(self._on_create_server)
        sp_layout.addWidget(add_server_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(server_panel)

        # ── Vertical separator ─────────────────────────────────────────────────
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setFixedWidth(1)
        root.addWidget(sep1)

        # ── Middle: channel + user panel (~240 px) ────────────────────────────
        mid_panel = QWidget()
        mid_panel.setFixedWidth(240)
        mid_layout = QVBoxLayout(mid_panel)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        mid_layout.setSpacing(0)

        self._server_name_label = QLabel(loc.get("servers"))
        self._server_name_label.setObjectName("server_name_label")
        mid_layout.addWidget(self._server_name_label)

        # Channel tree: two top-level categories
        self._channel_tree = QTreeWidget()
        self._channel_tree.setHeaderHidden(True)
        self._channel_tree.setObjectName("channel_tree")
        self._text_cat = QTreeWidgetItem([loc.get("text_channel").upper() + "S"])
        self._voice_cat = QTreeWidgetItem([loc.get("voice_channel").upper() + "S"])
        self._channel_tree.addTopLevelItem(self._text_cat)
        self._channel_tree.addTopLevelItem(self._voice_cat)
        self._text_cat.setExpanded(True)
        self._voice_cat.setExpanded(True)
        self._channel_tree.itemDoubleClicked.connect(self._on_channel_double_clicked)
        mid_layout.addWidget(self._channel_tree, stretch=3)

        # Separator between channels and users
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        mid_layout.addWidget(sep2)

        users_label = QLabel(loc.get("users").upper())
        users_label.setObjectName("section_label")
        mid_layout.addWidget(users_label)

        self._user_list = QListWidget()
        self._user_list.setObjectName("user_list")
        self._user_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._user_list.customContextMenuRequested.connect(self._on_user_context_menu)
        mid_layout.addWidget(self._user_list, stretch=2)

        root.addWidget(mid_panel)

        # ── Right: main chat area ──────────────────────────────────────────────
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Top bar: channel name + settings + disconnect
        top_bar = QWidget()
        top_bar.setFixedHeight(48)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(12, 4, 8, 4)

        hash_label = QLabel("#")
        hash_label.setStyleSheet("color: #b5bac1; font-size: 18px;")
        top_bar_layout.addWidget(hash_label)

        self._channel_name_label = QLabel(loc.get("no_channels"))
        self._channel_name_label.setObjectName("channel_name_label")
        top_bar_layout.addWidget(self._channel_name_label)
        top_bar_layout.addStretch()

        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("icon_btn")
        settings_btn.setFixedSize(36, 36)
        settings_btn.setToolTip(loc.get("settings"))
        settings_btn.clicked.connect(self.settings_requested)
        top_bar_layout.addWidget(settings_btn)

        disconnect_btn = QPushButton("✕")
        disconnect_btn.setObjectName("icon_btn")
        disconnect_btn.setFixedSize(36, 36)
        disconnect_btn.setToolTip(loc.get("disconnect"))
        disconnect_btn.clicked.connect(self.disconnect_requested)
        top_bar_layout.addWidget(disconnect_btn)

        right_layout.addWidget(top_bar)

        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.HLine)
        right_layout.addWidget(sep3)

        # Chat display (read-only)
        self._chat_area = QTextEdit()
        self._chat_area.setReadOnly(True)
        self._chat_area.setObjectName("chat_area")
        right_layout.addWidget(self._chat_area)

        # Message input row
        input_row = QWidget()
        input_row.setFixedHeight(52)
        input_layout = QHBoxLayout(input_row)
        input_layout.setContentsMargins(8, 4, 8, 4)
        input_layout.setSpacing(6)

        self._msg_input = QLineEdit()
        self._msg_input.setPlaceholderText(loc.get("type_message"))
        self._msg_input.returnPressed.connect(self._on_send_message)
        input_layout.addWidget(self._msg_input)

        send_btn = QPushButton(loc.get("send"))
        send_btn.setFixedWidth(80)
        send_btn.clicked.connect(self._on_send_message)
        input_layout.addWidget(send_btn)

        right_layout.addWidget(input_row)

        # ── Bottom voice controls bar ──────────────────────────────────────────
        voice_bar = QWidget()
        voice_bar.setObjectName("voice_bar")
        voice_bar.setFixedHeight(52)
        voice_layout = QHBoxLayout(voice_bar)
        voice_layout.setContentsMargins(8, 4, 8, 4)
        voice_layout.setSpacing(6)

        self._mic_btn = QPushButton("🎤")
        self._mic_btn.setObjectName("icon_btn")
        self._mic_btn.setFixedSize(36, 36)
        self._mic_btn.setToolTip(loc.get("mute"))
        self._mic_btn.clicked.connect(self._toggle_mic)
        voice_layout.addWidget(self._mic_btn)

        self._deafen_btn = QPushButton("🎧")
        self._deafen_btn.setObjectName("icon_btn")
        self._deafen_btn.setFixedSize(36, 36)
        self._deafen_btn.setToolTip(loc.get("deafen"))
        self._deafen_btn.clicked.connect(self._toggle_deafen)
        voice_layout.addWidget(self._deafen_btn)

        voice_layout.addStretch()

        username_label = QLabel(self._username)
        username_label.setObjectName("status_label")
        voice_layout.addWidget(username_label)

        voice_layout.addStretch()

        admin_btn = QPushButton("🛡")
        admin_btn.setObjectName("icon_btn")
        admin_btn.setFixedSize(36, 36)
        admin_btn.setToolTip("Admin Panel")
        admin_btn.clicked.connect(self.admin_panel_requested)
        voice_layout.addWidget(admin_btn)

        settings_btn2 = QPushButton("⚙")
        settings_btn2.setObjectName("icon_btn")
        settings_btn2.setFixedSize(36, 36)
        settings_btn2.setToolTip(loc.get("settings"))
        settings_btn2.clicked.connect(self.settings_requested)
        voice_layout.addWidget(settings_btn2)

        right_layout.addWidget(voice_bar)
        root.addWidget(right_panel)

        # ── Status bar ─────────────────────────────────────────────────────────
        self._status_label = QLabel(loc.get("disconnected"))
        self._status_label.setObjectName("status_label")
        self.statusBar().addPermanentWidget(self._status_label)

    # -------------------------------------------------------------------------
    # Public interface
    # -------------------------------------------------------------------------

    def add_server(self, server_data: dict):
        """Add a server entry to the left sidebar."""
        server_id = server_data.get("id")
        name = server_data.get("name", "?")
        item = QListWidgetItem(name[:2].upper())  # show initials as icon text
        item.setData(Qt.ItemDataRole.UserRole, server_id)
        item.setToolTip(name)
        item.setSizeHint(QSize(48, 48))
        self._server_list.addItem(item)
        self._server_items[server_id] = item

    def add_channel(self, channel_data: dict):
        """Add a channel under the correct category in the channel tree."""
        ch_id = channel_data.get("id")
        name = channel_data.get("name", "channel")
        ch_type = channel_data.get("type", "text")
        prefix = "# " if ch_type == "text" else "🔊 "
        item = QTreeWidgetItem([prefix + name])
        item.setData(0, Qt.ItemDataRole.UserRole, ch_id)
        if ch_type == "voice":
            self._voice_cat.addChild(item)
        else:
            self._text_cat.addChild(item)

    def clear_channels(self):
        """Remove all channel entries from the tree (keeps category headers)."""
        self._text_cat.takeChildren()
        self._voice_cat.takeChildren()

    def add_user(self, user_data: dict):
        """Add or update a user in the user list panel."""
        user_id = user_data.get("id") or user_data.get("user_id")
        username = user_data.get("username", "?")
        role = user_data.get("role", "")
        display = f"● {username}"
        if role:
            display += f"  [{role}]"

        if user_id in self._user_items:
            self._user_items[user_id].setText(display)
        else:
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, user_id)
            item.setForeground(QColor("#57f287"))  # green = online
            self._user_list.addItem(item)
            self._user_items[user_id] = item

    def clear_users(self):
        """Clear the user list."""
        self._user_list.clear()
        self._user_items.clear()

    def add_message(self, msg_data: dict):
        """Append a formatted message to the chat area."""
        username = msg_data.get("username", "?")
        content = msg_data.get("content", "")
        timestamp = msg_data.get("created_at", "")
        time_str = str(timestamp)[:16] if timestamp else ""
        line = f'<span style="color:#949ba4;font-size:11px;">[{time_str}]</span> ' \
               f'<b style="color:#5865f2;">{username}</b>: {content}'
        self._chat_area.append(line)
        # Scroll to bottom
        sb = self._chat_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clear_messages(self):
        """Clear all messages from the chat area."""
        self._chat_area.clear()

    def set_status(self, text: str):
        """Update the status bar text."""
        self._status_label.setText(text)

    def set_current_channel(self, name: str):
        """Update the channel name shown in the top bar."""
        self._channel_name_label.setText(name)

    def set_current_server(self, name: str):
        """Update the server name shown above the channel list."""
        self._server_name_label.setText(name)

    def update_user_status(self, user_id: int, online: bool):
        """Change a user's online indicator colour in the user list."""
        item = self._user_items.get(user_id)
        if item:
            item.setForeground(QColor("#57f287" if online else "#949ba4"))

    # -------------------------------------------------------------------------
    # Internal slots
    # -------------------------------------------------------------------------

    def _on_server_clicked(self, item: QListWidgetItem):
        server_id = item.data(Qt.ItemDataRole.UserRole)
        self.set_current_server(item.toolTip())
        self.join_server_requested.emit(server_id)

    def _on_channel_double_clicked(self, item: QTreeWidgetItem, _col: int):
        ch_id = item.data(0, Qt.ItemDataRole.UserRole)
        if ch_id is not None:
            self.set_current_channel(item.text(0))
            self.join_channel_requested.emit(ch_id)

    def _on_send_message(self):
        text = self._msg_input.text().strip()
        if text:
            self._msg_input.clear()
            self.send_message_requested.emit(text)

    def _on_create_server(self):
        name, ok = QInputDialog.getText(self, loc.get("create_server"),
                                        loc.get("server_name") + ":")
        if ok and name.strip():
            self.create_server_requested.emit(name.strip())

    def _toggle_mic(self):
        self._is_muted = not self._is_muted
        self._mic_btn.setProperty("active", str(self._is_muted).lower())
        self._mic_btn.setToolTip(loc.get("unmute") if self._is_muted else loc.get("mute"))
        self._mic_btn.style().unpolish(self._mic_btn)
        self._mic_btn.style().polish(self._mic_btn)
        self.mic_toggled.emit(self._is_muted)

    def _toggle_deafen(self):
        self._is_deafened = not self._is_deafened
        self._deafen_btn.setProperty("active", str(self._is_deafened).lower())
        self._deafen_btn.setToolTip(loc.get("undeafen") if self._is_deafened else loc.get("deafen"))
        self._deafen_btn.style().unpolish(self._deafen_btn)
        self._deafen_btn.style().polish(self._deafen_btn)
        self.deafen_toggled.emit(self._is_deafened)

    # ── User context menu ──────────────────────────────────────────────────────

    def _on_user_context_menu(self, pos):
        item = self._user_list.itemAt(pos)
        if not item:
            return
        user_id = item.data(Qt.ItemDataRole.UserRole)
        username = item.text().split("  ")[0].lstrip("● ").strip()

        menu = QMenu(self)

        kick_action = QAction(loc.get("kick_user"), self)
        kick_action.triggered.connect(lambda: self.kick_user_requested.emit(user_id))
        menu.addAction(kick_action)

        ban_action = QAction(loc.get("ban_user"), self)
        ban_action.triggered.connect(lambda: self.ban_user_requested.emit(user_id))
        menu.addAction(ban_action)

        mute_action = QAction(loc.get("mute_user"), self)
        mute_action.triggered.connect(lambda: self.mute_user_requested.emit(user_id))
        menu.addAction(mute_action)

        menu.addSeparator()

        # Role submenu
        role_menu = menu.addMenu(loc.get("set_role"))
        for role in ("admin", "moderator", "member"):
            role_action = QAction(loc.get(role), self)
            role_action.triggered.connect(
                lambda checked, uid=user_id, r=role: self.set_role_requested.emit(uid, r)
            )
            role_menu.addAction(role_action)

        menu.exec(self._user_list.viewport().mapToGlobal(pos))
