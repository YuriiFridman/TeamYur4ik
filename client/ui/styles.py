"""
Qt stylesheets for TeamYur4ik.
Two themes are provided:
  - DARK_THEME  : Discord-inspired dark palette
  - LIGHT_THEME : Clean light palette
Use get_style(name) to retrieve the desired stylesheet string.
"""

DARK_THEME = """
QMainWindow, QDialog {
    background-color: #1e1f22;
    color: #ffffff;
}
QWidget {
    background-color: #1e1f22;
    color: #ffffff;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
/* ── Server sidebar ─────────────────────────────────────────────────────── */
QListWidget#server_list {
    background-color: #1e1f22;
    border: none;
    padding: 4px;
}
QListWidget#server_list::item {
    background-color: #313338;
    border-radius: 50%;
    margin: 4px auto;
    padding: 8px;
    color: #ffffff;
    width: 48px;
    height: 48px;
}
QListWidget#server_list::item:selected,
QListWidget#server_list::item:hover {
    background-color: #5865f2;
    border-radius: 16px;
}
/* ── Channel / User lists ───────────────────────────────────────────────── */
QListWidget, QTreeWidget {
    background-color: #2b2d31;
    border: none;
    color: #b5bac1;
    padding: 4px 0;
}
QListWidget::item, QTreeWidget::item {
    padding: 4px 8px;
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
    padding: 8px;
    selection-background-color: #5865f2;
}
/* ── Input fields ───────────────────────────────────────────────────────── */
QLineEdit {
    background-color: #383a40;
    border: none;
    border-radius: 6px;
    padding: 8px 12px;
    color: #ffffff;
    selection-background-color: #5865f2;
}
QLineEdit:focus {
    background-color: #40434a;
    border: 2px solid #5865f2;
}
/* ── Buttons ────────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #5865f2;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover { background-color: #4752c4; }
QPushButton:pressed { background-color: #3c45a5; }
QPushButton:disabled {
    background-color: #4e5058;
    color: #9b9d9f;
}
QPushButton#danger_btn { background-color: #ed4245; }
QPushButton#danger_btn:hover { background-color: #c03537; }
QPushButton#icon_btn {
    background-color: transparent;
    color: #b5bac1;
    border-radius: 20px;
    padding: 6px;
    font-size: 16px;
}
QPushButton#icon_btn:hover {
    background-color: #35373c;
    color: #ffffff;
}
QPushButton#icon_btn[active="true"] { color: #ed4245; }
/* ── Labels ─────────────────────────────────────────────────────────────── */
QLabel {
    color: #ffffff;
    background-color: transparent;
}
QLabel#section_label {
    color: #949ba4;
    font-size: 11px;
    font-weight: bold;
    padding: 4px 8px;
    text-transform: uppercase;
}
QLabel#channel_name_label {
    color: #ffffff;
    font-size: 15px;
    font-weight: bold;
}
QLabel#server_name_label {
    color: #ffffff;
    font-size: 15px;
    font-weight: bold;
    padding: 12px 16px;
    border-bottom: 1px solid #3f4147;
}
QLabel#status_label {
    color: #949ba4;
    font-size: 12px;
}
/* ── ComboBox ───────────────────────────────────────────────────────────── */
QComboBox {
    background-color: #383a40;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 10px;
    min-width: 100px;
}
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background-color: #2b2d31;
    color: #ffffff;
    selection-background-color: #5865f2;
    border: 1px solid #1e1f22;
}
/* ── ScrollBar ──────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #1a1b1e;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background-color: #949ba4; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background-color: #1a1b1e;
    border-radius: 4px;
    min-width: 30px;
}
/* ── Tab widget ─────────────────────────────────────────────────────────── */
QTabWidget::pane {
    background-color: #313338;
    border: none;
}
QTabBar::tab {
    background-color: #2b2d31;
    color: #b5bac1;
    padding: 8px 16px;
    border: none;
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
    color: #b5bac1;
    border-bottom: 1px solid #3f4147;
}
QMenuBar::item:selected {
    background-color: #35373c;
    color: #ffffff;
}
QMenu {
    background-color: #2b2d31;
    color: #b5bac1;
    border: 1px solid #1e1f22;
    border-radius: 4px;
    padding: 4px;
}
QMenu::item:selected {
    background-color: #5865f2;
    color: #ffffff;
    border-radius: 3px;
}
/* ── Splitter ───────────────────────────────────────────────────────────── */
QSplitter::handle { background-color: #1e1f22; }
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
    border-top: 1px solid #3f4147;
    padding: 4px 8px;
}
/* ── Table ──────────────────────────────────────────────────────────────── */
QTableWidget {
    background-color: #2b2d31;
    border: none;
    color: #dcddde;
    gridline-color: #3f4147;
}
QTableWidget::item:selected {
    background-color: #5865f2;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #232428;
    color: #949ba4;
    font-weight: bold;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #3f4147;
}
"""

