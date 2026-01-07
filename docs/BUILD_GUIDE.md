# ビルドガイド

InsightMovieのビルドとインストーラー作成手順

## 前提条件

### 必須ツール

1. **Python 3.8以上**
   - https://www.python.org/downloads/

2. **Inno Setup 6以上**
   - https://jrsoftware.org/isdl.php
   - Windows用インストーラー作成ツール

3. **Git**
   - https://git-scm.com/

### 環境構築

```bash
# リポジトリクローン
git clone https://github.com/yourusername/insightmovie.git
cd insightmovie

# 仮想環境作成（推奨）
python -m venv venv
venv\Scripts\activate  # Windows

# 依存関係インストール
pip install -r requirements.txt
```

## ビルド手順

### 1. アプリケーションのテスト実行

まず開発環境で動作確認：

```bash
# メインアプリケーション実行
python -m src.insightmovie.main
```

**確認事項:**
- セットアップウィザードが表示される
- VOICEVOXエンジン検出が動作する
- 音声生成ができる

### 2. PyInstallerでビルド

```bash
# buildディレクトリに移動
cd build

# PyInstallerでビルド実行
pyinstaller insightmovie.spec

# ビルド完了後、以下に出力される:
# build/dist/InsightMovie/
```

**ビルド成果物:**
- `dist/InsightMovie/InsightMovie.exe` - メイン実行ファイル
- `dist/InsightMovie/` - 必要なDLLや依存ファイル

### 3. ビルド結果の動作確認

```bash
# ビルドしたアプリケーションを実行
cd dist\InsightMovie
InsightMovie.exe
```

**確認事項:**
- Pythonがインストールされていない環境で動作する
- セットアップウィザードが正常に表示される
- 全機能が正常に動作する

### 4. インストーラー作成

#### 4.1 Inno Setupでコンパイル

```bash
# installer ディレクトリに移動
cd ..\..\installer

# Inno Setup Compiler を使ってコンパイル
# （GUIから実行する場合）
# 1. insightmovie.iss をInno Setup Compilerで開く
# 2. メニューから Build > Compile を選択

# （コマンドラインから実行する場合）
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" insightmovie.iss
```

#### 4.2 インストーラー出力確認

```
build/installer_output/InsightMovie-Setup-1.0.0.exe
```

### 5. インストーラーのテスト

#### 5.1 クリーンな環境で実行

1. 仮想マシンまたはテスト用PCを用意
2. インストーラーを実行
3. インストールウィザードの動作確認

**確認項目:**
- インストール先の選択が正しく動作する
- VOICEVOX自動セットアップのチェックボックスが表示される
- ffmpeg自動セットアップのチェックボックスが表示される
- VOICEVOX利用規約への同意ページが表示される
- デスクトップアイコン作成が選択できる

#### 5.2 VOICEVOX自動セットアップのテスト

インストール時に「VOICEVOX自動セットアップ」にチェックを入れた場合：

**期待される動作:**
1. インストール中に「VOICEVOXエンジンをダウンロード中...」と表示
2. `%LOCALAPPDATA%\InsightMovie\voicevox\` にダウンロード
3. ZIPが自動展開される
4. run.exeが配置される

**確認方法:**
```cmd
# ダウンロード先を確認
dir %LOCALAPPDATA%\InsightMovie\voicevox

# run.exeの存在確認
where /R %LOCALAPPDATA%\InsightMovie\voicevox run.exe
```

#### 5.3 ffmpeg自動セットアップのテスト

インストール時に「ffmpeg自動セットアップ」にチェックを入れた場合：

**期待される動作:**
1. インストール中に「ffmpegをダウンロード中...」と表示
2. インストール先の `tools\ffmpeg\bin\` にダウンロード
3. ZIPが自動展開される
4. ffmpeg.exeが配置される

**確認方法:**
```cmd
# インストール先を確認（デフォルト: C:\Program Files\InsightMovie）
dir "C:\Program Files\InsightMovie\tools\ffmpeg\bin"

