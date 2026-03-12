#!/usr/bin/env python3
"""
Music Organizer CLI — subcommand-based entry point.

Subcommands:
  analyze   Scan library and show genre distribution (no file changes)
  organize  Organize files into genre folders (copy or move)
  genres    Show supported genres and mappings
  undo      Revert the last organize operation using journal
  config    Show or initialize configuration
"""

import argparse
import sys

from . import __version__


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments shared between analyze and organize."""
    parser.add_argument(
        "source",
        help="Root folder of the music library to scan.",
    )
    parser.add_argument(
        "--level",
        choices=["general", "specific", "both"],
        default="general",
        help="Genre classification level (default: general).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of files to process (useful for testing).",
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        metavar="DIR",
        help="Directory names to skip. Can be used multiple times.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show detailed classification decisions.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress informational output; show only summary and errors.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="music-organizer",
        description="DJ-grade music library organizer. Classifies and organizes audio files by genre.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- analyze ---
    p_analyze = subparsers.add_parser(
        "analyze",
        help="Scan library and show genre distribution without moving files.",
    )
    _add_common_args(p_analyze)
    p_analyze.add_argument(
        "--report",
        metavar="CSV_PATH",
        help="Write a CSV report of classification decisions.",
    )

    # --- organize ---
    p_organize = subparsers.add_parser(
        "organize",
        help="Organize files into genre folders.",
    )
    _add_common_args(p_organize)
    p_organize.add_argument(
        "destination",
        help="Destination root where genre folders will be created.",
    )
    p_organize.add_argument(
        "--mode",
        choices=["copy", "move"],
        default="copy",
        help="File operation: copy (default, safe) or move.",
    )
    p_organize.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would happen without touching files.",
    )
    p_organize.add_argument(
        "--report",
        metavar="CSV_PATH",
        help="Write a CSV report of each processed file.",
    )
    p_organize.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip files that already exist at the destination.",
    )
    p_organize.add_argument(
        "--skip-unknown-only",
        action="store_true",
        help="Process only files classified as Unknown.",
    )
    p_organize.add_argument(
        "--profile",
        choices=["default", "cdj-safe"],
        default="default",
        help="Output profile. cdj-safe shortens names and limits folder depth.",
    )
    p_organize.add_argument(
        "--interactive",
        action="store_true",
        help="Launch guided DJ workflow with prompts.",
    )

    # --- genres ---
    p_genres = subparsers.add_parser(
        "genres",
        help="Show all supported genres and their bucket mappings.",
    )
    p_genres.add_argument(
        "--bucket",
        metavar="NAME",
        help="Filter to a specific general bucket (e.g. Electronic, Latin).",
    )

    # --- undo ---
    subparsers.add_parser(
        "undo",
        help="Revert the last organize operation using the journal.",
    )

    # --- config ---
    p_config = subparsers.add_parser(
        "config",
        help="Show or initialize configuration.",
    )
    p_config.add_argument(
        "config_action",
        nargs="?",
        choices=["init", "show", "path"],
        default="show",
        help="Config action: init (create default), show (display current), path (print config location).",
    )

    return parser


def cli_main(argv: list = None) -> None:
    """Entry point for the music-organizer command."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    # Import handlers lazily to keep startup fast
    if args.command == "analyze":
        from .commands.analyze import run_analyze
        run_analyze(args)

    elif args.command == "organize":
        from .commands.organize import run_organize
        run_organize(args)

    elif args.command == "genres":
        from .commands.genres import run_genres
        run_genres(args)

    elif args.command == "undo":
        from .commands.undo import run_undo
        run_undo(args)

    elif args.command == "config":
        from .commands.config import run_config
        run_config(args)
