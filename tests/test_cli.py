"""
Tests for the new subcommand CLI structure.
"""

import pytest
from music_organizer.cli import build_parser, cli_main


class TestCLIParser:
    def test_no_command_shows_help(self, capsys):
        """Running with no args should print help and exit 0."""
        with pytest.raises(SystemExit) as exc_info:
            cli_main([])
        assert exc_info.value.code == 0

    def test_version(self, capsys):
        with pytest.raises(SystemExit):
            cli_main(["--version"])
        captured = capsys.readouterr()
        assert "2.0.0" in captured.out

    def test_analyze_parser(self):
        parser = build_parser()
        args = parser.parse_args(["analyze", "/tmp/music", "--level", "both"])
        assert args.command == "analyze"
        assert args.source == "/tmp/music"
        assert args.level == "both"

    def test_organize_parser(self):
        parser = build_parser()
        args = parser.parse_args([
            "organize", "/tmp/music", "/tmp/dest",
            "--mode", "move", "--dry-run", "--level", "specific",
        ])
        assert args.command == "organize"
        assert args.source == "/tmp/music"
        assert args.destination == "/tmp/dest"
        assert args.mode == "move"
        assert args.dry_run is True
        assert args.level == "specific"

    def test_organize_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["organize", "/src", "/dst"])
        assert args.mode == "copy"
        assert args.dry_run is False
        assert args.level == "general"
        assert args.profile == "default"

    def test_genres_parser(self):
        parser = build_parser()
        args = parser.parse_args(["genres", "--bucket", "Latin"])
        assert args.command == "genres"
        assert args.bucket == "Latin"

    def test_config_parser(self):
        parser = build_parser()
        args = parser.parse_args(["config", "path"])
        assert args.command == "config"
        assert args.config_action == "path"

    def test_config_default_action(self):
        parser = build_parser()
        args = parser.parse_args(["config"])
        assert args.config_action == "show"

    def test_undo_parser(self):
        parser = build_parser()
        args = parser.parse_args(["undo"])
        assert args.command == "undo"


class TestGenresCommand:
    def test_genres_runs(self, capsys):
        """genres command should print genre list without error."""
        cli_main(["genres"])
        captured = capsys.readouterr()
        assert "Electronic" in captured.out
        assert "House" in captured.out

    def test_genres_bucket_filter(self, capsys):
        cli_main(["genres", "--bucket", "Latin"])
        captured = capsys.readouterr()
        assert "Latin" in captured.out
        assert "Reggaeton" in captured.out
        # Should NOT show Electronic genres
        assert "Techno" not in captured.out


class TestConfigCommand:
    def test_config_path(self, capsys):
        cli_main(["config", "path"])
        captured = capsys.readouterr()
        assert "config.json" in captured.out
