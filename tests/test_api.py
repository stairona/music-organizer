"""
Tests for FastAPI backend scaffolding.
"""

from fastapi.testclient import TestClient

from app.backend.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_endpoint_bad_source_returns_400():
    response = client.post(
        "/api/v1/analyze",
        json={"source": "/nonexistent/path", "level": "specific"},
    )
    assert response.status_code == 400
    assert "Source directory does not exist" in response.json()["detail"]


def test_organize_endpoint_passes_collision_fields(tmp_path, monkeypatch):
    captured = {}

    def fake_organize_service(**kwargs):
        captured.update(kwargs)
        return {
            "success": True,
            "summary": {
                "total": 0,
                "processed": 0,
                "moved_or_copied": 0,
                "unknown_count": 0,
                "reason_counts": {},
                "specific_counter": {},
                "general_counter": {},
                "skipped_counts": {},
            },
            "unknown_diagnostics": {"count": 0, "sample_paths": []},
            "csv_report_path": None,
            "journal_saved": False,
            "warnings": [],
        }

    monkeypatch.setattr("app.backend.routes.organize_service", fake_organize_service)

    response = client.post(
        "/api/v1/organize",
        json={
            "source": str(tmp_path / "src"),
            "destination": str(tmp_path / "dst"),
            "skip_unknown_only": True,
            "on_collision": "rename",
        },
    )

    assert response.status_code == 200
    assert captured["skip_unknown_only"] is True
    assert captured["on_collision"] == "rename"