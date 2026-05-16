; Buzz Mini — small NSIS bootstrapper (downloads PyInstaller bundle from GitHub Releases).
;
; Build: .\tools\build_installer.ps1
; Upload payload first: .\tools\build_release_payload.ps1  ->  attach .7z to GitHub Release
;
; Manual:
;   makensis /DOUTFILE=dist\BuzzMini-Setup-1.0.0.exe /DPRODUCT_VERSION=1.0.0 /DPAYLOAD_URL=https://github.com/.../BuzzMini-1.0.0-win64.7z installer\BuzzMini.nsi

Unicode true
CRCCheck force
SetCompressor /SOLID lzma
SetCompressorDictSize 32
InstallDir "$PROGRAMFILES64\Buzz Mini"

!ifndef PRODUCT_VERSION
  !define PRODUCT_VERSION "1.0.0"
!endif

!ifndef PAYLOAD_URL
  !ifndef GITHUB_REPO
    !define GITHUB_REPO "kurskiev-t/BuzzMini"
  !endif
  !define PAYLOAD_URL "https://github.com/${GITHUB_REPO}/releases/download/${PRODUCT_VERSION}/BuzzMini-${PRODUCT_VERSION}-win64.7z"
!endif

!define COMPANY_NAME "BuzzMini"
!define PRODUCT_NAME "Buzz Mini"
!define EXE_NAME "BuzzMini.exe"
!define UNINSTALL_EXE_NAME "BuzzMini-Uninstall.exe"
!define UNINSTALL_REG_SUBKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\BuzzMini"
!define PAYLOAD_ARCHIVE_NAME "BuzzMini-payload.7z"

Name "${PRODUCT_NAME}"
Caption "${PRODUCT_NAME} ${PRODUCT_VERSION} Setup"

!ifdef OUTFILE
  OutFile "${OUTFILE}"
!else
  OutFile "..\dist\BuzzMini-Setup-${PRODUCT_VERSION}.exe"
!endif

!include "LogicLib.nsh"
!include "x64.nsh"
!include "MUI2.nsh"

RequestExecutionLevel admin

!if /FileExists "..\assets\app.ico"
  !define MUI_ICON "..\assets\app.ico"
  !define MUI_UNICON "..\assets\app.ico"
!else
  !define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
  !define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"
!endif

!define MUI_ABORTWARNING_TEXT "Cancel setup?"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY

