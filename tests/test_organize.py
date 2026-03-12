"""
Tests for organize command, specifically CDJ-safe profile warnings.
"""

import logging
from argparse import Namespace
import pytest
from music_organizer.commands.organize import run_organize


def test_cdj_safe_warns_on_folder_exceeding_500_files(tmp_path, caplog, monkeypatch):
    """Test that CDJ-safe profile logs warning when a folder would receive >500 files."""
    src_dir = tmp_path / "src"
    dest_dir = tmp_path / "dest"
    src_dir.mkdir()
    dest_dir.mkdir()

    # Create 501 fake file paths
    fake_files = [f"{src_dir}/track_{i}.mp3" for i in range(501)]

    # Mock dependencies
    monkeypatch.setattr('music_organizer.commands.organize.scan_source_directory', lambda *args, **kwargs: fake_files)
    monkeypatch.setattr('music_organizer.commands.organize.is_inside_dest', lambda src, dest: False)
    monkeypatch.setattr('music_organizer.commands.organize.classify_file', lambda *args, **kwargs: ("House", "Electronic", "test"))

    # Build args
    args = Namespace(
        source=str(src_dir),
        destination=str(dest_dir),
        mode='copy',
        level='general',
        dry_run=True,
        profile='cdj-safe',
        skip_existing=False,
        skip_unknown_only=False,
        quiet=False,
        debug=False,
        limit=None,
        exclude_dir=None,
        interactive=False,
        report=None
    )

    caplog.set_level(logging.WARNING)
    run_organize(args)

    # Check warning about folder exceeding 500 files
    warning_messages = [rec.message for rec in caplog.records if "CDJ-safe: Folder exceeds 500 files" in rec.message]
    assert len(warning_messages) >= 1
    # The warning should mention the Electronic folder
    assert any("Electronic" in msg for msg in warning_messages)


def test_cdj_safe_no_warning_when_folder_under_500_files(tmp_path, caplog, monkeypatch):
    """Test that no folder warning is logged when count is <=500."""
    src_dir = tmp_path / "src"
    dest_dir = tmp_path / "dest"
    src_dir.mkdir()
    dest_dir.mkdir()

    fake_files = [f"{src_dir}/track_{i}.mp3" for i in range(100)]

    monkeypatch.setattr('music_organizer.commands.organize.scan_source_directory', lambda *args, **kwargs: fake_files)
    monkeypatch.setattr('music_organizer.commands.organize.is_inside_dest', lambda src, dest: False)
    monkeypatch.setattr('music_organizer.commands.organize.classify_file', lambda *args, **kwargs: ("House", "Electronic", "test"))

    args = Namespace(
        source=str(src_dir),
        destination=str(dest_dir),
        mode='copy',
        level='general',
        dry_run=True,
        profile='cdj-safe',
        skip_existing=False,
        skip_unknown_only=False,
        quiet=False,
        debug=False,
        limit=None,
        exclude_dir=None,
        interactive=False,
        report=None
    )

    caplog.set_level(logging.WARNING)
    run_organize(args)

    warning_messages = [rec.message for rec in caplog.records if "CDJ-safe: Folder exceeds 500 files" in rec.message]
    assert len(warning_messages) == 0


def test_default_profile_no_cdj_warnings(tmp_path, caplog, monkeypatch):
    """Test that default profile does not produce any CDJ-safe warnings."""
    src_dir = tmp_path / "src"
    dest_dir = tmp_path / "dest"
    src_dir.mkdir()
    dest_dir.mkdir()

    fake_files = [f"{src_dir}/track_{i}.mp3" for i in range(501)]

    monkeypatch.setattr('music_organizer.commands.organize.scan_source_directory', lambda *args, **kwargs: fake_files)
    monkeypatch.setattr('music_organizer.commands.organize.is_inside_dest', lambda src, dest: False)
    monkeypatch.setattr('music_organizer.commands.organize.classify_file', lambda *args, **kwargs: ("House", "Electronic", "test"))

    args = Namespace(
        source=str(src_dir),
        destination=str(dest_dir),
        mode='copy',
        level='general',
        dry_run=True,
        profile='default',
        skip_existing=False,
        skip_unknown_only=False,
        quiet=False,
        debug=False,
        limit=None,
        exclude_dir=None,
        interactive=False,
        report=None
    )

    caplog.set_level(logging.WARNING)
    run_organize(args)

    cdj_warnings = [rec.message for rec in caplog.records if "CDJ-safe:" in rec.message]
    assert len(cdj_warnings) == 0
