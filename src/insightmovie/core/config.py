"""
Configuration Management
設定管理
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


class Config:
    """アプリケーション設定"""

    def __init__(self):
        self.config_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "InsightMovie"
        self.config_file = self.config_dir / "config.json"
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self):
        """設定を読み込み"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"設定読み込みエラー: {e}")
                self.data = {}
        else:
            self.data = {}

    def save(self):
        """設定を保存"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"設定保存エラー: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        """設定値を設定"""
        self.data[key] = value

    @property
    def is_first_run(self) -> bool:
        """初回実行かどうか"""
        return not self.get("setup_completed", False)

    def mark_setup_completed(self):
        """セットアップ完了をマーク"""
        self.set("setup_completed", True)
        self.save()

    @property
    def engine_url(self) -> Optional[str]:
        """VOICEVOXエンジンURL"""
        return self.get("engine_url")

    @engine_url.setter
    def engine_url(self, url: str):
        """VOICEVOXエンジンURLを設定"""
        self.set("engine_url", url)
        self.save()

    @property
    def engine_path(self) -> Optional[str]:
        """VOICEVOXエンジンパス"""
        return self.get("engine_path")

    @engine_path.setter
    def engine_path(self, path: str):
        """VOICEVOXエンジンパスを設定"""
        self.set("engine_path", path)
        self.save()

    @property
    def default_speaker_id(self) -> Optional[int]:
        """デフォルト話者ID"""
        return self.get("default_speaker_id")

    @default_speaker_id.setter
    def default_speaker_id(self, speaker_id: int):
        """デフォルト話者IDを設定"""
        self.set("default_speaker_id", speaker_id)
        self.save()