LIGHT_THEME = """
QMainWindow, QDialog {
    background-color: #ffffff;
    color: #060607;
}
QWidget {
    background-color: #ffffff;
    color: #060607;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QListWidget#server_list {
    background-color: #e3e5e8;
    border: none;
    padding: 4px;
}
QListWidget#server_list::item {
    background-color: #ffffff;
    border-radius: 50%;
    margin: 4px auto;
    padding: 8px;
    color: #060607;
}
QListWidget#server_list::item:selected,
QListWidget#server_list::item:hover {
    background-color: #5865f2;
    color: #ffffff;
    border-radius: 16px;
}
QListWidget, QTreeWidget {
    background-color: #f2f3f5;
    border: none;
    color: #4e5058;
    padding: 4px 0;
}
QListWidget::item, QTreeWidget::item {
    padding: 4px 8px;
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
QTextEdit {
    background-color: #ffffff;
    border: none;
    color: #2e3338;
    padding: 8px;
    selection-background-color: #5865f2;
}
QLineEdit {
    background-color: #e3e5e8;
    border: none;
    border-radius: 6px;
    padding: 8px 12px;
    color: #060607;
}
QLineEdit:focus { background-color: #d9dbdf; }
QPushButton {
    background-color: #5865f2;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover { background-color: #4752c4; }
QPushButton:pressed { background-color: #3c45a5; }
QPushButton:disabled {
    background-color: #d9dbdf;
    color: #8e9297;
}
QPushButton#icon_btn {
    background-color: transparent;
    color: #4e5058;
    border-radius: 20px;
    padding: 6px;
    font-size: 16px;
}
QPushButton#icon_btn:hover {
    background-color: #e0e1e5;
    color: #060607;
}
QPushButton#icon_btn[active="true"] { color: #ed4245; }
QLabel {
    color: #060607;
    background-color: transparent;
}
QLabel#section_label {
    color: #747f8d;
    font-size: 11px;
    font-weight: bold;
    padding: 4px 8px;
}
QLabel#channel_name_label {
    color: #060607;
    font-size: 15px;
    font-weight: bold;
}
QLabel#server_name_label {
    color: #060607;
    font-size: 15px;
    font-weight: bold;
    padding: 12px 16px;
    border-bottom: 1px solid #d9dbdf;
}
QLabel#status_label { color: #747f8d; }
QComboBox {
    background-color: #e3e5e8;
    color: #060607;
    border: none;
    border-radius: 4px;
    padding: 6px 10px;
    min-width: 100px;
}
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background-color: #f2f3f5;
    color: #060607;
    selection-background-color: #5865f2;
    border: 1px solid #d9dbdf;
}
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
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QTabWidget::pane {
    background-color: #ffffff;
    border: none;
}
QTabBar::tab {
    background-color: #f2f3f5;
    color: #4e5058;
    padding: 8px 16px;
    border: none;
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
    color: #4e5058;
    border: 1px solid #d9dbdf;
    border-radius: 4px;
    padding: 4px;
}
QMenu::item:selected {
    background-color: #5865f2;
    color: #ffffff;
    border-radius: 3px;
}
QSplitter::handle { background-color: #d9dbdf; }
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
QWidget#voice_bar {
    background-color: #ebedef;
    border-top: 1px solid #d9dbdf;
    padding: 4px 8px;
}
QTableWidget {
    background-color: #f2f3f5;
    border: none;
    color: #2e3338;
    gridline-color: #d9dbdf;
}
QTableWidget::item:selected {
    background-color: #5865f2;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #e3e5e8;
    color: #747f8d;
    font-weight: bold;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #d9dbdf;
}
"""


def get_style(theme_name: str) -> str:
    """Return the Qt stylesheet string for the given theme name."""
    if theme_name == "light":
        return LIGHT_THEME
    return DARK_THEME  # default to dark theme
