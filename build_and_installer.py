"""
SwiftLedger Build & Installer Generator
Builds the PyInstaller executable and generates a Windows NSIS uninstaller.
Replaces build_exe.py and build_uninstall.py.

Run: python build_and_installer.py
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# ─────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
PROJECT_NAME = "SwiftLedger"
VERSION = "1.0.0"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
MAIN_SCRIPT = PROJECT_ROOT / "main.py"

# ─────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────

def log(msg: str, level: str = "INFO") -> None:
    """Print formatted log messages."""
    symbols = {"INFO": "ℹ️ ", "SUCCESS": "✓ ", "ERROR": "✗ ", "WARN": "⚠ "}
    print(f"{symbols.get(level, '→ ')} {msg}")

def clean_build() -> None:
    """Remove previous build artifacts."""
    log("Cleaning previous builds...")
    for directory in [DIST_DIR, BUILD_DIR, PROJECT_ROOT / f"{PROJECT_NAME}.egg-info"]:
        if directory.exists():
            shutil.rmtree(directory)
            log(f"Removed {directory.name}", "SUCCESS")

def find_nsis_compiler() -> Path | None:
    """Locate makensis.exe from common install paths or PATH."""
    candidates = [
        Path("C:/Program Files (x86)/NSIS/makensis.exe"),
        Path("C:/Program Files/NSIS/makensis.exe"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    in_path = shutil.which("makensis")
    if in_path:
        return Path(in_path)

    return None

def build_executable() -> bool:
    """Build the executable using PyInstaller."""
    log("Building executable with PyInstaller...")
    
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", PROJECT_NAME,
        "--icon", str(PROJECT_ROOT / "assets" / "app_icon.ico"),
        "--add-data", f"{PROJECT_ROOT / 'assets'};assets",
        "--add-data", f"{PROJECT_ROOT / 'database'};database",
        "--hidden-import=PySide6",
        "--hidden-import=matplotlib",
        "--hidden-import=pandas",
        "--hidden-import=openpyxl",
        "--hidden-import=fpdf",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        str(MAIN_SCRIPT),
    ]
    
    try:
        result = subprocess.run(pyinstaller_args, check=True, capture_output=True, text=True)
        log("Executable built successfully", "SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        log(f"PyInstaller failed: {e.stderr}", "ERROR")
        return False

def generate_nsis_installer() -> None:
    """Generate NSIS installer script."""
    log("Generating NSIS installer script...")
    
    exe_path = DIST_DIR / f"{PROJECT_NAME}.exe"
    if not exe_path.exists():
        log(f"Executable not found at {exe_path}", "ERROR")
        return
    
    nsis_template = f"""
; SwiftLedger Installer Script
; Generated automatically by build_and_installer.py

!include "MUI2.nsh"
!include "LogicLib.nsh"

; ─────────────────────────────────────────────────────────────────
; Basic Settings
; ─────────────────────────────────────────────────────────────────
Name "SwiftLedger {VERSION}"
OutFile "{PROJECT_ROOT}\\SwiftLedger_Installer_{VERSION}.exe"
InstallDir "$PROGRAMFILES\\SwiftLedger"
InstallDirRegKey HKCU "Software\\SwiftLedger" "Install_Dir"

; ─────────────────────────────────────────────────────────────────
; MUI Settings
; ─────────────────────────────────────────────────────────────────
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

; ─────────────────────────────────────────────────────────────────
; Installer Sections
; ─────────────────────────────────────────────────────────────────
Section "Install"
    SetOutPath "$INSTDIR"
    
    ; Copy executable
    File "{exe_path}"
    
    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\\SwiftLedger"
    CreateShortcut "$SMPROGRAMS\\SwiftLedger\\SwiftLedger.lnk" "$INSTDIR\\{PROJECT_NAME}.exe"
    CreateShortcut "$DESKTOP\\SwiftLedger.lnk" "$INSTDIR\\{PROJECT_NAME}.exe"
    
    ; Write registry
    WriteRegStr HKCU "Software\\SwiftLedger" "Install_Dir" "$INSTDIR"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SwiftLedger" "DisplayName" "SwiftLedger"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SwiftLedger" "UninstallString" "$INSTDIR\\uninstall.exe"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SwiftLedger" "DisplayVersion" "{VERSION}"
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\\uninstall.exe"
SectionEnd

; ─────────────────────────────────────────────────────────────────
; Uninstaller Section
; ─────────────────────────────────────────────────────────────────
Section "Uninstall"
    ; Delete executable
    Delete "$INSTDIR\\{PROJECT_NAME}.exe"
    Delete "$INSTDIR\\uninstall.exe"
    RMDir "$INSTDIR"
    
    ; Delete shortcuts
    Delete "$SMPROGRAMS\\SwiftLedger\\SwiftLedger.lnk"
    RMDir "$SMPROGRAMS\\SwiftLedger"
    Delete "$DESKTOP\\SwiftLedger.lnk"
    
    ; Delete registry
    DeleteRegKey HKCU "Software\\SwiftLedger"
    DeleteRegKey HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SwiftLedger"
SectionEnd
"""
    
    nsis_path = PROJECT_ROOT / "SwiftLedger_Installer.nsi"
    with open(nsis_path, "w", encoding="utf-8") as f:
        f.write(nsis_template)
    
    log(f"NSIS script generated at {nsis_path}", "SUCCESS")
    
    # Attempt to compile with NSIS
    try:
        nsis_compiler = find_nsis_compiler()
        if nsis_compiler:
            log(f"Compiling NSIS installer with {nsis_compiler}...")
            subprocess.run([str(nsis_compiler), str(nsis_path)], check=True)
            log(f"Installer created: SwiftLedger_Installer_{VERSION}.exe", "SUCCESS")
        else:
            log("NSIS compiler not found. Install NSIS to compile the installer.", "WARN")
            log(f"Manual compilation: makensis.exe {nsis_path}", "INFO")
    except subprocess.CalledProcessError as e:
        log(f"NSIS compilation failed: {e}", "ERROR")

def main() -> None:
    """Main build process."""
    log(f"Starting {PROJECT_NAME} Build & Installer Generator v{VERSION}")
    
    # Step 1: Clean
    clean_build()
    
    # Step 2: Build executable
    if not build_executable():
        log("Build failed. Aborting.", "ERROR")
        sys.exit(1)
    
    # Step 3: Generate installer
    generate_nsis_installer()
    
    log(f"{PROJECT_NAME} is ready for distribution!", "SUCCESS")
    log(f"Executable: {DIST_DIR / f'{PROJECT_NAME}.exe'}")
    log(f"Installer: {PROJECT_ROOT / f'SwiftLedger_Installer_{VERSION}.exe'}")

if __name__ == "__main__":
    main()
