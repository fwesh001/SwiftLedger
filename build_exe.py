"""
Build script for packaging SwiftLedger into a single-file Windows EXE.

Usage
-----
    python build_exe.py

Requires PyInstaller to be installed:
    pip install pyinstaller
"""

import subprocess
import sys


def build() -> None:
    """Invoke PyInstaller with the correct flags for SwiftLedger."""

    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        # ── Core behaviour ──────────────────────────────────────────
        "--onefile",
        "--noconsole",
        "--name", "SwiftLedger_v1.0",
        # ── Bundled data ────────────────────────────────────────────
        # Assets folder (styles, icons, images)
        "--add-data", "assets;assets",
        # ── Hidden imports (not auto-detected) ──────────────────────
        "--hidden-import", "PySide6.QtPdf",
        "--hidden-import", "PySide6.QtPdfWidgets",
        # ── Icon ────────────────────────────────────────────────────
        "--icon", "assets/app_icon.ico",
        # ── Entry point ─────────────────────────────────────────────
        "main.py",
    ]

    print("=" * 60)
    print("  SwiftLedger – PyInstaller Build")
    print("=" * 60)
    print()
    print("Command:")
    print("  " + " ".join(pyinstaller_args[2:]))  # skip python -m
    print()

    result = subprocess.run(pyinstaller_args)

    if result.returncode == 0:
        print()
        print("Build succeeded!")
        print("Output: dist/SwiftLedger_v1.0.exe")
    else:
        print()
        print(f"Build FAILED (exit code {result.returncode})")
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
