"""
Main Application Window
メインアプリケーションウィンドウ
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFileDialog,
    QMessageBox, QStatusBar, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal
from pathlib import Path
import wave

from ..voicevox import VoiceVoxClient
from ..core.config import Config


class SynthesisThread(QThread):
    """音声合成スレッド"""
    finished = Signal(bytes)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, client: VoiceVoxClient, text: str, speaker_id: int):
        super().__init__()
        self.client = client
        self.text = text
        self.speaker_id = speaker_id

    def run(self):
        try:
            self.progress.emit("音声を生成中...")
            audio_data = self.client.generate_audio(self.text, self.speaker_id)
            self.finished.emit(audio_data)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """メインウィンドウ"""

    def __init__(self, config: Config, client: VoiceVoxClient):
        super().__init__()
        self.config = config
        self.client = client
        self.synth_thread = None

        self.setWindowTitle("InsightMovie")
        self.setMinimumSize(800, 600)

        self.setup_ui()
        self.setup_statusbar()

    def setup_ui(self):
        """UI構築"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        # タイトル
        title = QLabel("InsightMovie - 音声生成")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # エンジン状態表示
        self.engine_status = QLabel()
        self.update_engine_status()
        layout.addWidget(self.engine_status)

        # テキスト入力
        layout.addWidget(QLabel("生成するテキスト:"))
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "ここに音声にしたいテキストを入力してください...\n"
            "例: こんにちは、InsightMovieです。"
        )
        self.text_edit.setMaximumHeight(150)
        layout.addWidget(self.text_edit)

        # ボタンエリア
        button_layout = QHBoxLayout()

        self.generate_button = QPushButton("音声を生成")
        self.generate_button.clicked.connect(self.generate_audio)
        self.generate_button.setStyleSheet(
            "QPushButton { font-size: 14px; padding: 10px; background-color: #4CAF50; color: white; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        button_layout.addWidget(self.generate_button)

        self.save_button = QPushButton("WAVファイルとして保存")
        self.save_button.clicked.connect(self.save_audio)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

        # ログ表示
        layout.addWidget(QLabel("ログ:"))
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumHeight(200)
        layout.addWidget(self.log_edit)

        central_widget.setLayout(layout)

        # 生成した音声データ
        self.last_audio_data = None

    def setup_statusbar(self):
        """ステータスバー構築"""
        self.statusBar().showMessage("準備完了")

    def update_engine_status(self):
        """エンジン状態を更新"""
        if self.client.check_connection():
            info = self.client.engine_info
            if info:
                self.engine_status.setText(
                    f"✓ VOICEVOXエンジン接続中: {info.base_url} (version: {info.version})"
                )
                self.engine_status.setStyleSheet("color: green; padding: 5px;")
            else:
                self.engine_status.setText(f"✓ VOICEVOXエンジン接続中: {self.client.base_url}")
                self.engine_status.setStyleSheet("color: green; padding: 5px;")
        else:
            self.engine_status.setText("✗ VOICEVOXエンジンに接続できません")
            self.engine_status.setStyleSheet("color: red; padding: 5px;")

    def log(self, message: str):
        """ログに追加"""
        self.log_edit.append(message)

    def generate_audio(self):
        """音声を生成"""
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "入力エラー", "テキストを入力してください。")
            return

        speaker_id = self.config.default_speaker_id
        if speaker_id is None:
            QMessageBox.warning(
                self,
                "設定エラー",
                "話者が設定されていません。\nセットアップウィザードを再度実行してください。"
            )
            return

        # 音声合成開始
        self.generate_button.setEnabled(False)
        self.log(f"音声生成開始: {text[:50]}...")

        self.synth_thread = SynthesisThread(self.client, text, speaker_id)
        self.synth_thread.finished.connect(self.on_synthesis_finished)
        self.synth_thread.error.connect(self.on_synthesis_error)
        self.synth_thread.progress.connect(self.log)
        self.synth_thread.start()

    def on_synthesis_finished(self, audio_data: bytes):
        """音声合成完了"""
        self.last_audio_data = audio_data
        self.generate_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.log(f"✓ 音声生成完了 ({len(audio_data)} bytes)")
        self.statusBar().showMessage("音声生成完了", 3000)

    def on_synthesis_error(self, error: str):
        """音声合成エラー"""
        self.generate_button.setEnabled(True)
        self.log(f"✗ エラー: {error}")
        QMessageBox.critical(self, "生成エラー", f"音声生成に失敗しました:\n{error}")

    def save_audio(self):
        """音声をWAVファイルとして保存"""
        if not self.last_audio_data:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "音声ファイルを保存",
            str(Path.home() / "output.wav"),
            "WAVファイル (*.wav)"
        )

        if file_path:
            try:
                with open(file_path, 'wb') as f:
                    f.write(self.last_audio_data)
                self.log(f"✓ 保存完了: {file_path}")
                QMessageBox.information(self, "保存完了", f"ファイルを保存しました:\n{file_path}")
            except Exception as e:
                self.log(f"✗ 保存エラー: {e}")
                QMessageBox.critical(self, "保存エラー", f"ファイルの保存に失敗しました:\n{e}")
