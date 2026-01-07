# ffmpeg セットアップガイド

## Windows へのインストール方法

### 方法1: 公式サイトから手動ダウンロード（推奨）

1. **公式ビルドをダウンロード**
   - https://www.gyan.dev/ffmpeg/builds/ にアクセス
   - 「ffmpeg-release-essentials.zip」をダウンロード
   - または https://github.com/BtbN/FFmpeg-Builds/releases から最新版をダウンロード

2. **展開して配置**
   ```
   C:\ffmpeg\
   ├── bin\
   │   ├── ffmpeg.exe    ← これが必要
   │   ├── ffplay.exe
   │   └── ffprobe.exe
   └── ...
   ```

3. **環境変数PATHに追加（オプション）**
   - システムのプロパティ → 環境変数
   - Path に `C:\ffmpeg\bin` を追加
   - コマンドプロンプトで `ffmpeg -version` で確認

### 方法2: パッケージマネージャー

#### Chocolatey を使う場合
```powershell
# 管理者権限で実行
choco install ffmpeg
```

#### Scoop を使う場合
```powershell
scoop install ffmpeg
```

### 方法3: InsightMovie専用に配置

アプリと同じ場所に配置する場合：
```
InsightMovie/
├── ffmpeg/
│   └── bin/
│       └── ffmpeg.exe
└── src/
```

## InsightMovieでの検出

アプリケーションは以下の順序で自動検出します：

1. **システムPATH** (`where ffmpeg`)
2. **C:\ffmpeg\bin\ffmpeg.exe**
3. **C:\Program Files\ffmpeg\bin\ffmpeg.exe**
4. **%USERPROFILE%\ffmpeg\bin\ffmpeg.exe**

検出できない場合は起動時に警告が表示されます。

## 動作確認

### コマンドラインで確認
```bash
ffmpeg -version
```

正常なら以下のような出力が表示されます：
```
ffmpeg version 2024-xx-xx-git-xxxxxx-essentials_build-www.gyan.dev
Copyright (c) 2000-2024 the FFmpeg developers
...
```

## トラブルシューティング

### ffmpegが見つからない
- PATH環境変数が正しく設定されているか確認
- コマンドプロンプトを再起動
- InsightMovie起動時のエラーメッセージを確認

### 権限エラー
- ffmpeg.exeが実行可能か確認
- ウイルス対策ソフトでブロックされていないか確認

## ライセンス

ffmpegはLGPL/GPLライセンスです。
- 動画コーデックによってライセンスが異なります
- 商用利用の場合はライセンスを確認してください
- 詳細: https://ffmpeg.org/legal.html

## 参考リンク

- 公式サイト: https://ffmpeg.org/
- Windows用ビルド: https://www.gyan.dev/ffmpeg/builds/
- GitHub: https://github.com/FFmpeg/FFmpeg
