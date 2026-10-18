#define AppName "Spotify Lyrics Overlay"
#define AppVersion "1.0.0"
#define AppPublisher "Pratama"
#define AppExeName "SpotifyLyricsOverlay.exe"

[Setup]
AppId={{4B628588-21F2-4F4C-A34B-B929C923D671}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\Spotify Lyrics Overlay
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=SpotifyLyricsOverlay-Setup
SetupIconFile=spotify_lyrics_overlay\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
WizardStyle=modern
Uninstallable=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Spotify Lyrics Overlay"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\Spotify Lyrics Overlay"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch Spotify Lyrics Overlay"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\config.json"
Type: dirifempty; Name: "{app}"
