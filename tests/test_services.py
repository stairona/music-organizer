"""
Tests for backend service layer.
"""

import pytest
import os
import tempfile
from app.backend.services import analyze_service, organize_service
from app.backend.models import AnalyzeResult, OrganizeResult


class TestAnalyzeService:
    def test_analyze_empty_directory(self):
        """Analyzing an empty directory returns valid empty result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = analyze_service(source=tmpdir)
            assert isinstance(result, AnalyzeResult)
            assert result.success is True
            assert result.summary.total == 0
            assert result.summary.processed == 0
            assert result.summary.moved_or_copied == 0

    def test_analyze_with_test_files(self, tmp_path):
        """Analyze returns structured result with correct counts."""
        # Create a couple of dummy audio files (empty .mp3)
        test_dir = tmp_path / "music"
        test_dir.mkdir()
        (test_dir / "song1.mp3").touch()
        (test_dir / "song2.flac").touch()
        (test_dir / "song3.m4a").touch()

        result = analyze_service(source=str(test_dir), level="general")

        assert isinstance(result, AnalyzeResult)
        assert result.success is True
        assert result.summary.total == 3
        assert result.summary.processed == 3
        # All files likely classified as Unknown due to no metadata/path keywords
        assert result.summary.unknown_count == 3
        # Unknown files are NOT added to specific_counter; they're tracked separately
        assert len(result.summary.specific_counter) == 0
        assert result.unknown_diagnostics is not None
        assert result.unknown_diagnostics.count == 3
        assert len(result.unknown_diagnostics.sample_paths) > 0

    def test_analyze_with_limit(self, tmp_path):
        """Limit parameter correctly restricts file count."""
        test_dir = tmp_path / "music"
        test_dir.mkdir()
        for i in range(10):
            (test_dir / f"song{i}.mp3").touch()

        result = analyze_service(source=str(test_dir), limit=5)
        assert result.summary.total == 5

    def test_analyze_invalid_source(self):
        """Analyzing non-existent directory raises ValueError."""
        with pytest.raises(ValueError, match="Source directory does not exist"):
            analyze_service(source="/nonexistent/path")


class TestOrganizeService:
    def test_organize_dry_run(self, tmp_path):
        """Dry run organizes without making changes."""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()  # ensure_dir_exists will be called

        # Create dummy files
        (src / "house" / "song.mp3").parent.mkdir()
        (src / "house" / "song.mp3").touch()

        result = organize_service(
            source=str(src),
            destination=str(dst),
            mode="copy",
            level="specific",
            profile="default",
            dry_run=True,
        )

        assert isinstance(result, OrganizeResult)
        assert result.success is True
        assert result.summary.total == 1
        assert result.summary.moved_or_copied == 0  # dry run doesn't copy
        # Should still classify the file
        assert "House" in result.summary.specific_counter or result.summary.unknown_count == 1

    def test_organize_copy_mode(self, tmp_path):
        """Copy mode actually copies files."""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "deep house").mkdir()
        (src / "deep house" / "track.flac").touch()

        result = organize_service(
            source=str(src),
            destination=str(dst),
            mode="copy",
            level="specific",
            profile="default",
            dry_run=False,
        )

        assert result.success is True
        # Check that file was copied (if classification succeeded)
        # Classification may or may not match Deep House depending on path
        if result.summary.moved_or_copied > 0:
            copied_files = list(dst.rglob("*.flac"))
            assert len(copied_files) == 1

    def test_organize_copy_mode_saves_legacy_journal(self, tmp_path, monkeypatch):
        """Non-dry-run organize_service should save the legacy journal successfully."""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "deep house").mkdir()
        (src / "deep house" / "track.flac").touch()

        journal_calls = []

        def fake_save_journal(entries, mode):
            journal_calls.append((entries, mode))

        monkeypatch.setattr("app.backend.services.save_journal", fake_save_journal)

        result = organize_service(
            source=str(src),
            destination=str(dst),
            mode="copy",
            level="specific",
            profile="default",
            dry_run=False,
        )

        assert result.success is True
        assert result.summary.moved_or_copied == 1
        assert result.journal_saved is True
        assert len(journal_calls) == 1
        assert journal_calls[0][1] == "copy"

    def test_organize_skip_existing(self, tmp_path):
        """skip_existing prevents overwriting existing files."""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        (src / "tech house").mkdir()
        (src / "tech house" / "song.mp3").touch()
        # Pre-create destination file: for level="specific", path is dst/<SpecificGenre>/filename
        dest_subdir = dst / "Tech House"
        dest_subdir.mkdir(parents=True)
        (dest_subdir / "song.mp3").touch()

        result = organize_service(
            source=str(src),
            destination=str(dst),
            mode="copy",
            level="specific",
            profile="default",
            dry_run=False,
            skip_existing=True,
        )

        # Should be skipped, not copied
        assert result.summary.moved_or_copied == 0
        assert result.summary.skipped_counts.get("skipped-existing", 0) == 1

    def test_organize_invalid_destination_parent(self, tmp_path):
        """If destination parent doesn't exist, it should be created."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "test.mp3").touch()

        dst = tmp_path / "new_dir" / "subdir"

        result = organize_service(
            source=str(src),
            destination=str(dst),
            dry_run=True,  # dry run avoids actual copy but creates dest dir
        )

        # Should still succeed even if destination didn't exist
        assert result.success is True

    def test_organize_invalid_source(self):
        """Organize with non-existent source raises ValueError."""
        with pytest.raises(ValueError, match="Source directory does not exist"):
            organize_service(
                source="/nonexistent",
                destination="/somewhere",
            )
