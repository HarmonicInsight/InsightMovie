"""
Setup Wizard for First-Time Users
初回起動時セットアップウィザード
"""
from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QTextEdit,
    QCheckBox, QLineEdit, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
import time
from pathlib import Path
from typing import Optional

from ..voicevox import VoiceVoxClient, EngineLauncher


class EngineCheckThread(QThread):
    """エンジン検出スレッド"""
    found = Signal(str)  # base_url
    not_found = Signal()
    progress = Signal(str)  # メッセージ

    def __init__(self, client: VoiceVoxClient):
        super().__init__()
        self.client = client

    def run(self):
        self.progress.emit("VOICEVOXエンジンを検索中...")
        engine_info = self.client.discover_engine()

        if engine_info:
            self.found.emit(engine_info.base_url)
        else:
            self.not_found.emit()


class WelcomePage(QWizardPage):
    """ようこそページ"""

    def __init__(self):
        super().__init__()
        self.setTitle("InsightMovie へようこそ")
        self.setSubTitle("初回セットアップを開始します")

        layout = QVBoxLayout()

        # 説明テキスト
        intro = QLabel(
            "このウィザードでは、InsightMovieを使用するための\n"
            "初期設定を行います。\n\n"
            "設定内容：\n"
            "・VOICEVOXエンジンの検出と起動\n"
            "・デフォルト話者の設定\n"
            "・音声生成テスト\n\n"
            "「次へ」をクリックして開始してください。"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        layout.addStretch()
        self.setLayout(layout)


class EngineDetectionPage(QWizardPage):
    """エンジン検出ページ"""

    def __init__(self, client: VoiceVoxClient, launcher: EngineLauncher):
        super().__init__()
        self.client = client
        self.launcher = launcher
        self.check_thread: Optional[EngineCheckThread] = None

        self.setTitle("VOICEVOXエンジンの検出")
        self.setSubTitle("音声合成エンジンを検索しています")

        layout = QVBoxLayout()

        # ステータス表示
        self.status_label = QLabel("検索中...")
        self.status_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        self.status_label.setFont(font)
        layout.addWidget(self.status_label)

        # プログレスバー
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # 不定
        layout.addWidget(self.progress)

        layout.addSpacing(20)

        # ボタンエリア
        button_layout = QHBoxLayout()

        self.launch_button = QPushButton("エンジンを起動")
        self.launch_button.clicked.connect(self.launch_engine)
        self.launch_button.setEnabled(False)
        button_layout.addWidget(self.launch_button)

        self.rescan_button = QPushButton("再検索")
        self.rescan_button.clicked.connect(self.start_detection)
        button_layout.addWidget(self.rescan_button)

        self.manual_button = QPushButton("手動設定")
        self.manual_button.clicked.connect(self.manual_setup)
        button_layout.addWidget(self.manual_button)

        layout.addLayout(button_layout)

        # エンジンパス表示
        layout.addSpacing(20)
        self.path_label = QLabel("")
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)

        layout.addStretch()
        self.setLayout(layout)

    def initializePage(self):
        """ページ初期化時に自動検出開始"""
        self.start_detection()

    def start_detection(self):
        """エンジン検出を開始"""
        self.status_label.setText("VOICEVOXエンジンを検索中...")
        self.progress.setRange(0, 0)
        self.launch_button.setEnabled(False)

        # 検出スレッド開始
        self.check_thread = EngineCheckThread(self.client)
        self.check_thread.found.connect(self.on_engine_found)
        self.check_thread.not_found.connect(self.on_engine_not_found)
        self.check_thread.progress.connect(self.on_progress)
        self.check_thread.start()

    def on_progress(self, message: str):
        """進捗更新"""
        self.status_label.setText(message)

    def on_engine_found(self, base_url: str):
        """エンジン発見時"""
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.status_label.setText(f"✓ エンジンが見つかりました！\n{base_url}")
        self.status_label.setStyleSheet("color: green;")
        self.completeChanged.emit()

    def on_engine_not_found(self):
        """エンジンが見つからない場合"""
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status_label.setText("✗ エンジンが見つかりませんでした")
        self.status_label.setStyleSheet("color: red;")

        # エンジンパスを検索
        engine_path = self.launcher.find_default_engine_path()
        if engine_path:
            self.launcher.engine_path = engine_path
            self.path_label.setText(f"エンジンのパス: {engine_path}")
            self.launch_button.setEnabled(True)
        else:
            self.path_label.setText(
                "エンジンが見つかりません。\n"
                "インストーラーでVOICEVOXセットアップを実行したか確認してください。"
            )

    def launch_engine(self):
        """エンジンを起動"""
        self.status_label.setText("エンジンを起動中...")
        self.launch_button.setEnabled(False)

        if self.launcher.launch():
            # 起動後に再検索
            time.sleep(2)
            self.start_detection()
        else:
            QMessageBox.warning(
                self,
                "起動失敗",
                "エンジンの起動に失敗しました。\n手動で起動してから再検索してください。"
            )
            self.launch_button.setEnabled(True)

    def manual_setup(self):
        """手動設定"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "VOICEVOXエンジンのrun.exeを選択",
            "",
            "実行ファイル (*.exe)"
        )

        if path:
            self.launcher.engine_path = path
            self.path_label.setText(f"エンジンのパス: {path}")
            self.launch_button.setEnabled(True)

    def isComplete(self):
        """完了判定"""
        return self.client.check_connection()


class SpeakerSelectionPage(QWizardPage):
    """話者選択ページ"""

    def __init__(self, client: VoiceVoxClient):
        super().__init__()
        self.client = client
        self.speaker_id = None

        self.setTitle("デフォルト話者の設定")
        self.setSubTitle("音声合成に使用する話者を選択します")

        layout = QVBoxLayout()

        info = QLabel(
            "デフォルト話者を自動設定します。\n"
            "後でアプリケーション設定から変更できます。"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addSpacing(20)

        self.status_label = QLabel("話者情報を取得中...")
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setLayout(layout)

    def initializePage(self):
        """ページ初期化時に話者を検索"""
        try:
            # デフォルト話者を取得
            style_id = self.client.get_default_speaker()

            if style_id:
                self.speaker_id = style_id

                # 話者名を取得して表示
                speakers = self.client.get_speakers()
                speaker_name = "不明"
                style_name = "不明"

                for speaker in speakers:
                    for style in speaker.get("styles", []):
                        if style.get("id") == style_id:
                            speaker_name = speaker.get("name")
                            style_name = style.get("name")
                            break

                self.status_label.setText(
                    f"✓ デフォルト話者を設定しました\n"
                    f"話者: {speaker_name} ({style_name})\n"
                    f"Style ID: {style_id}"
                )
                self.status_label.setStyleSheet("color: green;")
            else:
                self.status_label.setText(
                    "✗ 話者の取得に失敗しました"
                )
                self.status_label.setStyleSheet("color: red;")

        except Exception as e:
            self.status_label.setText(f"✗ エラー: {e}")
            self.status_label.setStyleSheet("color: red;")

    def isComplete(self):
        """完了判定"""
        return self.speaker_id is not None


class CompletionPage(QWizardPage):
    """完了ページ"""

    def __init__(self):
        super().__init__()
        self.setTitle("セットアップ完了")
        self.setSubTitle("すべての設定が完了しました")

        layout = QVBoxLayout()

        completion_text = QLabel(
            "✓ セットアップが完了しました！\n\n"
            "「完了」をクリックしてInsightMovieを開始してください。\n\n"
            "今すぐ音声生成を試すことができます。"
        )
        completion_text.setWordWrap(True)
        font = QFont()
        font.setPointSize(11)
        completion_text.setFont(font)
        layout.addWidget(completion_text)

        layout.addStretch()
        self.setLayout(layout)


class SetupWizard(QWizard):
    """セットアップウィザード"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("InsightMovie - 初回セットアップ")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setMinimumSize(600, 400)

        # コンポーネント初期化
        self.client = VoiceVoxClient()
        self.launcher = EngineLauncher()

        # ページ追加
        self.addPage(WelcomePage())
        self.addPage(EngineDetectionPage(self.client, self.launcher))
        self.speaker_page = SpeakerSelectionPage(self.client)
        self.addPage(self.speaker_page)
        self.addPage(CompletionPage())

    def get_speaker_id(self) -> Optional[int]:
        """選択された話者IDを取得"""
        return self.speaker_page.speaker_id

    def get_client(self) -> VoiceVoxClient:
        """VOICEVOXクライアントを取得"""
        return self.client

    def get_launcher(self) -> EngineLauncher:
        """エンジンランチャーを取得"""
        return self.launcher
