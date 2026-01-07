"""
Audio Cache Manager
音声キャッシュ管理
"""
import hashlib
import wave
from pathlib import Path
from typing import Optional


class AudioCache:
    """音声キャッシュ管理クラス"""

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Args:
            cache_dir: キャッシュディレクトリ（Noneなら一時ディレクトリ）
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            import tempfile
            self.cache_dir = Path(tempfile.gettempdir()) / "insightmovie_cache" / "audio"

        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_key(self, text: str, speaker_id: int) -> str:
        """
        テキストと話者IDからキャッシュキーを生成

        Args:
            text: 音声化するテキスト
            speaker_id: 話者ID

        Returns:
            キャッシュキー（ハッシュ値）
        """
        content = f"{text}_{speaker_id}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def get_cache_path(self, text: str, speaker_id: int) -> Path:
        """
        キャッシュファイルのパスを取得

        Args:
            text: 音声化するテキスト
            speaker_id: 話者ID

        Returns:
            キャッシュファイルパス
        """
        cache_key = self.get_cache_key(text, speaker_id)
        return self.cache_dir / f"{cache_key}.wav"

    def exists(self, text: str, speaker_id: int) -> bool:
        """
        キャッシュが存在するかチェック

        Args:
            text: 音声化するテキスト
            speaker_id: 話者ID

        Returns:
            キャッシュが存在すればTrue
        """
        cache_path = self.get_cache_path(text, speaker_id)
        return cache_path.exists()

    def save(self, text: str, speaker_id: int, audio_data: bytes) -> str:
        """
        音声データをキャッシュに保存

        Args:
            text: 音声化したテキスト
            speaker_id: 話者ID
            audio_data: WAVファイルのバイナリデータ

        Returns:
            保存したファイルパス
        """
        cache_path = self.get_cache_path(text, speaker_id)
        with open(cache_path, 'wb') as f:
            f.write(audio_data)
        return str(cache_path)

    def load(self, text: str, speaker_id: int) -> Optional[bytes]:
        """
        キャッシュから音声データを読み込み

        Args:
            text: 音声化したテキスト
            speaker_id: 話者ID

        Returns:
            音声データ、存在しない場合はNone
        """
        cache_path = self.get_cache_path(text, speaker_id)
        if not cache_path.exists():
            return None

        with open(cache_path, 'rb') as f:
            return f.read()

    def get_duration(self, text: str, speaker_id: int) -> Optional[float]:
        """
        キャッシュ済み音声の長さを取得

        Args:
            text: 音声化したテキスト
            speaker_id: 話者ID

        Returns:
            音声の長さ（秒）、存在しない場合はNone
        """
        cache_path = self.get_cache_path(text, speaker_id)
        if not cache_path.exists():
            return None

        try:
            with wave.open(str(cache_path), 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                duration = frames / float(rate)
                return duration
        except Exception as e:
            print(f"音声長取得エラー: {e}")
            return None

    def clear_cache(self):
        """すべてのキャッシュを削除"""
        for cache_file in self.cache_dir.glob("*.wav"):
            cache_file.unlink()

    @staticmethod
    def get_audio_duration_from_bytes(audio_data: bytes) -> Optional[float]:
        """
        バイナリデータから音声長を取得

        Args:
            audio_data: WAVファイルのバイナリデータ

        Returns:
            音声の長さ（秒）、取得失敗時はNone
        """
        import io
        import wave

        try:
            with wave.open(io.BytesIO(audio_data), 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                duration = frames / float(rate)
                return duration
        except Exception as e:
            print(f"音声長取得エラー: {e}")
            return None
