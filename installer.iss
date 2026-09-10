; Script generated for OmniDoc Studio
#define MyAppName "OmniDoc Studio"
#define MyAppVersion "2.4"
#define MyAppPublisher "OmniDoc Technologies"
#define MyAppURL "https://github.com/rushikin/OmniDoc-Studio"
#define MyAppExeName "OmniDocStudio.exe"

[Setup]
AppId={{D81E57A8-941E-47BC-917B-4E38A375317C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=C:\Users\rushi\Downloads
OutputBaseFilename=OmniDocStudio_v2.4_Setup_Installer
SetupIconFile=c:\Users\rushi\OneDrive\Desktop\ocr\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=zip/1
SolidCompression=no
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "c:\Users\rushi\OneDrive\Desktop\ocr\dist\OmniDocStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "c:\Users\rushi\OneDrive\Desktop\ocr\app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--ui"; IconFilename: "{app}\app_icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--ui"; Tasks: desktopicon; IconFilename: "{app}\app_icon.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--ui"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
