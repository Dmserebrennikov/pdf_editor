"""Main application window and page navigation."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QGuiApplication, QImage, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from editor.constants import IMAGE_EXTENSIONS, PDF_EXTENSION
from editor.processors import (
    compose_overlay_page_image,
    create_overlay_pdf,
    get_pdf_page_count,
    merge_files_to_pdf,
    render_pdf_page_image,
    split_pdf_to_individual_pages,
)
from editor.ui.thumbnails import THUMBNAIL_SIZE, create_file_thumbnail
from editor.ui.widgets.file_row import FileRowWidget
from editor.ui.widgets.selection_preview import SelectionPreviewLabel

ALLOWED_EXTENSIONS = tuple(IMAGE_EXTENSIONS | {PDF_EXTENSION})
FILE_PATH_ROLE = Qt.ItemDataRole.UserRole
ROTATION_ROLE = Qt.ItemDataRole.UserRole + 1


def get_file_filter() -> str:
    exts = " ".join(f"*{e}" for e in sorted(ALLOWED_EXTENSIONS))
    return (
        f"PDF and images ({exts});;PDF files (*.pdf);;JPEG files (*.jpg *.jpeg);;"
        "PNG files (*.png);;All supported (*.pdf *.jpg *.jpeg *.png)"
    )


class PdfEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle("PDF Editor")
        self.setMinimumSize(560, 620)
        self.setAcceptDrops(True)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.start_page = self._build_start_page()
        self.merge_page = self._build_merge_page()
        self.split_page = self._build_split_page()
        self.frankenstein_page = self._build_frankenstein_page()

        self.stack.addWidget(self.start_page)
        self.stack.addWidget(self.merge_page)
        self.stack.addWidget(self.split_page)
        self.stack.addWidget(self.frankenstein_page)
        self.stack.setCurrentWidget(self.start_page)

        self._apply_initial_window_size()

    def _build_start_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        title = QLabel("Choose a tool")
        title.setObjectName("sectionLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Available processors")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        self.btn_go_merge = QPushButton("Merge PDF")
        self.btn_go_merge.setObjectName("primaryButton")
        self.btn_go_merge.setMinimumHeight(52)
        self.btn_go_merge.clicked.connect(self._show_merge_ui)
        layout.addWidget(self.btn_go_merge)

        self.btn_go_split = QPushButton("Split PDF")
        self.btn_go_split.setObjectName("primaryButton")
        self.btn_go_split.setMinimumHeight(52)
        self.btn_go_split.clicked.connect(self._show_split_ui)
        layout.addWidget(self.btn_go_split)

        self.btn_go_frankenstein = QPushButton("Frankenstein PDF")
        self.btn_go_frankenstein.setObjectName("primaryButton")
        self.btn_go_frankenstein.setMinimumHeight(52)
        self.btn_go_frankenstein.clicked.connect(self._show_frankenstein_ui)
        layout.addWidget(self.btn_go_frankenstein)

        layout.addStretch()
        return page

    def _build_merge_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        self.btn_back_from_merge = QPushButton("← Back")
        self.btn_back_from_merge.clicked.connect(self._show_start_menu)
        header_row.addWidget(self.btn_back_from_merge)
        merge_title = QLabel("Merge PDF")
        merge_title.setObjectName("sectionLabel")
        header_row.addWidget(merge_title)
        header_row.addStretch()
        layout.addLayout(header_row)

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

        self.btn_merge = QPushButton("Merge to PDF")
        self.btn_merge.setObjectName("mergeButton")
        self.btn_merge.setMinimumHeight(44)
        self.btn_merge.clicked.connect(self._merge)
        layout.addWidget(self.btn_merge)
        layout.addStretch()
        return page

    def _build_split_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        self.btn_back_from_split = QPushButton("← Back")
        self.btn_back_from_split.clicked.connect(self._show_start_menu)
        header_row.addWidget(self.btn_back_from_split)
        split_title = QLabel("Split PDF")
        split_title.setObjectName("sectionLabel")
        header_row.addWidget(split_title)
        header_row.addStretch()
        layout.addLayout(header_row)

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
        return page

    def _build_frankenstein_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        self.btn_back_from_frankenstein = QPushButton("← Back")
        self.btn_back_from_frankenstein.clicked.connect(self._show_start_menu)
        header_row.addWidget(self.btn_back_from_frankenstein)
        franken_title = QLabel("Frankenstein PDF")
        franken_title.setObjectName("sectionLabel")
        header_row.addWidget(franken_title)
        header_row.addStretch()
        layout.addLayout(header_row)

        config_group = QGroupBox("Source pages")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(12)

        row_a = QHBoxLayout()
        row_a.addWidget(QLabel("Acceptor PDF:"))
        self.franken_pdf_a_edit = QLineEdit()
        self.franken_pdf_a_edit.setPlaceholderText("Select acceptor PDF...")
        row_a.addWidget(self.franken_pdf_a_edit, 1)
        self.btn_franken_pdf_a = QPushButton("Browse...")
        self.btn_franken_pdf_a.clicked.connect(self._choose_franken_pdf_a)
        row_a.addWidget(self.btn_franken_pdf_a)
        row_a.addWidget(QLabel("Page:"))
        self.franken_page_a_spin = QSpinBox()
        self.franken_page_a_spin.setMinimum(1)
        self.franken_page_a_spin.setMaximum(1)
        self.franken_page_a_spin.valueChanged.connect(self._refresh_franken_preview_a)
        row_a.addWidget(self.franken_page_a_spin)
        config_layout.addLayout(row_a)

        row_b = QHBoxLayout()
        row_b.addWidget(QLabel("Donor PDF:"))
        self.franken_pdf_b_edit = QLineEdit()
        self.franken_pdf_b_edit.setPlaceholderText("Select donor PDF...")
        row_b.addWidget(self.franken_pdf_b_edit, 1)
        self.btn_franken_pdf_b = QPushButton("Browse...")
        self.btn_franken_pdf_b.clicked.connect(self._choose_franken_pdf_b)
        row_b.addWidget(self.btn_franken_pdf_b)
        row_b.addWidget(QLabel("Page:"))
        self.franken_page_b_spin = QSpinBox()
        self.franken_page_b_spin.setMinimum(1)
        self.franken_page_b_spin.setMaximum(1)
        self.franken_page_b_spin.valueChanged.connect(self._refresh_franken_preview_b)
        row_b.addWidget(self.franken_page_b_spin)
        config_layout.addLayout(row_b)

        layout.addWidget(config_group)

        previews_row = QHBoxLayout()
        previews_row.setSpacing(12)

        panel_a = QVBoxLayout()
        panel_a.addWidget(QLabel("Acceptor preview (with overlay result)"))
        self.franken_preview_a = SelectionPreviewLabel(interactive=False)
        self.franken_preview_a.setText("Load acceptor PDF")
        panel_a.addWidget(self.franken_preview_a)
        a_zoom_controls = QHBoxLayout()
        self.btn_zoom_out_a = QPushButton("−")
        self.btn_zoom_out_a.clicked.connect(self.franken_preview_a.zoom_out)
        a_zoom_controls.addWidget(self.btn_zoom_out_a)
        self.btn_zoom_in_a = QPushButton("+")
        self.btn_zoom_in_a.clicked.connect(self.franken_preview_a.zoom_in)
        a_zoom_controls.addWidget(self.btn_zoom_in_a)
        self.btn_zoom_reset_a = QPushButton("Reset")
        self.btn_zoom_reset_a.clicked.connect(self.franken_preview_a.reset_zoom)
        a_zoom_controls.addWidget(self.btn_zoom_reset_a)
        self.franken_zoom_a_label = QLabel("100%")
        a_zoom_controls.addWidget(self.franken_zoom_a_label)
        a_zoom_controls.addStretch()
        panel_a.addLayout(a_zoom_controls)
        self.franken_a_count_label = QLabel("Overlay preview updates automatically")
        panel_a.addWidget(self.franken_a_count_label)
        panel_a.addWidget(QLabel("Tip: wheel to zoom, drag to pan"))
        self.franken_preview_a.zoom_changed.connect(self._update_franken_zoom_labels)

        panel_b = QVBoxLayout()
        panel_b.addWidget(QLabel("Select area on donor page"))
        self.franken_preview_b = SelectionPreviewLabel(allow_multiple=True)
        self.franken_preview_b.selection_changed.connect(self._update_franken_selection_stats)
        panel_b.addWidget(self.franken_preview_b)
        b_zoom_controls = QHBoxLayout()
        self.btn_zoom_out_b = QPushButton("−")
        self.btn_zoom_out_b.clicked.connect(self.franken_preview_b.zoom_out)
        b_zoom_controls.addWidget(self.btn_zoom_out_b)
        self.btn_zoom_in_b = QPushButton("+")
        self.btn_zoom_in_b.clicked.connect(self.franken_preview_b.zoom_in)
        b_zoom_controls.addWidget(self.btn_zoom_in_b)
        self.btn_zoom_reset_b = QPushButton("Reset")
        self.btn_zoom_reset_b.clicked.connect(self.franken_preview_b.reset_zoom)
        b_zoom_controls.addWidget(self.btn_zoom_reset_b)
        self.franken_zoom_b_label = QLabel("100%")
        b_zoom_controls.addWidget(self.franken_zoom_b_label)
        b_zoom_controls.addStretch()
        panel_b.addLayout(b_zoom_controls)
        b_controls = QHBoxLayout()
        self.btn_clear_b = QPushButton("Clear donor area")
        self.btn_clear_b.clicked.connect(self.franken_preview_b.clear_selections)
        b_controls.addWidget(self.btn_clear_b)
        self.franken_b_count_label = QLabel("0 selected")
        b_controls.addWidget(self.franken_b_count_label)
        b_controls.addStretch()
        panel_b.addLayout(b_controls)
        panel_b.addWidget(QLabel("Tip: wheel to zoom, right-drag or Shift+drag to pan"))
        self.franken_preview_b.zoom_changed.connect(self._update_franken_zoom_labels)

        previews_row.addLayout(panel_a, 1)
        previews_row.addLayout(panel_b, 1)
        layout.addLayout(previews_row)

        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        output_layout.setSpacing(12)
        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Folder:"))
        self.franken_folder_edit = QLineEdit()
        self.franken_folder_edit.setPlaceholderText("Select output folder...")
        output_row.addWidget(self.franken_folder_edit)
        self.btn_franken_folder = QPushButton("Browse...")
        self.btn_franken_folder.clicked.connect(self._choose_franken_output_folder)
        output_row.addWidget(self.btn_franken_folder)
        output_layout.addLayout(output_row)

        output_name_row = QHBoxLayout()
        output_name_row.addWidget(QLabel("File name:"))
        self.franken_name_edit = QLineEdit("frankenstein.pdf")
        output_name_row.addWidget(self.franken_name_edit)
        output_layout.addLayout(output_name_row)
        layout.addWidget(output_group)

        self.btn_create_frankenstein = QPushButton("Create Overlay PDF")
        self.btn_create_frankenstein.setObjectName("mergeButton")
        self.btn_create_frankenstein.setMinimumHeight(42)
        self.btn_create_frankenstein.clicked.connect(self._create_frankenstein_pdf)
        layout.addWidget(self.btn_create_frankenstein)

        self._franken_base_image = None
        self._franken_donor_image = None
        self._update_franken_zoom_labels()

        layout.addStretch()
        return page

    def _show_start_menu(self) -> None:
        self.stack.setCurrentWidget(self.start_page)

    def _show_merge_ui(self) -> None:
        self.stack.setCurrentWidget(self.merge_page)

    def _show_split_ui(self) -> None:
        self.stack.setCurrentWidget(self.split_page)

    def _show_frankenstein_ui(self) -> None:
        self.stack.setCurrentWidget(self.frankenstein_page)

    @staticmethod
    def _pil_to_qpixmap(image) -> QPixmap:
        rgb = image.convert("RGB")
        data = rgb.tobytes("raw", "RGB")
        bytes_per_line = rgb.width * 3
        qimg = QImage(data, rgb.width, rgb.height, bytes_per_line, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimg.copy())

    def _choose_franken_pdf_a(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select acceptor PDF", "", "PDF files (*.pdf)")
        if not path:
            return
        self.franken_pdf_a_edit.setText(path)
        try:
            page_count = get_pdf_page_count(Path(path))
            self.franken_page_a_spin.setMaximum(max(1, page_count))
            self.franken_page_a_spin.setValue(1)
            self._refresh_franken_preview_a()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unable to load acceptor PDF:\n{e}")

    def _choose_franken_pdf_b(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select donor PDF", "", "PDF files (*.pdf)")
        if not path:
            return
        self.franken_pdf_b_edit.setText(path)
        try:
            page_count = get_pdf_page_count(Path(path))
            self.franken_page_b_spin.setMaximum(max(1, page_count))
            self.franken_page_b_spin.setValue(1)
            self._refresh_franken_preview_b()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unable to load donor PDF:\n{e}")

    def _refresh_franken_preview_a(self, *_args) -> None:
        path = self.franken_pdf_a_edit.text().strip()
        if not path:
            self.franken_preview_a.set_preview_pixmap(None)
            self.franken_preview_a.setText("Load acceptor PDF")
            self._franken_base_image = None
            return
        try:
            image = render_pdf_page_image(Path(path), self.franken_page_a_spin.value() - 1, dpi=110)
            self._franken_base_image = image
            self._update_franken_overlay_preview()
        except Exception:
            self._franken_base_image = None
            self.franken_preview_a.set_preview_pixmap(None)
            self.franken_preview_a.setText("Unable to render acceptor preview")

    def _refresh_franken_preview_b(self, *_args) -> None:
        path = self.franken_pdf_b_edit.text().strip()
        if not path:
            self.franken_preview_b.set_preview_pixmap(None)
            self._franken_donor_image = None
            self._update_franken_overlay_preview()
            return
        try:
            image = render_pdf_page_image(Path(path), self.franken_page_b_spin.value() - 1, dpi=110)
            self._franken_donor_image = image
            self.franken_preview_b.set_preview_pixmap(self._pil_to_qpixmap(image))
            self._update_franken_overlay_preview()
        except Exception:
            self._franken_donor_image = None
            self.franken_preview_b.set_preview_pixmap(None)
            self._update_franken_overlay_preview()

    def _update_franken_selection_stats(self) -> None:
        count_b = len(self.franken_preview_b.get_normalized_rectangles())
        self.franken_b_count_label.setText(f"{count_b} selected")
        self._update_franken_overlay_preview()

    def _update_franken_zoom_labels(self, *_args) -> None:
        self.franken_zoom_a_label.setText(f"{int(round(self.franken_preview_a.get_zoom_factor() * 100))}%")
        self.franken_zoom_b_label.setText(f"{int(round(self.franken_preview_b.get_zoom_factor() * 100))}%")

    def _update_franken_overlay_preview(self) -> None:
        if self._franken_base_image is None:
            return
        result = self._franken_base_image
        donor_rectangles = self.franken_preview_b.get_normalized_rectangles()
        if self._franken_donor_image is not None and donor_rectangles:
            try:
                result = compose_overlay_page_image(
                    self._franken_base_image,
                    self._franken_donor_image,
                    donor_rectangles,
                )
            except Exception:
                pass

        self.franken_preview_a.set_preview_pixmap(self._pil_to_qpixmap(result))

    def _choose_franken_output_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select output folder")
        if path:
            self.franken_folder_edit.setText(path)

    def _create_frankenstein_pdf(self) -> None:
        pdf_a = self.franken_pdf_a_edit.text().strip()
        pdf_b = self.franken_pdf_b_edit.text().strip()
        output_folder = self.franken_folder_edit.text().strip()
        output_name = self.franken_name_edit.text().strip()
        if not pdf_a or not pdf_b:
            QMessageBox.warning(self, "Missing input", "Choose both acceptor and donor PDFs.")
            return
        if not output_folder:
            QMessageBox.warning(self, "No folder", "Choose an output folder.")
            return
        if not output_name:
            QMessageBox.warning(self, "No file name", "Enter an output file name.")
            return
        if not output_name.lower().endswith(".pdf"):
            output_name += ".pdf"

        rectangles_b = self.franken_preview_b.get_normalized_rectangles()
        if not rectangles_b:
            QMessageBox.warning(self, "No donor area", "Select an area on the donor preview.")
            return
        try:
            out_path = Path(output_folder) / output_name
            create_overlay_pdf(
                Path(pdf_a),
                self.franken_page_a_spin.value() - 1,
                Path(pdf_b),
                self.franken_page_b_spin.value() - 1,
                rectangles_b,
                out_path,
            )
            QMessageBox.information(self, "Done", f"Saved overlay PDF to:\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create overlay PDF:\n{e}")

    def _apply_initial_window_size(self) -> None:
        """Set a taller default size while adapting to the current screen."""
        hint = self.sizeHint()
        desired_width = max(1200, hint.width() + 160)
        desired_height = max(900, hint.height() + 120)

        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            max_width = int(available.width() * 0.97)
            max_height = int(available.height() * 0.95)
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
        row_widget.rotate_clicked.connect(self._rotate_file)
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
        if self.stack.currentWidget() is self.merge_page and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        if self.stack.currentWidget() is not self.merge_page:
            event.ignore()
            return
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
