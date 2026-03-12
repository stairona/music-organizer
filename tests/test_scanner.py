"""
Tests for scanner module.
"""

import os
import pytest
from music_organizer.scanner import scan_source_directory, is_inside_dest


def test_scan_source_directory_basic(tmp_path):
    # Create a few dummy audio files
    music_dir = tmp_path / "music"
    music_dir.mkdir()
    (music_dir / "song1.mp3").touch()
    (music_dir / "song2.flac").touch()
    (music_dir / "song3.m4a").touch()
    # Non-audio file should be ignored
    (music_dir / "readme.txt").touch()

    result = scan_source_directory(str(music_dir))
    assert len(result) == 3
    # All paths should be absolute
    assert all(os.path.isabs(p) for p in result)


def test_scan_source_directory_nested(tmp_path):
    music_dir = tmp_path / "music"
    music_dir.mkdir()
    sub = music_dir / "albums" / "2024"
    sub.mkdir(parents=True)
    (music_dir / "song1.mp3").touch()
    (sub / "song2.ogg").touch()
    (sub / "song3.wav").touch()

    result = scan_source_directory(str(music_dir))
    assert len(result) == 3


def test_scan_source_directory_exclude_dirs(tmp_path):
    music_dir = tmp_path / "music"
    music_dir.mkdir()
    (music_dir / "song1.mp3").touch()
    temp_dir = music_dir / "temp_incomplete"
    temp_dir.mkdir()
    (temp_dir / "song2.mp3").touch()
    (music_dir / "incomplete_rejects").mkdir()
    (music_dir / "incomplete_rejects" / "song3.mp3").touch()

    # Without excludes, should find all 3
    result_all = scan_source_directory(str(music_dir))
    assert len(result_all) == 3

    # With excludes
    result_excl = scan_source_directory(str(music_dir), exclude_dirs=["temp_incomplete", "incomplete_rejects"])
    assert len(result_excl) == 1
    assert result_excl[0].endswith("song1.mp3")


def test_scan_source_directory_limit(tmp_path):
    music_dir = tmp_path / "music"
    music_dir.mkdir()
    for i in range(10):
        (music_dir / f"song{i}.mp3").touch()

    result = scan_source_directory(str(music_dir), limit=5)
    assert len(result) == 5


def test_scan_source_directory_ignores_hidden_system_files(tmp_path):
    music_dir = tmp_path / "music"
    music_dir.mkdir()
    (music_dir / "song1.mp3").touch()
    (music_dir / ".DS_Store").touch()
    (music_dir / "._song1.mp3").touch()
    (music_dir / "Thumbs.db").touch()

    result = scan_source_directory(str(music_dir))
    assert result == [str(music_dir / "song1.mp3")]


def test_scan_nonexistent_directory():
    with pytest.raises(NotADirectoryError):
        scan_source_directory("/nonexistent/path")


def test_is_inside_dest():
    # Simple case: file inside dest returns True
    dest = "/Volumes/Music/Organized"
    file_inside = "/Volumes/Music/Organized/Electronic/song.mp3"
    assert is_inside_dest(file_inside, dest) is True

    # File outside dest returns False
    file_outside = "/Volumes/Music/Raw/song.mp3"
    assert is_inside_dest(file_outside, dest) is False

    # Symlinks should be resolved
    # (hard to test portably, skip for now)


def test_is_inside_dest_edge_cases():
    dest = "/a/b"
    # Exact match
    assert is_inside_dest("/a/b", "/a/b") is True
    # Subdirectory
    assert is_inside_dest("/a/b/c/d", "/a/b") is True
    # Not subdirectory
    assert is_inside_dest("/a/bc", "/a/b") is False
    assert is_inside_dest("/a/bcd", "/a/b") is False
    assert is_inside_dest("/a/other", "/a/b") is False
