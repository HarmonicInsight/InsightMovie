"""
Project Window - 4 Scene Video Editor
4シーン動画編集ウィンドウ
"""
import os
import subprocess
import platform
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QTextEdit,
    QLineEdit, QFileDialog, QMessageBox, QProgressBar, QGroupBox,
    QComboBox, QSpinBox, QDoubleSpinBox, QRadioButton, QButtonGroup,
    QGridLayout, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon
from pathlib import Path
from typing import Optional

from ..project import Project, Scene, MediaType, DurationMode
from ..voicevox import VoiceVoxClient, AudioCache
from ..video import FFmpegWrapper, SceneGenerator, VideoComposer
from .theme import get_stylesheet, COLOR_PALETTE, SPACING


class VideoGenerationThread(QThread):
    """動画生成スレッド"""
    progress = Signal(str)  # 進捗メッセージ
    finished = Signal(bool, str)  # 成功/失敗, メッセージ

    def __init__(
        self,
        project: Project,
        voicevox_client: VoiceVoxClient,
        audio_cache: AudioCache,
        ffmpeg: FFmpegWrapper,
        speaker_id: int
    ):
        super().__init__()
        self.project = project
        self.voicevox = voicevox_client
        self.audio_cache = audio_cache
        self.ffmpeg = ffmpeg
        self.speaker_id = speaker_id

    def run(self):
        """動画生成処理"""
        try:
            import tempfile
            from pathlib import Path

            self.progress.emit("動画生成を開始します...")

            # 一時ディレクトリ
            temp_dir = Path(tempfile.gettempdir()) / "insightmovie_build"
            temp_dir.mkdir(parents=True, exist_ok=True)

            scene_videos = []

            # 各シーンを生成
            for i, scene in enumerate(self.project.scenes, 1):
                self.progress.emit(f"\n{'='*50}")
                self.progress.emit(f"シーン {i}/{len(self.project.scenes)} を処理中...")
                self.progress.emit(f"  ナレーション: {scene.narration_text[:50] if scene.has_narration else 'なし'}")
                self.progress.emit(f"  字幕: {scene.subtitle_text if scene.has_subtitle else 'なし'}")

                # 音声生成
                audio_path = None
                duration = scene.fixed_seconds  # デフォルト
                total_duration = scene.fixed_seconds  # シーンの長さ（無音含む）

                if scene.has_narration:
                    # キャッシュチェック
                    if self.audio_cache.exists(scene.narration_text, self.speaker_id):
                        self.progress.emit(f"  音声をキャッシュから取得中...")
                        audio_data = self.audio_cache.load(scene.narration_text, self.speaker_id)
                        audio_path = self.audio_cache.get_cache_path(
                            scene.narration_text,
                            self.speaker_id
                        )
                        duration = self.audio_cache.get_duration(
                            scene.narration_text,
                            self.speaker_id
                        )
                        self.progress.emit(f"  ✓ 音声取得: {Path(audio_path).name} ({duration:.2f}秒)")
                    else:
                        # 新規生成
                        self.progress.emit(f"  音声を生成中（VOICEVOX）...")
                        audio_data = self.voicevox.generate_audio(
                            scene.narration_text,
                            self.speaker_id
                        )
                        if not audio_data:
                            self.progress.emit(f"  ✗ 音声生成失敗")
                            self.finished.emit(False, "音声生成に失敗しました")
                            return

                        audio_path = self.audio_cache.save(
                            scene.narration_text,
                            self.speaker_id,
                            audio_data
                        )
                        duration = AudioCache.get_audio_duration_from_bytes(audio_data)
                        self.progress.emit(f"  ✓ 音声生成完了: {Path(audio_path).name} ({duration:.2f}秒)")

                    # 前後に無音パディングを追加するため+2秒
                    silence_padding = 2.0  # 前後1秒ずつ

                    if scene.duration_mode == DurationMode.AUTO:
                        # 音声長に合わせる（+無音パディング）
                        if duration:
                            total_duration = duration + silence_padding
                            scene.fixed_seconds = total_duration
                            self.progress.emit(f"  シーン長さを音声に合わせる: {duration:.2f}秒 + 無音{silence_padding}秒 = {total_duration:.2f}秒")
                    else:
                        # 固定長使用
                        total_duration = scene.fixed_seconds
                        self.progress.emit(f"  固定長を使用: {total_duration:.2f}秒")
                else:
                    self.progress.emit(f"  ナレーションなし（音声スキップ）")
                    total_duration = scene.fixed_seconds

                # シーン動画生成
                self.progress.emit(f"  動画を生成中...")
                scene_video_path = temp_dir / f"scene_{i:03d}.mp4"

                generator = SceneGenerator(
                    self.ffmpeg,
                    self.project.settings.font_path
                )

                success = generator.generate_scene(
                    scene,
                    str(scene_video_path),
                    total_duration,
                    self.project.output.resolution,
                    self.project.output.fps,
                    str(audio_path) if audio_path else None
                )

                if not success:
                    self.finished.emit(False, f"シーン {i} の生成に失敗しました")
                    return

                scene_videos.append(str(scene_video_path))

            # 動画を結合
            self.progress.emit("動画を結合中...")
            composer = VideoComposer(self.ffmpeg)

            success = composer.concat_videos(
                scene_videos,
                self.project.output.output_path
            )

            # 一時ファイル削除
            for video_path in scene_videos:
                if Path(video_path).exists():
                    Path(video_path).unlink()

            if success:
                self.finished.emit(True, f"動画を保存しました: {self.project.output.output_path}")
            else:
                self.finished.emit(False, "動画の結合に失敗しました")

        except Exception as e:
            self.finished.emit(False, f"エラー: {str(e)}")


