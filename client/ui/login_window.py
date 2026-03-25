import asyncio
import json
import logging
import sys
import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QTabWidget,
    QComboBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont

# Add parent directory to path so we can import sibling packages
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ui.styles import get_style
from localization import loc

logger = logging.getLogger(__name__)


class LoginWorker(QThread):
    """
    Background thread that performs the actual WebSocket login/register call.
    Emits success or failure signals back to the UI thread.
    """
    success = pyqtSignal(str, str, int, int, str)  # token, host, ws_port, voice_port, username
    failure = pyqtSignal(str)                        # error message

    def __init__(self, action: str, host: str, ws_port: int, voice_port: int,
                 username: str, password: str, email: str = None):
        super().__init__()
        self.action = action          # "login" or "register"
        self.host = host
        self.ws_port = ws_port
        self.voice_port = voice_port
        self.username = username
        self.password = password
        self.email = email

    def run(self):
        """Connect via WebSocket, send the action, parse the response."""
        try:
            import websockets

            async def _do():
                uri = f"ws://{self.host}:{self.ws_port}"
                async with websockets.connect(uri, open_timeout=10) as ws:
                    payload = {
                        "type": "action",
                        "action": self.action,
                        "data": {
                            "username": self.username,
                            "password": self.password,
                        }
                    }
                    if self.action == "register" and self.email:
                        payload["data"]["email"] = self.email
                    await ws.send(json.dumps(payload))
                    raw = await asyncio.wait_for(ws.recv(), timeout=10)
                    return json.loads(raw)

            response = asyncio.run(_do())
            if response.get("success"):
                if self.action == "login":
                    data = response.get("data", {})
                    token = data.get("token", "")
                    self.success.emit(token, self.host, self.ws_port,
                                      self.voice_port, self.username)
                else:
                    # Registration success – return empty token; UI will switch to login tab
                    self.success.emit("", self.host, self.ws_port,
                                      self.voice_port, self.username)
            else:
                error = response.get("data", {}).get("error", "Unknown error")
                self.failure.emit(error)
        except Exception as e:
            self.failure.emit(str(e))


