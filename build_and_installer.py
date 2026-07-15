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
VERSION = "1.0.2"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
MAIN_SCRIPT = PROJECT_ROOT / "main.py"

# ─────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────

def log(msg: str, level: str = "INFO") -> None:
    """Print formatted log messages."""
    symbols = {"INFO": "[INFO]", "SUCCESS": "[OK]", "ERROR": "[ERROR]", "WARN": "[WARN]"}
    print(f"{symbols.get(level, '[..]')} {msg}")

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
        "--hidden-import=qtpy",
        "--hidden-import=qtawesome",
        # qtawesome ships .ttf fonts + .json charmaps that must be bundled
        # so FontAwesome icons render in the frozen executable.
        "--collect-data", "qtawesome",
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

Unicode True
!include "MUI2.nsh"
!include "LogicLib.nsh"

; ─────────────────────────────────────────────────────────────────
; Basic Settings
; ─────────────────────────────────────────────────────────────────
!define APP_NAME "{PROJECT_NAME}"
!define APP_VERSION "{VERSION}"
!define APP_PUBLISHER "SwiftLedger"
!define APP_EXE "{PROJECT_NAME}.exe"
!define APP_OUTFILE "{PROJECT_ROOT}\\SwiftLedger_Installer_{VERSION}.exe"
!define APP_SOURCE_EXE "{exe_path}"
!define APP_DATA_DIR "$LOCALAPPDATA\\SwiftLedger"
!define APP_DB_FILE "$LOCALAPPDATA\\SwiftLedger\\swiftledger.db"

RequestExecutionLevel user

Name "SwiftLedger {VERSION}"
OutFile "${{APP_OUTFILE}}"
InstallDir "$LOCALAPPDATA\\Programs\\SwiftLedger"
InstallDirRegKey HKCU "Software\\SwiftLedger" "Install_Dir"
ShowInstDetails show
ShowUnInstDetails show

; ─────────────────────────────────────────────────────────────────
; MUI Settings
; ─────────────────────────────────────────────────────────────────
!define MUI_FINISHPAGE_RUN "$INSTDIR\\${{APP_EXE}}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${{APP_NAME}}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

; ─────────────────────────────────────────────────────────────────
; Installer Sections
; ─────────────────────────────────────────────────────────────────
Section "Install"
    SetShellVarContext current
    SetOutPath "$INSTDIR"
    SetOverwrite on

    ; Remove old app binary if present
    Delete "$INSTDIR\\${{APP_EXE}}"
    
    ; Copy executable
    File "${{APP_SOURCE_EXE}}"
    
    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\\SwiftLedger"
    CreateShortcut "$SMPROGRAMS\\SwiftLedger\\SwiftLedger.lnk" "$INSTDIR\\${{APP_EXE}}"
    CreateShortcut "$SMPROGRAMS\\SwiftLedger\\Uninstall SwiftLedger.lnk" "$INSTDIR\\uninstall.exe"
    CreateShortcut "$DESKTOP\\SwiftLedger.lnk" "$INSTDIR\\${{APP_EXE}}"
    
    ; Write registry
    WriteRegStr HKCU "Software\\SwiftLedger" "Install_Dir" "$INSTDIR"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SwiftLedger" "DisplayName" "${{APP_NAME}}"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SwiftLedger" "DisplayIcon" "$INSTDIR\\${{APP_EXE}}"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SwiftLedger" "Publisher" "${{APP_PUBLISHER}}"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SwiftLedger" "UninstallString" "$INSTDIR\\uninstall.exe"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SwiftLedger" "QuietUninstallString" "$INSTDIR\\uninstall.exe /S"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SwiftLedger" "DisplayVersion" "${{APP_VERSION}}"
    WriteRegDWORD HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SwiftLedger" "NoModify" 1
    WriteRegDWORD HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SwiftLedger" "NoRepair" 1
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\\uninstall.exe"
SectionEnd

; ─────────────────────────────────────────────────────────────────
; Uninstaller Section
; ─────────────────────────────────────────────────────────────────
Section "Uninstall"
    SetShellVarContext current

    ; Delete executable
    Delete "$INSTDIR\\${{APP_EXE}}"
    Delete "$INSTDIR\\uninstall.exe"
    RMDir "$INSTDIR"
    
    ; Delete shortcuts
    Delete "$SMPROGRAMS\\SwiftLedger\\SwiftLedger.lnk"
    Delete "$SMPROGRAMS\\SwiftLedger\\Uninstall SwiftLedger.lnk"
    RMDir "$SMPROGRAMS\\SwiftLedger"
    Delete "$DESKTOP\\SwiftLedger.lnk"

    ; Optional user-data cleanup (database + app data folder)
    MessageBox MB_ICONQUESTION|MB_YESNO "Also remove local SwiftLedger data (database and user files)?" IDNO SkipDataCleanup
    Delete "${{APP_DB_FILE}}"
    RMDir /r "${{APP_DATA_DIR}}"
SkipDataCleanup:
    
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
