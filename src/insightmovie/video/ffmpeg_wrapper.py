"""
FFmpeg Wrapper
ffmpeg ラッパー
"""
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List


class FFmpegNotFoundError(Exception):
    """ffmpegが見つからないエラー"""
    pass


class FFmpegWrapper:
    """ffmpegラッパークラス"""

    def __init__(self, ffmpeg_path: Optional[str] = None):
        """
        Args:
            ffmpeg_path: ffmpegの実行パス（Noneなら自動検出）
        """
        self.ffmpeg_path = ffmpeg_path or self.find_ffmpeg()
        if not self.ffmpeg_path:
            raise FFmpegNotFoundError(
                "ffmpegが見つかりません。インストールまたはパスを指定してください。"
            )

    @staticmethod
    def find_ffmpeg() -> Optional[str]:
        """
        ffmpegを自動検出

        Returns:
            ffmpegのパス、見つからない場合はNone
        """
        # システムPATHから検索
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            return ffmpeg_path

        # アプリケーションディレクトリからの相対パス
        # PyInstallerでパッケージ化された場合も対応
        import sys
        if getattr(sys, 'frozen', False):
            # PyInstallerでパッケージ化されている場合
            app_dir = Path(sys.executable).parent
        else:
            # 開発環境
            app_dir = Path(__file__).parent.parent.parent.parent

        relative_paths = [
            app_dir / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe",
            app_dir / "ffmpeg" / "bin" / "ffmpeg.exe",
            app_dir / "bin" / "ffmpeg.exe",
        ]

        for path in relative_paths:
            if path.exists():
                return str(path)

        # Windowsの一般的な場所を検索
        common_paths = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            Path.home() / "ffmpeg" / "bin" / "ffmpeg.exe",
        ]

        for path in common_paths:
            if Path(path).exists():
                return str(path)

        return None

    def check_available(self) -> bool:
        """
        ffmpegが利用可能かチェック

        Returns:
            利用可能ならTrue
        """
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_version(self) -> Optional[str]:
        """
        ffmpegのバージョンを取得

        Returns:
            バージョン文字列、取得失敗時はNone
        """
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # 最初の行からバージョンを抽出
                first_line = result.stdout.split('\n')[0]
                return first_line
            return None
        except Exception:
            return None

    def run_command(self, args: List[str], show_output: bool = False) -> bool:
        """
        ffmpegコマンドを実行

        Args:
            args: ffmpegの引数リスト
            show_output: 出力を表示するか

        Returns:
            成功したらTrue
        """
        cmd = [self.ffmpeg_path] + args

        try:
            if show_output:
                print(f"\nffmpegコマンド実行:")
                print(f"  {' '.join([str(arg) for arg in cmd[:5]])} ... ({len(cmd)}個の引数)")
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                if result.stdout:
                    print(f"stdout: {result.stdout[:200]}")
                if result.stderr:
                    # ffmpegは情報をstderrに出力するので、エラーでなければ表示しない
                    if result.returncode != 0:
                        print(f"stderr: {result.stderr[:500]}")
            else:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True
                )
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            print(f"\n✗ ffmpegエラー (終了コード: {e.returncode})")
            print(f"コマンド: {' '.join([str(arg) for arg in cmd[:10]])}")
            if hasattr(e, 'stderr') and e.stderr:
                print(f"エラー詳細:")
                print(e.stderr[-1000:])  # 最後の1000文字を表示
            if hasattr(e, 'stdout') and e.stdout:
                print(f"出力:")
                print(e.stdout[-500:])
            return False
        except Exception as e:
            print(f"\n✗ 実行エラー: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_video_info(self, video_path: str) -> Optional[dict]:
        """
        動画ファイルの情報を取得

        Args:
            video_path: 動画ファイルパス

        Returns:
            動画情報の辞書、取得失敗時はNone
        """
        try:
            cmd = [
                self.ffmpeg_path,
                "-i", video_path,
                "-hide_banner"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            # ffmpegは動画情報をstderrに出力する
            output = result.stderr

            # 長さを抽出（簡易版）
            import re
            duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})', output)
            if duration_match:
                hours, minutes, seconds = duration_match.groups()
                duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                return {'duration': duration}

            return None
        except Exception as e:
            print(f"動画情報取得エラー: {e}")
            return None
