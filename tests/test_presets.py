"""
Tests for DJ presets.
"""

import pytest
from music_organizer.presets import PRESETS, get_preset


class TestPresetsDefinitions:
    """Verify that all required presets exist and have correct structure."""

    REQUIRED_PRESETS = ["club", "latin", "open-format", "festival"]

    def test_all_presets_exist(self):
        for name in self.REQUIRED_PRESETS:
            assert name in PRESETS, f"Missing preset: {name}"

    def test_each_preset_has_required_keys(self):
        for name, preset in PRESETS.items():
            assert "level" in preset, f"Preset {name} missing 'level'"
            assert "profile" in preset, f"Preset {name} missing 'profile'"
            assert "description" in preset, f"Preset {name} missing 'description'"

    def test_level_values_are_valid(self):
        valid_levels = ("general", "specific", "both")
        for name, preset in PRESETS.items():
            assert preset["level"] in valid_levels, \
                f"Preset {name} has invalid level: {preset['level']}"

    def test_profile_values_are_valid(self):
        valid_profiles = ("default", "cdj-safe")
        for name, preset in PRESETS.items():
            assert preset["profile"] in valid_profiles, \
                f"Preset {name} has invalid profile: {preset['profile']}"

    def test_specific_preset_defaults(self):
        # Club
        assert PRESETS["club"]["level"] == "specific"
        assert PRESETS["club"]["profile"] == "cdj-safe"
        # Latin
        assert PRESETS["latin"]["level"] == "specific"
        assert PRESETS["latin"]["profile"] == "default"
        # Open-format
        assert PRESETS["open-format"]["level"] == "general"
        assert PRESETS["open-format"]["profile"] == "default"
        # Festival
        assert PRESETS["festival"]["level"] == "specific"
        assert PRESETS["festival"]["profile"] == "cdj-safe"


class TestGetPreset:
    def test_get_preset_returns_correct_dict(self):
        for name in TestPresetsDefinitions.REQUIRED_PRESETS:
            preset = get_preset(name)
            assert preset == PRESETS[name]

    def test_get_preset_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            get_preset("nonexistent")

    def test_get_preset_case_insensitive_keys(self):
        # Although choices are fixed, the function expects exact lowercase name
        # Our PRESETS keys are exact strings, not case-insensitive
        # So 'Club' (capital) should raise
        with pytest.raises(ValueError):
            get_preset("Club")