Section "!${PRODUCT_NAME} (required)" SID_MAIN
  SectionIn RO

  DetailPrint "========================================"
  DetailPrint "${PRODUCT_NAME} ${PRODUCT_VERSION} — online setup"
  DetailPrint "Install folder: $INSTDIR"
  DetailPrint "========================================"

  SetOutPath "$INSTDIR"
  WriteUninstaller "$INSTDIR\${UNINSTALL_EXE_NAME}"

  DetailPrint "Preparing extractor (7-Zip)..."
  InitPluginsDir
  SetOutPath "$PLUGINSDIR"
  File "redist\7zr.exe"

  StrCpy $0 "$TEMP\${PAYLOAD_ARCHIVE_NAME}"
  DetailPrint ""
  DetailPrint "Downloading application bundle from GitHub:"
  DetailPrint "${PAYLOAD_URL}"
  DetailPrint "(PyInstaller onedir: Python, Qt, PyTorch CUDA — not Whisper model weights)"
  DetailPrint ""

  NSISdl::download /TRANSLATE2 /END "Download: $9 (%u KB of %k KB at %s KB/s)" "${PAYLOAD_URL}" "$0"
  Pop $1
  ${If} $1 != "success"
    DetailPrint "Download failed: $1"
    MessageBox MB_OK|MB_ICONSTOP "Could not download the application bundle.$\n$\nURL:$\n${PAYLOAD_URL}$\n$\nReason: $1$\n$\nCheck your connection and that the GitHub Release exists with the correct asset name."
    Abort
  ${EndIf}

  DetailPrint "Download finished: $0"
  DetailPrint ""
  DetailPrint "Extracting to: $INSTDIR"
  DetailPrint "(This can take several minutes for a multi-GB archive.)"

  ExecWait '"$PLUGINSDIR\7zr.exe" x "$0" -o"$INSTDIR" -y -bb1' $2
  ${If} $2 != 0
    DetailPrint "7-Zip extract exit code: $2"
    MessageBox MB_OK|MB_ICONSTOP "Failed to extract the downloaded archive (exit code $2).$\n$\nSee the installation log (Show details) for more information."
    Abort
  ${EndIf}

  Delete "$0"
  DetailPrint "Temporary archive removed."

  IfFileExists "$INSTDIR\${EXE_NAME}" exe_ok 0
    DetailPrint "ERROR: ${EXE_NAME} not found after extraction."
    MessageBox MB_OK|MB_ICONSTOP "Installation incomplete: ${EXE_NAME} was not found in$\n$INSTDIR$\n$\nThe release archive layout may be wrong (expected BuzzMini.exe at archive root)."
    Abort
  exe_ok:
  DetailPrint "Verified: $INSTDIR\${EXE_NAME}"

  DetailPrint ""
  DetailPrint "Creating Start Menu shortcuts..."
  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\${EXE_NAME}"
  CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall ${PRODUCT_NAME}.lnk" "$INSTDIR\${UNINSTALL_EXE_NAME}"

  DetailPrint "Registering uninstall entry..."
  WriteRegStr HKLM "${UNINSTALL_REG_SUBKEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKLM "${UNINSTALL_REG_SUBKEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKLM "${UNINSTALL_REG_SUBKEY}" "Publisher" "${COMPANY_NAME}"
  WriteRegStr HKLM "${UNINSTALL_REG_SUBKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "${UNINSTALL_REG_SUBKEY}" "DisplayIcon" "$INSTDIR\${EXE_NAME},0"
  WriteRegDWORD HKLM "${UNINSTALL_REG_SUBKEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UNINSTALL_REG_SUBKEY}" "NoRepair" 1
  WriteRegStr HKLM "${UNINSTALL_REG_SUBKEY}" "UninstallString" '"$INSTDIR\${UNINSTALL_EXE_NAME}"'
  WriteRegStr HKLM "${UNINSTALL_REG_SUBKEY}" "QuietUninstallString" '"$INSTDIR\${UNINSTALL_EXE_NAME}" /S'

  DetailPrint ""
  DetailPrint "${PRODUCT_NAME} installed."
  DetailPrint "Whisper model weights are downloaded later from the Models tab on first use."
SectionEnd

Section /o "Desktop shortcut" SID_DESKTOP
  CreateShortcut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\${EXE_NAME}"
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SID_MAIN} "Download the application bundle from GitHub Releases and install to the chosen folder. Requires an internet connection."
  !insertmacro MUI_DESCRIPTION_TEXT ${SID_DESKTOP} "Optional shortcut on your desktop."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

VIProductVersion "${PRODUCT_VERSION}.0"
VIAddVersionKey /LANG=${LANG_ENGLISH} "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "CompanyName" "${COMPANY_NAME}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileDescription" "${PRODUCT_NAME} Setup"
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileVersion" "${PRODUCT_VERSION}"

ShowInstDetails show
ShowUninstDetails show
BrandingText "${PRODUCT_NAME} ${PRODUCT_VERSION}"

Section Uninstall
  DetailPrint "Removing ${PRODUCT_NAME}..."

  Delete "$DESKTOP\${PRODUCT_NAME}.lnk"

  DetailPrint "Removing shortcuts..."
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall ${PRODUCT_NAME}.lnk"
  RMDir "$SMPROGRAMS\${PRODUCT_NAME}"

  DetailPrint "Removing application files..."
  RMDir /r "$INSTDIR"

  DeleteRegKey HKLM "${UNINSTALL_REG_SUBKEY}"
  DetailPrint "Uninstall complete."
SectionEnd

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_OK|MB_ICONSTOP "${PRODUCT_NAME} requires 64-bit Windows."
    Abort
  ${EndIf}
FunctionEnd

Function .onInstFailed
  MessageBox MB_OK|MB_ICONSTOP "${PRODUCT_NAME} installation failed.$\n$\nOpen the installer log (Show details) for download and extract messages."
FunctionEnd
