"""
Tests for the journal (undo) system.
"""

import json
import os
import pytest
from music_organizer.journal import save_journal, load_journal, undo_last


@pytest.fixture
def journal_dir(tmp_path, monkeypatch):
    """Redirect journal to a temp directory."""
    import music_organizer.journal as jmod
    jpath = tmp_path / "journal.json"
    monkeypatch.setattr(jmod, "JOURNAL_DIR", str(tmp_path))
    monkeypatch.setattr(jmod, "JOURNAL_PATH", str(jpath))
    return tmp_path


def test_save_and_load_journal(journal_dir):
    entries = [
        {"source": "/a/song.mp3", "destination": "/b/song.mp3", "mode": "copy"},
        {"source": "/a/track.flac", "destination": "/b/track.flac", "mode": "copy"},
    ]
    save_journal(entries, "copy")

    journal = load_journal()
    assert journal["mode"] == "copy"
    assert journal["file_count"] == 2
    assert len(journal["entries"]) == 2
    assert "timestamp" in journal


def test_load_journal_no_file(journal_dir):
    assert load_journal() == {}


def test_undo_copy(journal_dir, tmp_path):
    """Undo of copy mode should delete the destination files."""
    # Create fake destination files
    dest1 = tmp_path / "organized" / "song.mp3"
    dest1.parent.mkdir(parents=True)
    dest1.write_text("fake audio")

    entries = [{"source": "/orig/song.mp3", "destination": str(dest1), "mode": "copy"}]
    save_journal(entries, "copy")

    reverted = undo_last()
    assert reverted == 1
    assert not dest1.exists()
    # Journal should be cleared
    assert load_journal() == {}


def test_undo_move(journal_dir, tmp_path):
    """Undo of move mode should move files back to original location."""
    orig = tmp_path / "original" / "song.mp3"
    dest = tmp_path / "organized" / "song.mp3"
    dest.parent.mkdir(parents=True)
    dest.write_text("fake audio")

    entries = [{"source": str(orig), "destination": str(dest), "mode": "move"}]
    save_journal(entries, "move")

    reverted = undo_last()
    assert reverted == 1
    assert orig.exists()
    assert not dest.exists()


def test_undo_nothing(journal_dir):
    assert undo_last() == 0
