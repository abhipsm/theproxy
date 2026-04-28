; ============================================================
; Proxy.ai Face Attendance System - Inno Setup Script
; DevSoft Technologies © 2026
; ============================================================

#define MyAppName "Proxy.ai Face Attendance"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "DevSoft Technologies"
#define MyAppURL "https://devsoft.tech"
#define MyAppExeName "ProxyFaceAttendance.exe"

[Setup]
AppId={{D8F3C2A1-4B5E-6789-ABCD-EF0123456789}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\ProxyFaceAttendance
DefaultGroupName={#MyAppName}
OutputDir=C:\Users\manda\OneDrive\Desktop\proxy by devsoft\proxy_software_setup
OutputBaseFilename=ProxyAI_Setup_v1.0.0
SetupIconFile=FaceAttendanceSystem\modern_ui\logo.ico
Compression=lzma2/fast
SolidCompression=no
PrivilegesRequired=admin
DisableProgramGroupPage=yes
WizardStyle=modern
WizardSizePercent=120
UninstallDisplayIcon={app}\{#MyAppExeName}
LicenseFile=C:\Users\manda\OneDrive\Desktop\proxy by devsoft\proxy_software_setup\license.txt
ArchitecturesAllowed=x64compatible
DisableWelcomePage=no
AllowNoIcons=yes
SetupLogging=yes

; Version info shown in file properties
VersionInfoVersion=1.0.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoCopyright=Copyright (C) 2026 {#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel1=Welcome to the {#MyAppName} Setup
WelcomeLabel2=This will install {#MyAppName} v{#MyAppVersion} on your computer.%n%nThe software includes:%n  • AI Face Recognition Engine%n  • YOLOv8 Anti-Spoofing Module%n  • Admin Analytics Dashboard%n  • Standalone Python Backend%n%nClick Next to continue.

[Tasks]
Name: "desktopicon"; Description: "Create a &Desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startmenuicon"; Description: "Create a &Start Menu shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
; Main application files from the standalone build (using shorter path to fix MAX_PATH limits)
Source: "..\proxy_build_src\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*\__pycache__\*"

; Database setup SQL (store in AppData for reference)
Source: "FaceAttendanceSystem\updated_setup_database.sql"; DestDir: "{localappdata}\ProxyFaceAttendance\database"; Flags: ignoreversion

; Environment config template
Source: "FaceAttendanceSystem\.env"; DestDir: "{localappdata}\ProxyFaceAttendance\config"; Flags: ignoreversion onlyifdoesntexist

; License file
Source: "proxy_software_setup\license.txt"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; Create AppData directories for logs and data
Name: "{localappdata}\ProxyFaceAttendance"
Name: "{localappdata}\ProxyFaceAttendance\logs"
Name: "{localappdata}\ProxyFaceAttendance\database"
Name: "{localappdata}\ProxyFaceAttendance\config"
Name: "{localappdata}\ProxyFaceAttendance\cache"

[Icons]
; Start Menu shortcuts
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; Desktop shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up AppData on full uninstall
Type: filesandordirs; Name: "{localappdata}\ProxyFaceAttendance\logs"
Type: filesandordirs; Name: "{localappdata}\ProxyFaceAttendance\cache"

[Code]
// Show a splash message after successful install
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    Log('Proxy.ai Face Attendance installed successfully.');
  end;
end;