# ffmpeg.exeの存在確認
"C:\Program Files\InsightMovie\tools\ffmpeg\bin\ffmpeg.exe" -version
```

#### 5.4 アプリケーション起動テスト

インストール後、アプリケーションを起動：

1. スタートメニューから「InsightMovie」を起動
2. セットアップウィザードが表示される
3. VOICEVOXエンジンが自動検出される
4. 「青山流星」が自動選択される
5. メイン画面が表示される

#### 5.5 音声生成・動画生成テスト

**音声生成:**
1. シーンにナレーションテキストを入力: "こんにちは、テストです。"
2. 音声生成が実行される
3. 生成された音声が再生できる

**動画生成:**
1. シーンに画像または動画を追加
2. ナレーションと字幕を設定
3. 「動画を生成」ボタンをクリック
4. プログレスバーが表示される
5. 動画生成が完了し、ファイルが保存される
6. 生成された動画が再生できる

## トラブルシューティング

### PyInstallerビルドエラー

#### エラー: "ModuleNotFoundError"

```bash
# hiddenimportsに追加
# insightmovie.spec を編集:
hiddenimports=[
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    '不足しているモジュール名',
],
```

#### エラー: "No module named 'PySide6'"

```bash
# PySide6を再インストール
pip uninstall PySide6
pip install PySide6
```

### Inno Setupコンパイルエラー

#### エラー: "Source file not found"

- `insightmovie.iss` の `Source` パスを確認
- PyInstallerのビルドが完了しているか確認
- `build/dist/InsightMovie/` が存在するか確認

#### エラー: "Unable to execute file"

- Python が正しくインストールされているか確認
- `voicevox_downloader.py` のパスが正しいか確認

### VOICEVOX/ffmpeg自動ダウンロードエラー

#### ダウンロードが失敗する

```bash
# 手動でテスト（VOICEVOX）
cd installer
python voicevox_downloader.py --install-dir "C:\test_voicevox"

# 手動でテスト（ffmpeg）
python ffmpeg_downloader.py --install-dir "C:\test_ffmpeg"
```

**考えられる原因:**
- インターネット接続がない
- GitHub APIのレート制限（VOICEVOX）
- 公式配布元のURL変更

**対処法:**
1. インターネット接続を確認
2. 時間を置いて再試行
3. 手動でVOICEVOX/ffmpegをダウンロードして配置
   - VOICEVOX: https://voicevox.hiroshiba.jp/
   - ffmpeg: https://www.gyan.dev/ffmpeg/builds/

## リリース手順

### 1. バージョン番号の更新

以下のファイルでバージョン番号を更新：

- `src/insightmovie/__init__.py` - `__version__`
- `installer/insightmovie.iss` - `#define MyAppVersion`
- `README.md` - バージョン番号

### 2. 変更履歴の更新

`README.md` の変更履歴セクションを更新

### 3. ビルドとテスト

上記の手順でビルド・テストを実行

### 4. GitHubリリース作成

```bash
# タグ作成
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# GitHub Releasesページで新規リリース作成
# インストーラーファイルをアップロード
```

### 5. リリースノート作成

リリースノートに以下を記載：

- 新機能
- バグ修正
- 既知の問題
- インストール手順
- システム要件

## システム要件（参考）

### 開発環境

- OS: Windows 10/11
- Python: 3.8以上
- メモリ: 4GB以上推奨
- ディスク: 2GB以上の空き容量

### エンドユーザー環境

- OS: Windows 10/11 (64bit)
- メモリ: 2GB以上推奨
- ディスク: 2GB以上の空き容量（VOICEVOX含む）
- インターネット接続（初回セットアップ時のみ）

## 自動化（オプション）

### ビルドスクリプト

`build/build.bat` を使用して自動ビルド：

```batch
@echo off
echo InsightMovie Build Script
echo ==============================

cd /d %~dp0

echo [1/3] Building with PyInstaller...
pyinstaller insightmovie.spec
if %errorlevel% neq 0 goto error

echo [2/3] Testing build...
dist\InsightMovie\InsightMovie.exe --version
if %errorlevel% neq 0 goto error

echo [3/3] Creating installer...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" ..\installer\insightmovie.iss
if %errorlevel% neq 0 goto error

echo.
echo ==============================
echo Build completed successfully!
echo ==============================
goto end

:error
echo.
echo ==============================
echo Build failed!
echo ==============================
exit /b 1

:end
```

## まとめ

これで InsightMovie のビルドとインストーラー作成が完了です。

質問や問題がある場合は、GitHub Issuesで報告してください。
