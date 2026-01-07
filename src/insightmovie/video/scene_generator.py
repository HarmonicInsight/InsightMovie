"""
Scene Generator
1シーン動画生成
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

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

    @staticmethod
    def _escape_filter_value(value: str) -> str:
        """
        ffmpeg フィルタ引数用に値をエスケープ。
        
        Notes:
            - ':' はフィルタ区切りなのでエスケープ必須。
            - "\\" は Windows パスで問題になるためエスケープ。
            - "'" は drawtext のシングルクォート境界を壊すためエスケープ。
        """
        return (
            value
            .replace("\\", r"\\")
            .replace(":", r"\:")
            .replace("'", r"\'")
        )

    @classmethod
    def _format_font_path(cls, font_path: str) -> str:
        """drawtext 用にフォントパスを整形。"""
        path = Path(font_path).as_posix()
        return cls._escape_filter_value(path)

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
            print("\n=== シーン動画生成開始 ===")
            print(f"  出力: {Path(output_path).name}")
            print(f"  長さ: {duration}秒")
            print(f"  解像度: {resolution}")
            print(f"  字幕: {scene.subtitle_text if scene.has_subtitle else 'なし'}")
            print(f"  音声: {'あり' if audio_path else 'なし'}")

            # 解像度をパース
            width, height = map(int, resolution.split('x'))

            # 一時ファイル
            temp_video = None

            # ステップ1: メディアから基本動画を生成
            print("\n[1/3] 基本動画生成...")
            if scene.has_media and scene.media_type == MediaType.IMAGE:
                print(f"  画像から動画を生成: {Path(scene.media_path).name}")
                temp_video = self._generate_from_image(
                    scene.media_path,
                    duration,
                    width,
                    height,
                    fps
                )
            elif scene.has_media and scene.media_type == MediaType.VIDEO:
                print(f"  動画をトリミング: {Path(scene.media_path).name}")
                temp_video = self._generate_from_video(
                    scene.media_path,
                    duration,
                    width,
                    height,
                    fps
                )
            else:
                # メディアなし：黒画面
                print("  黒画面動画を生成")
                temp_video = self._generate_blank_video(
                    duration,
                    width,
                    height,
                    fps
                )

            if not temp_video:
                print("  ✗ 基本動画生成失敗")
                return False
            print(f"  ✓ 基本動画生成完了: {Path(temp_video).name}")

            # ステップ2: 字幕を焼き込み
            print("\n[2/3] 字幕処理...")
            temp_with_subtitle = None
            if scene.has_subtitle:
                print(f"  字幕を焼き込み: '{scene.subtitle_text}'")
                temp_with_subtitle = self._add_subtitle(
                    temp_video,
                    scene.subtitle_text,
                    width,
                    height
                )
                if temp_with_subtitle:
                    Path(temp_video).unlink()
                    temp_video = temp_with_subtitle
                    print("  ✓ 字幕焼き込み完了")
                else:
                    print("  ✗ 字幕焼き込み失敗")
            else:
                print("  字幕なし（スキップ）")

            # ステップ3: 音声を合成
            print("\n[3/3] 音声処理...")
            if audio_path:
                print(f"  音声ファイル: {Path(audio_path).name}")
                success = self._add_audio(temp_video, audio_path, output_path)
                if success:
                    print("  ✓ 音声合成完了")
                else:
                    print("  ✗ 音声合成失敗")
            else:
                print("  音声なし（動画のみコピー）")
                import shutil
                shutil.copy(temp_video, output_path)
                success = True

            # 一時ファイル削除
            if Path(temp_video).exists():
                Path(temp_video).unlink()

            if success:
                print(f"\n✓ シーン動画生成完了: {Path(output_path).name}")
            else:
                print("\n✗ シーン動画生成失敗")

            return success

        except Exception as e:
            print(f"シーン生成エラー: {e}")
            import traceback
            traceback.print_exc()
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
        """
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        args = [
            "-loop", "1",
            "-i", image_path,
            "-t", str(duration),
            "-vf", (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
            ),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-y",
            temp_path
        ]

        if self.ffmpeg.run_command(args):
            return temp_path
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
        """
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        args = [
            "-i", video_path,
            "-t", str(duration),
            "-vf", (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
            ),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-an",
            "-y",
            temp_path
        ]

        if self.ffmpeg.run_command(args):
            return temp_path
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
        """
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        subtitle_height = int(height * 0.10)
        subtitle_y = height - subtitle_height
        font_size = int(height * 0.035)

        subtitle_file = tempfile.NamedTemporaryFile(
            suffix=".txt",
            delete=False,
            mode="w",
            encoding="utf-8"
        )
        subtitle_file.write(subtitle_text)
        subtitle_file.flush()
        subtitle_file.close()

        escaped_font_path = self._format_font_path(self.font_path)
        escaped_subtitle_path = self._escape_filter_value(
            Path(subtitle_file.name).as_posix()
        )

        filter_complex = (
            f"drawbox=x=0:y={subtitle_y}:w={width}:h={subtitle_height}:color=black@0.7:t=fill,"
            f"drawtext=fontfile='{escaped_font_path}':textfile='{escaped_subtitle_path}':"
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

        try:
            if self.ffmpeg.run_command(args):
                return temp_path
        finally:
            subtitle_path = Path(subtitle_file.name)
            if subtitle_path.exists():
                subtitle_path.unlink()

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
        """
        if not Path(video_path).exists():
            print(f"エラー: 動画ファイルが見つかりません: {video_path}")
            return False

        if not Path(audio_path).exists():
            print(f"エラー: 音声ファイルが見つかりません: {audio_path}")
            return False

        print(
            f"音声合成: {Path(video_path).name} + {Path(audio_path).name} -> {Path(output_path).name}"
        )

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
            print("✗ 音声合成失敗")

        return success
