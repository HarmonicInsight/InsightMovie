# InsightMovie

VOICEVOX powered 音声生成デスクトップアプリケーション

## 概要

InsightMovieは、ITリテラシーが低いユーザーでも簡単に音声合成ができるWindowsデスクトップアプリケーションです。
VOICEVOXエンジンを使用して、高品質な音声を生成できます。

### 主な機能

- 🎙️ **簡単な音声生成**: テキストを入力するだけで音声を生成
- 🚀 **自動セットアップ**: 初回起動時のウィザードで簡単設定
- 🔍 **エンジン自動検出**: VOICEVOXエンジンを自動で検出・接続
- 💾 **WAVファイル出力**: 生成した音声をファイルとして保存
- 🎨 **使いやすいUI**: 初心者でも迷わない直感的なインターフェース

## インストール

### 1. インストーラーのダウンロード

[Releases](https://github.com/yourusername/insightmovie/releases)から最新版のインストーラーをダウンロードしてください。

- `InsightMovie-Setup-1.0.0.exe`

### 2. インストール実行

1. ダウンロードしたインストーラーを実行
2. インストールウィザードの指示に従う
3. **重要**: 「VOICEVOX自動セットアップ」にチェックを入れる（推奨）

### 3. VOICEVOX自動セットアップについて

- VOICEVOXは**無断再配布禁止**のため、アプリには同梱されていません
- インストーラーが**公式配布元**（https://voicevox.hiroshiba.jp/）から自動的にダウンロードします
- インストール時に利用規約への同意が必要です
- ダウンロード先: `%LOCALAPPDATA%\InsightMovie\voicevox\`

### 4. オフライン環境の場合

インターネット接続がない環境では、以下の手順で手動セットアップしてください：

1. 別のPCでVOICEVOXエンジンを公式サイトからダウンロード
   - https://github.com/VOICEVOX/voicevox_engine/releases
   - Windows CPU版をダウンロード
2. ダウンロードしたZIPファイルを展開
3. 展開したフォルダを以下の場所に配置：
   - `%LOCALAPPDATA%\InsightMovie\voicevox\`
4. アプリを起動し、セットアップウィザードで「手動設定」を選択

## 使い方

### 初回起動

1. InsightMovieを起動
2. セットアップウィザードが表示されます：
   - VOICEVOXエンジンの検出
   - デフォルト話者の設定（青山流星）
   - 接続テスト
3. 「完了」をクリックしてメイン画面へ

### 音声生成

1. テキストボックスに音声にしたい文章を入力
2. 「音声を生成」ボタンをクリック
3. 生成が完了したら「WAVファイルとして保存」で保存

### トラブルシューティング

#### エンジンが見つからない

1. セットアップウィザードで「エンジンを起動」ボタンをクリック
2. それでも見つからない場合は「手動設定」でrun.exeを指定
3. エンジンのパス例: `%LOCALAPPDATA%\InsightMovie\voicevox\run.exe`

#### ポートが50021でない場合

- アプリは自動的にポート50020-50100をスキャンします
- 検出されたエンジンに自動接続します
- 手動でポートを変更したい場合は設定ファイルを編集：
  - `%LOCALAPPDATA%\InsightMovie\config.json`

#### エンジンが起動しない

1. VOICEVOXが正しくインストールされているか確認
2. タスクマネージャーで既にVOICEVOXが起動していないか確認
3. 手動でrun.exeを起動してみる
4. それでも動かない場合は、公式サイトから最新版を再ダウンロード

## 開発者向け情報

### 開発環境構築

```bash
# リポジトリクローン
git clone https://github.com/yourusername/insightmovie.git
cd insightmovie

# 依存関係インストール
pip install -r requirements.txt
```

### アプリケーション実行

```bash
# 開発モードで実行
python -m src.insightmovie.main
```

### ビルド

#### PyInstallerでビルド

```bash
# PyInstallerでアプリケーションをビルド
cd build
pyinstaller insightmovie.spec

# ビルド結果: build/dist/InsightMovie/
```

#### インストーラー作成

1. [Inno Setup](https://jrsoftware.org/isdl.php)をインストール
2. `installer/insightmovie.iss`を開く
3. コンパイル実行
4. インストーラー生成: `build/installer_output/InsightMovie-Setup-1.0.0.exe`

### プロジェクト構造

```
InsightMovie/
├── src/
│   └── insightmovie/
│       ├── core/              # コア機能（設定管理など）
│       │   ├── __init__.py
│       │   └── config.py
│       ├── voicevox/          # VOICEVOX連携
│       │   ├── __init__.py
│       │   ├── client.py      # エンジンクライアント
│       │   └── launcher.py    # エンジンランチャー
│       ├── setup_wizard/      # セットアップウィザード
│       │   ├── __init__.py
│       │   └── wizard.py
│       ├── ui/                # メインUI
│       │   ├── __init__.py
│       │   └── main_window.py
│       ├── __init__.py
│       └── main.py            # エントリーポイント
├── installer/
│   ├── insightmovie.iss       # Inno Setupスクリプト
│   └── voicevox_downloader.py # VOICEVOX自動ダウンロード
├── build/
│   └── insightmovie.spec      # PyInstaller設定
├── docs/                       # ドキュメント
├── requirements.txt
└── README.md
```

## 技術スタック

- **UI Framework**: PySide6 (Qt for Python)
- **HTTP Client**: requests
- **Process Management**: psutil
- **Packaging**: PyInstaller
- **Installer**: Inno Setup

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

### 重要な注意事項

- **VOICEVOX**: このアプリケーションはVOICEVOXを使用しますが、VOICEVOXエンジンは同梱していません
- VOICEVOXは公式配布元から取得され、VOICEVOXの利用規約に従う必要があります
- VOICEVOX公式サイト: https://voicevox.hiroshiba.jp/
- VOICEVOX利用規約: https://voicevox.hiroshiba.jp/term/

## クレジット

- VOICEVOX: https://voicevox.hiroshiba.jp/
- 音声合成エンジン: VOICEVOX Engine

## サポート

問題が発生した場合は、以下をご確認ください：

1. [よくある質問](docs/FAQ.md)
2. [トラブルシューティング](docs/TROUBLESHOOTING.md)
3. [GitHub Issues](https://github.com/yourusername/insightmovie/issues)

## 貢献

プルリクエストを歓迎します！

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにプッシュ (`git push origin feature/AmazingFeature`)
5. プルリクエストを作成

## 変更履歴

### v1.0.0 (2026-01-06)

- 初回リリース
- VOICEVOXエンジン自動検出機能
- セットアップウィザード
- 基本的な音声生成機能
