; Inno Setup 6 Script for Gayatri Chemistry Tutor
; Generates Gayatri_Chemistry_Tutor_v3_Setup.exe with gai3.ico branding

#define MyAppName "Gayatri Chemistry Tutor"
#define MyAppVersion "3.0.0"
#define MyAppPublisher "Gayatri Education"
#define MyAppURL "https://github.com/Gayatri-Education/Gayatri-Tutor-ChemistryDemo"
#define MyAppExeName "Gayatri_Chemistry_Tutor.exe"

[Setup]
AppId={{E5C31A76-88E2-4C1B-9430-81F2687A1E99}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\GayatriAI\Gayatri Chemistry Tutor
DefaultGroupName=Gayatri AI
DisableProgramGroupPage=yes
OutputDir=..\release_staging
OutputBaseFilename=Gayatri_Chemistry_Tutor_v3_Setup
SetupIconFile=..\gai3.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\gai3.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\Gayatri_Chemistry_Tutor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\gai3.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\gai3.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
