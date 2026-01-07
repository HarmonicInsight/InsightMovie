#!/usr/bin/env python3
"""
Integration Test for InsightMovie
統合テスト
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """モジュールインポートテスト"""
    print("Testing imports...")
    try:
        from insightmovie.project import Project, Scene
        from insightmovie.voicevox import VoiceVoxClient, AudioCache
        from insightmovie.video import FFmpegWrapper, SceneGenerator, VideoComposer
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_project_creation():
    """プロジェクト作成テスト"""
    print("\nTesting project creation...")
    try:
        from insightmovie.project import Project
        project = Project()
        assert len(project.scenes) == 4, "Should have 4 default scenes"
        print(f"✓ Project created with {len(project.scenes)} scenes")
        return True
    except Exception as e:
        print(f"✗ Project creation failed: {e}")
        return False

def test_ffmpeg_detection():
    """ffmpeg検出テスト"""
    print("\nTesting ffmpeg detection...")
    try:
        from insightmovie.video import FFmpegWrapper
        try:
            ffmpeg = FFmpegWrapper()
            version = ffmpeg.get_version()
            print(f"✓ ffmpeg detected: {version}")
            return True
        except Exception as e:
            print(f"⚠ ffmpeg not found (expected if not installed): {e}")
            return True  # Not a failure, just not installed
    except Exception as e:
        print(f"✗ ffmpeg detection failed: {e}")
        return False

def test_voicevox_client():
    """VOICEVOX クライアントテスト"""
    print("\nTesting VOICEVOX client...")
    try:
        from insightmovie.voicevox import VoiceVoxClient
        client = VoiceVoxClient()
        connected = client.check_connection()
        if connected:
            print("✓ VOICEVOX Engine connected")
        else:
            print("⚠ VOICEVOX Engine not running (expected if not started)")
        return True  # Not a failure
    except Exception as e:
        print(f"✗ VOICEVOX client test failed: {e}")
        return False

def test_scene_serialization():
    """シーンのシリアライズテスト"""
    print("\nTesting scene serialization...")
    try:
        from insightmovie.project import Project
        import tempfile

        project = Project()
        project.scenes[0].narration_text = "テストナレーション"
        project.scenes[0].subtitle_text = "テスト字幕"

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        project.save(temp_path)

        # Load back
        loaded_project = Project(temp_path)
        assert loaded_project.scenes[0].narration_text == "テストナレーション"
        assert loaded_project.scenes[0].subtitle_text == "テスト字幕"

        print("✓ Scene serialization working")
        Path(temp_path).unlink()  # Cleanup
        return True
    except Exception as e:
        print(f"✗ Serialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """メインテスト"""
    print("=" * 60)
    print("InsightMovie Integration Test")
    print("=" * 60)

    results = []
    results.append(("Imports", test_imports()))
    results.append(("Project Creation", test_project_creation()))
    results.append(("ffmpeg Detection", test_ffmpeg_detection()))
    results.append(("VOICEVOX Client", test_voicevox_client()))
    results.append(("Scene Serialization", test_scene_serialization()))

    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
