"""
Scene Model
シーンモデル
"""
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field
import uuid


class MediaType(Enum):
    """メディアタイプ"""
    IMAGE = "image"
    VIDEO = "video"
    NONE = "none"


class DurationMode(Enum):
    """シーン長さモード"""
    AUTO = "auto"  # 音声長に自動追従
    FIXED = "fixed"  # 固定秒数


@dataclass
class Scene:
    """シーンデータ"""

    # 識別子
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # メディア
    media_path: Optional[str] = None
    media_type: MediaType = MediaType.NONE

    # テキスト
    narration_text: str = ""  # 説明文（ナレーション）
    subtitle_text: str = ""   # 字幕

    # 長さ設定
    duration_mode: DurationMode = DurationMode.AUTO
    fixed_seconds: float = 3.0

    # 生成済みファイル（キャッシュ）
    audio_cache_path: Optional[str] = None
    video_cache_path: Optional[str] = None

    def to_dict(self) -> dict:
        """辞書に変換"""
        return {
            'id': self.id,
            'media_path': self.media_path,
            'media_type': self.media_type.value,
            'narration_text': self.narration_text,
            'subtitle_text': self.subtitle_text,
            'duration_mode': self.duration_mode.value,
            'fixed_seconds': self.fixed_seconds,
            'audio_cache_path': self.audio_cache_path,
            'video_cache_path': self.video_cache_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Scene':
        """辞書から復元"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            media_path=data.get('media_path'),
            media_type=MediaType(data.get('media_type', 'none')),
            narration_text=data.get('narration_text', ''),
            subtitle_text=data.get('subtitle_text', ''),
            duration_mode=DurationMode(data.get('duration_mode', 'auto')),
            fixed_seconds=data.get('fixed_seconds', 3.0),
            audio_cache_path=data.get('audio_cache_path'),
            video_cache_path=data.get('video_cache_path'),
        )

    @property
    def has_media(self) -> bool:
        """メディアが設定されているか"""
        return self.media_type != MediaType.NONE and self.media_path is not None

    @property
    def has_narration(self) -> bool:
        """ナレーションがあるか"""
        return len(self.narration_text.strip()) > 0

    @property
    def has_subtitle(self) -> bool:
        """字幕があるか"""
        return len(self.subtitle_text.strip()) > 0
