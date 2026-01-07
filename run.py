#!/usr/bin/env python3
"""
InsightMovie Entry Point
開発環境用エントリーポイント
"""
import sys
from pathlib import Path

# src ディレクトリをPythonパスに追加
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# メイン関数をインポートして実行
from insightmovie.main import main

if __name__ == "__main__":
    sys.exit(main())
