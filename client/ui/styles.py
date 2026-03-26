"""
Qt stylesheets for TeamYur4ik.
Two themes are provided:
  - DARK_THEME  : Discord-inspired dark palette
  - LIGHT_THEME : Clean light palette
Use get_style(name) to retrieve the desired stylesheet string.
"""

DARK_THEME = """
/* ── Global ─────────────────────────────────────────────────────────────── */
QMainWindow, QDialog {
    background-color: #313338;
    color: #dcddde;
}
QWidget {
    background-color: #313338;
    color: #dcddde;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
/* ── Server sidebar ─────────────────────────────────────────────────────── */
QWidget#server_panel {
    background-color: #1e1f22;
}
QListWidget#server_list {
    background-color: #1e1f22;
    border: none;
    padding: 4px 0;
}
QListWidget#server_list::item {
    background-color: #36393f;
    border-radius: 24px;
    margin: 4px auto;
    padding: 0;
    color: #dcddde;
    width: 48px;
    height: 48px;
    text-align: center;
    font-weight: bold;
}
QListWidget#server_list::item:selected,
QListWidget#server_list::item:hover {
    background-color: #5865f2;
    border-radius: 16px;
    color: #ffffff;
}
/* ── Channel panel ──────────────────────────────────────────────────────── */
QWidget#ch_header {
    background-color: #2b2d31;
}
QListWidget, QTreeWidget {
    background-color: #2b2d31;
    border: none;
    color: #949ba4;
    padding: 4px 0;
}
QListWidget::item, QTreeWidget::item {
    padding: 5px 8px;
    border-radius: 4px;
    margin: 1px 4px;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: #404249;
    color: #ffffff;
}
QListWidget::item:hover, QTreeWidget::item:hover {
    background-color: #35373c;
    color: #dcddde;
}
/* ── Chat area ──────────────────────────────────────────────────────────── */
QTextEdit {
    background-color: #313338;
    border: none;
    color: #dcddde;
    padding: 8px 12px;
    selection-background-color: #5865f2;
    line-height: 1.4;
}
/* ── Input fields ───────────────────────────────────────────────────────── */
QLineEdit {
    background-color: #383a40;
    border: none;
    border-radius: 8px;
    padding: 9px 14px;
    color: #dcddde;
    selection-background-color: #5865f2;
}
QLineEdit:focus {
    background-color: #40434a;
    border: 2px solid #5865f2;
}
QLineEdit:hover {
    background-color: #3e4046;
}
/* ── Buttons ────────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #5865f2;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 9px 18px;
    font-weight: 600;
    letter-spacing: 0.3px;
}
QPushButton:hover { background-color: #4752c4; }
QPushButton:pressed { background-color: #3c45a5; }
QPushButton:disabled {
    background-color: #4e5058;
    color: #72767d;
}
QPushButton#danger_btn {
    background-color: #ed4245;
}
QPushButton#danger_btn:hover { background-color: #c03537; }
QPushButton#icon_btn {
    background-color: transparent;
    color: #b5bac1;
    border-radius: 50%;
    padding: 5px;
    font-size: 16px;
    min-width: 0;
    min-height: 0;
}
QPushButton#icon_btn:hover {
    background-color: #35373c;
    color: #dcddde;
}
QPushButton#icon_btn[active="true"] { color: #ed4245; }
/* ── Labels ─────────────────────────────────────────────────────────────── */
QLabel {
    color: #dcddde;
    background-color: transparent;
}
QLabel#section_label {
    color: #949ba4;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 8px 2px 8px;
    letter-spacing: 0.5px;
}
QLabel#channel_name_label {
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
}
QLabel#server_name_label {
    color: #ffffff;
    background-color: #2b2d31;
    font-size: 15px;
    font-weight: 700;
    padding: 14px 16px;
    border-bottom: 1px solid #1e1f22;
}
QLabel#status_label {
    color: #949ba4;
    font-size: 12px;
}
/* ── ComboBox ───────────────────────────────────────────────────────────── */
QComboBox {
    background-color: #383a40;
    color: #dcddde;
    border: none;
    border-radius: 6px;
    padding: 7px 12px;
    min-width: 100px;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #18191c;
    color: #dcddde;
    selection-background-color: #5865f2;
    border: 1px solid #040405;
    border-radius: 4px;
    padding: 4px;
}
/* ── ScrollBar ──────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #202225;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background-color: #72767d; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background-color: #202225;
    border-radius: 4px;
    min-width: 30px;
}
/* ── Tab widget ─────────────────────────────────────────────────────────── */
QTabWidget::pane {
    background-color: #313338;
    border: none;
    border-top: 1px solid #1e1f22;
}
QTabBar::tab {
    background-color: #2b2d31;
    color: #949ba4;
    padding: 9px 18px;
    border: none;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: #313338;
    color: #ffffff;
    border-bottom: 2px solid #5865f2;
}
QTabBar::tab:hover {
    background-color: #35373c;
    color: #dcddde;
}
/* ── Menu ───────────────────────────────────────────────────────────────── */
QMenuBar {
    background-color: #1e1f22;
    color: #949ba4;
    border-bottom: 1px solid #2b2d31;
}
QMenuBar::item:selected {
    background-color: #35373c;
    color: #ffffff;
}
QMenu {
    background-color: #18191c;
    color: #dcddde;
    border: 1px solid #040405;
    border-radius: 6px;
    padding: 6px;
}
QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #5865f2;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background-color: #3f4147;
    margin: 4px 8px;
}
/* ── Splitter ───────────────────────────────────────────────────────────── */
QSplitter::handle { background-color: #1e1f22; width: 1px; }
/* ── Slider ─────────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {
    background-color: #4e5058;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background-color: #ffffff;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}
QSlider::sub-page:horizontal {
    background-color: #5865f2;
    border-radius: 2px;
}
/* ── Voice controls bar ─────────────────────────────────────────────────── */
QWidget#voice_bar {
    background-color: #232428;
    border-top: 1px solid #1e1f22;
}
/* ── Table ──────────────────────────────────────────────────────────────── */
QTableWidget {
    background-color: #2b2d31;
    border: none;
    color: #dcddde;
    gridline-color: #3f4147;
    selection-background-color: #5865f2;
}
QTableWidget::item:selected {
    background-color: #5865f2;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #1e1f22;
    color: #949ba4;
    font-weight: 700;
    padding: 7px;
    border: none;
    border-bottom: 1px solid #3f4147;
    letter-spacing: 0.5px;
}
/* ── Status bar ─────────────────────────────────────────────────────────── */
QStatusBar {
    background-color: #1e1f22;
    color: #72767d;
    font-size: 12px;
}
/* ── Dialog ─────────────────────────────────────────────────────────────── */
QDialogButtonBox QPushButton {
    min-width: 80px;
}
"""

