"""
Tests for fileops module.
"""

import logging
import os
import pytest
from music_organizer.fileops import (
    get_unique_dest_path,
    compute_destination,
    ensure_dir_exists,
    sanitize_filename,
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


# --- sanitize_filename tests ---

def test_sanitize_filename_removes_special_chars():
    # Disallowed characters are removed (not replaced with underscores)
    assert sanitize_filename("my:illegal*name?.mp3") == "myillegalname.mp3"
    assert sanitize_filename("song@with#many!special$chars.flac") == "songwithmanyspecialchars.flac"
    # Leading and trailing spaces are stripped from the name part
    assert sanitize_filename(" filename with spaces.mp3 ") == "filename with spaces.mp3"


def test_sanitize_filename_truncates_long_names():
    long_name = "a" * 100 + ".mp3"
    result = sanitize_filename(long_name, max_length=60)
    assert len(result) <= 60
    assert result.endswith(".mp3")
    # Should be exactly 60 if extension fits
    assert len(result) == 60
    assert result.startswith("a" * 56)


def test_sanitize_filename_preserves_extension():
    assert sanitize_filename("song.wav") == "song.wav"
    assert sanitize_filename("my.song.flac") == "my.song.flac"


def test_sanitize_filename_strips_leading_trailing():
    assert sanitize_filename("  spaced out  .mp3") == "spaced out.mp3"
    assert sanitize_filename("..dotstart.mp3") == "dotstart.mp3"


def test_sanitize_filename_empty_after_sanitization():
    assert sanitize_filename("?????.mp3") == "untitled.mp3"


# --- compute_destination CDJ-safe tests ---

def test_compute_destination_cdj_safe_sanitizes(tmp_path):
    src = tmp_path / "music" / "my:illegal*name?.mp3"
    dest_root = tmp_path / "organized"
    specific = "Deep House"
    general = "Electronic"
    result = compute_destination(str(src), str(dest_root), specific, general, "general", profile="cdj-safe")
    # The filename should be sanitized (special chars removed)
    assert result.endswith("myillegalname.mp3")
    # The folder should be Electronic
    assert os.path.dirname(result) == os.path.join(str(dest_root), "Electronic")


def test_compute_destination_default_no_sanitization(tmp_path):
    src = tmp_path / "music" / "my:illegal*name?.mp3"
    dest_root = tmp_path / "organized"
    specific = "Deep House"
    general = "Electronic"
    result = compute_destination(str(src), str(dest_root), specific, general, "general", profile="default")
    # The filename should be preserved as is
    assert result.endswith("my:illegal*name?.mp3")


def test_compute_destination_cdj_safe_warns_on_long_path(caplog):
    # Construct a long path that exceeds 180 characters even with sanitized filename (max 60)
    long_root = "/" + "a" * 150  # length 151
    src_file = "/src/" + "x" * 100 + ".mp3"  # basename will be sanitized to 60 chars
    specific = "House"
    general = "Electronic"
    caplog.set_level(logging.WARNING)
    compute_destination(src_file, long_root, specific, general, "general", create_dirs=False, profile="cdj-safe")
    assert any("CDJ-safe: Path exceeds 180 characters" in rec.message for rec in caplog.records)


def test_compute_destination_cdj_safe_warns_on_depth(caplog):
    # Use genre names with path separators to create deep folder structure
    dest_root = "/dest"
    src_file = "/src/song.mp3"
    specific = "d"
    general = "a/b/c"  # this will create nested folders, resulting in depth 4
    caplog.set_level(logging.WARNING)
    result = compute_destination(src_file, dest_root, specific, general, "both", create_dirs=False, profile="cdj-safe")
    # Should log a truncation warning
    assert any("CDJ-safe: Folder depth exceeds 3 levels; truncating:" in rec.message for rec in caplog.records)
    # The resulting path should be truncated to only first 3 levels: /dest/a/b/c/song.mp3
    # Note: the specific "d" is dropped due to depth limit
    expected = os.path.join(dest_root, "a", "b", "c", "song.mp3")
    assert result == expected


def test_compute_destination_cdj_safe_no_warnings_when_within_limits(tmp_path, caplog):
    src = tmp_path / "music" / "reasonable_name.mp3"
    dest_root = tmp_path / "organized"
    specific = "House"
    general = "Electronic"
    caplog.set_level(logging.WARNING)
    compute_destination(str(src), str(dest_root), specific, general, "both", create_dirs=False, profile="cdj-safe")
    # Should not have any CDJ-safe warnings
    cdj_warnings = [rec.message for rec in caplog.records if "CDJ-safe:" in rec.message]
    assert len(cdj_warnings) == 0