class LoginWindow(QMainWindow):
    """
    Login / Register window.
    Emits login_successful(token, host, ws_port, voice_port, username) when
    the user successfully authenticates.
    """

    login_successful = pyqtSignal(str, str, int, int, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(loc.get("app_name"))
        self.setMinimumSize(400, 480)
        self._worker: LoginWorker = None
        self._setup_ui()
        self.setStyleSheet(get_style("dark"))

    # -------------------------------------------------------------------------
    # UI construction
    # -------------------------------------------------------------------------

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        # ── App title ────────────────────────────────────────────────────────
        title = QLabel(loc.get("app_name"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        title.setFont(font)
        root.addWidget(title)

        # ── Language selector ─────────────────────────────────────────────────
        lang_row = QHBoxLayout()
        self._lang_label = QLabel(loc.get("language") + ":")
        self._lang_combo = QComboBox()
        self._lang_combo.addItem("English", "en")
        self._lang_combo.addItem("Русский", "ru")
        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_row.addStretch()
        lang_row.addWidget(self._lang_label)
        lang_row.addWidget(self._lang_combo)
        root.addLayout(lang_row)

        # ── Tab widget: Login / Register ──────────────────────────────────────
        self._tabs = QTabWidget()
        root.addWidget(self._tabs)

        # ── Login tab ─────────────────────────────────────────────────────────
        login_tab = QWidget()
        lt = QVBoxLayout(login_tab)
        lt.setSpacing(8)

        self._login_server = QLineEdit("localhost")
        self._login_server.setPlaceholderText(loc.get("server_address"))
        self._login_port = QLineEdit("8765")
        self._login_port.setPlaceholderText(loc.get("port"))
        self._login_voice_port = QLineEdit("9000")
        self._login_voice_port.setPlaceholderText(loc.get("voice_port"))
        self._login_user = QLineEdit()
        self._login_user.setPlaceholderText(loc.get("username"))
        self._login_pass = QLineEdit()
        self._login_pass.setPlaceholderText(loc.get("password"))
        self._login_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._login_btn = QPushButton(loc.get("login"))
        self._login_btn.clicked.connect(self._do_login)

        for w in (self._login_server, self._login_port, self._login_voice_port,
                  self._login_user, self._login_pass, self._login_btn):
            lt.addWidget(w)
        lt.addStretch()
        self._tabs.addTab(login_tab, loc.get("login"))

        # ── Register tab ──────────────────────────────────────────────────────
        reg_tab = QWidget()
        rt = QVBoxLayout(reg_tab)
        rt.setSpacing(8)

        self._reg_server = QLineEdit("localhost")
        self._reg_server.setPlaceholderText(loc.get("server_address"))
        self._reg_port = QLineEdit("8765")
        self._reg_port.setPlaceholderText(loc.get("port"))
        self._reg_voice_port = QLineEdit("9000")
        self._reg_voice_port.setPlaceholderText(loc.get("voice_port"))
        self._reg_user = QLineEdit()
        self._reg_user.setPlaceholderText(loc.get("username"))
        self._reg_pass = QLineEdit()
        self._reg_pass.setPlaceholderText(loc.get("password"))
        self._reg_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._reg_confirm = QLineEdit()
        self._reg_confirm.setPlaceholderText(loc.get("password") + " (confirm)")
        self._reg_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self._reg_btn = QPushButton(loc.get("register"))
        self._reg_btn.clicked.connect(self._do_register)

        for w in (self._reg_server, self._reg_port, self._reg_voice_port,
                  self._reg_user, self._reg_pass, self._reg_confirm, self._reg_btn):
            rt.addWidget(w)
        rt.addStretch()
        self._tabs.addTab(reg_tab, loc.get("register"))

        # ── Status label ──────────────────────────────────────────────────────
        self._status = QLabel("")
        self._status.setObjectName("status_label")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setWordWrap(True)
        root.addWidget(self._status)

    # -------------------------------------------------------------------------
    # Slots
    # -------------------------------------------------------------------------

    def _on_language_changed(self, idx: int):
        locale = self._lang_combo.itemData(idx)
        loc.set_locale(locale)
        self._retranslate()

    def _retranslate(self):
        """Re-apply all user-visible strings after a locale change."""
        self.setWindowTitle(loc.get("app_name"))
        self._lang_label.setText(loc.get("language") + ":")
        self._tabs.setTabText(0, loc.get("login"))
        self._tabs.setTabText(1, loc.get("register"))
        self._login_server.setPlaceholderText(loc.get("server_address"))
        self._login_port.setPlaceholderText(loc.get("port"))
        self._login_voice_port.setPlaceholderText(loc.get("voice_port"))
        self._login_user.setPlaceholderText(loc.get("username"))
        self._login_pass.setPlaceholderText(loc.get("password"))
        self._login_btn.setText(loc.get("login"))
        self._reg_server.setPlaceholderText(loc.get("server_address"))
        self._reg_port.setPlaceholderText(loc.get("port"))
        self._reg_voice_port.setPlaceholderText(loc.get("voice_port"))
        self._reg_user.setPlaceholderText(loc.get("username"))
        self._reg_pass.setPlaceholderText(loc.get("password"))
        self._reg_confirm.setPlaceholderText(loc.get("password") + " (confirm)")
        self._reg_btn.setText(loc.get("register"))

    def _set_status(self, text: str, error: bool = False):
        self._status.setText(text)
        color = "#ed4245" if error else "#57f287"
        self._status.setStyleSheet(f"color: {color};")

    def _set_busy(self, busy: bool):
        """Disable input widgets while a network request is in flight."""
        for w in (self._login_btn, self._reg_btn, self._tabs):
            w.setEnabled(not busy)

    # ── Login ──────────────────────────────────────────────────────────────────

    def _do_login(self):
        host = self._login_server.text().strip()
        ws_port = int(self._login_port.text().strip() or "8765")
        voice_port = int(self._login_voice_port.text().strip() or "9000")
        username = self._login_user.text().strip()
        password = self._login_pass.text()
        if not host or not username or not password:
            self._set_status(loc.get("error") + ": fill all fields", error=True)
            return
        self._set_status(loc.get("connecting"))
        self._set_busy(True)
        self._worker = LoginWorker("login", host, ws_port, voice_port, username, password)
        self._worker.success.connect(self._on_login_success)
        self._worker.failure.connect(self._on_login_failure)
        self._worker.finished.connect(lambda: self._set_busy(False))
        self._worker.start()

    @pyqtSlot(str, str, int, int, str)
    def _on_login_success(self, token: str, host: str, ws_port: int,
                          voice_port: int, username: str):
        self._set_status(loc.get("connected"))
        self.login_successful.emit(token, host, ws_port, voice_port, username)

    @pyqtSlot(str)
    def _on_login_failure(self, error: str):
        self._set_status(loc.get("login_failed") + f"\n{error}", error=True)

    # ── Register ───────────────────────────────────────────────────────────────

    def _do_register(self):
        host = self._reg_server.text().strip()
        ws_port = int(self._reg_port.text().strip() or "8765")
        voice_port = int(self._reg_voice_port.text().strip() or "9000")
        username = self._reg_user.text().strip()
        password = self._reg_pass.text()
        confirm = self._reg_confirm.text()
        if not host or not username or not password:
            self._set_status(loc.get("error") + ": fill all fields", error=True)
            return
        if password != confirm:
            self._set_status(loc.get("error") + ": passwords do not match", error=True)
            return
        self._set_status(loc.get("connecting"))
        self._set_busy(True)
        self._worker = LoginWorker("register", host, ws_port, voice_port, username, password)
        self._worker.success.connect(self._on_register_success)
        self._worker.failure.connect(self._on_register_failure)
        self._worker.finished.connect(lambda: self._set_busy(False))
        self._worker.start()

    @pyqtSlot(str, str, int, int, str)
    def _on_register_success(self, *_args):
        self._set_status(loc.get("register_success"))
        # Switch to login tab automatically
        self._tabs.setCurrentIndex(0)

    @pyqtSlot(str)
    def _on_register_failure(self, error: str):
        self._set_status(loc.get("error") + f": {error}", error=True)
