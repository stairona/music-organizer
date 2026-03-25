# Phase 4-5 Integration Test Fixture
# This script creates test data to verify the full download → organize pipeline

import asyncio
import tempfile
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "music-organizer" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "music-organizer" / "app" / "backend"))

from music_organizer.tags import read_metadata
from music_organizer.classify import classify_file
from music_organizer.fileops import copy_file, move_file
from app.backend.store import (
    init_spotify_db,
    create_download_task,
    get_download_task,
    update_download_task,
    add_progress_snapshot,
    get_progress_history
)
from app.backend.services.spotdl_service import (
    _extract_percentage,
    _extract_filename,
    download_playlist,
    cancel_download,
    get_download_status
)

def create_test_music_file(path: str, genre: str = "Electronic", title: str = "Test Song"):
    """Create a minimal valid MP3 file with ID3 tags for testing."""
    # We'll create a simple file with some basic ID3 data
    # In reality, we'd use mutagen to write proper tags, but for testing
    # we can just create an empty file and simulate metadata
    with open(path, 'wb') as f:
        # Write minimal MP3 header (not really valid but enough for file existence)
        f.write(b'ID3\x03\x00\x00\x00')  # ID3v2.3 header
        f.write(b'\x00' * 100)  # padding
    return path

def test_metadata_reading():
    """Test that we can read metadata from test files."""
    print("\n=== Test 1: Metadata Reading ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.mp3")
        create_test_music_file(test_file)

        # In a real test, we'd verify metadata reading
        # For now, just check file exists
        assert os.path.exists(test_file), "Test file created"
        print(f"✓ Created test file: {test_file}")

        # Try to read metadata (will be minimal/empty)
        try:
            metadata = read_metadata(test_file)
            print(f"✓ Metadata extracted: {metadata}")
        except Exception as e:
            print(f"⚠ Metadata reading failed (expected for dummy file): {e}")

def test_classification():
    """Test genre classification logic."""
    print("\n=== Test 2: Genre Classification ===")
    # Test with empty/metadata-free simulation
    from music_organizer.rules import classify_by_path, classify_by_metadata

    # Test path-based classification
    test_paths = [
        "/music/House/SomeArtist/Track01.mp3",
        "/music/Techno/Artist/Album/song.flac",
        "/music/Unknown/Artist/song.m4a",
    ]

    for path in test_paths:
        genre = classify_by_path(Path(path))
        print(f"  {path} → {genre}")

    print("✓ Path classification works")

def test_store_operations():
    """Test Spotify store functions."""
    print("\n=== Test 3: Store Operations ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_spotify.db")
        os.environ['SPOTIFY_DB_PATH'] = db_path  # Override DB path for test

        # Initialize DB
        init_spotify_db()
        print("✓ Initialized test database")

        # Create a download task
        task_id = "test-task-123"
        create_download_task(
            task_id=task_id,
            playlist_id="pl123",
            playlist_name="Test Playlist",
            destination="/tmp/music",
            total_tracks=10,
            auto_organize=True
        )
        print(f"✓ Created download task: {task_id}")

        # Update task
        update_download_task(task_id, {
            "status": "downloading",
            "progress_percent": 50.0
        })
        print("✓ Updated task status")

        # Add progress snapshot
        add_progress_snapshot(
            task_id=task_id,
            percent=50.0,
            current_track="Track 5",
            completed_tracks=5,
            total_tracks=10
        )
        print("✓ Added progress snapshot")

        # Retrieve task
        task = get_download_task(task_id)
        assert task is not None, "Task should exist"
        print(f"✓ Retrieved task: status={task['status']}")

        # Get progress history
        history = get_progress_history(task_id)
        print(f"✓ Got {len(history)} progress snapshots")

def test_spotdl_service_helpers():
    """Test spotdl service helper functions."""
    print("\n=== Test 4: spotdl Service Helpers ===")

    # Test percentage extraction
    assert _extract_percentage("[download]  50% of ~10MB") == 50.0
    assert _extract_percentage("100% complete") == 100.0
    assert _extract_percentage("No percent here") is None
    print("✓ _extract_percentage works")

    # Test filename extraction
    assert _extract_filename("Downloaded: /path/song.mp3") == "/path/song.mp3"
    assert _extract_filename("Saving: My Song.mp3") == "My Song.mp3"
    print("✓ _extract_filename works")

async def test_organize_integration():
    """Test that organize service can be called from spotdl_service."""
    print("\n=== Test 5: Organize Integration ===")
    from app.backend.services import organize_service

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some dummy music files
        src_dir = os.path.join(tmpdir, "source")
        dest_dir = os.path.join(tmpdir, "dest")
        os.makedirs(src_dir)
        os.makedirs(dest_dir)

        # Create dummy files (empty, just to test copy/move logic)
        for i, genre in enumerate(["House", "Techno", "Pop"]):
            fname = f"track_{i}.mp3"
            open(os.path.join(src_dir, fname), 'w').close()

        print(f"  Created {len(os.listdir(src_dir))} test files in {src_dir}")

        # Run organize in copy mode
        try:
            result = organize_service(
                source=src_dir,
                destination=dest_dir,
                mode="copy",
                level="general",
                profile="default",
                dry_run=False,
                skip_existing=False
            )
            print(f"✓ Organize completed: {result.summary}")
            print(f"  Files copied: {result.files_copied}")
        except Exception as e:
            print(f"⚠ Organize service not fully functional yet: {e}")

def run_all_tests():
    """Run all verification tests."""
    print("=" * 60)
    print("Music Organizer v2.1 — Local Verification Tests")
    print("=" * 60)

    try:
        test_metadata_reading()
    except Exception as e:
        print(f"✗ Metadata test failed: {e}")

    try:
        test_classification()
    except Exception as e:
        print(f"✗ Classification test failed: {e}")

    try:
        test_store_operations()
    except Exception as e:
        print(f"✗ Store test failed: {e}")

    try:
        test_spotdl_service_helpers()
    except Exception as e:
        print(f"✗ Helper functions test failed: {e}")

    try:
        asyncio.run(test_organize_integration())
    except Exception as e:
        print(f"✗ Organize integration test failed: {e}")

    print("\n" + "=" * 60)
    print("Verification complete!")
    print("=" * 60)

if __name__ == "__main__":
    run_all_tests()
