"""
Scene Generator
1シーン動画生成
"""
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from .ffmpeg_wrapper import FFmpegWrapper
from ..project import Scene, MediaType


class SceneGenerator:
    """1シーン動画生成クラス"""

    def __init__(self, ffmpeg: FFmpegWrapper, font_path: Optional[str] = None):
        """
        Args:
            ffmpeg: FFmpegWrapperインスタンス
            font_path: 字幕用フォントパス（Noneならシステムフォント）
        """
        self.ffmpeg = ffmpeg
        self.font_path = font_path or self._find_default_font()

    @staticmethod
    def _find_default_font() -> str:
        """
        デフォルト日本語フォントを検索

        Returns:
            フォントパス
        """
        # Windowsの一般的な日本語フォント
        common_fonts = [
            r"C:\Windows\Fonts\msgothic.ttc",  # MSゴシック
            r"C:\Windows\Fonts\meiryo.ttc",    # メイリオ
            r"C:\Windows\Fonts\YuGothM.ttc",   # 游ゴシック Medium
        ]

        for font in common_fonts:
            if Path(font).exists():
                return font

        # 見つからない場合は最初のフォントを返す（エラーは実行時に）
        return common_fonts[0]

    def generate_scene(
        self,
        scene: Scene,
        output_path: str,
        duration: float,
        resolution: str = "1080x1920",
        fps: int = 30,
        audio_path: Optional[str] = None
    ) -> bool:
        """
        1シーンの動画を生成

        Args:
            scene: シーンデータ
            output_path: 出力先mp4ファイルパス
            duration: シーンの長さ（秒）
            resolution: 解像度 "WxH"
            fps: フレームレート
            audio_path: 音声ファイルパス（Noneなら無音）

        Returns:
            成功したらTrue
        """
        try:
            # 解像度をパース
            width, height = map(int, resolution.split('x'))

            # 一時ファイル
            temp_video = None

            # ステップ1: メディアから基本動画を生成
            if scene.has_media and scene.media_type == MediaType.IMAGE:
                temp_video = self._generate_from_image(
                    scene.media_path,
                    duration,
                    width,
                    height,
                    fps
                )
            elif scene.has_media and scene.media_type == MediaType.VIDEO:
                temp_video = self._generate_from_video(
                    scene.media_path,
                    duration,
                    width,
                    height,
                    fps
                )
            else:
                # メディアなし：黒画面
                temp_video = self._generate_blank_video(
                    duration,
                    width,
                    height,
                    fps
                )

            if not temp_video:
                return False

            # ステップ2: 字幕を焼き込み
            temp_with_subtitle = None
            if scene.has_subtitle:
                temp_with_subtitle = self._add_subtitle(
                    temp_video,
                    scene.subtitle_text,
                    width,
                    height
                )
                if temp_with_subtitle:
                    Path(temp_video).unlink()  # 一時ファイル削除
                    temp_video = temp_with_subtitle

            # ステップ3: 音声を合成
            if audio_path:
                success = self._add_audio(temp_video, audio_path, output_path)
            else:
                # 音声なし：そのままコピー
                import shutil
                shutil.copy(temp_video, output_path)
                success = True

            # 一時ファイル削除
            if Path(temp_video).exists():
                Path(temp_video).unlink()

            return success

        except Exception as e:
            print(f"シーン生成エラー: {e}")
            return False

    def _generate_from_image(
        self,
        image_path: str,
        duration: float,
        width: int,
        height: int,
        fps: int
    ) -> Optional[str]:
        """
        画像から動画を生成

        Args:
            image_path: 画像ファイルパス
            duration: 長さ（秒）
            width, height: 解像度
            fps: フレームレート

        Returns:
            生成された一時動画ファイルパス、失敗時はNone
        """
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        args = [
            "-loop", "1",
            "-i", image_path,
            "-t", str(duration),
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-y",
            temp_path
        ]

        if self.ffmpeg.run_command(args):
            return temp_path
        else:
            if Path(temp_path).exists():
                Path(temp_path).unlink()
            return None

    def _generate_from_video(
        self,
        video_path: str,
        duration: float,
        width: int,
        height: int,
        fps: int
    ) -> Optional[str]:
        """
        動画を指定長さにトリミング・リサイズ

        Args:
            video_path: 動画ファイルパス
            duration: 長さ（秒）
            width, height: 解像度
            fps: フレームレート

        Returns:
            生成された一時動画ファイルパス、失敗時はNone
        """
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        args = [
            "-i", video_path,
            "-t", str(duration),
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-an",  # 音声なし（後で合成）
            "-y",
            temp_path
        ]

        if self.ffmpeg.run_command(args):
            return temp_path
        else:
            if Path(temp_path).exists():
                Path(temp_path).unlink()
            return None

    def _generate_blank_video(
        self,
        duration: float,
        width: int,
        height: int,
        fps: int
    ) -> Optional[str]:
        """
        黒画面動画を生成

        Args:
            duration: 長さ（秒）
            width, height: 解像度
            fps: フレームレート

        Returns:
            生成された一時動画ファイルパス、失敗時はNone
        """
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        args = [
            "-f", "lavfi",
            "-i", f"color=c=black:s={width}x{height}:d={duration}:r={fps}",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-y",
            temp_path
        ]

        if self.ffmpeg.run_command(args):
            return temp_path
        else:
            if Path(temp_path).exists():
                Path(temp_path).unlink()
            return None

    def _add_subtitle(
        self,
        video_path: str,
        subtitle_text: str,
        width: int,
        height: int
    ) -> Optional[str]:
        """
        字幕を焼き込み

        Args:
            video_path: 元動画ファイルパス
            subtitle_text: 字幕テキスト
            width, height: 解像度

        Returns:
            字幕付き一時動画ファイルパス、失敗時はNone
        """
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        # 字幕エリアの高さ（画面の10%）
        subtitle_height = int(height * 0.10)
        subtitle_y = height - subtitle_height

        # フォントサイズ（高さに応じて調整）
        font_size = int(height * 0.035)

        # エスケープ処理
        escaped_text = subtitle_text.replace(':', r'\:').replace("'", r"\'")

        # drawboxで黒背景、drawtextで白文字
        filter_complex = (
            f"drawbox=x=0:y={subtitle_y}:w={width}:h={subtitle_height}:color=black@0.7:t=fill,"
            f"drawtext=fontfile='{self.font_path}':text='{escaped_text}':"
            f"fontcolor=white:fontsize={font_size}:x=(w-text_w)/2:y={subtitle_y}+(h-{subtitle_y}-text_h)/2"
        )

        args = [
            "-i", video_path,
            "-vf", filter_complex,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            "-y",
            temp_path
        ]

        if self.ffmpeg.run_command(args):
            return temp_path
        else:
            if Path(temp_path).exists():
                Path(temp_path).unlink()
            return None

    def _add_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str
    ) -> bool:
        """
        動画に音声を合成

        Args:
            video_path: 動画ファイルパス
            audio_path: 音声ファイルパス
            output_path: 出力先mp4ファイルパス

        Returns:
            成功したらTrue
        """
        from pathlib import Path

        # ファイル存在確認
        if not Path(video_path).exists():
            print(f"エラー: 動画ファイルが見つかりません: {video_path}")
            return False

        if not Path(audio_path).exists():
            print(f"エラー: 音声ファイルが見つかりません: {audio_path}")
            return False

        print(f"音声合成: {Path(video_path).name} + {Path(audio_path).name} -> {Path(output_path).name}")

        args = [
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-strict", "experimental",
            "-shortest",
            "-y",
            output_path
        ]

        success = self.ffmpeg.run_command(args, show_output=True)

        if success:
            print(f"✓ 音声合成完了: {Path(output_path).name}")
        else:
            print(f"✗ 音声合成失敗")

        return success