class ProjectWindow(QMainWindow):
    """プロジェクトウィンドウ"""

    def __init__(
        self,
        voicevox_client: VoiceVoxClient,
        speaker_id: int,
        ffmpeg: Optional[FFmpegWrapper] = None
    ):
        super().__init__()
        self.voicevox = voicevox_client
        self.speaker_id = speaker_id

        try:
            self.ffmpeg = ffmpeg or FFmpegWrapper()
        except Exception as e:
            QMessageBox.warning(
                self,
                "ffmpeg未検出",
                f"ffmpegが見つかりません。\n動画生成には ffmpeg が必要です。\n\n{e}"
            )
            self.ffmpeg = None

        self.audio_cache = AudioCache()
        self.project = Project()
        self.current_scene: Optional[Scene] = None
        self.generation_thread: Optional[VideoGenerationThread] = None
        self.speaker_styles: dict = {}  # 話者選択用

        self.setWindowTitle("InsightMovie - 新規プロジェクト")
        self.setMinimumSize(1100, 700)
        self.resize(1300, 900)  # 初期サイズ（リサイズ可能）

        # Insightシリーズ統一テーマを適用
        self.setStyleSheet(get_stylesheet())

        self.setup_ui()
        self.load_scene_list()

    def setup_ui(self):
        """UI構築"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(SPACING['xl'], SPACING['xl'], SPACING['xl'], SPACING['xl'])
        layout.setSpacing(SPACING['lg'])

        # ヘッダー
        header_layout = QHBoxLayout()

        # アプリタイトル
        title_label = QLabel("InsightMovie")
        title_label.setStyleSheet(f"""
            font-size: 18pt;
            font-weight: 600;
            color: {COLOR_PALETTE['text_primary']};
            padding: 0;
        """)
        header_layout.addWidget(title_label)

        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet(f"""
            font-size: 10pt;
            color: {COLOR_PALETTE['text_muted']};
            padding: 0 0 0 {SPACING['sm']}px;
        """)
        header_layout.addWidget(version_label)

        header_layout.addStretch()

        # プロジェクト操作ボタン
        new_btn = QPushButton("新規")
        new_btn.setProperty("class", "secondary")
        new_btn.clicked.connect(self.new_project)
        header_layout.addWidget(new_btn)

        open_btn = QPushButton("開く")
        open_btn.setProperty("class", "secondary")
        open_btn.clicked.connect(self.open_project)
        header_layout.addWidget(open_btn)

        save_btn = QPushButton("保存")
        save_btn.setProperty("class", "secondary")
        save_btn.clicked.connect(self.save_project)
        header_layout.addWidget(save_btn)

        save_as_btn = QPushButton("名前を付けて保存")
        save_as_btn.setProperty("class", "secondary")
        save_as_btn.clicked.connect(self.save_project_as)
        header_layout.addWidget(save_as_btn)

        # ステータス
        voicevox_status = "✓ 接続OK" if self.voicevox.check_connection() else "✗ 未接続"
        ffmpeg_status = "✓ 検出OK" if self.ffmpeg and self.ffmpeg.check_available() else "✗ 未検出"

        self.status_label = QLabel(f"VOICEVOX: {voicevox_status}  •  ffmpeg: {ffmpeg_status}")
        self.status_label.setStyleSheet(f"""
            font-size: 10pt;
            color: {COLOR_PALETTE['text_muted']};
            padding: {SPACING['sm']}px {SPACING['md']}px;
            background-color: {COLOR_PALETTE['bg_secondary']};
            border-radius: 6px;
        """)
        header_layout.addWidget(self.status_label)

        layout.addLayout(header_layout)

        # メインスプリッター
        splitter = QSplitter(Qt.Horizontal)

        # 左側：シーン一覧
        left_panel = self.create_scene_list_panel()
        splitter.addWidget(left_panel)

        # 右側：シーン編集
        right_panel = self.create_scene_edit_panel()
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

        # 下部：書き出しエリア
        export_panel = self.create_export_panel()
        layout.addWidget(export_panel)

        # 進捗バー
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # ログ
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        layout.addWidget(QLabel("ログ:"))
        layout.addWidget(self.log_text)

        central_widget.setLayout(layout)

    def create_scene_list_panel(self) -> QWidget:
        """シーン一覧パネル作成"""
        panel = QGroupBox("シーン一覧")
        layout = QVBoxLayout()

        # シーンリスト
        self.scene_list = QListWidget()
        self.scene_list.currentItemChanged.connect(self.on_scene_selected)
        layout.addWidget(self.scene_list)

        # ボタン
        button_layout = QHBoxLayout()
        button_layout.setSpacing(SPACING['sm'])

        add_btn = QPushButton("＋ 追加")
        add_btn.setProperty("class", "small")
        add_btn.clicked.connect(self.add_scene)
        button_layout.addWidget(add_btn)

        remove_btn = QPushButton("－ 削除")
        remove_btn.setProperty("class", "small")
        remove_btn.clicked.connect(self.remove_scene)
        button_layout.addWidget(remove_btn)

        up_btn = QPushButton("↑")
        up_btn.setProperty("class", "small")
        up_btn.clicked.connect(lambda: self.move_scene(-1))
        button_layout.addWidget(up_btn)

        down_btn = QPushButton("↓")
        down_btn.setProperty("class", "small")
        down_btn.clicked.connect(lambda: self.move_scene(1))
        button_layout.addWidget(down_btn)

        layout.addLayout(button_layout)

        panel.setLayout(layout)
        return panel

    def create_scene_edit_panel(self) -> QWidget:
        """シーン編集パネル作成"""
        panel = QGroupBox("シーン編集")
        layout = QVBoxLayout()

        # 素材選択
        media_layout = QHBoxLayout()
        media_layout.addWidget(QLabel("素材:"))

        self.media_label = QLabel("未設定")
        self.media_label.setMinimumWidth(200)
        media_layout.addWidget(self.media_label)

        select_media_btn = QPushButton("画像/動画を選択")
        select_media_btn.setProperty("class", "secondary")
        select_media_btn.clicked.connect(self.select_media)
        media_layout.addWidget(select_media_btn)

        clear_media_btn = QPushButton("クリア")
        clear_media_btn.setProperty("class", "small")
        clear_media_btn.clicked.connect(self.clear_media)
        media_layout.addWidget(clear_media_btn)

        media_layout.addStretch()
        layout.addLayout(media_layout)

        # プレビューコンテナ（画像と字幕オーバーレイを重ねる）
        self.preview_container = QFrame()
        self.preview_container.setFixedSize(160, 284)  # 9:16比率
        self.preview_container.setStyleSheet(f"""
            QFrame {{
                background-color: #1a1a2e;
                border: 1px solid {COLOR_PALETTE['border_default']};
                border-radius: 4px;
            }}
        """)

        # コンテナ内のレイアウト（QGridLayoutで重ねる）
        preview_layout = QGridLayout(self.preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)

        # 画像表示用ラベル（背面）
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet(f"""
            background-color: transparent;
            color: {COLOR_PALETTE['text_muted']};
            border: none;
        """)
        preview_layout.addWidget(self.thumbnail_label, 0, 0)

        # プレースホルダーラベル（素材未設定時に表示）
        self.placeholder_label = QLabel("素材未設定\n\n画像/動画を\n選択してください")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet(f"""
            background-color: transparent;
            color: {COLOR_PALETTE['text_muted']};
            font-size: 9pt;
            border: none;
        """)
        preview_layout.addWidget(self.placeholder_label, 0, 0)

        # 字幕オーバーレイ（前面、下端に固定）
        self.subtitle_overlay = QLabel()
        self.subtitle_overlay.setAlignment(Qt.AlignCenter)
        self.subtitle_overlay.setWordWrap(True)
        self.subtitle_overlay.setStyleSheet("""
            background-color: rgba(0, 0, 0, 0.7);
            color: white;
            font-size: 8pt;
            padding: 4px 6px;
            border: none;
            border-radius: 0px;
        """)
        self.subtitle_overlay.setMaximumHeight(40)
        self.subtitle_overlay.hide()  # 初期状態は非表示（字幕がない時）
        preview_layout.addWidget(self.subtitle_overlay, 0, 0, Qt.AlignBottom)

        layout.addWidget(self.preview_container)

        # 説明文（ナレーション）
        layout.addWidget(QLabel("説明文（ナレーション）:"))
        self.narration_edit = QTextEdit()
        self.narration_edit.setPlaceholderText(
            "ここに説明文を入力してください。\n"
            "VOICEVOXで音声が生成され、その長さがシーンの長さになります。"
        )
        self.narration_edit.setMaximumHeight(100)
        self.narration_edit.textChanged.connect(self.on_narration_changed)
        layout.addWidget(self.narration_edit)

        # 字幕
        subtitle_layout = QHBoxLayout()
        subtitle_layout.addWidget(QLabel("字幕:"))

        self.subtitle_edit = QLineEdit()
        self.subtitle_edit.setPlaceholderText("画面下部に表示される字幕（空欄OK）")
        self.subtitle_edit.textChanged.connect(self.on_subtitle_changed)
        subtitle_layout.addWidget(self.subtitle_edit)

        layout.addLayout(subtitle_layout)

        # 長さ設定
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("シーンの長さ:"))

        # ラジオボタン
        self.duration_auto_radio = QRadioButton("自動（音声に合わせる）")
        self.duration_auto_radio.setChecked(True)  # デフォルトは自動
        self.duration_auto_radio.toggled.connect(self.on_duration_mode_changed)
        duration_layout.addWidget(self.duration_auto_radio)

        self.duration_fixed_radio = QRadioButton("固定秒数")
        duration_layout.addWidget(self.duration_fixed_radio)

        self.fixed_seconds_spin = QDoubleSpinBox()
        self.fixed_seconds_spin.setRange(0.1, 60.0)
        self.fixed_seconds_spin.setValue(3.0)
        self.fixed_seconds_spin.setSuffix(" 秒")
        self.fixed_seconds_spin.setEnabled(False)  # デフォルトは無効
        self.fixed_seconds_spin.valueChanged.connect(self.on_fixed_seconds_changed)
        duration_layout.addWidget(self.fixed_seconds_spin)

        duration_layout.addStretch()
        layout.addLayout(duration_layout)

        layout.addStretch()

        panel.setLayout(layout)
        return panel

    def create_export_panel(self) -> QWidget:
        """書き出しパネル作成"""
        panel = QGroupBox("書き出し設定")
        layout = QHBoxLayout()

        # 話者選択
        layout.addWidget(QLabel("話者:"))
        self.speaker_combo = QComboBox()
        self.speaker_combo.setMinimumWidth(200)
        self.load_speakers()
        self.speaker_combo.currentIndexChanged.connect(self.on_speaker_changed)
        layout.addWidget(self.speaker_combo)

        # 解像度
        layout.addWidget(QLabel("解像度:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "1080x1920 (縦動画)",
            "1920x1080 (横動画)"
        ])
        layout.addWidget(self.resolution_combo)

        # FPS
        layout.addWidget(QLabel("FPS:"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(15, 60)
        self.fps_spin.setValue(30)
        layout.addWidget(self.fps_spin)

        layout.addStretch()

        # 書き出しボタン
        export_btn = QPushButton("動画を書き出し")
        export_btn.setProperty("class", "success")
        export_btn.setMinimumWidth(150)
        export_btn.setMinimumHeight(44)
        export_btn.setStyleSheet("""
            QPushButton {
                font-size: 12pt;
                font-weight: 600;
            }
        """)
        export_btn.clicked.connect(self.export_video)
        layout.addWidget(export_btn)

        panel.setLayout(layout)
        return panel

    def load_speakers(self):
        """VOICEVOX話者一覧を読み込み"""
        self.speaker_combo.clear()
        self.speaker_styles = {}  # {表示名: style_id}

        try:
            speakers = self.voicevox.get_speakers()

            for speaker in speakers:
                speaker_name = speaker.get("name", "不明")
                for style in speaker.get("styles", []):
                    style_name = style.get("name", "ノーマル")
                    style_id = style.get("id")

                    if style_name == "ノーマル":
                        display_name = speaker_name
                    else:
                        display_name = f"{speaker_name} ({style_name})"

                    self.speaker_styles[display_name] = style_id
                    self.speaker_combo.addItem(display_name)

            # 現在のspeaker_idを選択状態にする
            for display_name, style_id in self.speaker_styles.items():
                if style_id == self.speaker_id:
                    index = self.speaker_combo.findText(display_name)
                    if index >= 0:
                        self.speaker_combo.setCurrentIndex(index)
                    break

        except Exception as e:
            self.speaker_combo.addItem("(話者取得失敗)")
            self.log(f"話者一覧の取得に失敗: {e}")

    def on_speaker_changed(self, index: int):
        """話者選択変更時"""
        display_name = self.speaker_combo.currentText()
        if display_name in self.speaker_styles:
            self.speaker_id = self.speaker_styles[display_name]
            self.log(f"話者を変更: {display_name}")

    def load_scene_list(self):
        """シーン一覧を読み込み"""
        self.scene_list.clear()
        for i, scene in enumerate(self.project.scenes, 1):
            # 画像設定状況を表示
            if scene.media_path:
                media_name = Path(scene.media_path).name
                # ファイル名が長い場合は省略
                if len(media_name) > 15:
                    media_name = media_name[:12] + "..."
                item_text = f"シーン {i}: {media_name}"
            else:
                item_text = f"シーン {i}: (未設定)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, scene.id)
            self.scene_list.addItem(item)

        if self.project.scenes:
            self.scene_list.setCurrentRow(0)

    def on_scene_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """シーン選択時"""
        if not current:
            return

        scene_id = current.data(Qt.UserRole)
        self.current_scene = self.project.get_scene(scene_id)

        if self.current_scene:
            self.load_scene_data()

    def load_scene_data(self):
        """現在のシーンデータをUIに読み込み"""
        if not self.current_scene:
            return

        # 素材
        if self.current_scene.media_path:
            self.media_label.setText(Path(self.current_scene.media_path).name)
            # サムネイル表示
            self.load_thumbnail(self.current_scene.media_path)
            self.placeholder_label.hide()
        else:
            self.media_label.setText("未設定")
            self.thumbnail_label.setPixmap(QPixmap())
            self.placeholder_label.show()

        # 説明文
        self.narration_edit.blockSignals(True)
        self.narration_edit.setText(self.current_scene.narration_text)
        self.narration_edit.blockSignals(False)

        # 字幕
        self.subtitle_edit.blockSignals(True)
        self.subtitle_edit.setText(self.current_scene.subtitle_text)
        self.subtitle_edit.blockSignals(False)

        # 字幕プレビュー更新
        self.update_subtitle_preview()

        # 長さモード（ラジオボタン）
        self.duration_auto_radio.blockSignals(True)
        self.duration_fixed_radio.blockSignals(True)

        if self.current_scene.duration_mode == DurationMode.AUTO:
            self.duration_auto_radio.setChecked(True)
        else:
            self.duration_fixed_radio.setChecked(True)

        self.duration_auto_radio.blockSignals(False)
        self.duration_fixed_radio.blockSignals(False)

        self.fixed_seconds_spin.blockSignals(True)
        self.fixed_seconds_spin.setValue(self.current_scene.fixed_seconds)
        self.fixed_seconds_spin.blockSignals(False)

        # スピンボックスの有効/無効を設定
        self.fixed_seconds_spin.setEnabled(self.current_scene.duration_mode == DurationMode.FIXED)

    def select_media(self):
        """素材選択"""
        if not self.current_scene:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "素材を選択",
            "",
            "画像・動画 (*.png *.jpg *.jpeg *.webp *.mp4 *.mov *.avi);;すべてのファイル (*)"
        )

        if file_path:
            self.current_scene.media_path = file_path

            # メディアタイプを判定
            ext = Path(file_path).suffix.lower()
            if ext in ['.png', '.jpg', '.jpeg', '.webp']:
                self.current_scene.media_type = MediaType.IMAGE
            elif ext in ['.mp4', '.mov', '.avi']:
                self.current_scene.media_type = MediaType.VIDEO
            else:
                self.current_scene.media_type = MediaType.NONE

            self.load_scene_data()
            self.update_scene_list_item()
            self.log(f"素材を設定: {Path(file_path).name}")

    def clear_media(self):
        """素材クリア"""
        if not self.current_scene:
            return

        self.current_scene.media_path = None
        self.current_scene.media_type = MediaType.NONE
        self.load_scene_data()
        self.update_scene_list_item()
        self.log("素材をクリアしました")

    def update_scene_list_item(self):
        """現在選択中のシーン一覧アイテムを更新"""
        current_row = self.scene_list.currentRow()
        if current_row < 0 or not self.current_scene:
            return

        # 画像設定状況を表示
        if self.current_scene.media_path:
            media_name = Path(self.current_scene.media_path).name
            if len(media_name) > 15:
                media_name = media_name[:12] + "..."
            item_text = f"シーン {current_row + 1}: {media_name}"
        else:
            item_text = f"シーン {current_row + 1}: (未設定)"

        self.scene_list.currentItem().setText(item_text)

    def load_thumbnail(self, media_path: str):
        """サムネイルを読み込み表示"""
        try:
            path = Path(media_path)
            ext = path.suffix.lower()

            if ext in ['.png', '.jpg', '.jpeg', '.webp']:
                # 画像の場合は直接読み込み
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    # 枠内に収まるよう縮小（アスペクト比維持、全体表示）
                    target_size = QSize(158, 282)  # border分を考慮
                    scaled = pixmap.scaled(
                        target_size,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.thumbnail_label.setPixmap(scaled)
                    self.placeholder_label.hide()
                else:
                    self.thumbnail_label.setPixmap(QPixmap())
                    self.placeholder_label.setText("読み込み\nエラー")
                    self.placeholder_label.show()
            elif ext in ['.mp4', '.mov', '.avi']:
                # 動画の場合はプレースホルダー表示
                self.thumbnail_label.setPixmap(QPixmap())
                self.placeholder_label.setText("動画\n(プレビュー非対応)")
                self.placeholder_label.show()
            else:
                self.thumbnail_label.setPixmap(QPixmap())
                self.placeholder_label.setText("プレビュー\nなし")
                self.placeholder_label.show()
        except Exception as e:
            self.thumbnail_label.setPixmap(QPixmap())
            self.placeholder_label.setText(f"エラー\n{str(e)[:20]}")
            self.placeholder_label.show()

    def on_narration_changed(self):
        """説明文変更時"""
        if not self.current_scene:
            return
        self.current_scene.narration_text = self.narration_edit.toPlainText()

    def on_subtitle_changed(self):
        """字幕変更時"""
        if not self.current_scene:
            return
        self.current_scene.subtitle_text = self.subtitle_edit.text()
        self.update_subtitle_preview()

    def update_subtitle_preview(self):
        """字幕プレビューを更新"""
        # シーン未選択または字幕が空の場合は非表示
        if not self.current_scene or not self.current_scene.subtitle_text:
            self.subtitle_overlay.hide()
            return

        subtitle = self.current_scene.subtitle_text

        # 文字数に応じて警告色を変更
        char_count = len(subtitle)
        max_chars_per_line = 18  # 動画と同じ設定
        max_total = 36  # 2行で収まる目安

        if char_count > max_total:
            # 長すぎる場合は赤背景で警告
            bg_color = "rgba(180, 50, 50, 0.9)"
            display_text = f"{subtitle[:32]}...\n({char_count}文字)"
        elif char_count > max_chars_per_line:
            # 2行になる場合（動画と同じ分割ロジック）
            bg_color = "rgba(0, 0, 0, 0.7)"
            display_text = self._split_subtitle_for_preview(subtitle, max_chars_per_line)
        else:
            # 1行で収まる
            bg_color = "rgba(0, 0, 0, 0.7)"
            display_text = subtitle

        self.subtitle_overlay.setText(display_text)
        self.subtitle_overlay.setStyleSheet(f"""
            background-color: {bg_color};
            color: white;
            font-size: 8pt;
            padding: 4px 6px;
            border: none;
        """)
        self.subtitle_overlay.show()  # 字幕がある時のみ表示

    def _split_subtitle_for_preview(self, text: str, max_chars: int = 18) -> str:
        """字幕テキストを分割（プレビュー用、動画生成と同じロジック）"""
        if len(text) <= max_chars:
            return text

        mid = len(text) // 2
        split_pos = mid

        for offset in range(6):
            pos = mid + offset
            if pos < len(text) and text[pos] in ' 、。，．！？':
                split_pos = pos + 1
                break
            pos = mid - offset
            if pos > 0 and text[pos] in ' 、。，．！？':
                split_pos = pos + 1
                break

        line1 = text[:split_pos].strip()
        line2 = text[split_pos:].strip()

        if line2:
            return f"{line1}\n{line2}"
        return line1

    def on_duration_mode_changed(self, checked: bool):
        """長さモード変更時"""
        if not self.current_scene:
            return

        # ラジオボタンのtoggledは両方のボタンで発火するため、checkedがTrueの時のみ処理
        if not checked:
            return

        if self.duration_auto_radio.isChecked():
            self.current_scene.duration_mode = DurationMode.AUTO
            self.fixed_seconds_spin.setEnabled(False)
        else:
            self.current_scene.duration_mode = DurationMode.FIXED
            self.fixed_seconds_spin.setEnabled(True)

    def on_fixed_seconds_changed(self, value: float):
        """固定秒数変更時"""
        if not self.current_scene:
            return
        self.current_scene.fixed_seconds = value

    def add_scene(self):
        """シーン追加"""
        current_row = self.scene_list.currentRow()
        self.project.add_scene(current_row + 1 if current_row >= 0 else None)
        self.load_scene_list()
        self.log("シーンを追加しました")

    def remove_scene(self):
        """シーン削除"""
        if not self.current_scene:
            return

        if len(self.project.scenes) <= 1:
            QMessageBox.warning(self, "削除不可", "最低1つのシーンは必要です")
            return

        self.project.remove_scene(self.current_scene.id)
        self.load_scene_list()
        self.log("シーンを削除しました")

    def move_scene(self, direction: int):
        """シーン移動"""
        if not self.current_scene:
            return

        if self.project.move_scene(self.current_scene.id, direction):
            current_row = self.scene_list.currentRow()
            self.load_scene_list()
            self.scene_list.setCurrentRow(current_row + direction)
            self.log("シーンを移動しました")

    def export_video(self):
        """動画書き出し"""
        if not self.ffmpeg:
            QMessageBox.warning(self, "エラー", "ffmpegが利用できません")
            return

        # 出力先選択
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "動画を保存",
            "",
            "MP4ファイル (*.mp4)"
        )

        if not output_path:
            return

        # 設定を反映
        resolution_text = self.resolution_combo.currentText()
        if "1080x1920" in resolution_text:
            self.project.output.resolution = "1080x1920"
        else:
            self.project.output.resolution = "1920x1080"

        self.project.output.fps = self.fps_spin.value()
        self.project.output.output_path = output_path

        # 生成スレッド開始
        self.generation_thread = VideoGenerationThread(
            self.project,
            self.voicevox,
            self.audio_cache,
            self.ffmpeg,
            self.speaker_id
        )

        self.generation_thread.progress.connect(self.log)
        self.generation_thread.finished.connect(self.on_generation_finished)

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        self.log("動画生成を開始します...")
        self.generation_thread.start()

    def on_generation_finished(self, success: bool, message: str):
        """動画生成完了時"""
        self.progress_bar.setVisible(False)
        self.log(message)

        if success:
            QMessageBox.information(self, "完了", message)
            # 出力フォルダを開く
            self.open_output_folder()
        else:
            QMessageBox.warning(self, "エラー", message)

    def open_output_folder(self):
        """出力フォルダをエクスプローラーで開く"""
        if not self.project.output.output_path:
            return

        output_path = Path(self.project.output.output_path)
        output_dir = output_path.parent

        try:
            if platform.system() == "Windows":
                # Windowsの場合、エクスプローラーでファイルを選択状態で開く
                # /select,とパスは一つの引数として渡す必要がある
                file_path_win = str(output_path.resolve()).replace('/', '\\')
                subprocess.run(['explorer', f'/select,{file_path_win}'])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(['open', '-R', str(output_path)])
            else:  # Linux
                subprocess.run(['xdg-open', str(output_dir)])
        except Exception as e:
            self.log(f"フォルダを開けませんでした: {e}")

    def log(self, message: str):
        """ログ表示"""
        self.log_text.append(message)

    def new_project(self):
        """新規プロジェクト"""
        reply = QMessageBox.question(
            self,
            "新規プロジェクト",
            "現在のプロジェクトを破棄して新規作成しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.project = Project()
            self.current_scene = None
            self.load_scene_list()
            self.update_window_title()
            self.log("新規プロジェクトを作成しました")

    def open_project(self):
        """プロジェクトを開く"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "プロジェクトを開く",
            "",
            "InsightMovieプロジェクト (*.improj);;JSONファイル (*.json);;すべてのファイル (*)"
        )

        if not file_path:
            return

        try:
            self.project = Project(file_path)
            self.current_scene = None
            self.load_scene_list()
            self.update_window_title()
            self.log(f"プロジェクトを開きました: {Path(file_path).name}")
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"プロジェクトを開けませんでした:\n{e}")

    def save_project(self):
        """プロジェクトを保存（上書き）"""
        if self.project.project_path:
            try:
                self.project.save()
                self.update_window_title()
                self.log(f"プロジェクトを保存しました: {Path(self.project.project_path).name}")
            except Exception as e:
                QMessageBox.warning(self, "エラー", f"保存に失敗しました:\n{e}")
        else:
            self.save_project_as()

    def save_project_as(self):
        """名前を付けてプロジェクトを保存"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "プロジェクトを保存",
            "",
            "InsightMovieプロジェクト (*.improj);;JSONファイル (*.json)"
        )

        if not file_path:
            return

        # 拡張子がなければ追加
        if not file_path.endswith(('.improj', '.json')):
            file_path += '.improj'

        try:
            self.project.save(file_path)
            self.update_window_title()
            self.log(f"プロジェクトを保存しました: {Path(file_path).name}")
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"保存に失敗しました:\n{e}")

    def update_window_title(self):
        """ウィンドウタイトルを更新"""
        if self.project.project_path:
            filename = Path(self.project.project_path).name
            self.setWindowTitle(f"InsightMovie - {filename}")
        else:
            self.setWindowTitle("InsightMovie - 新規プロジェクト")
