"""
Utility helpers for SwiftLedger.

Provides a resource-path resolver that works both when running from
source and when the application is bundled into a PyInstaller executable.
"""

import os
import shutil
import sys
from pathlib import Path


APP_NAME = "SwiftLedger"
APP_VERSION = "1.0.1"


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


def format_currency(value: float | int | str | None, symbol: str = "NGN") -> str:
    """Return a standardized currency string used across the UI and reports.

    Args:
        value: Numeric value to format. Non-numeric values fall back to ``0.0``.
        symbol: Currency prefix (e.g. ``"NGN"`` or ``"₦"``).

    Returns:
        Formatted amount like ``"NGN 12,345.67"``.
    """
    try:
        numeric_value = float(value or 0.0)
    except (TypeError, ValueError):
        numeric_value = 0.0
    return f"{symbol} {numeric_value:,.2f}"


def _int_to_words(number: int) -> str:
    ones = [
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
    ]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

    if number < 20:
        return ones[number]
    if number < 100:
        return tens[number // 10] + ("" if number % 10 == 0 else f"-{ones[number % 10]}")
    if number < 1000:
        rem = number % 100
        return f"{ones[number // 100]} hundred" + ("" if rem == 0 else f" {_int_to_words(rem)}")

    chunks = [
        (1_000_000_000_000, "trillion"),
        (1_000_000_000, "billion"),
        (1_000_000, "million"),
        (1_000, "thousand"),
    ]
    for value, label in chunks:
        if number >= value:
            major = number // value
            rem = number % value
            text = f"{_int_to_words(major)} {label}"
            return text if rem == 0 else f"{text} {_int_to_words(rem)}"
    return str(number)


def amount_to_words(value: float | int | str | None) -> str:
    """Return amount in words (naira/kobo)."""
    try:
        numeric_value = round(float(value or 0.0), 2)
    except (TypeError, ValueError):
        numeric_value = 0.0

    negative = numeric_value < 0
    absolute = abs(numeric_value)
    naira = int(absolute)
    kobo = int(round((absolute - naira) * 100))

    naira_words = _int_to_words(naira)
    if kobo > 0:
        words = f"{naira_words} naira and {_int_to_words(kobo)} kobo"
    else:
        words = f"{naira_words} naira"
    if negative:
        words = f"minus {words}"
    return words.title()


def set_button_icon(btn, theme_name: str, fallback_text: str) -> None:
    from PySide6.QtGui import QIcon
    icon = QIcon.fromTheme(theme_name)
    if not icon.isNull():
        btn.setIcon(icon)
        btn.setText(fallback_text.replace("⇱", "").replace("⇲", "").strip())
    else:
        btn.setText(fallback_text)

def get_export_path(page: str, export_type: str, member_name: str = None, staff_id: str = None) -> Path:
    """
    Returns a standardized export path on the user's Desktop.
    Format: Desktop/Swift-Ledger/{Page}/{Type}/{Year}/{Month}
    If member info is provided: .../Member-360/{FullName_StaffID}
    """
    import datetime
    now = datetime.datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    
    base_path = Path.home() / "Desktop" / "Swift-Ledger" / page / export_type / year / month
    if member_name and staff_id:
        safe_name = "".join(c for c in member_name if c.isalnum() or c in " -_").strip()
        safe_id = "".join(c for c in staff_id if c.isalnum() or c in " -_").strip()
        base_path = base_path / "Member-360" / f"{safe_name}_{safe_id}"
        
    base_path.mkdir(parents=True, exist_ok=True)
    return base_path

def format_currency_with_words(value: float | int | str | None, symbol: str = "NGN") -> str:
    """Return formatted amount with words, e.g. ``NGN 1,000,000.00 (One Million Naira)``."""
    return f"{format_currency(value, symbol=symbol)} ({amount_to_words(value)})"
