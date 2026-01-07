"""
Project Model
プロジェクトモデル
"""
import json
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field

from .scene import Scene


@dataclass
class OutputSettings:
    """出力設定"""
    resolution: str = "1080x1920"  # 縦動画デフォルト
    fps: int = 30
    output_path: str = ""

    def to_dict(self) -> dict:
        return {
            'resolution': self.resolution,
            'fps': self.fps,
            'output_path': self.output_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'OutputSettings':
        return cls(
            resolution=data.get('resolution', '1080x1920'),
            fps=data.get('fps', 30),
            output_path=data.get('output_path', ''),
        )


@dataclass
class ProjectSettings:
    """プロジェクト設定"""
    voicevox_base_url: str = "http://127.0.0.1:50021"
    voicevox_run_exe: Optional[str] = None
    ffmpeg_path: Optional[str] = None
    font_path: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'voicevox_base_url': self.voicevox_base_url,
            'voicevox_run_exe': self.voicevox_run_exe,
            'ffmpeg_path': self.ffmpeg_path,
            'font_path': self.font_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ProjectSettings':
        return cls(
            voicevox_base_url=data.get('voicevox_base_url', 'http://127.0.0.1:50021'),
            voicevox_run_exe=data.get('voicevox_run_exe'),
            ffmpeg_path=data.get('ffmpeg_path'),
            font_path=data.get('font_path'),
        )


class Project:
    """プロジェクト管理クラス"""

    def __init__(self, project_path: Optional[str] = None):
        """
        Args:
            project_path: プロジェクトファイルパス（.json）
        """
        self.project_path = project_path
        self.scenes: List[Scene] = []
        self.output: OutputSettings = OutputSettings()
        self.settings: ProjectSettings = ProjectSettings()

        if project_path and Path(project_path).exists():
            self.load()
        else:
            # 新規プロジェクト：デフォルト4シーン
            self.initialize_default_scenes()

    def initialize_default_scenes(self):
        """デフォルト2シーンを初期化"""
        self.scenes = [Scene() for _ in range(2)]

    def add_scene(self, index: Optional[int] = None) -> Scene:
        """
        シーンを追加

        Args:
            index: 挿入位置（Noneなら末尾）

        Returns:
            追加されたシーン
        """
        scene = Scene()
        if index is None:
            self.scenes.append(scene)
        else:
            self.scenes.insert(index, scene)
        return scene

    def remove_scene(self, scene_id: str) -> bool:
        """
        シーンを削除

        Args:
            scene_id: シーンID

        Returns:
            削除成功したらTrue
        """
        # 最低1シーンは残す
        if len(self.scenes) <= 1:
            return False

        for i, scene in enumerate(self.scenes):
            if scene.id == scene_id:
                self.scenes.pop(i)
                return True
        return False

    def move_scene(self, scene_id: str, direction: int) -> bool:
        """
        シーンを上下に移動

        Args:
            scene_id: シーンID
            direction: -1で上、1で下

        Returns:
            移動成功したらTrue
        """
        for i, scene in enumerate(self.scenes):
            if scene.id == scene_id:
                new_index = i + direction
                if 0 <= new_index < len(self.scenes):
                    self.scenes[i], self.scenes[new_index] = \
                        self.scenes[new_index], self.scenes[i]
                    return True
                return False
        return False

    def get_scene(self, scene_id: str) -> Optional[Scene]:
        """シーンIDからシーンを取得"""
        for scene in self.scenes:
            if scene.id == scene_id:
                return scene
        return None

    def to_dict(self) -> dict:
        """辞書に変換"""
        return {
            'scenes': [scene.to_dict() for scene in self.scenes],
            'output': self.output.to_dict(),
            'settings': self.settings.to_dict(),
        }

    def save(self, path: Optional[str] = None):
        """
        プロジェクトを保存

        Args:
            path: 保存先パス（Noneなら既存パス）
        """
        save_path = path or self.project_path
        if not save_path:
            raise ValueError("保存先パスが指定されていません")

        self.project_path = save_path

        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def load(self, path: Optional[str] = None):
        """
        プロジェクトを読み込み

        Args:
            path: 読み込み元パス（Noneなら既存パス）
        """
        load_path = path or self.project_path
        if not load_path:
            raise ValueError("読み込み元パスが指定されていません")

        with open(load_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.scenes = [Scene.from_dict(s) for s in data.get('scenes', [])]
        self.output = OutputSettings.from_dict(data.get('output', {}))
        self.settings = ProjectSettings.from_dict(data.get('settings', {}))
        self.project_path = load_path

    @property
    def total_scenes(self) -> int:
        """総シーン数"""
        return len(self.scenes)

    @property
    def is_valid(self) -> bool:
        """プロジェクトが有効か（最低限の条件）"""
        return len(self.scenes) > 0
