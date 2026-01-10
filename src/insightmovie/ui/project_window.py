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
    QGridLayout, QFrame, QScrollArea, QDialog, QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon, QAction
from pathlib import Path
from typing import Optional

from ..project import Project, Scene, MediaType, DurationMode
from ..voicevox import VoiceVoxClient, AudioCache
from ..video import FFmpegWrapper, SceneGenerator, VideoComposer
from .theme import get_stylesheet, COLOR_PALETTE, SPACING, RADIUS


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
                    # シーンごとの話者ID（指定がなければプロジェクトデフォルトを使用）
                    scene_speaker_id = scene.speaker_id if scene.speaker_id is not None else self.speaker_id

                    # キャッシュチェック
                    if self.audio_cache.exists(scene.narration_text, scene_speaker_id):
                        self.progress.emit(f"  音声をキャッシュから取得中...")
                        audio_data = self.audio_cache.load(scene.narration_text, scene_speaker_id)
                        audio_path = self.audio_cache.get_cache_path(
                            scene.narration_text,
                            scene_speaker_id
                        )
                        duration = self.audio_cache.get_duration(
                            scene.narration_text,
                            scene_speaker_id
                        )
                        self.progress.emit(f"  ✓ 音声取得: {Path(audio_path).name} ({duration:.2f}秒)")
                    else:
                        # 新規生成
                        self.progress.emit(f"  音声を生成中（VOICEVOX）...")
                        audio_data = self.voicevox.generate_audio(
                            scene.narration_text,
                            scene_speaker_id
                        )
                        if not audio_data:
                            self.progress.emit(f"  ✗ 音声生成失敗")
                            self.finished.emit(False, "音声生成に失敗しました")
                            return

                        audio_path = self.audio_cache.save(
                            scene.narration_text,
                            scene_speaker_id,
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
        self.setMinimumSize(1100, 750)
        self.resize(1300, 950)  # 初期サイズ（リサイズ可能）

        # Insightシリーズ統一テーマを適用
        self.setStyleSheet(get_stylesheet())

        self.setup_menu_bar()
        self.setup_ui()
        self.load_scene_list()

    def setup_menu_bar(self):
        """メニューバーの設定"""
        menu_bar = self.menuBar()

        # ファイルメニュー
        file_menu = menu_bar.addMenu("ファイル(&F)")

        new_action = QAction("新規プロジェクト(&N)", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)

        open_action = QAction("設定ファイルを開く(&O)...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("設定を上書き保存(&S)", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        save_as_action = QAction("設定を別名で保存(&A)...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction("終了(&X)", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 編集メニュー
        edit_menu = menu_bar.addMenu("編集(&E)")

        add_scene_action = QAction("シーンを追加(&A)", self)
        add_scene_action.setShortcut("Ctrl+T")
        add_scene_action.triggered.connect(self.add_scene)
        edit_menu.addAction(add_scene_action)

        remove_scene_action = QAction("シーンを削除(&D)", self)
        remove_scene_action.setShortcut("Delete")
        remove_scene_action.triggered.connect(self.remove_scene)
        edit_menu.addAction(remove_scene_action)

        edit_menu.addSeparator()

        move_up_action = QAction("シーンを上へ移動(&U)", self)
        move_up_action.setShortcut("Ctrl+Up")
        move_up_action.triggered.connect(lambda: self.move_scene(-1))
        edit_menu.addAction(move_up_action)

        move_down_action = QAction("シーンを下へ移動(&D)", self)
        move_down_action.setShortcut("Ctrl+Down")
        move_down_action.triggered.connect(lambda: self.move_scene(1))
        edit_menu.addAction(move_down_action)

        # ヘルプメニュー
        help_menu = menu_bar.addMenu("ヘルプ(&H)")

        tutorial_action = QAction("チュートリアル(&T)", self)
        tutorial_action.setShortcut("F1")
        tutorial_action.triggered.connect(self.show_tutorial)
        help_menu.addAction(tutorial_action)

        faq_action = QAction("よくある質問 (FAQ)(&F)", self)
        faq_action.triggered.connect(self.show_faq)
        help_menu.addAction(faq_action)

        help_menu.addSeparator()

        license_action = QAction("ライセンス情報(&L)", self)
        license_action.triggered.connect(self.show_license)
        help_menu.addAction(license_action)

        about_action = QAction("InsightMovieについて(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

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

        open_btn = QPushButton("設定ファイルを開く")
        open_btn.setProperty("class", "secondary")
        open_btn.clicked.connect(self.open_project)
        header_layout.addWidget(open_btn)

        save_btn = QPushButton("設定を上書き保存")
        save_btn.setProperty("class", "secondary")
        save_btn.clicked.connect(self.save_project)
        header_layout.addWidget(save_btn)

        save_as_btn = QPushButton("設定を別名で保存")
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

        # メインスプリッター（縦方向に伸縮）
        splitter = QSplitter(Qt.Horizontal)

        # 左側：シーン一覧
        left_panel = self.create_scene_list_panel()
        splitter.addWidget(left_panel)

        # 右側：シーン編集
        right_panel = self.create_scene_edit_panel()
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)  # シーン編集を大きく
        splitter.setSizes([200, 500])  # 初期サイズを設定

        # スプリッターのみ伸縮するように設定
        layout.addWidget(splitter, 1)  # stretch factor = 1

        # 下部：書き出しエリア（固定サイズ）
        export_panel = self.create_export_panel()
        layout.addWidget(export_panel, 0)  # stretch factor = 0

        # 進捗バー（固定サイズ）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar, 0)  # stretch factor = 0

        # ログ（固定サイズ）
        log_label = QLabel("ログ:")
        layout.addWidget(log_label, 0)  # stretch factor = 0

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(60)  # 100px → 60pxに縮小
        self.log_text.setMinimumHeight(60)  # 最小高さも固定
        layout.addWidget(self.log_text, 0)  # stretch factor = 0

        central_widget.setLayout(layout)

        # シーン用の話者コンボボックスを初期化（load_speakersでspeaker_stylesが設定された後）
        self.load_scene_speakers()

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
        """シーン編集パネル作成（スクロール可能）"""
        panel = QGroupBox("シーン編集")
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(SPACING['md'], SPACING['md'], SPACING['md'], SPACING['md'])

        # スクロールエリアを作成
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # スクロール可能なコンテンツウィジェット
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(SPACING['md'])

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

        # 元動画の音声を残すチェックボックス（動画選択時のみ有効）
        self.keep_audio_checkbox = QCheckBox("元動画の音声を残す")
        self.keep_audio_checkbox.setEnabled(False)
        self.keep_audio_checkbox.toggled.connect(self.on_keep_audio_changed)
        media_layout.addWidget(self.keep_audio_checkbox)

        media_layout.addStretch()
        layout.addLayout(media_layout)

        # プレビューと説明文を横並びにするレイアウト
        preview_narration_layout = QHBoxLayout()

        # プレビューコンテナ（画像と字幕オーバーレイを重ねる）
        self.preview_container = QFrame()
        self.preview_container.setFixedSize(120, 180)  # コンパクトに
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
        self.thumbnail_label.setScaledContents(False)
        self.thumbnail_label.setStyleSheet(f"""
            background-color: transparent;
            color: {COLOR_PALETTE['text_muted']};
            border: none;
        """)
        preview_layout.addWidget(self.thumbnail_label, 0, 0)

        # プレースホルダーラベル（素材未設定時に表示）
        self.placeholder_label = QLabel("素材未設定")
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
        self.subtitle_overlay.setMaximumHeight(30)
        self.subtitle_overlay.hide()
        preview_layout.addWidget(self.subtitle_overlay, 0, 0, Qt.AlignBottom)

        preview_narration_layout.addWidget(self.preview_container)

        # 説明文（ナレーション）- 画像の右側に配置
        narration_widget = QWidget()
        narration_vlayout = QVBoxLayout(narration_widget)
        narration_vlayout.setContentsMargins(0, 0, 0, 0)
        narration_vlayout.setSpacing(4)

        narration_vlayout.addWidget(QLabel("会話:"))

        self.narration_edit = QTextEdit()
        self.narration_edit.setPlaceholderText(
            "ここに話をさせる内容を入力してください。"
        )
        self.narration_edit.setMinimumHeight(140)
        self.narration_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLOR_PALETTE['bg_secondary']};
                border: 2px solid {COLOR_PALETTE['text_secondary']};
                border-radius: {RADIUS['default']}px;
                padding: {SPACING['sm']}px;
                color: {COLOR_PALETTE['text_primary']};
            }}
            QTextEdit:focus {{
                border: 2px solid {COLOR_PALETTE['brand_primary']};
                background-color: {COLOR_PALETTE['bg_input']};
            }}
        """)
        self.narration_edit.textChanged.connect(self.on_narration_changed)
        narration_vlayout.addWidget(self.narration_edit)

        preview_narration_layout.addWidget(narration_widget, 1)  # 説明文が残りスペースを使用

        layout.addLayout(preview_narration_layout)

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
        self.duration_fixed_radio.toggled.connect(self.on_duration_mode_changed)
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

        # 話者選択（シーンごと）
        speaker_layout = QHBoxLayout()
        speaker_layout.addWidget(QLabel("話者:"))

        self.scene_speaker_combo = QComboBox()
        self.scene_speaker_combo.setMinimumWidth(200)
        self.scene_speaker_combo.currentIndexChanged.connect(self.on_scene_speaker_changed)
        speaker_layout.addWidget(self.scene_speaker_combo)

        speaker_layout.addStretch()
        layout.addLayout(speaker_layout)

        # 動作説明
        info_label = QLabel(
            "【動作説明】\n"
            "・画像: 会話の長さに合わせて静止画を表示\n"
            "・動画: 会話より短い→ループ、長い→会話終了後も継続\n"
            "・元音声を残す: 動画をそのまま使用（会話は追加しない）"
        )
        info_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_PALETTE['text_muted']};
                font-size: 9pt;
                padding: 8px;
                background-color: {COLOR_PALETTE['bg_secondary']};
                border-radius: 4px;
            }}
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        layout.addStretch()

        # スクロールエリアにコンテンツを設定
        scroll_area.setWidget(scroll_content)
        panel_layout.addWidget(scroll_area)

        panel.setLayout(panel_layout)
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
        """話者選択変更時（プロジェクトデフォルト）"""
        display_name = self.speaker_combo.currentText()
        if display_name in self.speaker_styles:
            self.speaker_id = self.speaker_styles[display_name]
            self.log(f"デフォルト話者を変更: {display_name}")

    def load_scene_speakers(self):
        """シーン用の話者コンボボックスを初期化"""
        self.scene_speaker_combo.clear()

        # デフォルト選択肢を追加
        self.scene_speaker_combo.addItem("(デフォルトを使用)")

        # speaker_stylesから話者一覧を追加
        for display_name in self.speaker_styles.keys():
            self.scene_speaker_combo.addItem(display_name)

    def on_scene_speaker_changed(self, index: int):
        """シーンの話者選択変更時"""
        if not self.current_scene:
            return

        display_name = self.scene_speaker_combo.currentText()
        if display_name == "(デフォルトを使用)":
            self.current_scene.speaker_id = None
            self.log(f"シーンの話者: デフォルトを使用")
        elif display_name in self.speaker_styles:
            self.current_scene.speaker_id = self.speaker_styles[display_name]
            self.log(f"シーンの話者を変更: {display_name}")

    def on_keep_audio_changed(self, checked: bool):
        """元音声保持チェックボックス変更時"""
        if not self.current_scene:
            return

        self.current_scene.keep_original_audio = checked
        if checked:
            self.log("元動画の音声を残す設定に変更")
        else:
            self.log("元動画の音声を削除する設定に変更")

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

        # 話者選択を設定
        self.scene_speaker_combo.blockSignals(True)
        if self.current_scene.speaker_id is None:
            # デフォルトを使用
            self.scene_speaker_combo.setCurrentIndex(0)
        else:
            # シーン固有の話者を選択
            found = False
            for display_name, style_id in self.speaker_styles.items():
                if style_id == self.current_scene.speaker_id:
                    index = self.scene_speaker_combo.findText(display_name)
                    if index >= 0:
                        self.scene_speaker_combo.setCurrentIndex(index)
                        found = True
                    break
            if not found:
                # 話者が見つからない場合はデフォルトにフォールバック
                self.scene_speaker_combo.setCurrentIndex(0)
        self.scene_speaker_combo.blockSignals(False)

        # 元音声保持チェックボックス
        self.keep_audio_checkbox.blockSignals(True)
        is_video = self.current_scene.media_type == MediaType.VIDEO
        self.keep_audio_checkbox.setEnabled(is_video)
        self.keep_audio_checkbox.setChecked(self.current_scene.keep_original_audio if is_video else False)
        self.keep_audio_checkbox.blockSignals(False)

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
                    # プレビューコンテナサイズ 160x240 から border(1px*2) と余白を引いたサイズ
                    target_size = QSize(156, 236)
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
        """設定ファイルを開く"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "設定ファイルを開く",
            "",
            "InsightMovie設定ファイル (*.improj);;JSONファイル (*.json);;すべてのファイル (*)"
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

    def show_tutorial(self):
        """チュートリアルダイアログを表示"""
        dialog = QDialog(self)
        dialog.setWindowTitle("InsightMovie - チュートリアル")
        dialog.setMinimumSize(700, 600)

        layout = QVBoxLayout()

        # スクロール可能なテキストエリア
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml("""
        <h1 style='color: #3B82F6;'>InsightMovie チュートリアル</h1>

        <h2>1. 基本的な使い方</h2>
        <p><b>InsightMovie</b>は、テキストと画像から自動的にナレーション付き動画を生成するプロフェッショナルツールです。</p>

        <h3>📝 ステップ1: プロジェクトの作成</h3>
        <ul>
            <li><b>新規プロジェクト</b>: メニューバーから「ファイル」→「新規プロジェクト」を選択</li>
            <li><b>既存の設定を開く</b>: 「ファイル」→「設定ファイルを開く」から .improj ファイルを選択</li>
        </ul>

        <h3>🎬 ステップ2: シーンの編集</h3>
        <ol>
            <li><b>シーンを選択</b>: 左側の「シーン一覧」から編集したいシーンをクリック</li>
            <li><b>素材を設定</b>: 「画像/動画を選択」ボタンで素材ファイルを選択
                <ul>
                    <li>対応形式: PNG, JPG, JPEG, WEBP, MP4, MOV, AVI</li>
                    <li>プレビューエリアで確認できます</li>
                </ul>
            </li>
            <li><b>説明文を入力</b>: ナレーション用のテキストを入力
                <ul>
                    <li>VOICEVOXが自動的に音声を生成します</li>
                    <li>音声の長さに応じてシーンの長さが自動調整されます</li>
                </ul>
            </li>
            <li><b>字幕を入力</b>: 動画下部に表示される字幕テキスト（任意）
                <ul>
                    <li>18文字以内を推奨（読みやすさのため）</li>
                    <li>プレビューエリアで表示を確認できます</li>
                </ul>
            </li>
            <li><b>シーンの長さを設定</b>:
                <ul>
                    <li><b>自動（音声に合わせる）</b>: ナレーションの長さ + 2秒の無音を自動設定</li>
                    <li><b>固定秒数</b>: 0.1〜60秒の範囲で手動設定</li>
                </ul>
            </li>
        </ol>

        <h3>➕ ステップ3: シーンの管理</h3>
        <ul>
            <li><b>シーンを追加</b>: 「＋ 追加」ボタンまたは Ctrl+T</li>
            <li><b>シーンを削除</b>: 「－ 削除」ボタンまたは Delete キー</li>
            <li><b>順序を変更</b>: 「↑」「↓」ボタンまたは Ctrl+Up/Down</li>
        </ul>

        <h3>🎙️ ステップ4: 書き出し設定</h3>
        <ol>
            <li><b>話者を選択</b>: VOICEVOXの音声キャラクターを選択</li>
            <li><b>解像度を選択</b>:
                <ul>
                    <li><b>1080x1920（縦動画）</b>: YouTube Shorts、TikTok、Instagram向け</li>
                    <li><b>1920x1080（横動画）</b>: YouTube、ニコニコ動画向け</li>
                </ul>
            </li>
            <li><b>FPSを設定</b>: 15〜60fpsの範囲で設定（デフォルト: 30fps）</li>
        </ol>

        <h3>📹 ステップ5: 動画を書き出し</h3>
        <ol>
            <li>「動画を書き出し」ボタンをクリック</li>
            <li>保存先とファイル名を指定</li>
            <li>生成プロセスがログエリアに表示されます</li>
            <li>完了すると、自動的にエクスプローラーでファイルを表示します</li>
        </ol>

        <h2>2. プロジェクトの保存</h2>
        <ul>
            <li><b>設定を上書き保存（Ctrl+S）</b>: 現在の設定を上書き保存</li>
            <li><b>設定を別名で保存（Ctrl+Shift+S）</b>: 新しいファイル名で保存</li>
            <li>プロジェクトファイル（.improj）には、シーン情報、素材パス、設定が保存されます</li>
        </ul>

        <h2>3. ショートカットキー</h2>
        <table border='1' cellpadding='5' style='border-collapse: collapse;'>
            <tr><th>機能</th><th>ショートカット</th></tr>
            <tr><td>新規プロジェクト</td><td>Ctrl+N</td></tr>
            <tr><td>設定ファイルを開く</td><td>Ctrl+O</td></tr>
            <tr><td>保存</td><td>Ctrl+S</td></tr>
            <tr><td>設定を別名で保存</td><td>Ctrl+Shift+S</td></tr>
            <tr><td>シーンを追加</td><td>Ctrl+T</td></tr>
            <tr><td>シーンを削除</td><td>Delete</td></tr>
            <tr><td>シーンを上へ移動</td><td>Ctrl+Up</td></tr>
            <tr><td>シーンを下へ移動</td><td>Ctrl+Down</td></tr>
            <tr><td>チュートリアル</td><td>F1</td></tr>
        </table>

        <h2>4. ベストプラクティス</h2>
        <ul>
            <li>📊 <b>画像の推奨サイズ</b>: 1920x1080以上の解像度を推奨</li>
            <li>🎤 <b>ナレーション</b>: 1シーンあたり100文字程度が視聴者にとって聞きやすい</li>
            <li>📝 <b>字幕</b>: 18文字以内で改行すると読みやすい</li>
            <li>💾 <b>こまめな保存</b>: 作業中は定期的にCtrl+Sで保存</li>
            <li>🔊 <b>VOICEVOX接続</b>: 事前にVOICEVOXを起動しておく</li>
        </ul>

        <p style='margin-top: 20px; padding: 10px; background-color: #DBEAFE; border-left: 4px solid #3B82F6;'>
        <b>💡 ヒント:</b> プロジェクトファイルは定期的にバックアップすることをお勧めします。
        </p>
        """)
        layout.addWidget(text_edit)

        # 閉じるボタン
        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def show_faq(self):
        """FAQダイアログを表示"""
        dialog = QDialog(self)
        dialog.setWindowTitle("InsightMovie - よくある質問 (FAQ)")
        dialog.setMinimumSize(700, 600)

        layout = QVBoxLayout()

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml("""
        <h1 style='color: #3B82F6;'>よくある質問 (FAQ)</h1>

        <h2>🎬 動画生成について</h2>

        <h3>Q1. 動画生成に失敗します</h3>
        <p><b>A:</b> 以下の項目を確認してください：</p>
        <ul>
            <li><b>VOICEVOXの起動</b>: VOICEVOXが起動しており、ステータスが「接続OK」になっているか確認</li>
            <li><b>ffmpegの検出</b>: ステータスバーで「ffmpeg: 検出OK」が表示されているか確認</li>
            <li><b>素材ファイル</b>: 画像/動画ファイルが存在し、アクセス可能か確認</li>
            <li><b>ディスク容量</b>: 十分な空き容量があるか確認</li>
        </ul>

        <h3>Q2. 音声が生成されません</h3>
        <p><b>A:</b> VOICEVOXとの接続を確認してください：</p>
        <ol>
            <li>VOICEVOXアプリケーションを起動</li>
            <li>InsightMovieを再起動</li>
            <li>ステータスバーで「VOICEVOX: 接続OK」と表示されることを確認</li>
            <li>それでも接続できない場合は、VOICEVOXのポート設定（デフォルト: 50021）を確認</li>
        </ol>

        <h3>Q3. 動画の書き出しに時間がかかります</h3>
        <p><b>A:</b> これは正常な動作です。処理時間は以下の要因で変わります：</p>
        <ul>
            <li>シーン数（シーンが多いほど時間がかかります）</li>
            <li>解像度（高解像度ほど処理時間が長くなります）</li>
            <li>FPS設定（高いFPSほど処理時間が長くなります）</li>
            <li>PCのスペック（CPU/GPU性能により変動）</li>
        </ul>
        <p><b>目安:</b> 4シーン、1080x1920解像度、30fpsで約2〜5分程度です。</p>

        <h2>🎙️ 音声・字幕について</h2>

        <h3>Q4. 字幕が長すぎて画面に収まりません</h3>
        <p><b>A:</b> 字幕は18文字以内を推奨します。</p>
        <ul>
            <li>18文字を超えると自動的に2行に分割されます</li>
            <li>36文字を超えると赤い背景で警告が表示されます</li>
            <li>字幕プレビューで確認しながら調整してください</li>
        </ul>

        <h3>Q5. ナレーションの声を変更したいです</h3>
        <p><b>A:</b> 書き出し設定の「話者」ドロップダウンから選択できます。</p>
        <ul>
            <li>VOICEVOXにインストールされている全ての話者が選択可能</li>
            <li>話者名の後ろに「(ノーマル)」「(喜び)」などの感情タグが表示されます</li>
            <li>動画書き出し時に選択した話者で音声が生成されます</li>
        </ul>

        <h3>Q6. シーンごとに話者を変えられますか？</h3>
        <p><b>A:</b> 現在のバージョンでは、プロジェクト全体で1人の話者のみ選択可能です。</p>
        <p>将来のアップデートでシーンごとの話者選択機能を追加予定です。</p>

        <h2>💾 プロジェクト管理について</h2>

        <h3>Q7. プロジェクトファイル（.improj）には何が保存されますか？</h3>
        <p><b>A:</b> 以下の情報が保存されます：</p>
        <ul>
            <li>全シーンの説明文（ナレーション）と字幕</li>
            <li>素材ファイルのパス（絶対パス）</li>
            <li>シーンの長さ設定</li>
            <li>プロジェクト設定（フォントパスなど）</li>
        </ul>
        <p><b>注意:</b> 素材ファイル本体は含まれません。プロジェクトを他のPCで開く場合は、素材ファイルも一緒にコピーしてください。</p>

        <h3>Q8. 画像ファイルを移動したら読み込めなくなりました</h3>
        <p><b>A:</b> 素材ファイルのパスが変更された可能性があります：</p>
        <ol>
            <li>該当するシーンを選択</li>
            <li>「クリア」ボタンで古いパスをクリア</li>
            <li>「画像/動画を選択」で新しい場所から再度選択</li>
            <li>プロジェクトを保存（Ctrl+S）</li>
        </ol>

        <h2>⚙️ 技術的な問題</h2>

        <h3>Q9. ffmpegが検出されません</h3>
        <p><b>A:</b> ffmpegのインストールと設定を確認してください：</p>
        <ul>
            <li><b>Windows:</b> インストーラーが自動的にダウンロード・設定します</li>
            <li><b>手動インストール:</b> ffmpeg.orgから入手し、PATHに追加</li>
            <li>コマンドプロンプトで「ffmpeg -version」を実行して動作確認</li>
        </ul>

        <h3>Q10. エラーメッセージが表示されます</h3>
        <p><b>A:</b> ログエリアの内容を確認してください：</p>
        <ul>
            <li>ログには詳細なエラー情報が記録されています</li>
            <li>エラーメッセージをもとに、上記のFAQを参照</li>
            <li>解決しない場合は、サポートまでお問い合わせください</li>
        </ul>

        <h2>📊 パフォーマンス</h2>

        <h3>Q11. 推奨スペックを教えてください</h3>
        <p><b>A:</b> 以下のスペックを推奨します：</p>
        <table border='1' cellpadding='5' style='border-collapse: collapse;'>
            <tr><th>項目</th><th>最小スペック</th><th>推奨スペック</th></tr>
            <tr><td>OS</td><td>Windows 10</td><td>Windows 11</td></tr>
            <tr><td>CPU</td><td>Intel Core i5以上</td><td>Intel Core i7以上</td></tr>
            <tr><td>メモリ</td><td>8GB</td><td>16GB以上</td></tr>
            <tr><td>ストレージ</td><td>10GB以上の空き容量</td><td>SSD推奨</td></tr>
        </table>

        <h2>📞 サポート</h2>

        <h3>Q12. その他の質問やサポートが必要です</h3>
        <p><b>A:</b> 以下の情報をご準備の上、サポートまでお問い合わせください：</p>
        <ul>
            <li>InsightMovieのバージョン（v1.0.0）</li>
            <li>エラーメッセージの内容</li>
            <li>再現手順</li>
            <li>ログエリアの内容（可能であれば）</li>
        </ul>

        <p style='margin-top: 20px; padding: 10px; background-color: #DBEAFE; border-left: 4px solid #3B82F6;'>
        <b>💡 ヒント:</b> まずはチュートリアル（F1キー）で基本的な使い方をご確認ください。
        </p>
        """)
        layout.addWidget(text_edit)

        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def show_license(self):
        """ライセンス情報ダイアログを表示"""
        dialog = QDialog(self)
        dialog.setWindowTitle("InsightMovie - ライセンス情報")
        dialog.setMinimumSize(700, 600)

        layout = QVBoxLayout()

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml("""
        <h1 style='color: #3B82F6;'>ライセンス情報</h1>

        <h2>InsightMovie ソフトウェアライセンス</h2>

        <h3>1. 使用許諾</h3>
        <p>本ソフトウェア（InsightMovie）は、正規のライセンスを購入したお客様に対して、以下の権利を付与します：</p>
        <ul>
            <li>個人または法人での商用・非商用利用</li>
            <li>本ソフトウェアで生成した動画コンテンツの自由な配布・販売</li>
            <li>1ライセンスにつき1台のPCでの使用</li>
        </ul>

        <h3>2. 使用制限</h3>
        <p>以下の行為は禁止されています：</p>
        <ul>
            <li>本ソフトウェアの複製、再配布、転売</li>
            <li>リバースエンジニアリング、逆コンパイル、逆アセンブル</li>
            <li>ライセンスキーの共有または譲渡</li>
            <li>違法なコンテンツの生成</li>
        </ul>

        <h3>3. 生成コンテンツの著作権</h3>
        <p>InsightMovieで生成した動画の著作権は、以下のように取り扱われます：</p>
        <ul>
            <li><b>お客様が作成したテキスト・選択した素材</b>: お客様に帰属します</li>
            <li><b>音声（VOICEVOXによる生成）</b>: VOICEVOXの利用規約に従います
                <ul>
                    <li>商用利用可能（話者によっては制限あり）</li>
                    <li>詳細はVOICEVOXの公式サイトをご確認ください</li>
                </ul>
            </li>
            <li><b>最終的な動画</b>: お客様が自由に使用・配布・販売できます</li>
        </ul>

        <h3>4. 第三者ソフトウェア</h3>
        <p>InsightMovieは以下のオープンソースソフトウェアを使用しています：</p>

        <h4>PySide6 (Qt for Python)</h4>
        <ul>
            <li><b>ライセンス:</b> LGPL v3</li>
            <li><b>著作権:</b> The Qt Company</li>
            <li><b>用途:</b> ユーザーインターフェース</li>
        </ul>

        <h4>FFmpeg</h4>
        <ul>
            <li><b>ライセンス:</b> LGPL v2.1+</li>
            <li><b>著作権:</b> FFmpeg developers</li>
            <li><b>用途:</b> 動画エンコード・処理</li>
        </ul>

        <h4>VOICEVOX</h4>
        <ul>
            <li><b>開発:</b> Hiroshiba Kazuyuki</li>
            <li><b>ライセンス:</b> 各音声ライブラリに準拠</li>
            <li><b>用途:</b> 音声合成</li>
            <li><b>注意:</b> VOICEVOXは別途インストールが必要です</li>
        </ul>

        <h3>5. 免責事項</h3>
        <p>本ソフトウェアは「現状のまま」提供され、明示または黙示を問わず、いかなる保証も行いません：</p>
        <ul>
            <li>本ソフトウェアの使用によって生じた損害について、開発者は一切の責任を負いません</li>
            <li>生成されたコンテンツの品質、正確性、適合性について保証しません</li>
            <li>第三者の権利侵害について、お客様が責任を負うものとします</li>
        </ul>

        <h3>6. アップデート・サポート</h3>
        <ul>
            <li>ソフトウェアのアップデートは無償で提供される場合があります</li>
            <li>サポート期間は購入日から1年間です</li>
            <li>サポート期間終了後も、ソフトウェアは継続してご利用いただけます</li>
        </ul>

        <h3>7. プライバシー</h3>
        <p>InsightMovieは以下のプライバシーポリシーを遵守します：</p>
        <ul>
            <li>個人情報の収集は行いません</li>
            <li>プロジェクトデータはローカルPCにのみ保存されます</li>
            <li>インターネット接続が必要なのはVOICEVOXとの通信のみです</li>
            <li>使用統計やテレメトリーデータの送信は行いません</li>
        </ul>

        <h3>8. 準拠法</h3>
        <p>本ライセンス契約は日本国法に準拠し、解釈されるものとします。</p>

        <hr>

        <p style='margin-top: 20px; padding: 10px; background-color: #FEF3C7; border-left: 4px solid #F59E0B;'>
        <b>⚠️ 重要:</b> 本ソフトウェアを使用する前に、上記のライセンス条項をよくお読みください。
        本ソフトウェアのインストールまたは使用により、これらの条項に同意したものとみなされます。
        </p>

        <p style='text-align: center; margin-top: 30px; color: #6B7280;'>
        InsightMovie v1.0.0<br>
        Copyright © 2024-2025 Harmonic Insight. All Rights Reserved.
        </p>
        """)
        layout.addWidget(text_edit)

        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def show_about(self):
        """バージョン情報ダイアログを表示"""
        dialog = QDialog(self)
        dialog.setWindowTitle("InsightMovieについて")
        dialog.setMinimumSize(600, 500)

        layout = QVBoxLayout()

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml("""
        <div style='text-align: center;'>
            <h1 style='color: #3B82F6; margin-top: 30px;'>InsightMovie</h1>
            <p style='font-size: 14pt; color: #6B7280;'>プロフェッショナル動画自動生成ツール</p>
            <p style='font-size: 12pt; margin-top: 20px;'><b>バージョン 1.0.0</b></p>
        </div>

        <hr style='margin: 30px 0;'>

        <h2 style='color: #3B82F6;'>製品概要</h2>
        <p>InsightMovieは、テキストと画像から自動的にナレーション付き動画を生成する、
        プロフェッショナル向けの動画制作ツールです。</p>

        <h3>主な機能</h3>
        <ul>
            <li>🎬 <b>自動動画生成</b> - テキストと画像から高品質な動画を自動作成</li>
            <li>🎙️ <b>VOICEVOX連携</b> - 自然な日本語ナレーションを自動生成</li>
            <li>📝 <b>字幕サポート</b> - 読みやすい字幕を自動配置</li>
            <li>🎨 <b>柔軟な編集</b> - シーン単位での細かい調整が可能</li>
            <li>📊 <b>複数フォーマット</b> - 縦動画・横動画の両方に対応</li>
            <li>💾 <b>プロジェクト管理</b> - 作業を保存して後から編集可能</li>
        </ul>

        <h3>対応フォーマット</h3>
        <ul>
            <li><b>画像:</b> PNG, JPG, JPEG, WEBP</li>
            <li><b>動画:</b> MP4, MOV, AVI</li>
            <li><b>出力:</b> MP4 (H.264)</li>
            <li><b>解像度:</b> 1080x1920 (縦) / 1920x1080 (横)</li>
        </ul>

        <h3>技術スタック</h3>
        <ul>
            <li>Python 3.11+</li>
            <li>PySide6 (Qt for Python)</li>
            <li>FFmpeg</li>
            <li>VOICEVOX Engine</li>
        </ul>

        <hr style='margin: 30px 0;'>

        <h2 style='color: #3B82F6;'>開発元</h2>
        <p><b>Harmonic Insight</b><br>
        プロフェッショナル向けコンテンツ制作ツールの開発</p>

        <h3>Insightシリーズ製品</h3>
        <ul>
            <li><b>InsightSlide</b> - プレゼンテーション自動生成ツール</li>
            <li><b>InsightMovie</b> - 動画自動生成ツール (本製品)</li>
        </ul>

        <hr style='margin: 30px 0;'>

        <div style='background-color: #F8FAFC; padding: 15px; border-radius: 8px; margin-top: 20px;'>
            <p style='margin: 0; color: #64748B; font-size: 10pt;'>
            <b>システム情報</b><br>
            Python Version: 3.11+<br>
            PySide6 Version: 6.6+<br>
            Build Date: 2025-01-07
            </p>
        </div>

        <p style='text-align: center; margin-top: 30px; color: #94A3B8; font-size: 9pt;'>
        Copyright © 2024-2025 Harmonic Insight. All Rights Reserved.
        </p>
        """)
        layout.addWidget(text_edit)

        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec()
