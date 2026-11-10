"""
Studio color palettes (Dark & Light), QSS stylesheet builder, and procedural
vector AppIcon renderer (matching macOS EasyColab cloud + linked orange nodes).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)


@dataclass(frozen=True)
class StudioPalette:
    is_dark: bool
    sidebar_bg: str
    sidebar_card_fill: str
    workspace_canvas: str
    workspace_card_fill: str
    log_header_bg: str
    log_panel_bg: str
    log_terminal_fill: str
    split_divider: str
    card_border: str
    input_fill: str
    input_border: str
    text_primary: str
    text_secondary: str
    text_muted: str
    hover_fill: str
    selected_card_bg: str
    selected_card_border: str
    accent_blue: str = "#3B82F6"
    accent_blue_hover: str = "#2563EB"
    accent_green: str = "#1AC287"
    accent_orange: str = "#F59E0B"
    accent_red: str = "#EF4444"
    metric_vram: str = "#5487FA"
    metric_ram: str = "#1AC287"
    metric_disk: str = "#0DBAE0"


DARK_PALETTE = StudioPalette(
    is_dark=True,
    sidebar_bg="#1C1F25",
    sidebar_card_fill="#282B33",
    workspace_canvas="#121418",
    workspace_card_fill="#202229",
    log_header_bg="#1A1D23",
    log_panel_bg="#16181E",
    log_terminal_fill="#12151B",
    split_divider="#2E333D",
    card_border="#343944",
    input_fill="#17191E",
    input_border="#383E4C",
    text_primary="#F1F5F9",
    text_secondary="#94A3B8",
    text_muted="#64748B",
    hover_fill="#303540",
    selected_card_bg="#1E2B45",
    selected_card_border="#5487FA",
)

LIGHT_PALETTE = StudioPalette(
    is_dark=False,
    sidebar_bg="#EDF1F7",
    sidebar_card_fill="#FFFFFF",
    workspace_canvas="#F6F8FB",
    workspace_card_fill="#FFFFFF",
    log_header_bg="#EDF1F7",
    log_panel_bg="#F3F6FA",
    log_terminal_fill="#FFFFFF",
    split_divider="#D0D8E5",
    card_border="#D5DFEC",
    input_fill="#F8FAFD",
    input_border="#C4D0E0",
    text_primary="#0F172A",
    text_secondary="#475569",
    text_muted="#64748B",
    hover_fill="#E8EEF6",
    selected_card_bg="#EFF6FF",
    selected_card_border="#2563EB",
)


def icon_glyph(_sf_name: str) -> str:
    """Windows UI uses clean typography without emoji or symbol prefixes."""
    return ""


def draw_easycolab_icon_pixmap(size: int = 256) -> QPixmap:
    """
    Procedurally render the exact EasyColab squircle cloud + 3 warm orange linked nodes
    icon (matching macos_app/build_macos_app.sh) at any resolution.
    """
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    scale = size / 1024.0
    p.scale(scale, scale)

    # Rounded squircle tile (92, 92, 840, 840), radius 205
    tile_rect = QRectF(92, 92, 840, 840)
    tile_path = QPainterPath()
    tile_path.addRoundedRect(tile_rect, 205, 205)

    # Soft drop shadow
    shadow_path = QPainterPath()
    shadow_path.addRoundedRect(QRectF(92, 108, 840, 840), 205, 205)
    p.fillPath(shadow_path, QColor(0, 0, 0, 58))

    # Sky-blue gradient fill (note Qt Y-axis is top-down vs CoreGraphics bottom-up)
    grad = QLinearGradient(QPointF(150, 924), QPointF(850, 84))
    grad.setColorAt(0.0, QColor(207, 232, 245))
    grad.setColorAt(1.0, QColor(245, 252, 255))
    p.fillPath(tile_path, grad)

    # Subtle inner border
    p.setPen(QPen(QColor(255, 255, 255, 180), 8))
    p.drawPath(tile_path)

    # Convert CoreGraphics coordinates (Y up from 0..1024 with translate(-7, -48))
    # to Qt coordinates (Y down from 0..1024): qt_y = 1024 - (cg_y - 48) = 1072 - cg_y, qt_x = cg_x - 7
    def pt(cg_x: float, cg_y: float) -> QPointF:
        return QPointF(cg_x - 7.0, 1072.0 - cg_y)

    cloud = QPainterPath()
    cloud.moveTo(pt(322, 411))
    cloud.cubicTo(pt(247, 411), pt(235, 600), pt(320, 624))
    cloud.cubicTo(pt(358, 773), pt(558, 807), pt(617, 690))
    cloud.cubicTo(pt(670, 689), pt(707, 650), pt(711, 604))
    cloud.cubicTo(pt(813, 598), pt(828, 411), pt(710, 411))
    cloud.closeSubpath()

    # Cloud subtle shadow
    p.save()
    p.translate(0, 14)
    p.fillPath(cloud, QColor(61, 122, 163, 42))
    p.restore()

    # White cloud body
    p.fillPath(cloud, QColor(255, 255, 255))

    # Linked warm orange nodes
    n1 = pt(405, 506)
    n2 = pt(511, 579)
    n3 = pt(620, 506)

    link_pen = QPen(QColor(242, 102, 43), 34, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(link_pen)
    link_path = QPainterPath()
    link_path.moveTo(n1)
    link_path.lineTo(n2)
    link_path.lineTo(n3)
    p.drawPath(link_path)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 145, 64))
    for node in (n1, n2, n3):
        p.drawEllipse(node, 32, 32)

    p.end()
    return pix


def build_app_icon() -> QIcon:
    icon = QIcon()
    for sz in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(draw_easycolab_icon_pixmap(sz))
    return icon


def metric_threshold_color(metric: str, free_gb: float, default_hex: str) -> str:
    if metric == "vram":
        if free_gb < 3.0:
            return "#EF4444"
        if free_gb < 8.0:
            return "#F59E0B"
    elif metric == "ram":
        if free_gb < 5.0:
            return "#EF4444"
        if free_gb < 10.0:
            return "#F59E0B"
    elif metric == "disk":
        if free_gb < 10.0:
            return "#EF4444"
        if free_gb < 20.0:
            return "#F59E0B"
    return default_hex


def build_stylesheet(pal: StudioPalette) -> str:
    """Build crisp Windows 11 / Linux Studio QSS stylesheet (Light-first, zero emoji)."""
    font_family = '"Segoe UI Variable Text", "Segoe UI", "Noto Sans CJK SC", "Source Han Sans SC", "Cantarell", "Ubuntu", "Microsoft YaHei UI", "PingFang SC", sans-serif'
    btn_bg = "#303540" if pal.is_dark else "#FFFFFF"
    btn_hover_bg = "#3A404D" if pal.is_dark else "#F1F5F9"
    danger_bg = "rgba(239, 68, 68, 0.14)" if pal.is_dark else "rgba(239, 68, 68, 0.08)"
    danger_fg = "#F87171" if pal.is_dark else "#DC2626"
    danger_bd = "rgba(239, 68, 68, 0.40)" if pal.is_dark else "rgba(220, 38, 38, 0.35)"
    code_bg = "#12151B" if pal.is_dark else "#F8FAFC"
    code_fg = "#E2E8F0" if pal.is_dark else "#1E293B"
    code_bd = "#2D3340" if pal.is_dark else "#D5DFEC"
    return f"""
    QWidget {{
        font-family: {font_family};
        font-size: 12.5px;
        color: {pal.text_primary};
    }}
    QMainWindow, QDialog {{
        background-color: {pal.workspace_canvas};
    }}
    QFrame#TopHeaderBar {{
        background-color: {pal.sidebar_bg};
        border-bottom: 1px solid {pal.split_divider};
    }}
    QFrame#WorkspaceTopBar {{
        background-color: {pal.workspace_canvas};
        border-bottom: 1px solid {pal.split_divider};
    }}
    QFrame#LogTopBar {{
        background-color: {pal.log_header_bg};
        border-bottom: 1px solid {pal.split_divider};
    }}
    QWidget#LeftSidebarContainer {{
        background-color: {pal.sidebar_bg};
        border-right: 1px solid {pal.split_divider};
    }}
    QWidget#CenterWorkspaceContainer {{
        background-color: {pal.workspace_canvas};
    }}
    QWidget#RightLogContainer {{
        background-color: {pal.log_panel_bg};
        border-left: 1px solid {pal.split_divider};
    }}
    QFrame#SidebarCard {{
        background-color: {pal.sidebar_card_fill};
        border: 1px solid {pal.card_border};
        border-radius: 10px;
    }}
    QFrame#WorkspaceCard {{
        background-color: {pal.workspace_card_fill};
        border: 1px solid {pal.card_border};
        border-radius: 11px;
    }}
    QFrame#SubtlePanel {{
        background-color: {pal.input_fill};
        border: 1px solid {pal.card_border};
        border-radius: 8px;
    }}
    QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {pal.input_fill};
        color: {pal.text_primary};
        border: 1px solid {pal.input_border};
        border-radius: 6px;
        padding: 5px 8px;
        selection-background-color: {pal.accent_blue};
        selection-color: #FFFFFF;
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {pal.accent_blue};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {pal.sidebar_card_fill};
        color: {pal.text_primary};
        border: 1px solid {pal.card_border};
        selection-background-color: {pal.accent_blue};
        selection-color: #FFFFFF;
        outline: 0;
    }}
    QPushButton {{
        background-color: {btn_bg};
        color: {pal.text_primary};
        border: 1px solid {pal.card_border};
        border-radius: 6px;
        padding: 5px 11px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {btn_hover_bg};
        border-color: {pal.accent_blue};
    }}
    QPushButton:disabled {{
        color: {pal.text_muted};
        background-color: {pal.input_fill};
        border-color: {pal.card_border};
    }}
    QPushButton[btnRole="primary"] {{
        background-color: {pal.accent_blue};
        color: #FFFFFF;
        border: 1px solid {pal.accent_blue};
        font-weight: 600;
    }}
    QPushButton[btnRole="primary"]:hover {{
        background-color: {pal.accent_blue_hover};
        border-color: {pal.accent_blue_hover};
    }}
    QPushButton[btnRole="primary"]:disabled {{
        background-color: {pal.hover_fill};
        color: {pal.text_muted};
        border-color: {pal.card_border};
    }}
    QPushButton[btnRole="success"] {{
        background-color: #10B981;
        color: #FFFFFF;
        border: 1px solid #059669;
        font-weight: 600;
    }}
    QPushButton[btnRole="success"]:hover {{
        background-color: #059669;
    }}
    QPushButton[btnRole="danger"] {{
        background-color: {danger_bg};
        color: {danger_fg};
        border: 1px solid {danger_bd};
        font-weight: 600;
    }}
    QPushButton[btnRole="danger"]:hover {{
        background-color: #EF4444;
        color: #FFFFFF;
    }}
    QTextBrowser#LogTerminalView {{
        background-color: {pal.log_terminal_fill};
        color: {code_fg};
        border: 1px solid {code_bd};
        border-radius: 9px;
        padding: 8px;
        font-family: Consolas, "Cascadia Mono", "Microsoft YaHei UI", monospace;
        font-size: 11.5px;
    }}
    QPlainTextEdit#CodeSnippetBox {{
        background-color: {code_bg};
        color: {code_fg};
        border: 1px solid {code_bd};
        border-radius: 7px;
        font-family: Consolas, "Cascadia Mono", monospace;
        font-size: 11px;
        padding: 8px;
    }}
    QPushButton[btnRole="pill"] {{
        border-radius: 11px;
        padding: 3px 10px;
        font-size: 11.5px;
    }}
    QPushButton[btnRole="ghost"] {{
        background-color: transparent;
        border: 1px solid transparent;
        padding: 4px 8px;
    }}
    QPushButton[btnRole="ghost"]:hover {{
        background-color: {pal.hover_fill};
        border-color: {pal.card_border};
    }}
    QProgressBar {{
        background-color: {pal.input_fill};
        border: 1px solid {pal.card_border};
        border-radius: 4px;
        height: 8px;
        text-align: center;
        font-size: 10px;
    }}
    QProgressBar::chunk {{
        background-color: {pal.accent_blue};
        border-radius: 3px;
    }}
    QSlider::groove:horizontal {{
        height: 5px;
        background: {pal.input_fill};
        border: 1px solid {pal.card_border};
        border-radius: 3px;
    }}
    QSlider::sub-page:horizontal {{
        background: {pal.accent_blue};
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: #FFFFFF;
        border: 2px solid {pal.accent_blue};
        width: 13px;
        height: 13px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QCheckBox {{
        spacing: 6px;
        background: transparent;
    }}
    QLabel {{
        background: transparent;
    }}
    QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {{
        border: none;
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 2px 1px 2px 1px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(148, 163, 184, 0.35);
        min-height: 28px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba(148, 163, 184, 0.60);
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
    }}
    QScrollBar::handle:horizontal {{
        background: rgba(148, 163, 184, 0.35);
        min-width: 28px;
        border-radius: 4px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    QMenu {{
        background-color: {pal.sidebar_card_fill};
        color: {pal.text_primary};
        border: 1px solid {pal.card_border};
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 20px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background-color: {pal.accent_blue};
        color: #FFFFFF;
    }}
    """
