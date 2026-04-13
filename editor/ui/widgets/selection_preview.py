"""Interactive preview label with rectangle selection support."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPaintEvent, QPainter, QPen, QPixmap, QWheelEvent
from PySide6.QtWidgets import QLabel


class SelectionPreviewLabel(QLabel):
    """Preview widget that lets user draw rectangular selections."""

    selection_changed = Signal()
    zoom_changed = Signal(float)

    def __init__(self, allow_multiple: bool = True, interactive: bool = True):
        super().__init__()
        self._allow_multiple = allow_multiple
        self._interactive = interactive
        self.setMinimumSize(300, 420)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("border: 1px solid #45475a; background-color: #313244;")
        self._pixmap: QPixmap | None = None
        self._rectangles_norm: list[QRectF] = []
        self._start_pos: QPoint | None = None
        self._current_rect: QRect | None = None
        self._zoom_factor = 1.0
        self._min_zoom = 0.3
        self._max_zoom = 5.0
        self._pan_offset = QPointF(0.0, 0.0)
        self._is_panning = False
        self._pan_start = QPointF()
        self._pan_origin = QPointF()
        self._drag_rect_index: int | None = None
        self._drag_mode: str | None = None
        self._drag_start_pos = QPoint()
        self._drag_start_rect = QRect()

    def set_preview_pixmap(self, pixmap: QPixmap | None) -> None:
        self._pixmap = pixmap
        self.clear_selections()
        self.set_zoom_factor(1.0)
        self._pan_offset = QPointF(0.0, 0.0)
        self.update()

    def clear_selections(self) -> None:
        self._rectangles_norm.clear()
        self._start_pos = None
        self._current_rect = None
        self._drag_rect_index = None
        self._drag_mode = None
        self.unsetCursor()
        self.selection_changed.emit()
        self.update()

    def get_normalized_rectangles(self) -> list[tuple[float, float, float, float]]:
        return [(r.x(), r.y(), r.width(), r.height()) for r in self._rectangles_norm]

    def zoom_in(self) -> None:
        self.set_zoom_factor(self._zoom_factor * 1.2)

    def zoom_out(self) -> None:
        self.set_zoom_factor(self._zoom_factor / 1.2)

    def reset_zoom(self) -> None:
        self.set_zoom_factor(1.0)
        self._pan_offset = QPointF(0.0, 0.0)
        self.update()

    def set_zoom_factor(self, value: float) -> None:
        clamped = max(self._min_zoom, min(self._max_zoom, value))
        if abs(clamped - self._zoom_factor) < 1e-6:
            return
        self._zoom_factor = clamped
        self.zoom_changed.emit(self._zoom_factor)
        self.update()

    def get_zoom_factor(self) -> float:
        return self._zoom_factor

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        event.accept()

    def _scaled_size(self):
        if not self._pixmap or self._pixmap.isNull():
            return None
        base_scaled = self._pixmap.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        return (
            max(1, int(round(base_scaled.width() * self._zoom_factor))),
            max(1, int(round(base_scaled.height() * self._zoom_factor))),
        )

    def _clamped_pan(self, scaled_w: int, scaled_h: int) -> QPointF:
        max_x = max(0.0, (scaled_w - self.width()) / 2.0)
        max_y = max(0.0, (scaled_h - self.height()) / 2.0)
        x = max(-max_x, min(max_x, self._pan_offset.x()))
        y = max(-max_y, min(max_y, self._pan_offset.y()))
        return QPointF(x, y)

    def _image_rect(self) -> QRect:
        if not self._pixmap or self._pixmap.isNull():
            return QRect()
        scaled = self._scaled_size()
        if scaled is None:
            return QRect()
        scaled_w, scaled_h = scaled
        pan = self._clamped_pan(scaled_w, scaled_h)
        x = int((self.width() - scaled_w) / 2 + pan.x())
        y = int((self.height() - scaled_h) / 2 + pan.y())
        return QRect(x, y, scaled_w, scaled_h)

    def _to_normalized(self, rect: QRect) -> QRectF:
        img_rect = self._image_rect()
        if img_rect.isNull():
            return QRectF()
        x = (rect.x() - img_rect.x()) / img_rect.width()
        y = (rect.y() - img_rect.y()) / img_rect.height()
        w = rect.width() / img_rect.width()
        h = rect.height() / img_rect.height()
        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))
        w = max(0.0, min(1.0 - x, w))
        h = max(0.0, min(1.0 - y, h))
        return QRectF(x, y, w, h)

    def _from_normalized(self, rect: QRectF) -> QRect:
        img_rect = self._image_rect()
        return QRect(
            img_rect.x() + int(rect.x() * img_rect.width()),
            img_rect.y() + int(rect.y() * img_rect.height()),
            int(rect.width() * img_rect.width()),
            int(rect.height() * img_rect.height()),
        )

    def _resize_cursor_for_mode(self, mode: str):
        if mode in ("tl", "br"):
            return Qt.CursorShape.SizeFDiagCursor
        if mode in ("tr", "bl"):
            return Qt.CursorShape.SizeBDiagCursor
        if mode in ("l", "r"):
            return Qt.CursorShape.SizeHorCursor
        if mode in ("t", "b"):
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.SizeAllCursor

    def _hit_test_selection(self, pos: QPoint) -> tuple[int | None, str | None]:
        margin = 14
        for idx in range(len(self._rectangles_norm) - 1, -1, -1):
            rect = self._from_normalized(self._rectangles_norm[idx])
            if rect.width() <= 0 or rect.height() <= 0:
                continue
            if not rect.adjusted(-margin, -margin, margin, margin).contains(pos):
                continue

            dx_left = abs(pos.x() - rect.left())
            dx_right = abs(pos.x() - rect.right())
            dy_top = abs(pos.y() - rect.top())
            dy_bottom = abs(pos.y() - rect.bottom())

            near_left = dx_left <= margin
            near_right = dx_right <= margin
            near_top = dy_top <= margin
            near_bottom = dy_bottom <= margin

            if near_left and near_top:
                return idx, "tl"
            if near_right and near_top:
                return idx, "tr"
            if near_left and near_bottom:
                return idx, "bl"
            if near_right and near_bottom:
                return idx, "br"
            if near_left:
                return idx, "l"
            if near_right:
                return idx, "r"
            if near_top:
                return idx, "t"
            if near_bottom:
                return idx, "b"
            # Border bands (wider than exact-line hit) improve usability.
            if rect.contains(pos):
                dist_x = min(dx_left, dx_right)
                dist_y = min(dy_top, dy_bottom)
                if dist_x <= margin:
                    return idx, "l" if dx_left <= dx_right else "r"
                if dist_y <= margin:
                    return idx, "t" if dy_top <= dy_bottom else "b"
            if rect.contains(pos):
                return idx, "move"
        return None, None

    def _clamp_rect_to_image(self, rect: QRect, keep_size: bool) -> QRect:
        img = self._image_rect()
        if img.isNull():
            return rect
        out = QRect(rect)
        min_size = 8
        if keep_size:
            if out.left() < img.left():
                out.translate(img.left() - out.left(), 0)
            if out.right() > img.right():
                out.translate(img.right() - out.right(), 0)
            if out.top() < img.top():
                out.translate(0, img.top() - out.top())
            if out.bottom() > img.bottom():
                out.translate(0, img.bottom() - out.bottom())
            return out

        left = max(img.left(), min(out.left(), img.right() - min_size))
        top = max(img.top(), min(out.top(), img.bottom() - min_size))
        right = max(left + min_size, min(out.right(), img.right()))
        bottom = max(top + min_size, min(out.bottom(), img.bottom()))
        return QRect(QPoint(left, top), QPoint(right, bottom))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        can_pan = self._pixmap is not None and not self._image_rect().isNull()
        wants_pan = (
            event.button() in (Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton)
            or (event.button() == Qt.MouseButton.LeftButton and not self._interactive)
            or (
                event.button() == Qt.MouseButton.LeftButton
                and bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            )
        )
        if can_pan and wants_pan:
            self._is_panning = True
            self._pan_start = event.position()
            self._pan_origin = QPointF(self._pan_offset)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if not self._interactive:
            return super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and not self._image_rect().isNull():
            pos = event.position().toPoint()
            idx, mode = self._hit_test_selection(pos)
            if idx is not None and mode is not None:
                self._drag_rect_index = idx
                self._drag_mode = mode
                self._drag_start_pos = pos
                self._drag_start_rect = self._from_normalized(self._rectangles_norm[idx])
                self.setCursor(self._resize_cursor_for_mode(mode))
                event.accept()
                return
            if self._image_rect().contains(pos):
                self._start_pos = pos
                self._current_rect = QRect(self._start_pos, self._start_pos)
                self.update()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_panning:
            delta = event.position() - self._pan_start
            self._pan_offset = self._pan_origin + delta
            self.update()
            event.accept()
            return

        if not self._interactive:
            return super().mouseMoveEvent(event)
        if self._drag_rect_index is not None and self._drag_mode is not None:
            pos = event.position().toPoint()
            delta = pos - self._drag_start_pos
            rect = QRect(self._drag_start_rect)
            min_size = 8

            if self._drag_mode == "move":
                rect.translate(delta)
                rect = self._clamp_rect_to_image(rect, keep_size=True)
            else:
                left = rect.left()
                right = rect.right()
                top = rect.top()
                bottom = rect.bottom()
                if "l" in self._drag_mode:
                    left = min(left + delta.x(), right - min_size)
                if "r" in self._drag_mode:
                    right = max(right + delta.x(), left + min_size)
                if "t" in self._drag_mode:
                    top = min(top + delta.y(), bottom - min_size)
                if "b" in self._drag_mode:
                    bottom = max(bottom + delta.y(), top + min_size)
                rect = QRect(QPoint(left, top), QPoint(right, bottom))
                rect = self._clamp_rect_to_image(rect, keep_size=False)

            normalized = self._to_normalized(rect.normalized())
            if normalized.width() > 0 and normalized.height() > 0:
                self._rectangles_norm[self._drag_rect_index] = normalized
                self.selection_changed.emit()
                self.update()
            event.accept()
            return

        if self._start_pos is not None:
            img_rect = self._image_rect()
            pos = event.position().toPoint()
            pos.setX(max(img_rect.left(), min(img_rect.right(), pos.x())))
            pos.setY(max(img_rect.top(), min(img_rect.bottom(), pos.y())))
            self._current_rect = QRect(self._start_pos, pos).normalized()
            self.update()
            return
        idx, mode = self._hit_test_selection(event.position().toPoint())
        if idx is not None and mode is not None:
            self.setCursor(self._resize_cursor_for_mode(mode))
        else:
            self.unsetCursor()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._is_panning and event.button() in (
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.RightButton,
            Qt.MouseButton.MiddleButton,
        ):
            self._is_panning = False
            self.unsetCursor()
            event.accept()
            return

        if not self._interactive:
            return super().mouseReleaseEvent(event)
        if self._drag_rect_index is not None:
            self._drag_rect_index = None
            self._drag_mode = None
            self.unsetCursor()
            event.accept()
            return
        if self._start_pos is not None and self._current_rect is not None:
            rect = self._current_rect.normalized()
            self._start_pos = None
            self._current_rect = None
            if rect.width() >= 8 and rect.height() >= 8:
                normalized = self._to_normalized(rect)
                if normalized.width() > 0 and normalized.height() > 0:
                    if not self._allow_multiple:
                        self._rectangles_norm.clear()
                    self._rectangles_norm.append(normalized)
                    self.selection_changed.emit()
            self.update()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if not self._pixmap or self._pixmap.isNull():
            return

        painter = QPainter(self)
        img_rect = self._image_rect()
        painter.drawPixmap(img_rect, self._pixmap, self._pixmap.rect())

        pen_saved = QPen(Qt.GlobalColor.cyan, 2)
        painter.setPen(pen_saved)
        for rect_norm in self._rectangles_norm:
            painter.drawRect(self._from_normalized(rect_norm))

        if self._current_rect is not None:
            pen_current = QPen(Qt.GlobalColor.yellow, 2, Qt.PenStyle.DashLine)
            painter.setPen(pen_current)
            painter.drawRect(self._current_rect.normalized())
