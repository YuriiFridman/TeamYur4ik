import json
import logging
import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QSlider,
    QPushButton, QDialogButtonBox, QLabel, QWidget, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from localization import loc

logger = logging.getLogger(__name__)

SETTINGS_FILE = Path.home() / ".teamyur4ik" / "settings.json"


class SettingsDialog(QDialog):
    """
    Settings dialog covering language, theme, audio devices,
    VAD threshold, and push-to-talk key binding.
    Changes are persisted to ~/.teamyur4ik/settings.json on OK.
    """

    def __init__(self, audio_manager=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(loc.get("settings"))
        self.setMinimumWidth(380)
        self._audio_manager = audio_manager
        self._capturing_ptt = False   # True while waiting for a key press
        self._settings: dict = {}
        self._setup_ui()
        self.load_settings()

    # -------------------------------------------------------------------------
    # UI
    # -------------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setSpacing(10)

        # Language
        self._lang_combo = QComboBox()
        self._lang_combo.addItem("English", "en")
        self._lang_combo.addItem("Русский", "ru")
        form.addRow(QLabel(loc.get("language") + ":"), self._lang_combo)

        # Theme
        self._theme_combo = QComboBox()
        self._theme_combo.addItem(loc.get("dark_theme"), "dark")
        self._theme_combo.addItem(loc.get("light_theme"), "light")
        form.addRow(QLabel("Theme:"), self._theme_combo)

        # Input device
        self._input_combo = QComboBox()
        form.addRow(QLabel(loc.get("input_device") + ":"), self._input_combo)

        # Output device
        self._output_combo = QComboBox()
        form.addRow(QLabel(loc.get("output_device") + ":"), self._output_combo)

        # VAD threshold slider (0 – 100, displayed as 0.0 – 1.0)
        self._vad_slider = QSlider(Qt.Orientation.Horizontal)
        self._vad_slider.setRange(0, 100)
        self._vad_slider.setValue(1)
        self._vad_label = QLabel("0.01")
        self._vad_slider.valueChanged.connect(
            lambda v: self._vad_label.setText(f"{v / 100:.2f}")
        )
        vad_row = QWidget()
        vad_layout = QHBoxLayout(vad_row)
        vad_layout.setContentsMargins(0, 0, 0, 0)
        vad_layout.addWidget(self._vad_slider)
        vad_layout.addWidget(self._vad_label)
        form.addRow(QLabel(loc.get("vad_threshold") + ":"), vad_row)

        # PTT key
        self._ptt_btn = QPushButton(loc.get("press_key"))
        self._ptt_btn.clicked.connect(self._start_ptt_capture)
        form.addRow(QLabel(loc.get("ptt_key") + ":"), self._ptt_btn)

        layout.addLayout(form)

        # OK / Cancel buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        # Populate audio device dropdowns
        self._populate_devices()

    def _populate_devices(self):
        """Fill input/output device combos from the audio manager."""
        self._input_combo.addItem("Default", None)
        self._output_combo.addItem("Default", None)
        if self._audio_manager:
            devices = self._audio_manager.get_devices()
            for i, name in enumerate(devices.get("input", [])):
                self._input_combo.addItem(name, i)
            for i, name in enumerate(devices.get("output", [])):
                self._output_combo.addItem(name, i)

    # -------------------------------------------------------------------------
    # Load / Save
    # -------------------------------------------------------------------------

    def load_settings(self):
        """Read settings from disk and apply them to the form widgets."""
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    self._settings = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            self._settings = {}

        # Apply loaded values to widgets
        lang = self._settings.get("language", "en")
        idx = self._lang_combo.findData(lang)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)

        theme = self._settings.get("theme", "dark")
        tidx = self._theme_combo.findData(theme)
        if tidx >= 0:
            self._theme_combo.setCurrentIndex(tidx)

        threshold = self._settings.get("vad_threshold", 0.01)
        self._vad_slider.setValue(int(threshold * 100))

        ptt_key = self._settings.get("ptt_key", "space")
        self._ptt_btn.setText(ptt_key)

        input_dev = self._settings.get("input_device")
        if input_dev is not None:
            idx2 = self._input_combo.findData(input_dev)
            if idx2 >= 0:
                self._input_combo.setCurrentIndex(idx2)

        output_dev = self._settings.get("output_device")
        if output_dev is not None:
            idx3 = self._output_combo.findData(output_dev)
            if idx3 >= 0:
                self._output_combo.setCurrentIndex(idx3)

    def save_settings(self):
        """Write current form values to disk."""
        self._settings["language"] = self._lang_combo.currentData()
        self._settings["theme"] = self._theme_combo.currentData()
        self._settings["vad_threshold"] = self._vad_slider.value() / 100.0
        self._settings["ptt_key"] = self._ptt_btn.text()
        self._settings["input_device"] = self._input_combo.currentData()
        self._settings["output_device"] = self._output_combo.currentData()
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    # -------------------------------------------------------------------------
    # Slots
    # -------------------------------------------------------------------------

    def _on_ok(self):
        """Save settings, propagate to audio manager, then accept the dialog."""
        self.save_settings()
        # Apply language
        loc.set_locale(self._settings.get("language", "en"))
        # Apply audio manager settings
        if self._audio_manager:
            threshold = self._settings["vad_threshold"]
            self._audio_manager.set_vad_threshold(threshold)
            ptt_key = self._settings.get("ptt_key", "space")
            self._audio_manager.set_ptt_key(ptt_key)
            input_dev = self._settings.get("input_device")
            output_dev = self._settings.get("output_device")
            if input_dev is not None:
                self._audio_manager.set_input_device(input_dev)
            if output_dev is not None:
                self._audio_manager.set_output_device(output_dev)
        self.accept()

    def _start_ptt_capture(self):
        """Enter PTT key-capture mode: next key press sets the PTT key."""
        self._capturing_ptt = True
        self._ptt_btn.setText(loc.get("press_key"))

    # -------------------------------------------------------------------------
    # Key capture for PTT
    # -------------------------------------------------------------------------

    def keyPressEvent(self, event):
        """Intercept key presses; when in capture mode, record the PTT key."""
        if self._capturing_ptt:
            from PyQt6.QtGui import QKeySequence
            # Use QKeySequence for a human-readable name (handles F-keys, modifiers, etc.)
            key_name = QKeySequence(event.key()).toString() or event.text() or str(event.key())
            self._ptt_btn.setText(key_name)
            if self._audio_manager:
                self._audio_manager.set_ptt_key(key_name)
            self._capturing_ptt = False
            return  # consume the event
        super().keyPressEvent(event)
