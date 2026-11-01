"""Shared visual tokens and reusable styles for the SMED Studio interface."""

COLORS = {
    "bg_darkest": "#E9EEF4",
    "bg_main": "#F3F6FA",
    "bg_card": "#FFFFFF",
    "bg_card_elevated": "#F8FAFC",
    "bg_input": "#FFFFFF",
    "border": "#D6E0EA",
    "border_focus": "#2563EB",
    "accent_cyan": "#2563EB",
    "accent_cyan_hover": "#1D4ED8",
    "accent_cyan_pressed": "#1E40AF",
    "text_primary": "#172B3F",
    "text_secondary": "#52677D",
    "text_muted": "#718397",
    "internal_red": "#A84949",
    "internal_bg": "#FCEEEE",
    "external_emerald": "#286B4B",
    "external_bg": "#EAF5EF",
    "warning_amber": "#9A6500",
    "digital_display_bg": "#F7FAFC",
    "digital_display_border": "#CBD7E3",
    "deep_navy": "#17324D",
    "navy_hover": "#244766",
    "primary_blue": "#2563EB",
    "primary_blue_hover": "#1D4ED8",
    "primary_blue_pressed": "#1E40AF",
    "success_green": "#2F7D5B",
    "success_green_hover": "#276B4D",
    "danger_red": "#B45353",
    "danger_red_hover": "#9F4141",
    "selection_bg": "#DBEAFE",
    "focus_ring": "#2563EB",
}

TYPOGRAPHY = {
    "family": '"Segoe UI"',
    "body": "14px",
    "page_heading": "24px",
    "section_heading": "18px",
    "table": "12px",
    "caption": "12px",
    "button": "14px",
}

SPACING = {
    "control_y": 8,
    "control_x": 12,
    "button_y": 9,
    "button_x": 16,
    "card": 16,
    "section": 12,
}

RADII = {
    "small": 4,
    "control": 6,
    "card": 8,
}

_STYLE_TOKENS = {
    **COLORS,
    **{f"font_{name}": value for name, value in TYPOGRAPHY.items()},
    **{f"space_{name}": f"{value}px" for name, value in SPACING.items()},
    **{f"radius_{name}": f"{value}px" for name, value in RADII.items()},
}

