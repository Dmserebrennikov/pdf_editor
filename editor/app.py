"""Application bootstrap and runtime wiring."""

from __future__ import annotations

import sys
import traceback

from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QMessageBox

from editor.ui.main_window import PdfEditorWindow
from editor.ui.styles import apply_app_style


def run() -> int:
    app = QApplication(sys.argv)
    apply_app_style(app)
    window = PdfEditorWindow()
    window.show()

    def _handle_uncaught_exception(exc_type, exc_value, exc_tb) -> None:
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(details, file=sys.stderr)
        QMessageBox.critical(
            window,
            "Unexpected error",
            f"The app hit an unexpected error:\n{exc_value}\n\nSee terminal for details.",
        )

    sys.excepthook = _handle_uncaught_exception
    return app.exec()
