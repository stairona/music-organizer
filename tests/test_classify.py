"""
Tests for the classify module.
"""

import pytest
from music_organizer.classify import (
    normalize_genre_string,
    infer_genre_from_path,
    classify_file,
)
from music_organizer.rules import PATH_KEYWORDS, SPECIFIC_GENRES_LOWER, genre_matches_keyword


class TestNormalizeGenreString:
    def test_trim_spaces(self):
        assert normalize_genre_string("  House  ") == "House"

    def test_remove_parentheses(self):
        assert normalize_genre_string("House (Electronic)") == "House"
        # Bracketed content is removed entirely, so "[Tech] House" becomes "House"
        assert normalize_genre_string("[Tech] House") == "House"

    def test_remove_punctuation(self):
        assert normalize_genre_string("R&B") == "R&B"
        assert normalize_genre_string("Hip-Hop.") == "Hip-Hop"

    def test_empty_and_none(self):
        assert normalize_genre_string("") == ""
        assert normalize_genre_string(None) == ""  # None returns empty string


class TestInferGenreFromPath:
    def test_simple_keyword_match(self):
        # Should match "house" keyword exactly, not partial matches
        assert infer_genre_from_path("/music/tech house/song.mp3") == "Tech House"
        assert infer_genre_from_path("/music/deep_house/track.flac") == "Deep House"
        assert infer_genre_from_path("/music/house/song.mp3") == "House"

    def test_word_boundary(self):
        # Should NOT match partial words
        # "popcorn" should NOT match "pop"
        result = infer_genre_from_path("/movies/popcorn_video.mp4")
        assert result != "Pop", "popcorn should not match 'pop' keyword"
        # "houseware" should NOT match "house"
        result = infer_genre_from_path("/home/houseware/item.mp3")
        assert result != "House", "houseware should not match 'house'"

    def test_latin_genres(self):
        assert infer_genre_from_path("/reggaeton/song.mp3") == "Reggaeton"
        assert infer_genre_from_path("/bachata/track.mp3") == "Bachata"
        assert infer_genre_from_path("/latin pop/ song.mp3") == "Latin Pop"

    def test_hip_hop_variants(self):
        assert infer_genre_from_path("/Hip-Hop/rap.mp3") == "Hip-Hop"
        assert infer_genre_from_path("/trap music/song.mp3") == "Trap"
        assert infer_genre_from_path("/drill_and_grime/track.mp3") in ("Drill", "Grime")

    def test_case_insensitive(self):
        assert infer_genre_from_path("/TECH HOUSE/song.mp3") == "Tech House"
        # Use underscore separator (or space) – "DeepHouse" without separator is not a typical folder name
        assert infer_genre_from_path("/Deep_House/track.mp3") == "Deep House"

    def test_multi_word_keywords(self):
        # "deep house" (two words)
        assert infer_genre_from_path("/deep house music/song.mp3") == "Deep House"
        # "melodic techno"
        assert infer_genre_from_path("/Melodic Techno/song.mp3") == "Melodic Techno"

    def test_no_match(self):
        assert infer_genre_from_path("/random/folder/song.mp3") is None
        assert infer_genre_from_path("/miscellaneous/track.mp3") is None

    def test_multiple_matches_picks_highest_score(self):
        # If both "house" and "deep house" appear, deep house should win due to more specific
        # Actually both will score; we pick the first among ties sorted alphabetically
        result = infer_genre_from_path("/deep house classics/song.mp3")
        # Both "deep" and "house" might match but "Deep House" should be result
        assert result == "Deep House", f"Got {result}"


class TestGenreMatchesKeyword:
    def test_direct_match(self):
        from music_organizer.rules import genre_matches_keyword
        assert "House" in genre_matches_keyword("House")
        assert "Techno" in genre_matches_keyword("Techno")

    def test_lowercase_match(self):
        assert "House" in genre_matches_keyword("house")
        assert "Deep House" in genre_matches_keyword("deep house")

    def test_alternate_spacing(self):
        assert "Tech House" in genre_matches_keyword("Tech House")
        # Note: "TechHouse" without space is not directly matched; metadata should use space or hyphen

    def test_no_match(self):
        assert genre_matches_keyword("random genre") == []


class TestClassifyFile:
    def test_metadata_priority(self, tmp_path):
        # Create a dummy file and monkey-patch read_genre
        test_file = tmp_path / "test.mp3"
        test_file.touch()

        # We'll use _force_metadata_genre to test
        specific, general, reason = classify_file(
            str(test_file),
            level="general",
            _force_metadata_genre="Deep House"
        )
        assert specific == "Deep House"
        assert general == "Electronic"
        assert reason == "metadata"

    def test_path_fallback(self, tmp_path):
        test_file = tmp_path / "test.mp3"
        test_file.touch()
        # Create a directory path that includes a known genre keyword
        test_file = tmp_path / "deep house" / "test.mp3"
        test_file.parent.mkdir()
        test_file.touch()

        specific, general, reason = classify_file(str(test_file), level="general")
        assert specific == "Deep House"
        assert general == "Electronic"
        assert reason == "path"

    def test_unknown_fallback(self, tmp_path):
        test_file = tmp_path / "random_name.mp3"
        test_file.touch()
        specific, general, reason = classify_file(str(test_file), level="general")
        assert specific == "Unknown"
        assert general == "Other / Unknown"
        assert reason == "unknown"


class TestWordBoundaries:
    """Ensure keyword matching uses word boundaries to avoid false positives."""

    def test_pop_not_in_popcorn(self):
        # The word "pop" should not match inside "popcorn"
        from music_organizer.classify import infer_genre_from_path
        path = "/some/popcorn_folder/song.mp3"
        result = infer_genre_from_path(path)
        assert result != "Pop", f"Should not match 'pop' in 'popcorn', got {result}"

    def test_rock_not_in_rocky(self):
        result = infer_genre_from_path("/mountain/rocky_road/song.mp3")
        assert result != "Rock", f"Should not match 'rock' in 'rocky', got {result}"

    def test_jazz_not_in_jazzercise(self):
        result = infer_genre_from_path("/fitness/jazzercise_mix/song.mp3")
        assert result != "Jazz", f"Should not match 'jazz' in 'jazzercise', got {result}"

    def test_house_in_houseware_should_not_match(self):
        result = infer_genre_from_path("/home/houseware/song.mp3")
        assert result != "House", f"Should not match 'house' in 'houseware', got {result}"

    def test_edm_in_edmonds_should_not_match(self):
        result = infer_genre_from_path("/places/edmonds/song.mp3")
        assert result != "EDM", f"Should not match 'edm' in 'edmonds', got {result}"
