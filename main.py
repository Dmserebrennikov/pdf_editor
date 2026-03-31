"""
PDF Editor — Join PDF and image files into a single PDF.
Modern PySide6 interface.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLineEdit,
    QGroupBox,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QImage, QGuiApplication

from editor.processors import (
    merge_files_to_pdf,
    split_pdf_to_individual_pages,
    IMAGE_EXTENSIONS,
    PDF_EXTENSION,
)
from styles import apply_app_style

ALLOWED_EXTENSIONS = tuple(IMAGE_EXTENSIONS | {PDF_EXTENSION})

THUMBNAIL_SIZE = 48
FILE_PATH_ROLE = Qt.ItemDataRole.UserRole
ROTATION_ROLE = Qt.ItemDataRole.UserRole + 1


def _thumbnail_for_image(path: Path, rotation: int = 0) -> QPixmap | None:
    """Generate a thumbnail from an image file."""
    try:
        img = Image.open(path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        if rotation:
            img = img.rotate(-rotation, expand=True)
        img.thumbnail((THUMBNAIL_SIZE * 2, THUMBNAIL_SIZE * 2), Image.Resampling.LANCZOS)
        data = img.tobytes("raw", "RGB")
        qimg = QImage(data, img.width, img.height, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimg).scaled(
            THUMBNAIL_SIZE, THUMBNAIL_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
    except Exception:
        return None


def _thumbnail_for_pdf(path: Path, rotation: int = 0) -> QPixmap | None:
    """Generate a thumbnail from the first page of a PDF."""
    try:
        import fitz
        doc = fitz.open(path)
        if len(doc) == 0:
            doc.close()
            return None
        page = doc[0]
        scale = THUMBNAIL_SIZE / max(page.rect.width, page.rect.height)
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        if rotation:
            img = img.rotate(-rotation, expand=True)
        data = img.tobytes("raw", "RGB")
        qimg = QImage(data, img.width, img.height, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimg).scaled(
            THUMBNAIL_SIZE, THUMBNAIL_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
    except Exception:
        return None


def create_file_thumbnail(path: str, rotation: int = 0) -> QPixmap | None:
    """Create a small thumbnail for a file (image or PDF)."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return _thumbnail_for_image(p, rotation)
    if suffix == PDF_EXTENSION:
        return _thumbnail_for_pdf(p, rotation)
    return None


def get_file_filter() -> str:
    exts = " ".join(f"*{e}" for e in sorted(ALLOWED_EXTENSIONS))
    return f"PDF and images ({exts});;PDF files (*.pdf);;JPEG files (*.jpg *.jpeg);;PNG files (*.png);;All supported (*.pdf *.jpg *.jpeg *.png)"


class FileRowWidget(QWidget):
    """A row widget: thumbnail, filename, rotate button."""

    rotateClicked = Signal(str)

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
        self.btn_rotate.clicked.connect(lambda: self.rotateClicked.emit(self.path))
        layout.addWidget(self.btn_rotate)

    def update_thumbnail(self, thumb: QPixmap | None) -> None:
        if thumb:
            self.thumb_label.setPixmap(thumb)
        else:
            self.thumb_label.clear()
            self.thumb_label.setText("?")


class PdfEditorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle("PDF Editor — Join PDFs & Images")
        self.setMinimumSize(560, 620)
        self.setAcceptDrops(True)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Files section
        files_label = QLabel("Files to join (PDF, JPEG, PNG)")
        files_label.setObjectName("sectionLabel")
        layout.addWidget(files_label)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_widget.setMinimumHeight(160)
        self.list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.list_widget.setIconSize(QSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE))
        self.list_widget.setSpacing(6)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_add = QPushButton("Add files…")
        self.btn_add.setObjectName("primaryButton")
        self.btn_add.clicked.connect(self._add_files)

        self.btn_remove = QPushButton("Remove selected")
        self.btn_remove.clicked.connect(self._remove_selected)

        self.btn_clear = QPushButton("Clear all")
        self.btn_clear.clicked.connect(self._clear_list)

        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_remove)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Output section
        output_group = QGroupBox("Output")
        output_group.setObjectName("outputGroup")
        output_layout = QVBoxLayout(output_group)
        output_layout.setSpacing(12)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Folder:"))
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Select output folder…")
        folder_row.addWidget(self.folder_edit)

        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.clicked.connect(self._choose_output_folder)
        folder_row.addWidget(self.btn_browse)
        output_layout.addLayout(folder_row)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("File name:"))
        self.filename_edit = QLineEdit()
        self.filename_edit.setPlaceholderText("merged.pdf")
        self.filename_edit.setText("merged.pdf")
        name_row.addWidget(self.filename_edit)
        output_layout.addLayout(name_row)

        layout.addWidget(output_group)

        # Merge button
        self.btn_merge = QPushButton("Merge to PDF")
        self.btn_merge.setObjectName("mergeButton")
        self.btn_merge.setMinimumHeight(44)
        self.btn_merge.clicked.connect(self._merge)
        layout.addWidget(self.btn_merge)

        # Split section
        split_group = QGroupBox("Split PDF into pages")
        split_group.setObjectName("outputGroup")
        split_layout = QVBoxLayout(split_group)
        split_layout.setSpacing(12)

        split_input_row = QHBoxLayout()
        split_input_row.addWidget(QLabel("Input PDF:"))
        self.split_input_edit = QLineEdit()
        self.split_input_edit.setPlaceholderText("Select a PDF file to split…")
        split_input_row.addWidget(self.split_input_edit)
        self.btn_split_input_browse = QPushButton("Browse…")
        self.btn_split_input_browse.clicked.connect(self._choose_split_input_pdf)
        split_input_row.addWidget(self.btn_split_input_browse)
        split_layout.addLayout(split_input_row)

        split_folder_row = QHBoxLayout()
        split_folder_row.addWidget(QLabel("Output folder:"))
        self.split_folder_edit = QLineEdit()
        self.split_folder_edit.setPlaceholderText("Select output folder…")
        split_folder_row.addWidget(self.split_folder_edit)
        self.btn_split_folder_browse = QPushButton("Browse…")
        self.btn_split_folder_browse.clicked.connect(self._choose_split_output_folder)
        split_folder_row.addWidget(self.btn_split_folder_browse)
        split_layout.addLayout(split_folder_row)

        split_prefix_row = QHBoxLayout()
        split_prefix_row.addWidget(QLabel("File prefix:"))
        self.split_prefix_edit = QLineEdit()
        self.split_prefix_edit.setPlaceholderText("Optional (defaults to source file name)")
        split_prefix_row.addWidget(self.split_prefix_edit)
        split_layout.addLayout(split_prefix_row)

        self.btn_split = QPushButton("Split PDF")
        self.btn_split.setObjectName("primaryButton")
        self.btn_split.setMinimumHeight(40)
        self.btn_split.clicked.connect(self._split_pdf)
        split_layout.addWidget(self.btn_split)

        layout.addWidget(split_group)

        layout.addStretch()
        self._apply_initial_window_size()

    def _apply_initial_window_size(self) -> None:
        """Set a taller default size while adapting to the current screen."""
        hint = self.sizeHint()
        desired_width = max(700, hint.width() + 40)
        desired_height = max(760, hint.height() + 60)

        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            max_width = int(available.width() * 0.9)
            max_height = int(available.height() * 0.9)
            desired_width = min(desired_width, max_width)
            desired_height = min(desired_height, max_height)

        self.resize(desired_width, desired_height)

    def _get_file_list(self) -> list[tuple[str, int]]:
        """Return (path, rotation) tuples in current widget order."""
        result = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            path = item.data(FILE_PATH_ROLE)
            rotation = item.data(ROTATION_ROLE)
            if path is not None:
                result.append((path, rotation if isinstance(rotation, int) else 0))
        return result

    def _add_file_item(self, path: str) -> None:
        """Add a file to the list with its thumbnail preview and rotate button."""
        existing_paths = [p for p, _ in self._get_file_list()]
        if path in existing_paths:
            return
        item = QListWidgetItem()
        item.setData(FILE_PATH_ROLE, path)
        item.setData(ROTATION_ROLE, 0)
        item.setSizeHint(QSize(400, THUMBNAIL_SIZE + 12))
        thumb = create_file_thumbnail(path, 0)
        row_widget = FileRowWidget(path, thumb)
        row_widget.rotateClicked.connect(self._rotate_file)
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, row_widget)

    def _rotate_file(self, path: str) -> None:
        """Rotate the given file 90° clockwise and update its thumbnail."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(FILE_PATH_ROLE) == path:
                rotation = item.data(ROTATION_ROLE) or 0
                rotation = (rotation + 90) % 360
                item.setData(ROTATION_ROLE, rotation)
                row_widget = self.list_widget.itemWidget(item)
                if isinstance(row_widget, FileRowWidget):
                    thumb = create_file_thumbnail(path, rotation)
                    row_widget.update_thumbnail(thumb)
                break

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                suffix = Path(path).suffix.lower()
                if suffix in ALLOWED_EXTENSIONS:
                    self._add_file_item(path)
        event.acceptProposedAction()

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select PDF or image files",
            "",
            get_file_filter(),
        )
        for p in paths:
            if p:
                self._add_file_item(p)

    def _remove_selected(self) -> None:
        indices = [i.row() for i in self.list_widget.selectedIndexes()]
        for i in sorted(indices, reverse=True):
            self.list_widget.takeItem(i)

    def _clear_list(self) -> None:
        self.list_widget.clear()

    def _choose_output_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select output folder")
        if path:
            self.folder_edit.setText(path)

    def _choose_split_input_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF file",
            "",
            "PDF files (*.pdf)",
        )
        if path:
            self.split_input_edit.setText(path)

    def _choose_split_output_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select output folder")
        if path:
            self.split_folder_edit.setText(path)

    def _split_pdf(self) -> None:
        input_pdf = self.split_input_edit.text().strip()
        if not input_pdf:
            QMessageBox.warning(
                self,
                "No input PDF",
                "Choose a PDF file to split.",
            )
            return

        output_folder = self.split_folder_edit.text().strip()
        if not output_folder:
            QMessageBox.warning(
                self,
                "No folder",
                "Choose an output folder.",
            )
            return

        prefix = self.split_prefix_edit.text().strip()

        try:
            created_files = split_pdf_to_individual_pages(
                Path(input_pdf),
                Path(output_folder),
                prefix if prefix else None,
            )
            QMessageBox.information(
                self,
                "Done",
                f"Created {len(created_files)} file(s) in:\n{output_folder}",
            )
        except FileNotFoundError as e:
            QMessageBox.critical(self, "File error", str(e))
        except ValueError as e:
            QMessageBox.critical(self, "Error", str(e))
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Split failed:\n{e}",
            )

    def _merge(self) -> None:
        file_list = self._get_file_list()
        if not file_list:
            QMessageBox.warning(
                self,
                "No files",
                "Add at least one file to join.",
            )
            return
        folder = self.folder_edit.text().strip()
        if not folder:
            QMessageBox.warning(
                self,
                "No folder",
                "Choose an output folder.",
            )
            return
        name = self.filename_edit.text().strip()
        if not name:
            QMessageBox.warning(
                self,
                "No file name",
                "Enter an output file name.",
            )
            return
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        out_path = Path(folder) / name
        paths = [Path(p) for p, _ in file_list]
        rotations = [r for _, r in file_list]
        try:
            merge_files_to_pdf(paths, out_path, rotations)
            QMessageBox.information(
                self,
                "Done",
                f"Saved to:\n{out_path}",
            )
        except FileNotFoundError as e:
            QMessageBox.critical(self, "File error", str(e))
        except ValueError as e:
            QMessageBox.critical(self, "Error", str(e))
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Merge failed:\n{e}",
            )


def main() -> None:
    app = QApplication(sys.argv)
    apply_app_style(app)
    window = PdfEditorApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
