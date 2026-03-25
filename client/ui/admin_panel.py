import logging
import os
import sys

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox, QCheckBox,
    QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from localization import loc

logger = logging.getLogger(__name__)


class AdminPanel(QDialog):
    """
    Administrator panel dialog.

    Tabs:
      1. Channels  – list channels, add new, delete existing
      2. Users & Roles – table of members with role controls, kick button
      3. Bans      – list of banned users, unban button
    """

    def __init__(self, network_client=None, server_id: int = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Admin Panel")
        self.setMinimumSize(560, 420)
        self._network = network_client
        self._server_id = server_id
        self._setup_ui()

    # -------------------------------------------------------------------------
    # UI
    # -------------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._setup_channels_tab()
        self._setup_users_tab()
        self._setup_bans_tab()

        close_btn = QPushButton(loc.get("close"))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    # ── Channels tab ──────────────────────────────────────────────────────────

    def _setup_channels_tab(self):
        tab = QWidget()
        vbox = QVBoxLayout(tab)

        self._channels_list = QListWidget()
        vbox.addWidget(self._channels_list)

        # Add channel form
        form_row = QHBoxLayout()
        self._ch_name_input = QLineEdit()
        self._ch_name_input.setPlaceholderText(loc.get("channel_name"))
        self._ch_type_combo = QComboBox()
        self._ch_type_combo.addItem(loc.get("text_channel"), "text")
        self._ch_type_combo.addItem(loc.get("voice_channel"), "voice")
        self._ch_private_check = QCheckBox(loc.get("private_channel"))
        self._ch_pass_input = QLineEdit()
        self._ch_pass_input.setPlaceholderText(loc.get("channel_password"))
        self._ch_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        add_ch_btn = QPushButton("+ " + loc.get("create_channel"))
        add_ch_btn.clicked.connect(self._on_create_channel)
        form_row.addWidget(self._ch_name_input)
        form_row.addWidget(self._ch_type_combo)
        form_row.addWidget(self._ch_private_check)
        form_row.addWidget(self._ch_pass_input)
        form_row.addWidget(add_ch_btn)
        vbox.addLayout(form_row)

        del_ch_btn = QPushButton(loc.get("delete_channel"))
        del_ch_btn.setObjectName("danger_btn")
        del_ch_btn.clicked.connect(self._on_delete_channel)
        vbox.addWidget(del_ch_btn)

        self._tabs.addTab(tab, loc.get("channels"))

    # ── Users tab ─────────────────────────────────────────────────────────────

    def _setup_users_tab(self):
        tab = QWidget()
        vbox = QVBoxLayout(tab)

        self._users_table = QTableWidget(0, 2)
        self._users_table.setHorizontalHeaderLabels([
            loc.get("username"), loc.get("set_role")
        ])
        self._users_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._users_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        vbox.addWidget(self._users_table)

        btn_row = QHBoxLayout()
        self._role_combo = QComboBox()
        self._role_combo.addItem(loc.get("admin"), "admin")
        self._role_combo.addItem(loc.get("moderator"), "moderator")
        self._role_combo.addItem(loc.get("member"), "member")

        apply_role_btn = QPushButton(loc.get("set_role"))
        apply_role_btn.clicked.connect(self._on_apply_role)
        kick_btn = QPushButton(loc.get("kick_user"))
        kick_btn.setObjectName("danger_btn")
        kick_btn.clicked.connect(self._on_kick_user)

        btn_row.addWidget(QLabel(loc.get("set_role") + ":"))
        btn_row.addWidget(self._role_combo)
        btn_row.addWidget(apply_role_btn)
        btn_row.addStretch()
        btn_row.addWidget(kick_btn)
        vbox.addLayout(btn_row)

        self._tabs.addTab(tab, loc.get("user_management"))

    # ── Bans tab ──────────────────────────────────────────────────────────────

    def _setup_bans_tab(self):
        tab = QWidget()
        vbox = QVBoxLayout(tab)

        self._bans_list = QListWidget()
        vbox.addWidget(self._bans_list)

        unban_btn = QPushButton(loc.get("unban"))
        unban_btn.clicked.connect(self._on_unban)
        vbox.addWidget(unban_btn)

        self._tabs.addTab(tab, loc.get("bans"))

    # -------------------------------------------------------------------------
    # Data loading
    # -------------------------------------------------------------------------

    def refresh(self):
        """Re-request all admin data from the server."""
        if self._network:
            self._network.send_command("get_channels", {"server_id": self._server_id})
            self._network.send_command("get_members",  {"server_id": self._server_id})
            self._network.send_command("get_bans",     {"server_id": self._server_id})

    def populate_channels(self, channels: list):
        """Fill the channels list widget."""
        self._channels_list.clear()
        for ch in channels:
            item = QListWidgetItem(
                f"{'🔊' if ch.get('type') == 'voice' else '#'} {ch.get('name', '?')}"
            )
            item.setData(Qt.ItemDataRole.UserRole, ch.get("id"))
            self._channels_list.addItem(item)

    def populate_members(self, members: list):
        """Fill the users table."""
        self._users_table.setRowCount(0)
        for m in members:
            row = self._users_table.rowCount()
            self._users_table.insertRow(row)
            username_item = QTableWidgetItem(m.get("username", "?"))
            username_item.setData(Qt.ItemDataRole.UserRole, m.get("id"))
            role_item = QTableWidgetItem(m.get("role", "member"))
            self._users_table.setItem(row, 0, username_item)
            self._users_table.setItem(row, 1, role_item)

    def populate_bans(self, bans: list):
        """Fill the bans list widget."""
        self._bans_list.clear()
        for b in bans:
            text = b.get("username", "?")
            reason = b.get("reason", "")
            if reason:
                text += f" — {reason}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, b.get("user_id"))
            self._bans_list.addItem(item)

    # -------------------------------------------------------------------------
    # Action handlers
    # -------------------------------------------------------------------------

    def _on_create_channel(self):
        name = self._ch_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, loc.get("error"), loc.get("channel_name") + "?")
            return
        ch_type = self._ch_type_combo.currentData()
        is_private = 1 if self._ch_private_check.isChecked() else 0
        password = self._ch_pass_input.text() or None
        if self._network:
            self._network.send_command("create_channel", {
                "name": name,
                "type": ch_type,
                "is_private": is_private,
                "password": password,
            })
        self._ch_name_input.clear()
        self._ch_pass_input.clear()

    def _on_delete_channel(self):
        item = self._channels_list.currentItem()
        if not item:
            return
        ch_id = item.data(Qt.ItemDataRole.UserRole)
        if self._network:
            self._network.send_command("delete_channel", {"channel_id": ch_id})
        self._channels_list.takeItem(self._channels_list.row(item))

    def _on_apply_role(self):
        row = self._users_table.currentRow()
        if row < 0:
            return
        user_id = self._users_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        role = self._role_combo.currentData()
        if self._network:
            self._network.send_command("set_role", {"user_id": user_id, "role": role})
        self._users_table.item(row, 1).setText(role)

    def _on_kick_user(self):
        row = self._users_table.currentRow()
        if row < 0:
            return
        user_id = self._users_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if self._network:
            self._network.send_command("kick_user", {"user_id": user_id})
        self._users_table.removeRow(row)

    def _on_unban(self):
        item = self._bans_list.currentItem()
        if not item:
            return
        user_id = item.data(Qt.ItemDataRole.UserRole)
        if self._network:
            self._network.send_command("unban_user", {"user_id": user_id})
        self._bans_list.takeItem(self._bans_list.row(item))
