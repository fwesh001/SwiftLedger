"""Theme stylesheet helpers for SwiftLedger."""

from __future__ import annotations

import os
from utils import get_asset_path


def build_theme_stylesheet(theme: str = "dark", text_scale: float = 1.0) -> str:
    """Load a QSS template and inject scaled font size.

    Args:
        theme: "dark" or "light"
        text_scale: multiplier where 1.0 == 100%

    Returns:
        Rendered stylesheet string.
    """
    safe_theme = "light" if str(theme).lower() == "light" else "dark"
    font_px = max(10, int(14 * float(text_scale or 1.0)))

    qss_file = "light.qss" if safe_theme == "light" else "dark.qss"
    qss_path = get_asset_path(os.path.join("assets", qss_file))

    if not os.path.isfile(qss_path):
        return ""

    with open(qss_path, "r", encoding="utf-8") as qss_stream:
        template = qss_stream.read()

    return template.replace("{{FONT_SIZE}}", str(font_px))
