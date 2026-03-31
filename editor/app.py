"""Application bootstrap and runtime wiring."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from editor.ui.main_window import PdfEditorWindow
from editor.ui.styles import apply_app_style


def run() -> int:
    app = QApplication(sys.argv)
    apply_app_style(app)
    window = PdfEditorWindow()
    window.show()
    return app.exec()
