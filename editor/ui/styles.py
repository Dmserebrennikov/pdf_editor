"""
Application styles and theme configuration.
Centralizes all Qt stylesheets and visual settings.
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

# --- Theme colors (Catppuccin Mocha palette) ---
BG_BASE = "#1e1e2e"
BG_SURFACE = "#313244"
BG_OVERLAY = "#45475a"
BG_HOVER = "#585b70"
BORDER = "#45475a"
TEXT = "#cdd6f4"
ACCENT = "#89b4fa"
ACCENT_HOVER = "#b4befe"
SUCCESS = "#a6e3a1"
SUCCESS_HOVER = "#94e2d5"


def get_stylesheet() -> str:
    """Return the application stylesheet."""
    return f"""
        QMainWindow {{
            background-color: {BG_BASE};
        }}
        QWidget {{
            background-color: {BG_BASE};
            color: {TEXT};
        }}
        QLabel {{
            color: {TEXT};
        }}
        QLabel#sectionLabel {{
            font-size: 13px;
            font-weight: 600;
            color: {ACCENT};
        }}
        QListWidget {{
            background-color: {BG_SURFACE};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 8px;
            color: {TEXT};
            font-size: 12px;
        }}
        QListWidget::item {{
            padding: 8px 12px;
            border-radius: 4px;
        }}
        QListWidget::item:selected {{
            background-color: {BG_OVERLAY};
            color: {ACCENT};
        }}
        QListWidget::item:hover {{
            background-color: {BG_OVERLAY};
        }}
        QGroupBox {{
            font-weight: 600;
            color: {ACCENT};
            border: 1px solid {BORDER};
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 16px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            padding: 0 8px;
            background-color: {BG_BASE};
        }}
        QLineEdit {{
            background-color: {BG_SURFACE};
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 8px 12px;
            color: {TEXT};
            font-size: 12px;
        }}
        QLineEdit:focus {{
            border-color: {ACCENT};
        }}
        QPushButton {{
            background-color: {BG_OVERLAY};
            color: {TEXT};
            border: none;
            border-radius: 6px;
            padding: 10px 18px;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {BG_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {BG_SURFACE};
        }}
        QPushButton#primaryButton {{
            background-color: {ACCENT};
            color: {BG_BASE};
        }}
        QPushButton#primaryButton:hover {{
            background-color: {ACCENT_HOVER};
        }}
        QPushButton#mergeButton {{
            background-color: {SUCCESS};
            color: {BG_BASE};
            font-size: 14px;
            font-weight: 600;
        }}
        QPushButton#mergeButton:hover {{
            background-color: {SUCCESS_HOVER};
        }}
        QPushButton#rotateButton {{
            padding: 4px;
            font-size: 16px;
        }}
        QLabel#fileRowName {{
            color: {TEXT};
        }}
    """


def apply_app_style(app: QApplication) -> None:
    """Apply global application styling (font, style, stylesheet)."""
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(get_stylesheet())
