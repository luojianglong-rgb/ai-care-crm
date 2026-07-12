; ============================================================
; AI-Care CRM Inno Setup 安装脚本
; ============================================================
; 使用方法：
;   1. 安装 Inno Setup: https://jrsoftware.org/isdl.php
;   2. 打开此文件，点击 Build -> Compile
;   3. 生成的安装包在：Output\AI-Care-CRM-Setup-1.0.0.exe
; ============================================================

#define MyAppName "AI-Care CRM"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "AI-Care"
#define MyDistDir "dist"
#define MyAppExeName "AI-Care-CRM.exe"

[Setup]
; 基础设置
AppId={{A7B8C9D0-E1F2-3456-7890-ABCDEF123456}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://example.com
AppSupportURL=https://example.com/support
AppUpdatesURL=https://example.com/updates

; 安装目录 - 使用 {sd} 让用户选择安装位置
DefaultDirName={sd}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; 输出设置
OutputDir=Output
OutputBaseFilename=AI-Care-CRM-Setup-{#MyAppVersion}
SetupIconFile=
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

; 压缩设置
Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes

; 权限设置
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=commandline

; 其他设置
ShowLanguageDialog=auto
CloseApplications=yes
RestartApplications=no
AllowNoIcons=yes
DisableDirPage=no
DisableReadyPage=no

; 卸载设置
Uninstallable=yes
CreateUninstallRegKey=yes

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 主程序 EXE
Source: "{#MyDistDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; 启动和关闭脚本
Source: "start.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "stop.bat"; DestDir: "{app}"; Flags: ignoreversion

; 配置文件模板（首次启动时自动生成 config.yaml）
Source: "src\config.yaml.template"; DestDir: "{app}\src"; Flags: ignoreversion

; README
Source: "install-package\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; 开始菜单
Name: "{group}\启动 AI-Care CRM"; Filename: "{app}\start.bat"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\关闭 AI-Care CRM"; Filename: "{app}\stop.bat"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\配置文件目录"; Filename: "{app}\src"
Name: "{group}\使用说明"; Filename: "{app}\README.md"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\start.bat"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; 卸载程序
Name: "{autouninstall}\{#MyAppName}"; Filename: "{uninstallexe}"

[Run]
; 安装完成后显示 README
Filename: "notepad.exe"; Parameters: "{app}\README.md"; Description: "查看使用说明"; Flags: postinstall skipifsilent

[Code]
var
  ConfigPage: TWizardPage;
  ApiKeyEdit: TEdit;
  StoreNameEdit: TEdit;

// 安装前检查
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

// 安装完成后显示配置提示
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    MsgBox('安装成功！' + #13 + #13 +
           '下一步操作：' + #13 +
           '1. 点击"启动 AI-Care CRM"快捷方式启动服务' + #13 +
           '2. 浏览器访问 http://localhost:8000/login' + #13 +
           '3. 默认账号：admin / admin' + #13 + #13 +
           '首次启动时系统会自动生成配置文件，' + #13 +
           '请前往安装目录编辑 src\config.yaml 填写 API Key。',
           mbInformation, MB_OK);
  end;
end;

// 卸载前确认
function InitializeUninstall(): Boolean;
begin
  if SuppressibleMsgBox('确定要卸载 AI-Care CRM 吗？' + #13 + #13 +
                        '卸载将删除程序文件，但保留配置文件和数据库。',
                        mbConfirmation, MB_YESNO, IDYES) = IDNO then
    Result := False
  else
    Result := True;
end;

// 卸载时保留配置和数据库
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    // 不删除配置文件和数据库
    DelTree(ExpandConstant('{app}\logs'), True, True, False);
    // 保留 src\config.yaml 和 src\wellness_crm.db
  end;
end;
