"""
PDF Editor — Join PDF and image files into a single PDF.
Modern PySide6 interface.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QLineEdit,
    QGroupBox,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent

from pdf_merge import merge_files_to_pdf, IMAGE_EXTENSIONS, PDF_EXTENSION

ALLOWED_EXTENSIONS = tuple(IMAGE_EXTENSIONS | {PDF_EXTENSION})


def get_file_filter() -> str:
    exts = " ".join(f"*{e}" for e in sorted(ALLOWED_EXTENSIONS))
    return f"PDF and images ({exts});;PDF files (*.pdf);;JPEG files (*.jpg *.jpeg);;PNG files (*.png);;All supported (*.pdf *.jpg *.jpeg *.png)"


class PdfEditorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.file_list: list[str] = []
        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        self.setWindowTitle("PDF Editor — Join PDFs & Images")
        self.setMinimumSize(520, 480)
        self.resize(600, 520)
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

        layout.addStretch()

    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e2e;
            }
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QLabel {
                color: #cdd6f4;
            }
            QLabel#sectionLabel {
                font-size: 13px;
                font-weight: 600;
                color: #89b4fa;
            }
            QListWidget {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 8px;
                color: #cdd6f4;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 6px 10px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #45475a;
                color: #89b4fa;
            }
            QListWidget::item:hover {
                background-color: #45475a;
            }
            QGroupBox {
                font-weight: 600;
                color: #89b4fa;
                border: 1px solid #45475a;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 0 8px;
                background-color: #1e1e2e;
            }
            QLineEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 8px 12px;
                color: #cdd6f4;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border: none;
                border-radius: 6px;
                padding: 10px 18px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #585b70;
            }
            QPushButton:pressed {
                background-color: #313244;
            }
            QPushButton#primaryButton {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QPushButton#primaryButton:hover {
                background-color: #b4befe;
            }
            QPushButton#mergeButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton#mergeButton:hover {
                background-color: #94e2d5;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and path not in self.file_list:
                suffix = Path(path).suffix.lower()
                if suffix in ALLOWED_EXTENSIONS:
                    self.file_list.append(path)
                    self.list_widget.addItem(Path(path).name)
        event.acceptProposedAction()

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select PDF or image files",
            "",
            get_file_filter(),
        )
        for p in paths:
            if p and p not in self.file_list:
                self.file_list.append(p)
                self.list_widget.addItem(Path(p).name)

    def _remove_selected(self) -> None:
        indices = [i.row() for i in self.list_widget.selectedIndexes()]
        for i in sorted(indices, reverse=True):
            self.list_widget.takeItem(i)
            del self.file_list[i]

    def _clear_list(self) -> None:
        self.list_widget.clear()
        self.file_list.clear()

    def _choose_output_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select output folder")
        if path:
            self.folder_edit.setText(path)

    def _merge(self) -> None:
        if not self.file_list:
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
        try:
            merge_files_to_pdf([Path(p) for p in self.file_list], out_path)
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
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    window = PdfEditorApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
