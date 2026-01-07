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
    QComboBox, QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon
from pathlib import Path
from typing import Optional

from ..project import Project, Scene, MediaType, DurationMode
from ..voicevox import VoiceVoxClient, AudioCache
from ..video import FFmpegWrapper, SceneGenerator, VideoComposer


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
                self.progress.emit(f"シーン {i}/{len(self.project.scenes)} を処理中...")

                # 音声生成
                audio_path = None
                duration = scene.fixed_seconds  # デフォルト

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
                    else:
                        # 新規生成
                        self.progress.emit(f"  音声を生成中...")
                        audio_data = self.voicevox.generate_audio(
                            scene.narration_text,
                            self.speaker_id
                        )
                        audio_path = self.audio_cache.save(
                            scene.narration_text,
                            self.speaker_id,
                            audio_data
                        )
                        duration = AudioCache.get_audio_duration_from_bytes(audio_data)

                    if scene.duration_mode == DurationMode.AUTO:
                        # 音声長に合わせる
                        if duration:
                            scene.fixed_seconds = duration
                    else:
                        # 固定長使用
                        duration = scene.fixed_seconds

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
                    duration or scene.fixed_seconds,
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

        self.setWindowTitle("InsightMovie - 動画自動生成")
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)  # 初期サイズ（リサイズ可能）

        self.setup_ui()
        self.load_scene_list()

    def setup_ui(self):
        """UI構築"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        # ステータスバー
        status_layout = QHBoxLayout()

        voicevox_status = "✓ 接続OK" if self.voicevox.check_connection() else "✗ 未接続"
        ffmpeg_status = "✓ 検出OK" if self.ffmpeg and self.ffmpeg.check_available() else "✗ 未検出"

        self.status_label = QLabel(f"VOICEVOX: {voicevox_status} | ffmpeg: {ffmpeg_status}")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        layout.addLayout(status_layout)

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

        add_btn = QPushButton("＋ 追加")
        add_btn.clicked.connect(self.add_scene)
        button_layout.addWidget(add_btn)

        remove_btn = QPushButton("－ 削除")
        remove_btn.clicked.connect(self.remove_scene)
        button_layout.addWidget(remove_btn)

        up_btn = QPushButton("↑")
        up_btn.clicked.connect(lambda: self.move_scene(-1))
        button_layout.addWidget(up_btn)

        down_btn = QPushButton("↓")
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
        select_media_btn.clicked.connect(self.select_media)
        media_layout.addWidget(select_media_btn)

        clear_media_btn = QPushButton("クリア")
        clear_media_btn.clicked.connect(self.clear_media)
        media_layout.addWidget(clear_media_btn)

        media_layout.addStretch()
        layout.addLayout(media_layout)

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
        layout.addWidget(QLabel("字幕:"))
        self.subtitle_edit = QLineEdit()
        self.subtitle_edit.setPlaceholderText("画面下部に表示される字幕（空欄OK）")
        self.subtitle_edit.textChanged.connect(self.on_subtitle_changed)
        layout.addWidget(self.subtitle_edit)

        # 長さ設定
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("シーンの長さ:"))

        self.duration_combo = QComboBox()
        self.duration_combo.addItems(["自動（音声に合わせる）", "固定秒数"])
        self.duration_combo.currentIndexChanged.connect(self.on_duration_mode_changed)
        duration_layout.addWidget(self.duration_combo)

        self.fixed_seconds_spin = QDoubleSpinBox()
        self.fixed_seconds_spin.setRange(0.1, 60.0)
        self.fixed_seconds_spin.setValue(3.0)
        self.fixed_seconds_spin.setSuffix(" 秒")
        self.fixed_seconds_spin.valueChanged.connect(self.on_fixed_seconds_changed)
        duration_layout.addWidget(self.fixed_seconds_spin)

        duration_layout.addStretch()
        layout.addLayout(duration_layout)

        layout.addStretch()

        panel.setLayout(layout)
        return panel

    def create_export_panel(self) -> QWidget:
        """書き出しパネル作成"""
        panel = QGroupBox("書き出し")
        layout = QHBoxLayout()

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
        export_btn.setMinimumWidth(150)
        export_btn.clicked.connect(self.export_video)
        layout.addWidget(export_btn)

        panel.setLayout(layout)
        return panel

    def load_scene_list(self):
        """シーン一覧を読み込み"""
        self.scene_list.clear()
        for i, scene in enumerate(self.project.scenes, 1):
            item = QListWidgetItem(f"シーン {i}")
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
        else:
            self.media_label.setText("未設定")

        # 説明文
        self.narration_edit.blockSignals(True)
        self.narration_edit.setText(self.current_scene.narration_text)
        self.narration_edit.blockSignals(False)

        # 字幕
        self.subtitle_edit.blockSignals(True)
        self.subtitle_edit.setText(self.current_scene.subtitle_text)
        self.subtitle_edit.blockSignals(False)

        # 長さモード
        mode_index = 0 if self.current_scene.duration_mode == DurationMode.AUTO else 1
        self.duration_combo.blockSignals(True)
        self.duration_combo.setCurrentIndex(mode_index)
        self.duration_combo.blockSignals(False)

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
            self.log(f"素材を設定: {Path(file_path).name}")

    def clear_media(self):
        """素材クリア"""
        if not self.current_scene:
            return

        self.current_scene.media_path = None
        self.current_scene.media_type = MediaType.NONE
        self.load_scene_data()
        self.log("素材をクリアしました")

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

    def on_duration_mode_changed(self, index: int):
        """長さモード変更時"""
        if not self.current_scene:
            return

        if index == 0:
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

        output_dir = Path(self.project.output.output_path).parent

        try:
            if platform.system() == "Windows":
                # Windowsの場合、エクスプローラーでファイルを選択状態で開く
                subprocess.run(['explorer', '/select,', str(self.project.output.output_path)])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(['open', '-R', str(self.project.output.output_path)])
            else:  # Linux
                subprocess.run(['xdg-open', str(output_dir)])
        except Exception as e:
            self.log(f"フォルダを開けませんでした: {e}")

    def log(self, message: str):
        """ログ表示"""
        self.log_text.append(message)
