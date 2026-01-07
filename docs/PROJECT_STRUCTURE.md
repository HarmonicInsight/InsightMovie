# プロジェクト構造設計

## project.json スキーマ

### scenes（配列）
各シーンは以下のプロパティを持つ：

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `id` | string | シーン一意識別子（UUID） |
| `media_path` | string/null | 画像または動画ファイルの絶対パス |
| `media_type` | enum | `"image"`, `"video"`, `"none"` |
| `narration_text` | string | 説明文（VOICEVOX音声生成用） |
| `subtitle_text` | string | 字幕テキスト（動画に焼き込み） |
| `duration_mode` | enum | `"auto"` = 音声長に追従, `"fixed"` = 固定秒数 |
| `fixed_seconds` | float | `duration_mode="fixed"` の場合の秒数（デフォルト3.0） |
| `audio_cache_path` | string/null | 生成済み音声ファイルのキャッシュパス |
| `video_cache_path` | string/null | 生成済み動画ファイルのキャッシュパス |

### output（オブジェクト）
最終動画の出力設定：

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `resolution` | string | `"1080x1920"` (縦), `"1920x1080"` (横) |
| `fps` | int | フレームレート（デフォルト30） |
| `output_path` | string | 出力先mp4ファイルパス |

### settings（オブジェクト）
アプリケーション設定：

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `voicevox_base_url` | string | VOICEVOXエンジンのベースURL |
| `voicevox_run_exe` | string/null | run.exeのパス |
| `ffmpeg_path` | string/null | ffmpegの実行パス |
| `font_path` | string/null | 字幕用フォントファイルパス |

## ディレクトリ構造

```
InsightMovie/
├── src/
│   └── insightmovie/
│       ├── project/          # プロジェクト管理（新規）
│       │   ├── __init__.py
│       │   ├── scene.py      # Sceneモデル
│       │   └── project.py    # Projectモデル
│       ├── video/            # 動画生成（新規）
│       │   ├── __init__.py
│       │   ├── ffmpeg_wrapper.py  # ffmpegラッパー
│       │   ├── scene_generator.py # 1シーン生成
│       │   └── video_composer.py  # 動画結合
│       ├── core/             # コア機能
│       ├── voicevox/         # VOICEVOX連携（既存）
│       ├── setup_wizard/     # セットアップ（既存）
│       ├── ui/               # UI（拡張予定）
│       └── main.py
```

## 実装済み機能（Step1）

✅ `Scene` クラス
- メディア、説明文、字幕の管理
- 辞書との相互変換
- プロパティによる状態チェック

✅ `Project` クラス
- デフォルト4シーンの初期化
- シーン追加・削除・並び替え
- JSON保存・読み込み
- バリデーション

✅ 設定クラス
- `OutputSettings`: 出力設定
- `ProjectSettings`: アプリ設定

## 次のステップ

Step2: VOICEVOX クライアントは既存実装を活用
Step3: ffmpeg による1シーン生成の実装
