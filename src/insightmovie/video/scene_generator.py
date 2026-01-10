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

    @staticmethod
    def _split_subtitle_text(text: str, max_chars: int = 18) -> str:
        """
        字幕テキストを適切な位置で分割

        Args:
            text: 字幕テキスト
            max_chars: 1行あたりの最大文字数

        Returns:
            分割された文字列（改行は\\nで表現）
        """
        if len(text) <= max_chars:
            return text

        # 分割位置を探す（中央付近で句読点やスペースを優先）
        mid = len(text) // 2
        split_pos = mid

        # 中央から前後5文字以内で句読点を探す
        for offset in range(6):
            # 中央より後ろを先に探す
            pos = mid + offset
            if pos < len(text) and text[pos] in ' 、。，．！？':
                split_pos = pos + 1
                break
            # 中央より前を探す
            pos = mid - offset
            if pos > 0 and text[pos] in ' 、。，．！？':
                split_pos = pos + 1
                break

        line1 = text[:split_pos].strip()
        line2 = text[split_pos:].strip()

        if line2:
            return f"{line1}\\n{line2}"
        return line1

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
            print(f"\n=== シーン動画生成開始 ===")
            print(f"  出力: {Path(output_path).name}")
            print(f"  長さ: {duration}秒")
            print(f"  解像度: {resolution}")
            print(f"  字幕: {scene.subtitle_text if scene.has_subtitle else 'なし'}")
            print(f"  音声: {'あり' if audio_path else 'なし'}")
            print(f"  元音声保持: {'はい' if scene.keep_original_audio else 'いいえ'}")

            # 解像度をパース
            width, height = map(int, resolution.split('x'))

            # 一時ファイル
            temp_video = None
            has_original_audio = False  # 元動画の音声があるか

            # ステップ1: メディアから基本動画を生成
            print(f"\n[1/3] 基本動画生成...")
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
                keep_audio = scene.keep_original_audio
                temp_video = self._generate_from_video(
                    scene.media_path,
                    duration,
                    width,
                    height,
                    fps,
                    keep_audio=keep_audio
                )
                has_original_audio = keep_audio
            else:
                # メディアなし：黒画面
                print(f"  黒画面動画を生成")
                temp_video = self._generate_blank_video(
                    duration,
                    width,
                    height,
                    fps
                )

            if not temp_video:
                print(f"  ✗ 基本動画生成失敗")
                return False
            print(f"  ✓ 基本動画生成完了: {Path(temp_video).name}")

            # ステップ2: 字幕を焼き込み
            print(f"\n[2/3] 字幕処理...")
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
                    Path(temp_video).unlink()  # 一時ファイル削除
                    temp_video = temp_with_subtitle
                    print(f"  ✓ 字幕焼き込み完了")
                else:
                    print(f"  ✗ 字幕焼き込み失敗")
            else:
                print(f"  字幕なし（スキップ）")

            # ステップ3: 音声を合成
            print(f"\n[3/3] 音声処理...")
            if has_original_audio:
                # 元動画の音声を残す場合：会話音声は追加せず、動画をそのまま使用
                print(f"  元動画の音声を使用（会話音声は追加しない）")
                import shutil
                shutil.copy(temp_video, output_path)
                success = True
            elif audio_path:
                print(f"  音声ファイル: {Path(audio_path).name}")
                success = self._add_audio(temp_video, audio_path, output_path)
                if success:
                    print(f"  ✓ 音声合成完了")
                else:
                    print(f"  ✗ 音声合成失敗")
            else:
                # 音声なし：そのままコピー
                print(f"  音声なし（動画のみコピー）")
                import shutil
                shutil.copy(temp_video, output_path)
                success = True

            # 一時ファイル削除
            if Path(temp_video).exists():
                Path(temp_video).unlink()

            if success:
                print(f"\n✓ シーン動画生成完了: {Path(output_path).name}")
            else:
                print(f"\n✗ シーン動画生成失敗")

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
        fps: int,
        keep_audio: bool = False
    ) -> Optional[str]:
        """
        動画を指定長さにトリミング・リサイズ（ループ対応）

        Args:
            video_path: 動画ファイルパス
            duration: 長さ（秒）
            width, height: 解像度
            fps: フレームレート
            keep_audio: 元音声を残すか

        Returns:
            生成された一時動画ファイルパス、失敗時はNone
        """
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        # 動画の長さを取得
        video_info = self.ffmpeg.get_video_info(video_path)
        video_duration = video_info.get('duration', 0) if video_info else 0

        if keep_audio:
            # 元音声を残す場合：動画をそのまま最後まで使用（カットしない）
            print(f"  元動画の音声を残す: 動画の長さ({video_duration:.2f}秒)をそのまま使用")
            args = [
                "-i", video_path,
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", str(fps),
                "-c:a", "aac",
                "-b:a", "192k",
            ]
        elif video_duration > 0 and video_duration < duration:
            # 動画が短い場合はループ再生
            print(f"  動画が短いためループ再生: {video_duration:.2f}秒 → {duration:.2f}秒")
            args = [
                "-stream_loop", "-1",
                "-i", video_path,
                "-t", str(duration),
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", str(fps),
                "-an",
            ]
        else:
            # 動画が長い場合は指定長さにカット
            args = [
                "-i", video_path,
                "-t", str(duration),
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", str(fps),
                "-an",
            ]

        args.extend(["-y", temp_path])

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
        height: int,
        max_chars_per_line: int = 18
    ) -> Optional[str]:
        """
        字幕を焼き込み（2行対応）

        Args:
            video_path: 元動画ファイルパス
            subtitle_text: 字幕テキスト
            width, height: 解像度
            max_chars_per_line: 1行あたりの最大文字数

        Returns:
            字幕付き一時動画ファイルパス、失敗時はNone
        """
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        # 字幕エリアの設定
        # 下部マージン（メディアプレイヤーの操作バーを避ける）
        bottom_margin = int(height * 0.12)
        # 字幕エリアの高さ（2行対応）
        subtitle_height = int(height * 0.10)
        subtitle_y = height - subtitle_height - bottom_margin

        # フォントサイズ（高さに応じて調整）
        font_size = int(height * 0.022)

        # 長い字幕を2行に分割
        display_text = self._split_subtitle_text(subtitle_text, max_chars_per_line)

        # エスケープ処理
        escaped_text = display_text.replace(':', r'\:').replace("'", r"\'")

        # フォントパスのエスケープ（Windowsパス対応）
        # ffmpegフィルターではコロンとバックスラッシュをエスケープする必要がある
        escaped_font_path = str(self.font_path).replace('\\', '/').replace(':', r'\:')

        # drawboxで黒背景、drawtextで白文字（中央揃え）
        filter_complex = (
            f"drawbox=x=0:y={subtitle_y}:w={width}:h={subtitle_height}:color=black@0.7:t=fill,"
            f"drawtext=fontfile='{escaped_font_path}':text='{escaped_text}':"
            f"fontcolor=white:fontsize={font_size}:x=(w-text_w)/2:y={subtitle_y}+({subtitle_height}-text_h)/2"
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
        output_path: str,
        silence_padding: float = 1.0,
        mix_original: bool = False
    ) -> bool:
        """
        動画に音声を合成（前後に無音を追加）

        Args:
            video_path: 動画ファイルパス
            audio_path: 音声ファイルパス（VOICEVOX会話音声）
            output_path: 出力先mp4ファイルパス
            silence_padding: 前後に追加する無音秒数（デフォルト1秒）
            mix_original: 元動画の音声とミックスするか

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
        print(f"  前後無音: {silence_padding}秒ずつ")
        print(f"  元音声ミックス: {'はい' if mix_original else 'いいえ'}")

        if mix_original:
            # 元音声とVOICEVOX音声をミックス
            # 元音声（0:a）と会話音声（1:a、前後無音付き）をamixで合成
            filter_complex = (
                f"[1:a]aformat=sample_rates=44100:channel_layouts=stereo[voice];"
                f"anullsrc=r=44100:cl=stereo:d={silence_padding}[silence1];"
                f"anullsrc=r=44100:cl=stereo:d={silence_padding}[silence2];"
                f"[silence1][voice][silence2]concat=n=3:v=0:a=1[voicewithpad];"
                f"[0:a]aformat=sample_rates=44100:channel_layouts=stereo[original];"
                f"[original][voicewithpad]amix=inputs=2:duration=longest:dropout_transition=0[aout]"
            )
        else:
            # VOICEVOX音声のみ（従来の動作）
            filter_complex = (
                f"[1:a]aformat=sample_rates=44100:channel_layouts=stereo[main];"
                f"anullsrc=r=44100:cl=stereo:d={silence_padding}[silence1];"
                f"anullsrc=r=44100:cl=stereo:d={silence_padding}[silence2];"
                f"[silence1][main][silence2]concat=n=3:v=0:a=1[aout]"
            )

        args = [
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
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
