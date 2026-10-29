"""
SMED Studio - Modern Dark Industrial QSS Stylesheet & Visual Tokens
High-contrast, professional engineering aesthetic tailored for manufacturing and industrial engineers.
"""

COLORS = {
    "bg_darkest": "#0B0F17",
    "bg_main": "#121826",
    "bg_card": "#1E293B",
    "bg_card_elevated": "#26354A",
    "bg_input": "#0F172A",
    "border": "#334155",
    "border_focus": "#0EA5E9",
    "accent_cyan": "#0EA5E9",
    "accent_cyan_hover": "#38BDF8",
    "accent_cyan_pressed": "#0284C7",
    "text_primary": "#F8FAFC",
    "text_secondary": "#94A3B8",
    "text_muted": "#64748B",
    "internal_red": "#EF4444",
    "internal_bg": "rgba(239, 68, 68, 0.18)",
    "external_emerald": "#10B981",
    "external_bg": "rgba(16, 185, 129, 0.18)",
    "warning_amber": "#F59E0B",
    "digital_display_bg": "#080D15",
    "digital_display_border": "#1E293B",
}

MODERN_DARK_INDUSTRIAL_QSS = """
/* === Global Application Reset === */
QWidget {
    background-color: #121826;
    color: #F8FAFC;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Roboto", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    selection-background-color: #0EA5E9;
    selection-color: #FFFFFF;
}

QMainWindow {
    background-color: #0B0F17;
}

/* === Main Tab Bar Navigation === */
QTabWidget::pane {
    border: 1px solid #1E293B;
    background-color: #121826;
    border-radius: 6px;
    top: -1px;
}

QTabBar::tab {
    background-color: #1E293B;
    color: #94A3B8;
    padding: 10px 20px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
    font-size: 13px;
    border: 1px solid #334155;
    border-bottom: none;
}

QTabBar::tab:selected {
    background-color: #121826;
    color: #38BDF8;
    border-top: 3px solid #0EA5E9;
    border-left: 1px solid #334155;
    border-right: 1px solid #334155;
}

QTabBar::tab:hover:!selected {
    background-color: #26354A;
    color: #F8FAFC;
}

/* === Panel Cards & Group Boxes === */
QGroupBox {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 24px;
    padding: 16px;
    font-weight: 700;
    font-size: 13px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    left: 14px;
    background-color: #26354A;
    color: #38BDF8;
    border: 1px solid #334155;
    border-radius: 4px;
}

/* === Input Fields === */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #0F172A;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 13px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #0EA5E9;
    background-color: #141E33;
}

QLineEdit:disabled, QTextEdit:disabled {
    background-color: #182234;
    color: #64748B;
    border: 1px solid #233044;
}

/* === Combo Boxes === */
QComboBox {
    background-color: #0F172A;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    min-height: 24px;
}

QComboBox:hover {
    border: 1px solid #0EA5E9;
}

QComboBox:on {
    border: 1px solid #0EA5E9;
    background-color: #141E33;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 26px;
    border-left: 1px solid #334155;
}

QComboBox QAbstractItemView {
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid #334155;
    selection-background-color: #0EA5E9;
    selection-color: #FFFFFF;
    padding: 4px;
    border-radius: 6px;
    outline: none;
}

/* === Push Buttons === */
QPushButton {
    background-color: #26354A;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #334155;
    border: 1px solid #475569;
}

QPushButton:pressed {
    background-color: #1E293B;
}

QPushButton:disabled {
    background-color: #182234;
    color: #64748B;
    border: 1px solid #233044;
}

/* Primary Cyan Action Button */
QPushButton#primaryBtn {
    background-color: #0EA5E9;
    color: #FFFFFF;
    border: 1px solid #0284C7;
    font-weight: 700;
}

QPushButton#primaryBtn:hover {
    background-color: #38BDF8;
    border: 1px solid #0EA5E9;
}

QPushButton#primaryBtn:pressed {
    background-color: #0284C7;
}

/* Success Emerald Button */
QPushButton#successBtn {
    background-color: #10B981;
    color: #FFFFFF;
    border: 1px solid #059669;
    font-weight: 700;
}

QPushButton#successBtn:hover {
    background-color: #34D399;
}

QPushButton#successBtn:pressed {
    background-color: #059669;
}

/* Accent Indigo/Violet Button */
QPushButton#accentBtn {
    background-color: #6366F1;
    color: #FFFFFF;
    border: 1px solid #4F46E5;
    font-weight: 700;
}

QPushButton#accentBtn:hover {
    background-color: #818CF8;
    border: 1px solid #6366F1;
}

QPushButton#accentBtn:pressed {
    background-color: #4338CA;
}

/* Danger / Stop Red Button */
QPushButton#dangerBtn {
    background-color: #EF4444;
    color: #FFFFFF;
    border: 1px solid #DC2626;
    font-weight: 700;
}

QPushButton#dangerBtn:hover {
    background-color: #F87171;
}

QPushButton#dangerBtn:pressed {
    background-color: #DC2626;
}

/* === Radio Buttons & Checkboxes === */
QRadioButton {
    color: #F8FAFC;
    font-weight: 600;
    spacing: 8px;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid #64748B;
    background-color: #0F172A;
}

QRadioButton::indicator:hover {
    border-color: #0EA5E9;
}

QRadioButton::indicator:checked {
    border-color: #0EA5E9;
    background-color: #0EA5E9;
}

QCheckBox {
    color: #F8FAFC;
    font-weight: 600;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #64748B;
    background-color: #0F172A;
}

QCheckBox::indicator:hover {
    border-color: #0EA5E9;
}

QCheckBox::indicator:checked {
    border-color: #10B981;
    background-color: #10B981;
}

/* === Tables === */
QTableWidget {
    background-color: #121826;
    color: #F8FAFC;
    gridline-color: #26354A;
    border: 1px solid #334155;
    border-radius: 6px;
    font-size: 13px;
}

QTableWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #1E293B;
}

QTableWidget::item:selected {
    background-color: #26354A;
    color: #38BDF8;
    font-weight: 600;
}

QHeaderView::section {
    background-color: #1E293B;
    color: #94A3B8;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #334155;
    border-right: 1px solid #26354A;
    font-weight: 700;
    font-size: 12px;
    text-transform: uppercase;
}

/* === Sliders (Video Seek Timeline) === */
QSlider::groove:horizontal {
    height: 8px;
    background: #1E293B;
    border: 1px solid #334155;
    border-radius: 4px;
}

QSlider::sub-page:horizontal {
    background: #0EA5E9;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background: #F8FAFC;
    border: 2px solid #0EA5E9;
    width: 18px;
    margin-top: -6px;
    margin-bottom: -6px;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #38BDF8;
    border-color: #FFFFFF;
}

/* === Scrollbars === */
QScrollBar:vertical {
    border: none;
    background-color: #0F172A;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #334155;
    min-height: 24px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background-color: #0F172A;
    height: 10px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #334155;
    min-width: 24px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #475569;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* === Status Bar === */
QStatusBar {
    background-color: #0B0F17;
    color: #94A3B8;
    border-top: 1px solid #1E293B;
    padding: 4px 12px;
    font-size: 12px;
}

/* === Tooltips === */
QToolTip {
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid #0EA5E9;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 12px;
}
"""


def get_internal_badge_style() -> str:
    """CSS styling for Internal (Machine Stopped) activity badges."""
    return """
        background-color: rgba(239, 68, 68, 0.22);
        color: #FCA5A5;
        border: 1px solid #EF4444;
        border-radius: 4px;
        padding: 3px 8px;
        font-weight: 700;
        font-size: 11px;
    """


def get_external_badge_style() -> str:
    """CSS styling for External (Machine Running) activity badges."""
    return """
        background-color: rgba(16, 185, 129, 0.22);
        color: #6EE7B7;
        border: 1px solid #10B981;
        border-radius: 4px;
        padding: 3px 8px;
        font-weight: 700;
        font-size: 11px;
    """


def get_digital_readout_style(font_size_pt: int = 24, text_color: str = "#38BDF8") -> str:
    """CSS styling for high-contrast digital stopwatch LCD displays."""
    return f"""
        background-color: #080D15;
        color: {text_color};
        border: 2px solid #1E293B;
        border-radius: 8px;
        padding: 6px 14px;
        font-family: "Consolas", "Courier New", monospace;
        font-size: {font_size_pt}pt;
        font-weight: 700;
        letter-spacing: 2px;
    """
