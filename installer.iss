; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{8289447E-9572-4CF3-A2CD-841289716F65}
AppName=Inductive calibration GUI
AppVersion=1.0
;AppVerName=Inductive calibration GUI 1.0
AppPublisher=Martijn Schouten
DefaultDirName={autopf}\Inductive calibration GUI
DisableProgramGroupPage=yes
; Remove the following line to run in administrative install mode (install for all users.)
PrivilegesRequired=lowest
OutputBaseFilename=mysetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "D:\phd\git\inductive_calibration_GUI\dist\app\app.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\phd\git\inductive_calibration_GUI\dist\app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{autoprograms}\Inductive calibration GUI"; Filename: "{app}\app.exe"
Name: "{autodesktop}\Inductive calibration GUI"; Filename: "{app}\app.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\app.exe"; Description: "{cm:LaunchProgram,Inductive calibration GUI}"; Flags: nowait postinstall skipifsilent

