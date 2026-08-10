; AutoDocGenerator installer
; Build the PyInstaller onedir bundle first, then compile this script with Inno Setup.

#define MyAppName "AutoDocGenerator"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "AutoDocGenerator"
#define MyAppExeName "AutoDocGenerator.exe"
#define MyDistDir "dist\AutoDocGenerator"

#ifnexist MyDistDir + "\" + MyAppExeName
  #error "Build belum ditemukan. Jalankan build_windows.bat terlebih dahulu."
#endif

[Setup]
AppId={{8A2A537A-EA8B-45A4-994D-4A1A07039E77}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
OutputDir=installer_output
OutputBaseFilename=AutoDocGenerator_Setup_{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
MinVersion=10.0
UsePreviousAppDir=yes
UsePreviousTasks=yes

[Tasks]
Name: "desktopicon"; Description: "Buat shortcut di Desktop"; GroupDescription: "Shortcut tambahan:"; Flags: unchecked

[Files]
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Jalankan {#MyAppName}"; Flags: nowait postinstall skipifsilent
