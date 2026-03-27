"""Theme stylesheet helpers for SwiftLedger."""

from __future__ import annotations

import os
from utils import get_asset_path
from PySide6.QtGui import QCursor, QPixmap, QPainter, QPolygon, QColor
from PySide6.QtCore import Qt, QPoint

def create_custom_cursor(theme: str, custom_colors: dict = None) -> QCursor:
    size = 32
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    color_hex = "#3498db" # default
    if theme == "dark":
        color_hex = "#ecf0f1"
    elif theme == "light":
        color_hex = "#e67e22"
    elif theme == "custom" and custom_colors:
        color_hex = custom_colors.get("fg", "#ffffff")
        
    color = QColor(color_hex)
    painter.setBrush(color)
    painter.setPen(Qt.PenStyle.NoPen)
    
    poly = QPolygon([
        QPoint(2, 2),
        QPoint(2, 24),
        QPoint(8, 18),
        QPoint(18, 18),
    ])
    painter.drawPolygon(poly)
    painter.end()
    
    return QCursor(pixmap, 2, 2)

def build_theme_stylesheet(theme: str = "dark", text_scale: float = 1.0, custom_colors: dict = None) -> str:
    """Load a QSS template and inject scaled font size.
    """
    font_px = max(10, int(14 * float(text_scale or 1.0)))

    if str(theme).lower() == "custom" and custom_colors:
        qss_path = get_asset_path(os.path.join("assets", "dark.qss"))
        if not os.path.isfile(qss_path):
            return ""
        with open(qss_path, "r", encoding="utf-8") as qss_stream:
            template = qss_stream.read()
            
        template = template.replace("#1e1e1e", custom_colors.get("bg", "#1e1e1e"))
        template = template.replace("#ecf0f1", custom_colors.get("fg", "#ecf0f1"))
        template = template.replace("#2c3e50", custom_colors.get("sidebar", "#2c3e50"))
        
        return template.replace("{{FONT_SIZE}}", str(font_px))

    safe_theme = "light" if str(theme).lower() == "light" else "dark"

    qss_file = "light.qss" if safe_theme == "light" else "dark.qss"
    qss_path = get_asset_path(os.path.join("assets", qss_file))

    if not os.path.isfile(qss_path):
        return ""

    with open(qss_path, "r", encoding="utf-8") as qss_stream:
        template = qss_stream.read()

    return template.replace("{{FONT_SIZE}}", str(font_px))
