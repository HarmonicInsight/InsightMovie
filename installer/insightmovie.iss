; Inno Setup Script for InsightMovie
; Windows インストーラー設定

#define MyAppName "InsightMovie"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "InsightMovie"
#define MyAppURL "https://github.com/yourusername/insightmovie"
#define MyAppExeName "InsightMovie.exe"

[Setup]
; アプリケーション基本情報
AppId={{YOUR-GUID-HERE}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
OutputDir=..\build\installer_output
OutputBaseFilename=InsightMovie-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64

; アンインストール設定
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
japanese.VoicevoxSetupTitle=VOICEVOX自動セットアップ
japanese.VoicevoxSetupDescription=VOICEVOXエンジンを公式配布元からダウンロードしてセットアップします（推奨）
japanese.VoicevoxAgreement=VOICEVOXは公式配布元（https://voicevox.hiroshiba.jp/）からダウンロードされます。VOICEVOX利用規約に同意します。
japanese.VoicevoxNote=注意: VOICEVOXは無断再配布禁止のため、公式配布元から直接取得します。
english.VoicevoxSetupTitle=VOICEVOX Auto Setup
english.VoicevoxSetupDescription=Download and setup VOICEVOX Engine from official source (Recommended)
english.VoicevoxAgreement=I agree to download VOICEVOX from the official source (https://voicevox.hiroshiba.jp/) and accept its terms of use.
english.VoicevoxNote=Note: VOICEVOX will be downloaded directly from the official source as redistribution is prohibited.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "voicevoxsetup"; Description: "{cm:VoicevoxSetupDescription}"; GroupDescription: "VOICEVOX"; Flags: checkedonce

[Files]
; アプリケーション本体（PyInstallerでビルドしたフォルダ全体）
Source: "..\build\dist\InsightMovie\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; VOICEVOX自動ダウンロードスクリプト
Source: "voicevox_downloader.py"; DestDir: "{tmp}"; Flags: deleteafterinstall

; Pythonランタイム（オプション: スタンドアロン実行の場合は不要）
; Source: "python-embed\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; VOICEVOX自動セットアップ（チェックされている場合のみ）
Filename: "{cmd}"; Parameters: "/c python ""{tmp}\voicevox_downloader.py"" --install-dir ""{localappdata}\InsightMovie\voicevox"""; StatusMsg: "VOICEVOXエンジンをダウンロード中..."; Flags: runhidden waituntilterminated; Tasks: voicevoxsetup; Check: PythonInstalled

; アプリケーション起動（オプション）
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; アンインストール時にVOICEVOXも削除するか確認
Filename: "{cmd}"; Parameters: "/c rd /s /q ""{localappdata}\InsightMovie\voicevox"""; Flags: runhidden; Check: VoicevoxInstalled

[Code]
var
  VoicevoxAgreementPage: TInputOptionWizardPage;

procedure InitializeWizard;
begin
  // VOICEVOX同意ページを作成
  VoicevoxAgreementPage := CreateInputOptionPage(
    wpSelectTasks,
    ExpandConstant('{cm:VoicevoxSetupTitle}'),
    ExpandConstant('{cm:VoicevoxSetupDescription}'),
    ExpandConstant('{cm:VoicevoxNote}'),
    False,
    False
  );

  VoicevoxAgreementPage.Add(ExpandConstant('{cm:VoicevoxAgreement}'));
  VoicevoxAgreementPage.Values[0] := True;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  // VOICEVOXセットアップタスクが選択されていない場合、同意ページをスキップ
  if (PageID = VoicevoxAgreementPage.ID) and (not IsTaskSelected('voicevoxsetup')) then
    Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  // VOICEVOX同意ページで同意が必要
  if CurPageID = VoicevoxAgreementPage.ID then
  begin
    if not VoicevoxAgreementPage.Values[0] then
    begin
      MsgBox('VOICEVOXのセットアップを続けるには、利用規約に同意する必要があります。', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function PythonInstalled: Boolean;
var
  ResultCode: Integer;
begin
  // Pythonがインストールされているかチェック
  // 注: PyInstallerでビルドした場合は不要（Pythonランタイムが含まれる）
  Result := Exec('python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  // Python未インストールの場合は警告（ただしスキップ可能）
  if not Result then
  begin
    MsgBox('Pythonが見つかりません。VOICEVOXの自動セットアップをスキップします。' + #13#10 +
           '手動でVOICEVOXをインストールしてください。', mbInformation, MB_OK);
  end;
end;

function VoicevoxInstalled: Boolean;
var
  VoicevoxPath: String;
begin
  VoicevoxPath := ExpandConstant('{localappdata}\InsightMovie\voicevox');
  Result := DirExists(VoicevoxPath);
end;

[Registry]
; ファイル関連付け（オプション）
; Root: HKCU; Subkey: "Software\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"

[Messages]
; カスタムメッセージ（必要に応じて）
