"""
Tests for fileops module.
"""

import os
import pytest
from music_organizer.fileops import (
    get_unique_dest_path,
    compute_destination,
    ensure_dir_exists,
)


def test_ensure_dir_exists(tmp_path):
    test_dir = tmp_path / "new" / "nested" / "dir"
    assert not test_dir.exists()
    ensure_dir_exists(str(test_dir))
    assert test_dir.exists()
    # Should not raise if called again
    ensure_dir_exists(str(test_dir))


def test_get_unique_dest_path_no_collision(tmp_path):
    dest_file = tmp_path / "song.mp3"
    # File doesn't exist
    result = get_unique_dest_path(str(dest_file))
    assert result == str(dest_file)


def test_get_unique_dest_path_with_collision(tmp_path):
    dest_file = tmp_path / "song.mp3"
    dest_file.touch()  # Create the file
    result = get_unique_dest_path(str(dest_file))
    expected = tmp_path / "song (1).mp3"
    assert result == str(expected)
    assert not os.path.exists(result)  # not actually created, just computed

    # Create the first duplicate and check second duplicate
    result2 = get_unique_dest_path(str(dest_file))
    # Actually get_unique_dest_path would create files if we called it, but we are just testing path generation
    # Let's test more: create (1) and see if (2) is returned
    (tmp_path / "song (1).mp3").touch()
    result3 = get_unique_dest_path(str(dest_file))
    assert result3 == str(tmp_path / "song (2).mp3")


def test_compute_destination_general(tmp_path):
    src = tmp_path / "music" / "song.mp3"
    dest_root = tmp_path / "organized"
    specific = "Deep House"
    general = "Electronic"

    result = compute_destination(str(src), str(dest_root), specific, general, "general")
    expected = dest_root / "Electronic" / "song.mp3"
    assert result == str(expected)
    # Verify the genre directory was created (not necessarily the file itself)
    assert os.path.isdir(dest_root / "Electronic")

    # Clean up
    os.rmdir(dest_root / "Electronic")


def test_compute_destination_specific(tmp_path):
    src = tmp_path / "music" / "song.mp3"
    dest_root = tmp_path / "organized"
    specific = "Deep House"
    general = "Electronic"

    result = compute_destination(str(src), str(dest_root), specific, general, "specific")
    expected = dest_root / "Deep House" / "song.mp3"
    assert result == str(expected)


def test_compute_destination_both(tmp_path):
    src = tmp_path / "music" / "song.mp3"
    dest_root = tmp_path / "organized"
    specific = "Deep House"
    general = "Electronic"

    result = compute_destination(str(src), str(dest_root), specific, general, "both")
    expected = dest_root / "Electronic" / "Deep House" / "song.mp3"
    assert result == str(expected)
