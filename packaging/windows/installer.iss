#ifndef BundleDir
  #error BundleDir is required
#endif
#ifndef OutputDir
  #error OutputDir is required
#endif
[Setup]
AppId={{D38A3E38-621E-43B7-8F13-437B49A7903D}
AppName=Downloads Organizer
AppVersion=1.1.0
AppPublisher=kashnordeen
AppPublisherURL=https://github.com/kashnordeen/downloads-organizer
DefaultDirName={localappdata}\Programs\DownloadsOrganizer
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
OutputDir={#OutputDir}
OutputBaseFilename=DownloadsOrganizer-1.1.0-windows-x64-setup
SetupIconFile=Assets\Organizer.ico
LicenseFile=..\..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\DownloadsOrganizer.exe
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes
[Tasks]
Name: desktopicon; Description: Create a desktop shortcut; Flags: unchecked
[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{userprograms}\Downloads Organizer"; Filename: "{app}\DownloadsOrganizer.exe"
Name: "{userdesktop}\Downloads Organizer"; Filename: "{app}\DownloadsOrganizer.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\DownloadsOrganizer.exe"; Description: Open Downloads Organizer; Flags: nowait postinstall skipifsilent
; User settings/history are outside {app}; retain them on upgrade and uninstall.
