"""
VOICEVOX Engine Launcher
エンジンの起動・停止を管理
"""
import os
import subprocess
import time
import psutil
from pathlib import Path
from typing import Optional


class EngineLauncher:
    """VOICEVOXエンジンランチャー"""

    def __init__(self, engine_path: Optional[str] = None):
        """
        Args:
            engine_path: VOICEVOXエンジンのrun.exeへのパス
        """
        self._engine_path = engine_path
        self._process: Optional[subprocess.Popen] = None
        self._pid: Optional[int] = None

    @property
    def engine_path(self) -> Optional[str]:
        """エンジンパス"""
        return self._engine_path

    @engine_path.setter
    def engine_path(self, path: str):
        """エンジンパスを設定"""
        self._engine_path = path

    @property
    def is_running(self) -> bool:
        """エンジンが起動中かチェック"""
        if self._pid:
            return psutil.pid_exists(self._pid)
        return False

    def find_default_engine_path(self) -> Optional[str]:
        """
        デフォルトのエンジンパスを検索

        Returns:
            見つかったパス、見つからない場合はNone
        """
        # ユーザーローカルの標準インストール場所
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            voicevox_path = Path(local_app_data) / "InsightMovie" / "voicevox"
            run_exe = voicevox_path / "run.exe"
            if run_exe.exists():
                return str(run_exe)

        # カレントディレクトリ相対
        local_voicevox = Path("voicevox") / "run.exe"
        if local_voicevox.exists():
            return str(local_voicevox.absolute())

        # Program Files
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        voicevox_program = Path(program_files) / "VOICEVOX" / "run.exe"
        if voicevox_program.exists():
            return str(voicevox_program)

        return None

    def launch(self, port: int = 50021, use_gpu: bool = True) -> bool:
        """
        エンジンを起動

        Args:
            port: 使用するポート番号
            use_gpu: GPU使用フラグ

        Returns:
            起動成功ならTrue
        """
        if not self._engine_path:
            # デフォルトパスを検索
            self._engine_path = self.find_default_engine_path()

        if not self._engine_path:
            print("エンジンのパスが設定されていません")
            return False

        if not os.path.exists(self._engine_path):
            print(f"エンジンが見つかりません: {self._engine_path}")
            return False

        # 既に起動中の場合
        if self.is_running:
            print("エンジンは既に起動しています")
            return True

        try:
            # コマンドライン引数
            cmd = [self._engine_path, f"--port={port}"]
            if not use_gpu:
                cmd.append("--use_gpu=false")

            # プロセス起動（バックグラウンド）
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            self._pid = self._process.pid

            print(f"エンジンを起動しました (PID: {self._pid}, Port: {port})")

            # 起動待機（最大10秒）
            for _ in range(20):
                time.sleep(0.5)
                if self.is_running:
                    return True

            print("エンジンの起動確認がタイムアウトしました")
            return False

        except Exception as e:
            print(f"エンジン起動エラー: {e}")
            return False

    def stop(self) -> bool:
        """
        エンジンを停止

        Returns:
            停止成功ならTrue
        """
        if not self.is_running:
            print("エンジンは起動していません")
            return True

        try:
            if self._process:
                self._process.terminate()

                # 終了待機（最大5秒）
                for _ in range(10):
                    time.sleep(0.5)
                    if not self.is_running:
                        print("エンジンを停止しました")
                        self._process = None
                        self._pid = None
                        return True

                # 強制終了
                self._process.kill()
                self._process = None
                self._pid = None
                print("エンジンを強制終了しました")
                return True

            # プロセスオブジェクトがない場合はPIDから終了
            elif self._pid:
                process = psutil.Process(self._pid)
                process.terminate()
                process.wait(timeout=5)
                self._pid = None
                print("エンジンを停止しました")
                return True

        except psutil.NoSuchProcess:
            print("エンジンプロセスが見つかりません（既に終了済み）")
            self._process = None
            self._pid = None
            return True

        except Exception as e:
            print(f"エンジン停止エラー: {e}")
            return False

        return False

    def restart(self, port: int = 50021, use_gpu: bool = True) -> bool:
        """
        エンジンを再起動

        Args:
            port: 使用するポート番号
            use_gpu: GPU使用フラグ

        Returns:
            再起動成功ならTrue
        """
        self.stop()
        time.sleep(1)
        return self.launch(port=port, use_gpu=use_gpu)
