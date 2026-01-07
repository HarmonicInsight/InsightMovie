"""
VOICEVOX Engine Client with Auto-Discovery
エンジン自動検出機能付きクライアント
"""
import requests
import json
import time
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class EngineInfo:
    """VOICEVOXエンジン情報"""
    host: str
    port: int
    version: str

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class VoiceVoxClient:
    """VOICEVOXエンジンクライアント"""

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 50021
    PORT_SCAN_RANGE = (50020, 50100)
    CONNECTION_TIMEOUT = 0.5  # 高速スキャン用の短いタイムアウト

    def __init__(self, base_url: Optional[str] = None):
        """
        Args:
            base_url: エンジンのベースURL（例: http://127.0.0.1:50021）
                     Noneの場合は自動検出を試みる
        """
        self._base_url = base_url
        self._engine_info: Optional[EngineInfo] = None

    @property
    def base_url(self) -> Optional[str]:
        """現在のベースURL"""
        return self._base_url

    @property
    def engine_info(self) -> Optional[EngineInfo]:
        """エンジン情報"""
        return self._engine_info

    def discover_engine(self, fast_check_first: bool = True) -> Optional[EngineInfo]:
        """
        VOICEVOXエンジンを自動検出

        Args:
            fast_check_first: デフォルトポートを最初にチェック

        Returns:
            見つかったエンジン情報、見つからない場合はNone
        """
        # まずデフォルトポートをチェック
        if fast_check_first:
            info = self._check_engine(self.DEFAULT_HOST, self.DEFAULT_PORT)
            if info:
                self._engine_info = info
                self._base_url = info.base_url
                return info

        # ポート範囲をスキャン
        print(f"エンジンをポート {self.PORT_SCAN_RANGE[0]}-{self.PORT_SCAN_RANGE[1]} でスキャン中...")
        for port in range(self.PORT_SCAN_RANGE[0], self.PORT_SCAN_RANGE[1] + 1):
            if port == self.DEFAULT_PORT and fast_check_first:
                continue  # 既にチェック済み

            info = self._check_engine(self.DEFAULT_HOST, port)
            if info:
                print(f"エンジンを検出: {info.base_url} (version: {info.version})")
                self._engine_info = info
                self._base_url = info.base_url
                return info

        print("エンジンが見つかりませんでした")
        return None

    def _check_engine(self, host: str, port: int) -> Optional[EngineInfo]:
        """
        指定ホスト・ポートでエンジンをチェック

        Args:
            host: ホスト名
            port: ポート番号

        Returns:
            エンジン情報、接続できない場合はNone
        """
        try:
            url = f"http://{host}:{port}/version"
            response = requests.get(url, timeout=self.CONNECTION_TIMEOUT)

            if response.status_code == 200:
                version = response.text.strip('"')
                return EngineInfo(host=host, port=port, version=version)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException):
            pass

        return None

    def check_connection(self) -> bool:
        """
        エンジンへの接続確認

        Returns:
            接続可能ならTrue
        """
        if not self._base_url:
            return False

        try:
            response = requests.get(
                f"{self._base_url}/version",
                timeout=2.0
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_speakers(self) -> List[Dict]:
        """
        利用可能な話者一覧を取得

        Returns:
            話者情報のリスト
        """
        if not self._base_url:
            raise RuntimeError("エンジンに接続されていません")

        try:
            response = requests.get(
                f"{self._base_url}/speakers",
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"話者情報の取得に失敗: {e}")

    def find_speaker_by_name(self, name: str) -> Optional[int]:
        """
        話者名から style_id を検索

        Args:
            name: 話者名（例: "四国めたん"）

        Returns:
            style_id、見つからない場合はNone
        """
        try:
            speakers = self.get_speakers()

            # デバッグ: 利用可能な話者を表示
            print("利用可能な話者:")
            for speaker in speakers:
                print(f"  - {speaker.get('name')}")
                for style in speaker.get("styles", []):
                    print(f"    - {style.get('name')} (ID: {style.get('id')})")

            for speaker in speakers:
                if speaker.get("name") == name:
                    # 最初のスタイルを使用
                    styles = speaker.get("styles", [])
                    if styles:
                        style_id = styles[0].get("id")
                        print(f"✓ 話者「{name}」を見つけました (Style ID: {style_id})")
                        return style_id

            print(f"✗ 話者「{name}」が見つかりませんでした")
            return None
        except Exception as e:
            print(f"話者検索エラー: {e}")
            return None

    def get_default_speaker(self) -> Optional[int]:
        """
        デフォルト話者のstyle_idを取得

        優先順位:
        1. 青山龍星
        2. 四国めたん
        3. ずんだもん
        4. 最初の話者

        Returns:
            style_id、見つからない場合はNone
        """
        try:
            speakers = self.get_speakers()

            # 優先話者リスト
            preferred_speakers = ["青山龍星", "四国めたん", "ずんだもん", "春日部つむぎ"]

            for preferred in preferred_speakers:
                for speaker in speakers:
                    if speaker.get("name") == preferred:
                        styles = speaker.get("styles", [])
                        if styles:
                            style_id = styles[0].get("id")
                            print(f"デフォルト話者: {preferred} (Style ID: {style_id})")
                            return style_id

            # フォールバック: 最初の話者
            if speakers and speakers[0].get("styles"):
                first_speaker = speakers[0].get("name")
                style_id = speakers[0]["styles"][0].get("id")
                print(f"デフォルト話者（フォールバック）: {first_speaker} (Style ID: {style_id})")
                return style_id

            return None
        except Exception as e:
            print(f"デフォルト話者取得エラー: {e}")
            return None

    def create_audio_query(self, text: str, speaker_id: int) -> Dict:
        """
        音声合成用のクエリを作成

        Args:
            text: 合成するテキスト
            speaker_id: 話者ID

        Returns:
            オーディオクエリ
        """
        if not self._base_url:
            raise RuntimeError("エンジンに接続されていません")

        try:
            response = requests.post(
                f"{self._base_url}/audio_query",
                params={"text": text, "speaker": speaker_id},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"音声クエリの作成に失敗: {e}")

    def synthesize(self, query: Dict, speaker_id: int) -> bytes:
        """
        音声を合成

        Args:
            query: オーディオクエリ
            speaker_id: 話者ID

        Returns:
            WAVファイルのバイナリデータ
        """
        if not self._base_url:
            raise RuntimeError("エンジンに接続されていません")

        try:
            response = requests.post(
                f"{self._base_url}/synthesis",
                params={"speaker": speaker_id},
                json=query,
                timeout=30.0
            )
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"音声合成に失敗: {e}")

    def generate_audio(self, text: str, speaker_id: int) -> bytes:
        """
        テキストから音声を生成（ワンステップ）

        Args:
            text: 合成するテキスト
            speaker_id: 話者ID

        Returns:
            WAVファイルのバイナリデータ
        """
        query = self.create_audio_query(text, speaker_id)
        return self.synthesize(query, speaker_id)
