"""
Tests for reporting helpers.
"""

from music_organizer.reporting import summarize_unknown_artifacts, summarize_unknown_tokens


def test_summarize_unknown_artifacts_counts_known_patterns():
    paths = [
        "/music/A Fire Inside Of Me.{ext}.mp3",
        "/music/AL037_-_Fideles_-_Wave_Rider_(getmp3.pro).mp3",
        "/music/._song.mp3",
    ]

    result = summarize_unknown_artifacts(paths)
    assert result["placeholder_ext"] == 1
    assert result["getmp3"] == 1
    assert result["appledouble"] == 1


def test_summarize_unknown_tokens_surfaces_meaningful_terms():
    paths = [
        "/music/latin house anthem.{ext}.mp3",
        "/music/latin house club mix.mp3",
        "/music/house session.mp3",
    ]

    result = dict(summarize_unknown_tokens(paths, limit=5))
    assert result["house"] == 3
    assert result["latin"] == 2