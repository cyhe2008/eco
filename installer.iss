; EcoTank (生态缸) 安装脚本
; 用法: ISCC.exe installer.iss
; 产物: dist\EcoTank-Setup-1.0.0.exe

#define MyAppName "生态缸 EcoTank"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "陈彦和 (cyhe2008)"
#define MyAppURL "https://github.com/cyhe2008/eco"
#define MyAppExeName "EcoTank.exe"

[Setup]
AppId={{A1B2C3D4-5E6F-4A7B-8C9D-0E1F2A3B4C5D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\EcoTank
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=EcoTank-Setup-1.0.0
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
LicenseFile=LICENSE
SetupLogging=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 主程序（已打包的 exe）
Source: "dist\EcoTank.exe"; DestDir: "{app}"; Flags: ignoreversion
; 源码与文档（整个项目目录）
Source: "*.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "build.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "EcoTank.spec"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "release_notes.md"; DestDir: "{app}"; Flags: ignoreversion
Source: ".gitignore"; DestDir: "{app}"; Flags: ignoreversion
Source: "生态缸项目技术总结报告.docx"; DestDir: "{app}"; Flags: ignoreversion
Source: "images\*"; DestDir: "{app}\images"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 清理安装后产生的运行时文件
Type: filesandordirs; Name: "{app}\brains"
Type: files; Name: "{app}\eco_settings.json"
Type: files; Name: "{app}\*.pkl"
