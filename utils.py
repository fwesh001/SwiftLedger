"""
Utility helpers for SwiftLedger.

Provides a resource-path resolver that works both when running from
source and when the application is bundled into a PyInstaller executable.
"""

import os
import sys


def get_asset_path(relative_path: str) -> str:
    """Return the absolute path to a bundled asset.

    When the application is running as a PyInstaller one-file EXE, assets
    are extracted to a temporary directory referenced by ``sys._MEIPASS``.
    In normal (source) mode the path is resolved relative to the project
    root directory.

    Args:
        relative_path: A forward-slash or OS-native path relative to the
            project root (e.g. ``"assets/styles.qss"``).

    Returns:
        The absolute filesystem path to the requested resource.
    """
    # PyInstaller stores the extraction folder in sys._MEIPASS
    if getattr(sys, "_MEIPASS", None):
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)