_LIGHT_INDUSTRIAL_QSS = """
QWidget {
    color: @text_primary;
    font-family: @font_family;
    font-size: @font_body;
    selection-background-color: @selection_bg;
    selection-color: @text_primary;
}

QMainWindow, QDialog {
    background-color: @bg_main;
}

QMenuBar {
    background-color: @deep_navy;
    color: #FFFFFF;
    padding: 4px 8px;
}

QMenuBar::item {
    background: transparent;
    padding: 7px 10px;
    border-radius: @radius_small;
}

QMenuBar::item:selected, QMenuBar::item:pressed {
    background-color: @navy_hover;
}

QMenu {
    background-color: @bg_card;
    color: @text_primary;
    border: 1px solid @border;
    padding: 4px;
}

QMenu::item {
    padding: 7px 28px 7px 10px;
    border-radius: @radius_small;
}

QMenu::item:selected {
    background-color: @selection_bg;
    color: @text_primary;
}

QMenu::separator {
    height: 1px;
    background-color: @border;
    margin: 4px 8px;
}

QTabWidget::pane {
    background-color: @bg_main;
    border: 1px solid @border;
    border-radius: @radius_card;
    top: -1px;
}

QTabBar::tab {
    background-color: @bg_card_elevated;
    color: @text_secondary;
    border: 1px solid @border;
    border-bottom: 3px solid transparent;
    border-top-left-radius: @radius_control;
    border-top-right-radius: @radius_control;
    padding: 10px 16px;
    margin-right: 4px;
    font-size: @font_body;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: @bg_card;
    color: @deep_navy;
    border-bottom-color: @primary_blue;
    font-weight: 700;
}

QTabBar::tab:hover:!selected {
    background-color: @selection_bg;
    color: @deep_navy;
}

QTabBar::tab:focus {
    border: 2px solid @focus_ring;
}

QGroupBox {
    background-color: @bg_card;
    border: 1px solid @border;
    border-radius: @radius_card;
    margin-top: 22px;
    padding: @space_card;
    font-size: @font_body;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: @deep_navy;
    background-color: @bg_card;
    font-size: @font_section_heading;
    font-weight: 700;
}

QFrame#card, QFrame#kpiCard, QFrame#toolbar, QFrame#sectionHeader {
    background-color: @bg_card;
    border: 1px solid @border;
    border-radius: @radius_card;
}

QLabel#pageTitle {
    color: @deep_navy;
    font-size: @font_page_heading;
    font-weight: 700;
}

QLabel#sectionTitle {
    color: @deep_navy;
    font-size: @font_section_heading;
    font-weight: 700;
}

QLabel#mutedText {
    color: @text_secondary;
}

QLabel#internalBadge {
    color: @internal_red;
    background-color: @internal_bg;
    border: 1px solid @internal_red;
    border-radius: @radius_small;
    padding: 3px 8px;
    font-size: @font_caption;
    font-weight: 700;
}

QLabel#externalBadge {
    color: @external_emerald;
    background-color: @external_bg;
    border: 1px solid @external_emerald;
    border-radius: @radius_small;
    padding: 3px 8px;
    font-size: @font_caption;
    font-weight: 700;
}

QLabel#warningBadge {
    color: @warning_amber;
    background-color: #FFF4D6;
    border: 1px solid #E8C46A;
    border-radius: @radius_small;
    padding: 3px 8px;
    font-size: @font_caption;
    font-weight: 700;
}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    color: @text_primary;
    background-color: @bg_input;
    border: 1px solid @border;
    border-radius: @radius_control;
    padding: @space_control_y @space_control_x;
    font-size: @font_body;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    min-height: 20px;
}

QTextEdit, QPlainTextEdit {
    padding: @space_control_y;
}

QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover,
QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {
    border-color: #9BAFC2;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 2px solid @focus_ring;
}

QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled,
QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
    color: @text_muted;
    background-color: #EDF1F5;
    border-color: @border;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid @border;
}

QComboBox QAbstractItemView {
    color: @text_primary;
    background-color: @bg_card;
    border: 1px solid @border;
    selection-background-color: @selection_bg;
    selection-color: @text_primary;
    padding: 4px;
    outline: none;
}

QPushButton, QToolButton {
    color: @deep_navy;
    background-color: @bg_card;
    border: 1px solid @border;
    border-radius: @radius_control;
    padding: @space_button_y @space_button_x;
    font-size: @font_button;
    font-weight: 600;
}

QPushButton:hover, QToolButton:hover {
    background-color: #EDF4FB;
    border-color: #9BAFC2;
}

QPushButton:pressed, QToolButton:pressed {
    background-color: #E1EAF3;
}

QPushButton:focus, QToolButton:focus {
    border: 2px solid @focus_ring;
}

QPushButton:disabled, QToolButton:disabled {
    color: #8796A5;
    background-color: #EDF1F5;
    border-color: #DCE3EA;
}

QPushButton#primaryBtn {
    color: #FFFFFF;
    background-color: @primary_blue;
    border-color: @primary_blue;
    font-weight: 700;
}

QPushButton#primaryBtn:hover {
    background-color: @primary_blue_hover;
    border-color: @primary_blue_hover;
}

QPushButton#primaryBtn:pressed {
    background-color: @primary_blue_pressed;
}

QPushButton#successBtn {
    color: #FFFFFF;
    background-color: @success_green;
    border-color: @success_green;
    font-weight: 700;
}

QPushButton#successBtn:hover {
    background-color: @success_green_hover;
    border-color: @success_green_hover;
}

QPushButton#accentBtn {
    color: @deep_navy;
    background-color: #E8F0F8;
    border-color: #C5D5E5;
    font-weight: 700;
}

QPushButton#accentBtn:hover {
    background-color: #DCE9F5;
    border-color: #AFC4D8;
}

QPushButton#dangerBtn {
    color: #FFFFFF;
    background-color: @danger_red;
    border-color: @danger_red;
    font-weight: 700;
}

QPushButton#dangerBtn:hover {
    background-color: @danger_red_hover;
    border-color: @danger_red_hover;
}

QPushButton#primaryBtn:focus, QPushButton#successBtn:focus,
QPushButton#accentBtn:focus, QPushButton#dangerBtn:focus {
    border: 2px solid @deep_navy;
}

QRadioButton, QCheckBox {
    color: @text_primary;
    spacing: 8px;
    font-weight: 500;
}

QRadioButton::indicator, QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #8B9BAC;
    background-color: @bg_card;
}

QRadioButton::indicator {
    border-radius: 9px;
}

QCheckBox::indicator {
    border-radius: @radius_small;
}

QRadioButton::indicator:hover, QCheckBox::indicator:hover {
    border-color: @primary_blue;
}

QRadioButton::indicator:checked {
    border-color: @primary_blue;
    background-color: @primary_blue;
}

QCheckBox::indicator:checked {
    border-color: @success_green;
    background-color: @success_green;
}

QRadioButton#internalRadio::indicator:checked {
    border-color: @internal_red;
    background-color: @internal_red;
}

QRadioButton#externalRadio::indicator:checked {
    border-color: @external_emerald;
    background-color: @external_emerald;
}

QRadioButton:focus, QCheckBox:focus {
    color: @deep_navy;
}

QRadioButton:focus::indicator, QCheckBox:focus::indicator {
    border: 2px solid @focus_ring;
}

QTableWidget, QTableView, QTreeWidget, QTreeView {
    color: @text_primary;
    background-color: @bg_card;
    alternate-background-color: #F5F8FB;
    gridline-color: #E6ECF2;
    border: 1px solid @border;
    border-radius: @radius_control;
    font-size: @font_table;
    selection-background-color: @selection_bg;
    selection-color: @text_primary;
}

QTableWidget::item, QTableView::item, QTreeWidget::item, QTreeView::item {
    padding: 6px 8px;
    border-bottom: 1px solid #E8EDF2;
}

QTableWidget::item:selected, QTableView::item:selected,
QTreeWidget::item:selected, QTreeView::item:selected {
    background-color: @selection_bg;
    color: @deep_navy;
}

QTableWidget:focus, QTableView:focus, QTreeWidget:focus, QTreeView:focus {
    border: 2px solid @focus_ring;
}

QHeaderView::section {
    color: @deep_navy;
    background-color: #EAF0F6;
    padding: 8px 10px;
    border: none;
    border-right: 1px solid @border;
    border-bottom: 1px solid @border;
    font-size: @font_table;
    font-weight: 700;
}

QSlider::groove:horizontal {
    height: 8px;
    background-color: #E1E8EF;
    border: 1px solid @border;
    border-radius: @radius_small;
}

QSlider::sub-page:horizontal {
    background-color: @primary_blue;
    border-radius: @radius_small;
}

QSlider::handle:horizontal {
    width: 18px;
    margin-top: -6px;
    margin-bottom: -6px;
    background-color: @bg_card;
    border: 2px solid @primary_blue;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover, QSlider::handle:horizontal:focus {
    background-color: @selection_bg;
    border-color: @primary_blue_hover;
}

QScrollBar:vertical {
    width: 12px;
    margin: 2px;
    border: none;
    background-color: transparent;
}

QScrollBar:horizontal {
    height: 12px;
    margin: 2px;
    border: none;
    background-color: transparent;
}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    min-width: 24px;
    min-height: 24px;
    background-color: #B8C6D4;
    border: 2px solid @bg_main;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background-color: #91A5B8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}

QStatusBar {
    color: #FFFFFF;
    background-color: @deep_navy;
    border-top: 1px solid #294660;
    padding: 5px 12px;
    font-size: @font_caption;
}

QToolTip {
    color: @text_primary;
    background-color: @bg_card;
    border: 1px solid @border_focus;
    border-radius: @radius_small;
    padding: 6px 8px;
    font-size: @font_caption;
}
"""

