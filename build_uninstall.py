"""
Build script for packaging the SwiftLedger uninstaller into a single-file EXE.

Usage
-----
    python build_uninstall.py

Requires PyInstaller to be installed:
    pip install pyinstaller
"""

import subprocess
import sys


def build() -> None:
    """Invoke PyInstaller with the correct flags for the uninstaller."""

    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        # ── Core behaviour ──────────────────────────────────────────
        "--onefile",
        "--noconsole",
        "--name", "uninstall",
        # ── Output locations ─────────────────────────────────────────
        "--distpath", "setup",
        "--workpath", "build/pyinstaller_uninstall",
        "--specpath", "build/specs",
        # ── Icon ────────────────────────────────────────────────────
        "--icon", "assets/app_icon.ico",
        # ── Entry point ─────────────────────────────────────────────
        "uninstall.py",
    ]

    print("=" * 60)
    print("  SwiftLedger – Uninstaller Build")
    print("=" * 60)
    print()
    print("Command:")
    print("  " + " ".join(pyinstaller_args[2:]))  # skip python -m
    print()

    result = subprocess.run(pyinstaller_args)

    if result.returncode == 0:
        print()
        print("Build succeeded!")
        print("Output: setup/uninstall.exe")
    else:
        print()
        print(f"Build FAILED (exit code {result.returncode})")
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