LIGHT_THEME = """
/* ── Global ─────────────────────────────────────────────────────────────── */
QMainWindow, QDialog {
    background-color: #ffffff;
    color: #2e3338;
}
QWidget {
    background-color: #ffffff;
    color: #2e3338;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
/* ── Server sidebar ─────────────────────────────────────────────────────── */
QWidget#server_panel {
    background-color: #e3e5e8;
}
QListWidget#server_list {
    background-color: #e3e5e8;
    border: none;
    padding: 4px 0;
}
QListWidget#server_list::item {
    background-color: #ffffff;
    border-radius: 24px;
    margin: 4px auto;
    padding: 0;
    color: #4e5058;
    width: 48px;
    height: 48px;
    text-align: center;
    font-weight: bold;
}
QListWidget#server_list::item:selected,
QListWidget#server_list::item:hover {
    background-color: #5865f2;
    border-radius: 16px;
    color: #ffffff;
}
/* ── Channel panel ──────────────────────────────────────────────────────── */
QWidget#ch_header {
    background-color: #f2f3f5;
}
QListWidget, QTreeWidget {
    background-color: #f2f3f5;
    border: none;
    color: #4e5058;
    padding: 4px 0;
}
QListWidget::item, QTreeWidget::item {
    padding: 5px 8px;
    border-radius: 4px;
    margin: 1px 4px;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: #d9dbdf;
    color: #060607;
}
QListWidget::item:hover, QTreeWidget::item:hover {
    background-color: #e0e1e5;
    color: #060607;
}
/* ── Chat area ──────────────────────────────────────────────────────────── */
QTextEdit {
    background-color: #ffffff;
    border: none;
    color: #2e3338;
    padding: 8px 12px;
    selection-background-color: #5865f2;
}
/* ── Input fields ───────────────────────────────────────────────────────── */
QLineEdit {
    background-color: #e3e5e8;
    border: none;
    border-radius: 8px;
    padding: 9px 14px;
    color: #060607;
}
QLineEdit:focus {
    background-color: #d9dbdf;
    border: 2px solid #5865f2;
}
QLineEdit:hover {
    background-color: #dcdee2;
}
/* ── Buttons ────────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #5865f2;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 9px 18px;
    font-weight: 600;
}
QPushButton:hover { background-color: #4752c4; }
QPushButton:pressed { background-color: #3c45a5; }
QPushButton:disabled {
    background-color: #d9dbdf;
    color: #8e9297;
}
QPushButton#danger_btn { background-color: #ed4245; }
QPushButton#danger_btn:hover { background-color: #c03537; }
QPushButton#icon_btn {
    background-color: transparent;
    color: #4e5058;
    border-radius: 50%;
    padding: 5px;
    font-size: 16px;
    min-width: 0;
    min-height: 0;
}
QPushButton#icon_btn:hover {
    background-color: #e0e1e5;
    color: #060607;
}
QPushButton#icon_btn[active="true"] { color: #ed4245; }
/* ── Labels ─────────────────────────────────────────────────────────────── */
QLabel {
    color: #2e3338;
    background-color: transparent;
}
QLabel#section_label {
    color: #747f8d;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 8px 2px 8px;
    letter-spacing: 0.5px;
}
QLabel#channel_name_label {
    color: #060607;
    font-size: 15px;
    font-weight: 700;
}
QLabel#server_name_label {
    color: #060607;
    background-color: #f2f3f5;
    font-size: 15px;
    font-weight: 700;
    padding: 14px 16px;
    border-bottom: 1px solid #d9dbdf;
}
QLabel#status_label { color: #747f8d; font-size: 12px; }
/* ── ComboBox ───────────────────────────────────────────────────────────── */
QComboBox {
    background-color: #e3e5e8;
    color: #060607;
    border: none;
    border-radius: 6px;
    padding: 7px 12px;
    min-width: 100px;
}
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #2e3338;
    selection-background-color: #5865f2;
    border: 1px solid #d9dbdf;
    border-radius: 4px;
    padding: 4px;
}
/* ── ScrollBar ──────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #c7ccd1;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background-color: #8e9297; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
/* ── Tab widget ─────────────────────────────────────────────────────────── */
QTabWidget::pane {
    background-color: #ffffff;
    border: none;
    border-top: 1px solid #d9dbdf;
}
QTabBar::tab {
    background-color: #f2f3f5;
    color: #4e5058;
    padding: 9px 18px;
    border: none;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    color: #060607;
    border-bottom: 2px solid #5865f2;
}
QTabBar::tab:hover {
    background-color: #e0e1e5;
    color: #060607;
}
/* ── Menu ───────────────────────────────────────────────────────────────── */
QMenuBar {
    background-color: #f2f3f5;
    color: #4e5058;
    border-bottom: 1px solid #d9dbdf;
}
QMenuBar::item:selected {
    background-color: #e0e1e5;
    color: #060607;
}
QMenu {
    background-color: #ffffff;
    color: #2e3338;
    border: 1px solid #d9dbdf;
    border-radius: 6px;
    padding: 6px;
}
QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #5865f2;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background-color: #d9dbdf;
    margin: 4px 8px;
}
/* ── Splitter ───────────────────────────────────────────────────────────── */
QSplitter::handle { background-color: #d9dbdf; width: 1px; }
/* ── Slider ─────────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {
    background-color: #d9dbdf;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background-color: #5865f2;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}
QSlider::sub-page:horizontal {
    background-color: #5865f2;
    border-radius: 2px;
}
/* ── Voice controls bar ─────────────────────────────────────────────────── */
QWidget#voice_bar {
    background-color: #ebedef;
    border-top: 1px solid #d9dbdf;
}
/* ── Table ──────────────────────────────────────────────────────────────── */
QTableWidget {
    background-color: #f2f3f5;
    border: none;
    color: #2e3338;
    gridline-color: #d9dbdf;
    selection-background-color: #5865f2;
}
QTableWidget::item:selected {
    background-color: #5865f2;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #e3e5e8;
    color: #747f8d;
    font-weight: 700;
    padding: 7px;
    border: none;
    border-bottom: 1px solid #d9dbdf;
}
/* ── Status bar ─────────────────────────────────────────────────────────── */
QStatusBar {
    background-color: #f2f3f5;
    color: #747f8d;
    font-size: 12px;
}
/* ── Dialog ─────────────────────────────────────────────────────────────── */
QDialogButtonBox QPushButton {
    min-width: 80px;
}
"""


def get_style(theme_name: str) -> str:
    """Return the Qt stylesheet string for the given theme name."""
    if theme_name == "light":
        return LIGHT_THEME
    return DARK_THEME  # default to dark theme
