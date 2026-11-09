"""
Custom high-DPI Qt6 widgets for EasyColab Studio (Windows):
  - StatusDot, PillBadge, SidebarCard, WorkspaceCard, CollapsibleBox
  - SingleMetricChartWidget & CombinedTelemetryChartWidget (Catmull-Rom Bezier splines + hover crosshair)
  - FrameDropWell (drag & drop + file picker + 0.92 JPEG raw base64 encoder)
  - MediaPreviewWidget (QtMultimedia MP4 + 32kHz stereo audio player + 2K image viewer)
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt, QUrl, Signal
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QImage,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget

    HAS_QT_MULTIMEDIA = True
except Exception:
    HAS_QT_MULTIMEDIA = False

from windows_app.models import format_duration, open_path_in_os, tr
from windows_app.theme import LIGHT_PALETTE, StudioPalette


def set_btn_role(btn: QPushButton, role: str) -> QPushButton:
    btn.setProperty("btnRole", role)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


class StatusDot(QWidget):
    """8x8 antialiased status indicator dot."""

    def __init__(self, color_hex: str = "#64748B", size: int = 9, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._color = QColor(color_hex)
        self.setFixedSize(size + 4, size + 4)
        self._dot_size = size

    def set_color(self, color_hex: str) -> None:
        c = QColor(color_hex)
        if c != self._color:
            self._color = c
            self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        glow = QColor(self._color)
        glow.setAlpha(65)
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r = self._dot_size / 2.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QPointF(cx, cy), r + 1.8, r + 1.8)
        p.setBrush(self._color)
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.end()


class PillBadge(QLabel):
    """Compact rounded badge label."""

    def __init__(
        self,
        text: str = "",
        fg: str = "#94A3B8",
        bg: str = "rgba(148, 163, 184, 0.15)",
        mono: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(text, parent)
        self._mono = mono
        self.set_badge_style(fg, bg)

    def set_badge_style(self, fg: str, bg: str) -> None:
        ff = '"Consolas", "Cascadia Mono", monospace' if self._mono else '"Segoe UI", "Microsoft YaHei UI", sans-serif'
        self.setStyleSheet(
            f"QLabel {{ color: {fg}; background-color: {bg}; border-radius: 9px; "
            f"padding: 2px 8px; font-size: 11px; font-weight: 600; font-family: {ff}; }}"
        )


class SidebarCard(QFrame):
    """Rounded card used in the Left Sidebar."""

    def __init__(
        self,
        title: str,
        trailing: Optional[QWidget] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("SidebarCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 11, 12, 12)
        root.setSpacing(9)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 12.5px; font-weight: 700; background: transparent; border: none;")
        header.addWidget(self.title_label)
        header.addStretch(1)
        if trailing is not None:
            header.addWidget(trailing)
        root.addLayout(header)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(8)
        root.addLayout(self.body)


class WorkspaceCard(QFrame):
    """Rounded card used in the Center Studio Workspace."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        icon_text: str = "",
        trailing: Optional[QWidget] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("WorkspaceCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 15)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(2)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(6)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 13.5px; font-weight: 700; background: transparent; border: none;")
        title_row.addWidget(self.title_label)
        title_row.addStretch(1)
        title_col.addLayout(title_row)

        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setWordWrap(True)
            self.subtitle_label.setStyleSheet(
                "font-size: 11.5px; color: #64748B; background: transparent; border: none;"
            )
            title_col.addWidget(self.subtitle_label)
        else:
            self.subtitle_label = None

        header.addLayout(title_col, 1)
        if trailing is not None:
            header.addWidget(trailing, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(10)
        root.addLayout(self.body)


class AutoHeightStackedWidget(QWidget):
    """
    Drop-in replacement for QStackedWidget that places pages in a QVBoxLayout
    and toggles .setVisible(i == index). Preserves 100% native Qt heightForWidth
    word-wrapping and dynamic child resizing inside QScrollArea!
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._pages: List[QWidget] = []
        self._current_idx: int = 0
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(0)

    def addWidget(self, w: QWidget) -> int:
        idx = len(self._pages)
        self._pages.append(w)
        self._lay.addWidget(w)
        w.setVisible(idx == self._current_idx)
        return idx

    def count(self) -> int:
        return len(self._pages)

    def widget(self, index: int) -> Optional[QWidget]:
        return self._pages[index] if 0 <= index < len(self._pages) else None

    def currentWidget(self) -> Optional[QWidget]:
        return self.widget(self._current_idx)

    def setCurrentIndex(self, index: int) -> None:
        self._current_idx = index
        for i, w in enumerate(self._pages):
            w.setVisible(i == index)


class ModeRadioCard(QFrame):
    """Clickable horizontal radio card with word-wrapped subtitle so center column never overflows."""

    clicked = Signal()

    def __init__(
        self,
        glyph: str,
        title: str,
        subtitle: str,
        selected: bool,
        pal: StudioPalette,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        bg = pal.selected_card_bg if selected else pal.input_fill
        bd = f"1.5px solid {pal.selected_card_border}" if selected else f"1px solid {pal.card_border}"
        self.setStyleSheet(
            f"ModeRadioCard {{ background-color: {bg}; border: {bd}; border-radius: 9px; }}"
            f"ModeRadioCard:hover {{ border-color: {pal.accent_blue}; }}"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(11, 8, 11, 8)
        lay.setSpacing(3)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(6)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"font-size: 12.5px; font-weight: 700; color: {pal.text_primary}; border: none;")
        top.addWidget(t_lbl, 1)
        if selected:
            badge_fg = "#60A5FA" if pal.is_dark else "#2563EB"
            top.addWidget(PillBadge(tr("当前模式", "Active"), fg=badge_fg, bg="rgba(59,130,246,0.14)"))
        lay.addLayout(top)

        s_lbl = QLabel(subtitle)
        s_lbl.setWordWrap(True)
        s_lbl.setStyleSheet(f"font-size: 11px; color: {pal.text_secondary}; border: none;")
        lay.addWidget(s_lbl)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class CollapsibleBox(QWidget):
    """Expandable/collapsible disclosure container."""

    def __init__(self, title: str, expanded: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._expanded = expanded
        self._base_title = title

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.toggle_btn = set_btn_role(QPushButton(), "ghost")
        self.toggle_btn.setStyleSheet(
            "QPushButton { text-align: left; font-size: 11.5px; font-weight: 600; color: #64748B; padding: 3px 4px; }"
            "QPushButton:hover { color: #2563EB; }"
        )
        self.toggle_btn.clicked.connect(self.toggle)
        layout.addWidget(self.toggle_btn)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(4, 2, 4, 4)
        self.content_layout.setSpacing(4)
        layout.addWidget(self.content)

        self._refresh_state()

    def set_title(self, title: str) -> None:
        self._base_title = title
        self._refresh_state()

    def toggle(self) -> None:
        self._expanded = not self._expanded
        self._refresh_state()

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self._refresh_state()

    def _refresh_state(self) -> None:
        prefix = "[-]" if self._expanded else "[+]"
        self.toggle_btn.setText(f"{prefix} {self._base_title}")
        self.content.setVisible(self._expanded)


# ─── Catmull-Rom Smooth Spline Telemetry Charts ──────────────────────────────


def build_smooth_spline_paths(
    samples: List[float],
    width: float,
    height: float,
    top_inset: float = 5.0,
    bottom_inset: float = 4.0,
) -> Tuple[QPainterPath, QPainterPath, List[QPointF]]:
    """
    Exact port of macOS buildSmoothTelemetryPaths:
    Catmull-Rom to cubic Bezier conversion with flat-plateau overshoot clamping.
    """
    stroke = QPainterPath()
    fill = QPainterPath()
    if not samples or width <= 2 or height <= (top_inset + bottom_inset + 2):
        return stroke, fill, []

    vals = samples if len(samples) >= 2 else [samples[0], samples[0]]
    n = len(vals)
    min_y = top_inset
    max_y = height - bottom_inset
    usable_h = max(1.0, max_y - min_y)

    pts: List[QPointF] = []
    for i, raw in enumerate(vals):
        pct = max(0.0, min(1.0, float(raw)))
        x = (i / float(n - 1)) * width
        y = max_y - pct * usable_h
        pts.append(QPointF(x, y))

    stroke.moveTo(pts[0])
    for i in range(n - 1):
        p0 = pts[max(0, i - 1)]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[min(n - 1, i + 2)]
        if abs(p2.y() - p1.y()) < 0.25:
            stroke.lineTo(p2)
        else:
            dx = p2.x() - p1.x()
            cp1_y = max(min_y, min(max_y, p1.y() + (p2.y() - p0.y()) / 6.0))
            cp2_y = max(min_y, min(max_y, p2.y() - (p3.y() - p1.y()) / 6.0))
            stroke.cubicTo(
                QPointF(p1.x() + dx / 3.0, cp1_y),
                QPointF(p2.x() - dx / 3.0, cp2_y),
                p2,
            )

    fill = QPainterPath(stroke)
    fill.lineTo(QPointF(pts[-1].x(), height))
    fill.lineTo(QPointF(pts[0].x(), height))
    fill.closeSubpath()
    return stroke, fill, pts


class SingleMetricChartWidget(QWidget):
    """Single-metric smooth area chart with hover crosshair and GB/% tooltip."""

    def __init__(self, label: str, accent_hex: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.label = label
        self.accent_hex = accent_hex
        self.samples: List[float] = []
        self.used_gb: float = 0.0
        self.total_gb: float = 0.0
        self._hover_x: Optional[float] = None
        self._palette: StudioPalette = LIGHT_PALETTE
        self.setMouseTracking(True)
        self.setFixedHeight(56)

    def set_palette_theme(self, pal: StudioPalette) -> None:
        self._palette = pal
        self.update()

    def update_metric(
        self,
        samples: List[float],
        used_gb: float,
        total_gb: float,
        accent_hex: str,
    ) -> None:
        self.samples = list(samples)
        self.used_gb = used_gb
        self.total_gb = total_gb
        self.accent_hex = accent_hex
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._hover_x = float(event.position().x())
        self.update()

    def leaveEvent(self, _event) -> None:
        self._hover_x = None
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w = float(self.width())
        h = float(self.height())

        bg = QColor(self._palette.input_fill)
        border = QColor(self._palette.card_border)
        box = QPainterPath()
        box.addRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), 7, 7)
        p.fillPath(box, bg)

        # Header caption inside top of chart box
        header_h = 18.0
        chart_top = header_h + 2.0
        p.save()
        p.setClipPath(box)

        # Subtle horizontal grid line
        grid_pen = QPen(QColor(148, 163, 184, 30), 1, Qt.PenStyle.DashLine)
        p.setPen(grid_pen)
        mid_y = chart_top + (h - chart_top) * 0.5
        p.drawLine(QPointF(4, mid_y), QPointF(w - 4, mid_y))

        accent = QColor(self.accent_hex)
        if self.samples:
            # Shift spline into [chart_top .. h]
            sub_h = h - chart_top
            stroke, fill, pts = build_smooth_spline_paths(self.samples, w, sub_h, top_inset=3.0, bottom_inset=2.0)
            p.save()
            p.translate(0, chart_top)
            grad = QLinearGradient(QPointF(0, 0), QPointF(0, sub_h))
            c_top = QColor(accent)
            c_top.setAlpha(72)
            c_bot = QColor(accent)
            c_bot.setAlpha(4)
            grad.setColorAt(0.0, c_top)
            grad.setColorAt(1.0, c_bot)
            p.fillPath(fill, grad)
            p.setPen(QPen(accent, 1.8))
            p.drawPath(stroke)

            if self._hover_x is not None and pts:
                hx = max(0.0, min(w, self._hover_x))
                idx = int(round((hx / max(1.0, w)) * (len(self.samples) - 1)))
                idx = max(0, min(len(self.samples) - 1, idx))
                pt = pts[idx]
                dash_pen = QPen(QColor(226, 232, 240, 140), 1.0, Qt.PenStyle.DashLine)
                p.setPen(dash_pen)
                p.drawLine(QPointF(pt.x(), 0), QPointF(pt.x(), sub_h))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(accent)
                p.drawEllipse(pt, 3.2, 3.2)
            p.restore()

        p.restore()
        p.setPen(QPen(border, 1.0))
        p.drawPath(box)

        # Draw title (left) and value / hover tooltip (right)
        font = QFont("Segoe UI", 9)
        font.setWeight(QFont.Weight.DemiBold)
        p.setFont(font)
        p.setPen(QColor(self._palette.text_secondary))
        p.drawText(QRectF(8, 2, w * 0.48, header_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.label)

        mono_font = QFont("Consolas", 8)
        mono_font.setWeight(QFont.Weight.Bold)
        p.setFont(mono_font)
        if self._hover_x is not None and self.samples and self.total_gb > 0:
            idx = int(round((max(0.0, min(w, self._hover_x)) / max(1.0, w)) * (len(self.samples) - 1)))
            idx = max(0, min(len(self.samples) - 1, idx))
            pct = max(0.0, min(1.0, self.samples[idx]))
            gb_val = pct * self.total_gb
            val_str = f"{gb_val:.1f} GB ({pct * 100:.0f}%)"
            p.setPen(accent)
        elif self.total_gb > 0:
            pct = (self.used_gb / self.total_gb) * 100.0
            val_str = f"{self.used_gb:.1f}/{self.total_gb:.0f}G ({pct:.0f}%)"
            p.setPen(QColor(self._palette.text_primary))
        else:
            val_str = "-- / -- GB"
            p.setPen(QColor(self._palette.text_muted))
        p.drawText(QRectF(w * 0.30, 2, w * 0.70 - 10, header_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, val_str)
        p.end()


class CombinedTelemetryChartWidget(QWidget):
    """Combined 3-metric overlay line chart (VRAM + RAM + Disk) with interactive crosshair."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._palette: StudioPalette = LIGHT_PALETTE
        self._series: List[Tuple[str, List[float], float, float, str]] = []
        self._hover_x: Optional[float] = None
        self.setMouseTracking(True)
        self.setFixedHeight(112)

    def set_palette_theme(self, pal: StudioPalette) -> None:
        self._palette = pal
        self.update()

    def update_all(self, series: List[Tuple[str, List[float], float, float, str]]) -> None:
        """series: list of (name, samples, used_gb, total_gb, color_hex)."""
        self._series = series
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._hover_x = float(event.position().x())
        self.update()

    def leaveEvent(self, _event) -> None:
        self._hover_x = None
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w = float(self.width())
        h = float(self.height())
        legend_h = 22.0
        chart_h = h - legend_h

        box = QPainterPath()
        box.addRoundedRect(QRectF(0.5, 0.5, w - 1.0, chart_h - 1.0), 7, 7)
        p.fillPath(box, QColor(self._palette.input_fill))

        p.save()
        p.setClipPath(box)
        grid_pen = QPen(QColor(148, 163, 184, 28), 1, Qt.PenStyle.DashLine)
        p.setPen(grid_pen)
        for frac in (0.25, 0.5, 0.75):
            gy = chart_h * frac
            p.drawLine(QPointF(4, gy), QPointF(w - 4, gy))

        hover_idx_ratio: Optional[float] = None
        if self._hover_x is not None:
            hover_idx_ratio = max(0.0, min(1.0, self._hover_x / max(1.0, w)))
            hx = hover_idx_ratio * w
            p.setPen(QPen(QColor(226, 232, 240, 130), 1.0, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(hx, 2), QPointF(hx, chart_h - 2))

        for _name, samples, _used, _total, color_hex in self._series:
            if not samples:
                continue
            stroke, fill, pts = build_smooth_spline_paths(samples, w, chart_h, top_inset=5.0, bottom_inset=4.0)
            col = QColor(color_hex)
            fill_col = QColor(col)
            fill_col.setAlpha(24)
            p.fillPath(fill, fill_col)
            p.setPen(QPen(col, 1.8))
            p.drawPath(stroke)
            if hover_idx_ratio is not None and pts:
                idx = int(round(hover_idx_ratio * (len(pts) - 1)))
                idx = max(0, min(len(pts) - 1, idx))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(col)
                p.drawEllipse(pts[idx], 3.0, 3.0)

        p.restore()
        p.setPen(QPen(QColor(self._palette.card_border), 1.0))
        p.drawPath(box)

        # Bottom compact 3-item legend
        font = QFont("Consolas", 8.5)
        font.setWeight(QFont.Weight.DemiBold)
        p.setFont(font)
        col_w = w / max(1, len(self._series))
        for i, (name, samples, used, total, color_hex) in enumerate(self._series):
            x0 = i * col_w
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(color_hex))
            p.drawEllipse(QPointF(x0 + 5, chart_h + legend_h * 0.52), 3.5, 3.5)
            p.setPen(QColor(self._palette.text_secondary))
            if hover_idx_ratio is not None and samples and total > 0:
                idx = int(round(hover_idx_ratio * (len(samples) - 1)))
                idx = max(0, min(len(samples) - 1, idx))
                pct = samples[idx] * 100.0
                txt = f"{name} {pct:.0f}%"
            elif total > 0:
                txt = f"{name} {used:.0f}/{total:.0f}G"
            else:
                txt = f"{name} --"
            p.drawText(
                QRectF(x0 + 12, chart_h + 1, col_w - 14, legend_h - 1),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                txt,
            )
        p.end()


# ─── Drag-and-Drop Image Frame Well ──────────────────────────────────────────


class FrameDropWell(QFrame):
    """Drag-and-drop or click-to-select image input well with JPEG 0.92 raw base64 output."""

    image_changed = Signal()

    def __init__(self, title: str, subtitle: Optional[str] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._title = title
        self._subtitle = subtitle if subtitle is not None else tr("拖拽或点击选择图片", "Drag & drop or click to select image")
        self._image: Optional[QImage] = None
        self._file_path: Optional[Path] = None
        self._drag_hover = False
        self._palette: StudioPalette = LIGHT_PALETTE

        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(148)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(2, 0, 2, 0)
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-size: 11.5px; font-weight: 600; color: #64748B; background: transparent;")
        top_row.addWidget(self.title_lbl)
        top_row.addStretch(1)

        self.clear_btn = set_btn_role(QPushButton(tr("清除", "Clear")), "ghost")
        self.clear_btn.setStyleSheet(
            "QPushButton { font-size: 11px; color: #DC2626; padding: 1px 6px; border-radius: 4px; }"
            "QPushButton:hover { background-color: rgba(239,68,68,0.14); }"
        )
        self.clear_btn.clicked.connect(self.clear_image)
        self.clear_btn.setVisible(False)
        top_row.addWidget(self.clear_btn)
        root.addLayout(top_row)

        self.preview_lbl = QLabel(self._subtitle)
        self.preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_lbl.setWordWrap(True)
        self.preview_lbl.setStyleSheet("font-size: 12px; color: #64748B; background: transparent;")
        root.addWidget(self.preview_lbl, 1)

    def has_image(self) -> bool:
        return self._image is not None and not self._image.isNull()

    def clear_image(self) -> None:
        self._image = None
        self._file_path = None
        self.clear_btn.setVisible(False)
        self.preview_lbl.setPixmap(QPixmap())
        self.preview_lbl.setText(self._subtitle)
        self.update()
        self.image_changed.emit()

    def load_from_file(self, path: Path) -> bool:
        img = QImage(str(path))
        if img.isNull():
            return False
        self._image = img
        self._file_path = path
        self.clear_btn.setVisible(True)
        self._refresh_thumbnail()
        self.update()
        self.image_changed.emit()
        return True

    def to_jpeg_base64(self, quality: int = 92) -> Optional[str]:
        """Encode loaded QImage as JPEG quality 0.92 raw base64 (no data: prefix)."""
        if not self.has_image():
            return None
        assert self._image is not None
        rgb_img = self._image.convertToFormat(QImage.Format.Format_RGB888)
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        rgb_img.save(buf, "JPG", quality)
        raw = bytes(buf.data())
        buf.close()
        return base64.b64encode(raw).decode("ascii")

    def _refresh_thumbnail(self) -> None:
        if not self.has_image():
            return
        assert self._image is not None
        pix = QPixmap.fromImage(self._image)
        avail_w = max(80, self.width() - 24)
        avail_h = max(60, self.height() - 42)
        scaled = pix.scaled(
            avail_w,
            avail_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_lbl.setText("")
        self.preview_lbl.setPixmap(scaled)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.has_image():
            self._refresh_thumbnail()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                tr(f"选择图片 — {self._title}", f"Select Image — {self._title}"),
                str(Path.home()),
                tr("图像文件 (*.png *.jpg *.jpeg *.webp *.bmp)", "Image Files (*.png *.jpg *.jpeg *.webp *.bmp)"),
            )
            if file_path:
                self.load_from_file(Path(file_path))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for u in event.mimeData().urls():
                if u.isLocalFile() and Path(u.toLocalFile()).suffix.lower() in {
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".webp",
                    ".bmp",
                }:
                    self._drag_hover = True
                    self.update()
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragLeaveEvent(self, _event) -> None:
        self._drag_hover = False
        self.update()

    def dropEvent(self, event: QDropEvent) -> None:
        self._drag_hover = False
        for u in event.mimeData().urls():
            if u.isLocalFile():
                p = Path(u.toLocalFile())
                if self.load_from_file(p):
                    event.acceptProposedAction()
                    return
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(1.0, 1.0, self.width() - 2.0, self.height() - 2.0)
        path = QPainterPath()
        path.addRoundedRect(rect, 9, 9)
        bg = QColor("#1E293B") if self._drag_hover else QColor(self._palette.input_fill)
        p.fillPath(path, bg)
        pen_col = QColor("#3B82F6") if self._drag_hover else QColor(self._palette.input_border)
        pen = QPen(pen_col, 1.4, Qt.PenStyle.SolidLine if self.has_image() else Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.drawPath(path)
        p.end()

    def set_palette_theme(self, pal: StudioPalette) -> None:
        self._palette = pal
        self.update()


# ─── Aspect-Ratio Image Viewer + MP4 Stereo Video Player ─────────────────────


class AspectImageLabel(QWidget):
    """Smoothly scales a high-res QPixmap to fit container while preserving aspect ratio."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._pixmap: Optional[QPixmap] = None
        self.setMinimumHeight(240)

    def set_image_path(self, path: Optional[Path]) -> None:
        if path and path.exists():
            pix = QPixmap(str(path))
            self._pixmap = pix if not pix.isNull() else None
        else:
            self._pixmap = None
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.fillRect(self.rect(), QColor("#0F1114"))
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
        p.end()


class MediaPreviewWidget(QFrame):
    """
    Unified Video (MP4 w/ 32kHz stereo audio via QtMultimedia) & Image (2K PNG/JPG)
    studio preview card matching macOS mediaPreviewCard.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("WorkspaceCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(335)
        self._current_path: Optional[Path] = None
        self._is_image: bool = False
        self._slider_dragging: bool = False
        self._palette: StudioPalette = LIGHT_PALETTE

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        # Top header strip (title + elapsed pill)
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(2, 0, 2, 0)
        self.header_lbl = QLabel(tr("成片预览舞台", "Output Preview Stage"))
        self.header_lbl.setStyleSheet("font-size: 12.5px; font-weight: 700; background: transparent; border: none;")
        top_bar.addWidget(self.header_lbl)
        top_bar.addStretch(1)

        self.elapsed_badge = PillBadge("", fg="#059669", bg="rgba(16, 185, 129, 0.14)", mono=True)
        self.elapsed_badge.setVisible(False)
        top_bar.addWidget(self.elapsed_badge)
        root.addLayout(top_bar)

        # Stage stack (theme-aware empty stage, theater dark when playing media)
        self.stage_frame = QFrame()
        stage_layout = QVBoxLayout(self.stage_frame)
        stage_layout.setContentsMargins(0, 0, 0, 0)
        stage_layout.setSpacing(0)

        self.stack = QStackedWidget()
        # Page 0: Empty placeholder
        self.empty_page = QWidget()
        ep_layout = QVBoxLayout(self.empty_page)
        ep_lbl = QLabel(
            tr(
                "生成的有声视频与高清海报将自动回传并在此播放\n支持 24 FPS 视频 + 32 kHz 立体声音轨实时预览",
                "Generated audio-videos & HD images are automatically saved and played here\nSupports real-time 24 FPS video + 32 kHz stereo audio preview",
            )
        )
        ep_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ep_lbl.setStyleSheet("color: #64748B; font-size: 12.5px; line-height: 1.5; background: transparent; border: none;")
        ep_layout.addWidget(ep_lbl)
        self.stack.addWidget(self.empty_page)

        # Page 1: Video player
        video_page = QWidget()
        video_page.setStyleSheet("background-color: #0F1114;")
        vp_layout = QVBoxLayout(video_page)
        vp_layout.setContentsMargins(0, 0, 0, 0)
        vp_layout.setSpacing(0)

        if HAS_QT_MULTIMEDIA:
            self.video_widget = QVideoWidget()
            self.video_widget.setMinimumHeight(230)
            self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            vp_layout.addWidget(self.video_widget, 1)

            self.audio_output = QAudioOutput(self)
            self.audio_output.setVolume(0.9)
            self.player = QMediaPlayer(self)
            self.player.setAudioOutput(self.audio_output)
            self.player.setVideoOutput(self.video_widget)
            self.player.positionChanged.connect(self._on_position_changed)
            self.player.durationChanged.connect(self._on_duration_changed)
            self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        else:
            self.video_widget = None
            self.audio_output = None
            self.player = None
            fallback = QLabel(
                tr(
                    "当前环境未加载 QtMultimedia，请点击下方「用默认播放器打开」观看有声视频",
                    "QtMultimedia is unavailable here. Click 'Replay / Open' below to play in default media player.",
                )
            )
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback.setStyleSheet("color: #94A3B8;")
            vp_layout.addWidget(fallback, 1)

        # Video transport controls bar
        ctrl_bar = QWidget()
        ctrl_bar.setStyleSheet("background-color: #161920; border-top: 1px solid #262A34;")
        ctrl_layout = QHBoxLayout(ctrl_bar)
        ctrl_layout.setContentsMargins(8, 4, 8, 4)
        ctrl_layout.setSpacing(8)

        self.play_btn = set_btn_role(QPushButton(tr("播放", "Play")), "ghost")
        self.play_btn.setFixedWidth(60)
        self.play_btn.setStyleSheet("color: #E2E8F0; font-size: 11.5px;")
        self.play_btn.clicked.connect(self.toggle_play_pause)
        ctrl_layout.addWidget(self.play_btn)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderPressed.connect(lambda: setattr(self, "_slider_dragging", True))
        self.seek_slider.sliderReleased.connect(self._on_seek_released)
        ctrl_layout.addWidget(self.seek_slider, 1)

        self.time_lbl = QLabel("00:00 / 00:00")
        self.time_lbl.setStyleSheet("color: #94A3B8; font-family: Consolas, monospace; font-size: 11px;")
        ctrl_layout.addWidget(self.time_lbl)

        self.mute_btn = set_btn_role(QPushButton(tr("静音", "Mute")), "ghost")
        self.mute_btn.setFixedWidth(64)
        self.mute_btn.setStyleSheet("color: #E2E8F0; font-size: 11.5px;")
        self.mute_btn.clicked.connect(self._toggle_mute)
        ctrl_layout.addWidget(self.mute_btn)

        vp_layout.addWidget(ctrl_bar)
        self.stack.addWidget(video_page)

        # Page 2: Image viewer
        self.image_viewer = AspectImageLabel()
        self.stack.addWidget(self.image_viewer)

        stage_layout.addWidget(self.stack, 1)
        root.addWidget(self.stage_frame, 1)

        # Bottom file info & OS actions bar
        bot = QHBoxLayout()
        bot.setContentsMargins(2, 0, 2, 0)
        bot.setSpacing(8)
        self.filename_lbl = QLabel(tr("尚未选择本地成片", "No local media selected"))
        self.filename_lbl.setStyleSheet("color: #64748B; font-family: Consolas, monospace; font-size: 11.5px;")
        bot.addWidget(self.filename_lbl, 1)

        self.replay_or_open_btn = QPushButton(tr("重播 / 默认打开", "Replay / Open"))
        self.replay_or_open_btn.setEnabled(False)
        self.replay_or_open_btn.clicked.connect(self._on_replay_or_external_open)
        bot.addWidget(self.replay_or_open_btn)

        if sys.platform == "darwin":
            reveal_zh, reveal_en = "在 Finder 中显示", "Show in Finder"
        elif sys.platform == "win32":
            reveal_zh, reveal_en = "在资源管理器中显示", "Show in Explorer"
        else:
            reveal_zh, reveal_en = "在文件管理器中显示", "Show in File Manager"
        self.reveal_btn = QPushButton(tr(reveal_zh, reveal_en))
        self.reveal_btn.setEnabled(False)
        self.reveal_btn.clicked.connect(self._on_reveal)
        bot.addWidget(self.reveal_btn)
        root.addLayout(bot)
        self.set_palette_theme(self._palette)

    def set_palette_theme(self, pal: StudioPalette) -> None:
        self._palette = pal
        self._sync_stage_style()

    def _sync_stage_style(self) -> None:
        has_media = self.stack.currentIndex() != 0
        if self._palette.is_dark or has_media:
            self.stage_frame.setStyleSheet(
                "QFrame { background-color: #0F1114; border-radius: 8px; border: 1px solid #262A34; }"
            )
            self.empty_page.setStyleSheet("background-color: #0F1114;")
        else:
            self.stage_frame.setStyleSheet(
                "QFrame { background-color: #F1F5F9; border-radius: 8px; border: 1px solid #D5DFEC; }"
            )
            self.empty_page.setStyleSheet("background-color: #F1F5F9;")

    def load_media(self, path: Optional[Path], elapsed_seconds: Optional[float] = None, auto_play: bool = True) -> None:
        self._current_path = path
        if elapsed_seconds is not None and elapsed_seconds > 0:
            self.elapsed_badge.setText(
                tr(f"生成耗时 {format_duration(elapsed_seconds)}", f"Elapsed {format_duration(elapsed_seconds)}")
            )
            self.elapsed_badge.setVisible(True)
        else:
            self.elapsed_badge.setVisible(False)

        if path is None or not path.exists():
            self.stop_video()
            self.stack.setCurrentIndex(0)
            self._sync_stage_style()
            self.filename_lbl.setText(tr("尚未选择本地成片", "No local media selected"))
            self.replay_or_open_btn.setEnabled(False)
            self.reveal_btn.setEnabled(False)
            return

        self.filename_lbl.setText(path.name)
        self.replay_or_open_btn.setEnabled(True)
        self.reveal_btn.setEnabled(True)
        self._is_image = path.suffix.lower() != ".mp4"

        if self._is_image:
            self.stop_video()
            self.replay_or_open_btn.setText(tr("用默认看图打开", "Open in Viewer"))
            self.image_viewer.set_image_path(path)
            self.stack.setCurrentIndex(2)
            self._sync_stage_style()
        else:
            self.replay_or_open_btn.setText(tr("重播", "Replay"))
            self.stack.setCurrentIndex(1)
            self._sync_stage_style()
            if self.player is not None:
                self.player.stop()
                self.player.setSource(QUrl.fromLocalFile(str(path.resolve())))
                if auto_play:
                    self.player.play()

    def stop_video(self) -> None:
        if self.player is not None:
            self.player.stop()

    def toggle_play_pause(self) -> None:
        if self.player is None:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if self.player.position() >= max(1, self.player.duration() - 80):
                self.player.setPosition(0)
            self.player.play()

    def _on_seek_released(self) -> None:
        self._slider_dragging = False
        if self.player is not None:
            self.player.setPosition(self.seek_slider.value())

    def _toggle_mute(self) -> None:
        if self.audio_output is None:
            return
        muted = not self.audio_output.isMuted()
        self.audio_output.setMuted(muted)
        self.mute_btn.setText(tr("已静音", "Muted") if muted else tr("静音", "Mute"))

    def _on_position_changed(self, pos_ms: int) -> None:
        if not self._slider_dragging:
            self.seek_slider.setValue(pos_ms)
        dur_ms = self.player.duration() if self.player else 0
        self.time_lbl.setText(f"{self._fmt_ms(pos_ms)} / {self._fmt_ms(dur_ms)}")

    def _on_duration_changed(self, dur_ms: int) -> None:
        self.seek_slider.setRange(0, max(0, dur_ms))

    def _on_playback_state_changed(self, state) -> None:
        if HAS_QT_MULTIMEDIA and state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText(tr("暂停", "Pause"))
        else:
            self.play_btn.setText(tr("播放", "Play"))

    @staticmethod
    def _fmt_ms(ms: int) -> str:
        sec = max(0, int(ms // 1000))
        return f"{sec // 60:02d}:{sec % 60:02d}"

    def _on_replay_or_external_open(self) -> None:
        if not self._current_path or not self._current_path.exists():
            return
        if self._is_image or self.player is None:
            open_path_in_os(self._current_path, reveal=False)
        else:
            self.player.setPosition(0)
            self.player.play()

    def _on_reveal(self) -> None:
        if self._current_path and self._current_path.exists():
            open_path_in_os(self._current_path, reveal=True)
