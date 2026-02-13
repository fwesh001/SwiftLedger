
; SwiftLedger Installer Script
; Generated automatically by build_and_installer.py

!include "MUI2.nsh"
!include "LogicLib.nsh"

; ─────────────────────────────────────────────────────────────────
; Basic Settings
; ─────────────────────────────────────────────────────────────────
Name "SwiftLedger 1.0.0"
OutFile "c:\Users\zabdiel\Desktop\SwiftLedger\SwiftLedger_Installer_1.0.0.exe"
InstallDir "$PROGRAMFILES\SwiftLedger"
InstallDirRegKey HKCU "Software\SwiftLedger" "Install_Dir"

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
    File "c:\Users\zabdiel\Desktop\SwiftLedger\dist\SwiftLedger.exe"
    
    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\SwiftLedger"
    CreateShortcut "$SMPROGRAMS\SwiftLedger\SwiftLedger.lnk" "$INSTDIR\SwiftLedger.exe"
    CreateShortcut "$DESKTOP\SwiftLedger.lnk" "$INSTDIR\SwiftLedger.exe"
    
    ; Write registry
    WriteRegStr HKCU "Software\SwiftLedger" "Install_Dir" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SwiftLedger" "DisplayName" "SwiftLedger"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SwiftLedger" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SwiftLedger" "DisplayVersion" "1.0.0"
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

; ─────────────────────────────────────────────────────────────────
; Uninstaller Section
; ─────────────────────────────────────────────────────────────────
Section "Uninstall"
    ; Delete executable
    Delete "$INSTDIR\SwiftLedger.exe"
    Delete "$INSTDIR\uninstall.exe"
    RMDir "$INSTDIR"
    
    ; Delete shortcuts
    Delete "$SMPROGRAMS\SwiftLedger\SwiftLedger.lnk"
    RMDir "$SMPROGRAMS\SwiftLedger"
    Delete "$DESKTOP\SwiftLedger.lnk"
    
    ; Delete registry
    DeleteRegKey HKCU "Software\SwiftLedger"
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SwiftLedger"
SectionEnd