MODERN_LIGHT_INDUSTRIAL_QSS = _LIGHT_INDUSTRIAL_QSS
MODERN_DARK_INDUSTRIAL_QSS = MODERN_LIGHT_INDUSTRIAL_QSS

for _token_name, _token_value in _STYLE_TOKENS.items():
    MODERN_LIGHT_INDUSTRIAL_QSS = MODERN_LIGHT_INDUSTRIAL_QSS.replace(
        f"@{_token_name}", _token_value
    )
    MODERN_DARK_INDUSTRIAL_QSS = MODERN_DARK_INDUSTRIAL_QSS.replace(
        f"@{_token_name}", _token_value
    )


def get_internal_badge_style() -> str:
    """Return the shared muted-red style for Internal activity badges."""
    return f"""
        background-color: {COLORS["internal_bg"]};
        color: {COLORS["internal_red"]};
        border: 1px solid {COLORS["internal_red"]};
        border-radius: {RADII["small"]}px;
        padding: 3px 8px;
        font-weight: 700;
        font-size: {TYPOGRAPHY["caption"]};
    """


def get_external_badge_style() -> str:
    """Return the shared muted-green style for External activity badges."""
    return f"""
        background-color: {COLORS["external_bg"]};
        color: {COLORS["external_emerald"]};
        border: 1px solid {COLORS["external_emerald"]};
        border-radius: {RADII["small"]}px;
        padding: 3px 8px;
        font-weight: 700;
        font-size: {TYPOGRAPHY["caption"]};
    """


def get_digital_readout_style(
    font_size_pt: int = 24,
    text_color: str = COLORS["primary_blue"],
) -> str:
    """Return a high-contrast timer style using the shared light palette."""
    text_color = {
        "#38BDF8": COLORS["primary_blue"],
        "#10B981": COLORS["external_emerald"],
    }.get(text_color.upper(), text_color)
    return f"""
        background-color: {COLORS["digital_display_bg"]};
        color: {text_color};
        border: 2px solid {COLORS["digital_display_border"]};
        border-radius: {RADII["card"]}px;
        padding: 6px 14px;
        font-family: "Consolas", "Courier New", monospace;
        font-size: {font_size_pt}pt;
        font-weight: 700;
        letter-spacing: 2px;
    """
