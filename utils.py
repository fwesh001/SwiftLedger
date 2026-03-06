"""
Utility helpers for SwiftLedger.

Provides a resource-path resolver that works both when running from
source and when the application is bundled into a PyInstaller executable.
"""

import os
import shutil
import sys
from pathlib import Path


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


def get_database_path(db_filename: str = "swiftledger.db") -> str:
    """Return a writable database path for the current runtime mode.

    - Source mode: store DB in the project root (current behavior).
    - Packaged EXE: store DB under the current user's LocalAppData folder,
      e.g. ``%LOCALAPPDATA%\\SwiftLedger\\swiftledger.db``.

    If a legacy database exists beside the EXE and the user-profile database
    does not yet exist, the legacy file is copied once to preserve data.
    """
    if getattr(sys, "frozen", False):
        base_dir = (
            os.environ.get("LOCALAPPDATA")
            or os.environ.get("APPDATA")
            or str(Path.home())
        )
        app_data_dir = os.path.join(base_dir, "SwiftLedger")
        os.makedirs(app_data_dir, exist_ok=True)

        user_db_path = os.path.join(app_data_dir, db_filename)
        legacy_db_path = os.path.join(os.path.dirname(sys.executable), db_filename)

        if not os.path.exists(user_db_path) and os.path.exists(legacy_db_path):
            try:
                shutil.copy2(legacy_db_path, user_db_path)
            except OSError:
                pass

        return user_db_path

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), db_filename)
