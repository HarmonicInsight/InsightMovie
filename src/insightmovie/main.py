"""
InsightMovie - Main Entry Point
メインエントリーポイント
"""
import sys
from PySide6.QtWidgets import QApplication, QDialog

from .core import Config
from .voicevox import VoiceVoxClient, EngineLauncher
from .setup_wizard import SetupWizard
from .ui import ProjectWindow
from .video import FFmpegWrapper


def main():
    """メイン関数"""
    app = QApplication(sys.argv)
    app.setApplicationName("InsightMovie")
    app.setOrganizationName("InsightMovie")

    # 設定読み込み
    config = Config()

    # 初回実行チェック
    if config.is_first_run:
        # セットアップウィザード表示
        wizard = SetupWizard()
        if wizard.exec() != QDialog.DialogCode.Accepted:
            # キャンセルされた場合は終了
            return 0

        # 設定を保存
        client = wizard.get_client()
        launcher = wizard.get_launcher()

        if client.base_url:
            config.engine_url = client.base_url

        if launcher.engine_path:
            config.engine_path = launcher.engine_path

        speaker_id = wizard.get_speaker_id()
        if speaker_id is not None:
            config.default_speaker_id = speaker_id

        config.mark_setup_completed()
    else:
        # 既存設定を使用
        client = VoiceVoxClient(base_url=config.engine_url)

        # エンジン接続確認
        if not client.check_connection():
            # 再検出を試みる
            print("エンジンに接続できません。再検出を試みます...")
            engine_info = client.discover_engine()
            if engine_info:
                config.engine_url = engine_info.base_url

    # ffmpeg検出
    try:
        ffmpeg = FFmpegWrapper()
    except Exception as e:
        print(f"ffmpeg警告: {e}")
        ffmpeg = None

    # デフォルト話者ID取得
    speaker_id = config.default_speaker_id or 13  # 青山龍星

    # メインウィンドウ表示
    window = ProjectWindow(client, speaker_id, ffmpeg)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
