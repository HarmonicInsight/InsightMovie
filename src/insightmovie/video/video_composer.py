"""
Video Composer
動画結合
"""
import tempfile
from pathlib import Path
from typing import List

from .ffmpeg_wrapper import FFmpegWrapper


class VideoComposer:
    """動画結合クラス"""

    def __init__(self, ffmpeg: FFmpegWrapper):
        """
        Args:
            ffmpeg: FFmpegWrapperインスタンス
        """
        self.ffmpeg = ffmpeg

    def concat_videos(
        self,
        video_paths: List[str],
        output_path: str
    ) -> bool:
        """
        複数の動画を結合

        Args:
            video_paths: 動画ファイルパスのリスト（順番通り）
            output_path: 出力先mp4ファイルパス

        Returns:
            成功したらTrue
        """
        if not video_paths:
            print("結合する動画がありません")
            return False

        if len(video_paths) == 1:
            # 1つだけの場合はコピー
            import shutil
            shutil.copy(video_paths[0], output_path)
            return True

        try:
            # concat用のリストファイルを作成
            list_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.txt',
                delete=False,
                encoding='utf-8'
            )

            for video_path in video_paths:
                # パスをエスケープ（ffmpeg concat demuxer用）
                escaped_path = str(Path(video_path).absolute()).replace('\\', '/')
                list_file.write(f"file '{escaped_path}'\n")

            list_file.close()

            # concat demuxerで結合
            args = [
                "-f", "concat",
                "-safe", "0",
                "-i", list_file.name,
                "-c", "copy",
                "-y",
                output_path
            ]

            success = self.ffmpeg.run_command(args)

            # 一時ファイル削除
            Path(list_file.name).unlink()

            return success

        except Exception as e:
            print(f"動画結合エラー: {e}")
            return False

    def concat_videos_with_re_encode(
        self,
        video_paths: List[str],
        output_path: str,
        resolution: str = "1080x1920",
        fps: int = 30
    ) -> bool:
        """
        複数の動画を再エンコードして結合（設定が異なる動画用）

        Args:
            video_paths: 動画ファイルパスのリスト
            output_path: 出力先mp4ファイルパス
            resolution: 解像度 "WxH"
            fps: フレームレート

        Returns:
            成功したらTrue
        """
        if not video_paths:
            print("結合する動画がありません")
            return False

        try:
            # 一時ファイルとして各動画を再エンコード
            temp_videos = []
            width, height = map(int, resolution.split('x'))

            for video_path in video_paths:
                temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
                temp_path = temp_file.name
                temp_file.close()

                args = [
                    "-i", video_path,
                    "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-r", str(fps),
                    "-c:a", "aac",
                    "-ar", "44100",
                    "-y",
                    temp_path
                ]

                if self.ffmpeg.run_command(args):
                    temp_videos.append(temp_path)
                else:
                    # 失敗した場合、一時ファイルをクリーンアップ
                    for temp in temp_videos:
                        if Path(temp).exists():
                            Path(temp).unlink()
                    if Path(temp_path).exists():
                        Path(temp_path).unlink()
                    return False

            # 再エンコードした動画を結合
            success = self.concat_videos(temp_videos, output_path)

            # 一時ファイル削除
            for temp in temp_videos:
                if Path(temp).exists():
                    Path(temp).unlink()

            return success

        except Exception as e:
            print(f"再エンコード結合エラー: {e}")
            return False
