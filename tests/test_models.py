"""
Tests for backend API models.
"""

import pytest
from pydantic import ValidationError
from app.backend.models import (
    AnalyzeRequest,
    OrganizeRequest,
    RunSummary,
    UnknownDiagnostics,
    AnalyzeResult,
    OrganizeResult,
    ProgressEvent,
)


class TestAnalyzeRequest:
    def test_valid_request(self):
        req = AnalyzeRequest(source="/music", level="specific")
        assert req.source == "/music"
        assert req.level == "specific"

    def test_default_level(self):
        req = AnalyzeRequest(source="/music")
        assert req.level == "general"

    def test_invalid_level(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(source="/music", level="invalid")


class TestOrganizeRequest:
    def test_valid_request(self):
        req = OrganizeRequest(
            source="/music",
            destination="/organized",
            mode="move",
            level="both",
            profile="cdj-safe",
        )
        assert req.source == "/music"
        assert req.destination == "/organized"
        assert req.mode == "move"
        assert req.profile == "cdj-safe"

    def test_defaults(self):
        req = OrganizeRequest(source="/music", destination="/organized")
        assert req.mode == "copy"
        assert req.level == "general"
        assert req.profile == "default"
        assert req.dry_run is False
        assert req.skip_existing is False

    def test_invalid_mode(self):
        with pytest.raises(ValidationError):
            OrganizeRequest(source="/music", destination="/organized", mode="invalid")

    def test_invalid_profile(self):
        with pytest.raises(ValidationError):
            OrganizeRequest(source="/music", destination="/organized", profile="invalid")


class TestRunSummary:
    def test_valid_summary(self):
        summary = RunSummary(
            total=100,
            processed=95,
            moved_or_copied=80,
            unknown_count=5,
            reason_counts={"metadata": 60, "path": 30, "unknown": 10},
            specific_counter={"House": 40, "Techno": 30, "Unknown": 30},
            general_counter={"Electronic": 70, "Other / Unknown": 30},
            skipped_counts={"skipped-existing": 5},
        )
        assert summary.total == 100
        assert summary.skipped_counts is not None


class TestUnknownDiagnostics:
    def test_valid(self):
        diag = UnknownDiagnostics(
            count=5, sample_paths=["/path1.mp3", "/path2.mp3"]
        )
        assert diag.count == 5
        assert len(diag.sample_paths) == 2

    def test_empty_samples(self):
        diag = UnknownDiagnostics(count=0)
        assert diag.sample_paths == []


class TestAnalyzeResult:
    def test_valid_result(self):
        summary = RunSummary(
            total=10,
            processed=10,
            moved_or_copied=0,
            unknown_count=2,
            reason_counts={"metadata": 8, "path": 0, "unknown": 2},
            specific_counter={"House": 8},
            general_counter={"Electronic": 8},
        )
        result = AnalyzeResult(
            success=True, summary=summary, csv_report_path="/report.csv"
        )
        assert result.success is True
        assert result.csv_report_path == "/report.csv"


class TestOrganizeResult:
    def test_valid_result(self):
        summary = RunSummary(
            total=10,
            processed=10,
            moved_or_copied=8,
            unknown_count=2,
            reason_counts={"metadata": 8, "path": 0, "unknown": 2},
            specific_counter={"House": 8},
            general_counter={"Electronic": 8},
        )
        result = OrganizeResult(
            success=True,
            summary=summary,
            journal_saved=True,
            warnings=["CDJ-safe: Folder exceeds 500 files..."],
        )
        assert result.journal_saved is True
        assert len(result.warnings) == 1


class TestProgressEvent:
    def test_valid_progress_event(self):
        event = ProgressEvent(
            event_type="classification_progress", data={"current": 50, "total": 100}
        )
        assert event.event_type == "classification_progress"
        assert event.data["current"] == 50
