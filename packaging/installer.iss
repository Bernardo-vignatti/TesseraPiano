#ifndef AppVersion
  #error Use scripts/build.py para informar a versão do aplicativo.
#endif
#ifndef BuildDirectory
  #define BuildDirectory "..\dist\TesseraPiano"
#endif
[Setup]
AppId={{8ED65A63-FF38-4B82-9DE9-21162E345B88}
AppName=Tessera Piano
AppVersion={#AppVersion}
AppPublisher=Vignatti
AppPublisherURL=https://github.com/Bernardo-vignatti/TesseraPiano
AppSupportURL=https://github.com/Bernardo-vignatti/TesseraPiano/issues
AppUpdatesURL=https://github.com/Bernardo-vignatti/TesseraPiano/releases
DefaultDirName={localappdata}\Programs\TesseraPiano
DefaultGroupName=Tessera Piano
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=TesseraPiano-Setup-{#AppVersion}-x64
SetupIconFile=..\src\tessera_piano\resources\icons\tessera.ico
UninstallDisplayIcon={app}\TesseraPiano.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
WizardImageFile=assets\installer-side.bmp
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
AppMutex=Local\Vignatti.TesseraPiano
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
CreateUninstallRegKey=not IsIsolatedTest
Uninstallable=not IsIsolatedTest

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; Flags: unchecked

[Files]
Source: "{#BuildDirectory}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Tessera Piano"; Filename: "{app}\TesseraPiano.exe"
Name: "{autodesktop}\Tessera Piano"; Filename: "{app}\TesseraPiano.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\TesseraPiano.exe"; Description: "Abrir Tessera Piano"; Flags: nowait postinstall skipifsilent

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal\tessera_piano\resources\sources"
Type: files; Name: "{app}\_internal\tessera_piano\resources\icons\tessera-master.png"
Type: files; Name: "{app}\_internal\tessera_piano\resources\icons\tessera-160.png"
Type: files; Name: "{app}\_internal\tessera_piano\resources\icons\tessera-256.png"
Type: files; Name: "{app}\_internal\tessera_piano\resources\icons\tessera-32.png"
Type: files; Name: "{app}\_internal\tessera_piano\resources\icons\tessera-64.png"
Type: files; Name: "{app}\_internal\tessera_piano\resources\icons\tessera-96.png"
Type: files; Name: "{app}\_internal\tessera_piano\resources\icons\installer-header.bmp"
Type: files; Name: "{app}\_internal\tessera_piano\resources\icons\installer-side.bmp"
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\runtime"
Type: files; Name: "{app}\Desinstalar.exe"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\TesseraPiano"; Flags: deletekey; Check: not IsIsolatedTest

[Code]
function IsIsolatedTest: Boolean;
begin
  Result := ExpandConstant('{param:ISOLATEDTEST|0}') = '1';
end;
