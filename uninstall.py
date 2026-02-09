"""
SwiftLedger Uninstaller

Standalone script that:
  1. Terminates any running SwiftLedger process.
  2. Asks the user for confirmation before proceeding.
  3. Optionally deletes the society database (swiftledger.db).
  4. Removes the assets/ folder and the main executable.
  5. Schedules self-deletion via a delayed cmd.exe call.

Usage (from the install directory):
    python uninstall.py
    — or, if compiled to an EXE —
    uninstall.exe
"""

import os
import sys
import shutil
import subprocess
import time
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve the directory this script / EXE lives in
# ---------------------------------------------------------------------------
if getattr(sys, "_MEIPASS", None):
    INSTALL_DIR = Path(sys.executable).parent
else:
    INSTALL_DIR = Path(__file__).resolve().parent

APP_EXE = INSTALL_DIR / "SwiftLedger_v1.0.exe"
ASSETS_DIR = INSTALL_DIR / "assets"
DB_FILE = INSTALL_DIR / "swiftledger.db"
UNINSTALLER = Path(sys.executable) if getattr(sys, "frozen", False) else Path(__file__).resolve()


# ---------------------------------------------------------------------------
# 1. Process management — kill running SwiftLedger instances
# ---------------------------------------------------------------------------
def terminate_swiftledger() -> None:
    """Find and kill any running SwiftLedger_v1.0.exe processes."""
    try:
        import psutil
    except ImportError:
        # psutil unavailable — fall back to taskkill on Windows
        os.system('taskkill /F /IM "SwiftLedger_v1.0.exe" 2>nul')
        return

    target = "SwiftLedger_v1.0.exe".lower()
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if (proc.info["name"] or "").lower() == target:
                proc.kill()
                proc.wait(timeout=5)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            pass


# ---------------------------------------------------------------------------
# 2. Self-deletion trick
# ---------------------------------------------------------------------------
def schedule_self_delete() -> None:
    """Use cmd.exe to delete this uninstaller after a short delay."""
    if sys.platform != "win32":
        return

    target = str(UNINSTALLER)
    # ping — cheap 2-second delay (works on all Windows versions)
    cmd = (
        f'cmd.exe /C ping 127.0.0.1 -n 3 > nul '
        f'& del /F /Q "{target}" '
        f'& rmdir /Q "{INSTALL_DIR}" 2>nul'
    )
    subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,  # type: ignore[attr-defined]
    )


# ---------------------------------------------------------------------------
# Main uninstall flow
# ---------------------------------------------------------------------------
def main() -> None:
    # Hide the default tkinter root window
    root = tk.Tk()
    root.withdraw()

    # ── Confirmation dialog ──────────────────────────────────────────
    proceed = messagebox.askyesno(
        "SwiftLedger Uninstaller",
        "Are you sure you want to remove SwiftLedger?",
    )
    if not proceed:
        root.destroy()
        sys.exit(0)

    # ── Data-protection dialog ───────────────────────────────────────
    delete_db = messagebox.askyesno(
        "SwiftLedger Uninstaller",
        "Do you want to PERMANENTLY delete your society records (swiftledger.db)?",
    )

    # ── Terminate running instances ──────────────────────────────────
    terminate_swiftledger()
    time.sleep(1)  # brief pause to let file handles release

    # ── Deletion logic ───────────────────────────────────────────────
    errors: list[str] = []

    # Delete assets/ folder
    if ASSETS_DIR.is_dir():
        try:
            shutil.rmtree(ASSETS_DIR)
        except Exception as exc:
            errors.append(f"assets/: {exc}")

    # Delete the main executable
    if APP_EXE.is_file():
        try:
            APP_EXE.unlink()
        except Exception as exc:
            errors.append(f"SwiftLedger_v1.0.exe: {exc}")

    # Optionally delete the database
    if delete_db and DB_FILE.is_file():
        try:
            DB_FILE.unlink()
        except Exception as exc:
            errors.append(f"swiftledger.db: {exc}")

    # ── Final message ────────────────────────────────────────────────
    if errors:
        messagebox.showwarning(
            "SwiftLedger Uninstaller",
            "Uninstallation completed with warnings:\n\n" + "\n".join(errors),
        )
    else:
        messagebox.showinfo(
            "SwiftLedger Uninstaller",
            "Uninstallation Successful!\n\nSwiftLedger has been removed from your system.",
        )

    root.destroy()

    # ── Self-deletion ────────────────────────────────────────────────
    schedule_self_delete()
    sys.exit(0)


if __name__ == "__main__":
    main()
