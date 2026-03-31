"""Row widget for merge file list."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from editor.ui.thumbnails import THUMBNAIL_SIZE


class FileRowWidget(QWidget):
    """A row widget: thumbnail, filename, rotate button."""

    rotate_clicked = Signal(str)

    def __init__(self, path: str, thumb: QPixmap | None, parent: QWidget | None = None):
        super().__init__(parent)
        self.path = path
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(10)

        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if thumb:
            self.thumb_label.setPixmap(thumb)
        else:
            self.thumb_label.setText("?")
        layout.addWidget(self.thumb_label)

        self.name_label = QLabel(Path(path).name)
        self.name_label.setObjectName("fileRowName")
        self.name_label.setMinimumWidth(120)
        layout.addWidget(self.name_label, 1)

        self.btn_rotate = QPushButton("↻")
        self.btn_rotate.setObjectName("rotateButton")
        self.btn_rotate.setFixedSize(32, 32)
        self.btn_rotate.setToolTip("Rotate 90° clockwise")
        self.btn_rotate.clicked.connect(lambda: self.rotate_clicked.emit(self.path))
        layout.addWidget(self.btn_rotate)

    def update_thumbnail(self, thumb: QPixmap | None) -> None:
        if thumb:
            self.thumb_label.setPixmap(thumb)
        else:
            self.thumb_label.clear()
            self.thumb_label.setText("?")
