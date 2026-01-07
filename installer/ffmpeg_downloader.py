"""
FFmpeg Auto Downloader
ffmpeg自動ダウンロードスクリプト

Inno Setupインストーラーから呼ばれる
"""
import os
import sys
import zipfile
import requests
from pathlib import Path
from typing import Optional


class FFmpegDownloader:
    """ffmpegダウンローダー"""

    # 公式ビルド（gyan.dev）
    FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

    def __init__(self, install_dir: Optional[str] = None):
        """
        Args:
            install_dir: インストール先ディレクトリ
        """
        if install_dir:
            self.install_dir = Path(install_dir)
        else:
            # デフォルトはプログラムファイル内
            program_files = os.environ.get("PROGRAMFILES", "C:\\Program Files")
            self.install_dir = Path(program_files) / "InsightMovie" / "tools" / "ffmpeg"

        self.install_dir.mkdir(parents=True, exist_ok=True)

    def download_ffmpeg(self) -> bool:
        """
        ffmpegをダウンロードして展開

        Returns:
            成功したらTrue
        """
        try:
            print(f"ffmpegをダウンロード中: {self.FFMPEG_URL}")

            # ダウンロード
            response = requests.get(self.FFMPEG_URL, stream=True, timeout=300)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            # 一時ファイルに保存
            temp_zip = self.install_dir.parent / "ffmpeg_temp.zip"

            with open(temp_zip, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"  ダウンロード中: {progress:.1f}%", end='\r')

            print("\nffmpegを展開中...")

            # ZIPを展開
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                # ffmpeg-x.x.x-essentials_build/bin/ の中身を取得
                for member in zip_ref.namelist():
                    if '/bin/' in member and member.endswith(('.exe', '.dll')):
                        # bin/以下のファイルのみ展開
                        filename = Path(member).name
                        target_dir = self.install_dir / "bin"
                        target_dir.mkdir(parents=True, exist_ok=True)

                        source = zip_ref.open(member)
                        target = target_dir / filename

                        with open(target, 'wb') as f:
                            f.write(source.read())

            # 一時ファイル削除
            temp_zip.unlink()

            # ffmpeg.exeの存在確認
            ffmpeg_exe = self.install_dir / "bin" / "ffmpeg.exe"
            if ffmpeg_exe.exists():
                print(f"✓ ffmpegのインストール完了: {ffmpeg_exe}")
                return True
            else:
                print("✗ ffmpeg.exeが見つかりません")
                return False

        except requests.RequestException as e:
            print(f"ダウンロードエラー: {e}")
            return False
        except zipfile.BadZipFile as e:
            print(f"ZIPファイルエラー: {e}")
            return False
        except Exception as e:
            print(f"予期しないエラー: {e}")
            return False


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description='ffmpeg自動ダウンロード')
    parser.add_argument(
        '--install-dir',
        type=str,
        help='インストール先ディレクトリ'
    )

    args = parser.parse_args()

    downloader = FFmpegDownloader(args.install_dir)
    success = downloader.download_ffmpeg()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
