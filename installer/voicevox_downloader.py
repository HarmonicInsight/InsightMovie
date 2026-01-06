"""
VOICEVOX Auto Downloader
VOICEVOXエンジン自動ダウンロード・セットアップスクリプト

このスクリプトは公式配布元からVOICEVOXをダウンロードし、展開します。
"""
import os
import sys
import zipfile
import requests
from pathlib import Path
from typing import Optional


class VoicevoxDownloader:
    """VOICEVOXダウンローダー"""

    # 公式配布元（GitHub Releases）
    RELEASE_API = "https://api.github.com/repos/VOICEVOX/voicevox_engine/releases/latest"
    DOWNLOAD_ASSET_PATTERN = "windows-cpu"  # CPUバージョンを取得

    def __init__(self, install_dir: Optional[str] = None):
        """
        Args:
            install_dir: インストール先ディレクトリ
        """
        if install_dir:
            self.install_dir = Path(install_dir)
        else:
            # デフォルトはユーザーのローカルAppData
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            self.install_dir = Path(local_appdata) / "ShortMakerStudio" / "voicevox"

        self.install_dir.mkdir(parents=True, exist_ok=True)

    def get_latest_release_info(self) -> dict:
        """
        最新リリース情報を取得

        Returns:
            リリース情報
        """
        print("最新のVOICEVOXエンジン情報を取得中...")
        try:
            response = requests.get(self.RELEASE_API, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise RuntimeError(f"リリース情報の取得に失敗: {e}")

    def find_download_url(self, release_info: dict) -> Optional[str]:
        """
        ダウンロードURLを検索

        Args:
            release_info: リリース情報

        Returns:
            ダウンロードURL
        """
        assets = release_info.get("assets", [])
        for asset in assets:
            name = asset.get("name", "")
            if self.DOWNLOAD_ASSET_PATTERN in name.lower() and name.endswith(".zip"):
                return asset.get("browser_download_url")

        return None

    def download(self, url: str, dest_path: Path, progress_callback=None) -> bool:
        """
        ファイルをダウンロード

        Args:
            url: ダウンロードURL
            dest_path: 保存先パス
            progress_callback: 進捗コールバック(current, total)

        Returns:
            成功ならTrue
        """
        try:
            print(f"ダウンロード中: {url}")
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)

            print(f"ダウンロード完了: {dest_path}")
            return True

        except Exception as e:
            print(f"ダウンロードエラー: {e}")
            return False

    def extract_zip(self, zip_path: Path, extract_to: Path) -> bool:
        """
        ZIPファイルを展開

        Args:
            zip_path: ZIPファイルパス
            extract_to: 展開先ディレクトリ

        Returns:
            成功ならTrue
        """
        try:
            print(f"展開中: {zip_path}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            print(f"展開完了: {extract_to}")
            return True

        except Exception as e:
            print(f"展開エラー: {e}")
            return False

    def install(self, progress_callback=None) -> bool:
        """
        VOICEVOXをインストール

        Args:
            progress_callback: 進捗コールバック

        Returns:
            成功ならTrue
        """
        try:
            # リリース情報取得
            release_info = self.get_latest_release_info()
            version = release_info.get("tag_name", "unknown")
            print(f"最新バージョン: {version}")

            # ダウンロードURL取得
            download_url = self.find_download_url(release_info)
            if not download_url:
                print("ダウンロードURLが見つかりませんでした")
                return False

            print(f"ダウンロードURL: {download_url}")

            # ダウンロード
            zip_path = self.install_dir / "voicevox_engine.zip"
            if not self.download(download_url, zip_path, progress_callback):
                return False

            # 展開
            if not self.extract_zip(zip_path, self.install_dir):
                return False

            # ZIPファイル削除
            zip_path.unlink()

            # run.exeの存在確認
            run_exe = self.find_run_exe()
            if run_exe:
                print(f"✓ インストール完了: {run_exe}")
                return True
            else:
                print("✗ run.exeが見つかりません")
                return False

        except Exception as e:
            print(f"インストールエラー: {e}")
            return False

    def find_run_exe(self) -> Optional[Path]:
        """
        run.exeを検索

        Returns:
            run.exeのパス
        """
        for path in self.install_dir.rglob("run.exe"):
            return path
        return None


def main():
    """メイン関数（CLI用）"""
    import argparse

    parser = argparse.ArgumentParser(description="VOICEVOX Auto Installer")
    parser.add_argument(
        "--install-dir",
        help="インストール先ディレクトリ"
    )
    args = parser.parse_args()

    # 進捗表示
    def progress(current, total):
        percent = (current / total * 100) if total > 0 else 0
        print(f"\r進捗: {percent:.1f}% ({current}/{total} bytes)", end="")

    downloader = VoicevoxDownloader(install_dir=args.install_dir)

    print("=" * 60)
    print("VOICEVOX Engine Auto Installer")
    print("=" * 60)
    print()
    print("注意:")
    print("- このスクリプトはVOICEVOXの公式配布元からダウンロードします")
    print("- VOICEVOX公式サイト: https://voicevox.hiroshiba.jp/")
    print("- GitHub: https://github.com/VOICEVOX/voicevox_engine")
    print()

    if downloader.install():
        print("\n✓ セットアップ完了")
        run_exe = downloader.find_run_exe()
        if run_exe:
            print(f"エンジンパス: {run_exe}")
        return 0
    else:
        print("\n✗ セットアップ失敗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
