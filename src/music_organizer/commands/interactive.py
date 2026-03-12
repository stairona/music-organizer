"""
interactive command — guided DJ workflow with prompts.

Asks the user a series of questions then runs the organize pipeline.
"""

import os
import sys


def _ask(prompt: str, choices: list = None, default: str = None) -> str:
    """Ask a question with optional numbered choices."""
    if choices:
        print(f"\n{prompt}")
        for i, choice in enumerate(choices, 1):
            marker = " (default)" if choice == default else ""
            print(f"  ({i}) {choice}{marker}")
        while True:
            raw = input("> ").strip()
            if not raw and default:
                return default
            try:
                idx = int(raw)
                if 1 <= idx <= len(choices):
                    return choices[idx - 1]
            except ValueError:
                # Allow typing the choice directly
                if raw in choices:
                    return raw
            print(f"Please enter 1-{len(choices)}")
    else:
        suffix = f" [{default}]" if default else ""
        raw = input(f"\n{prompt}{suffix}\n> ").strip()
        return raw if raw else (default or "")


def run_interactive(args) -> None:
    """Launch interactive DJ workflow then delegate to organize."""
    print("\n╔══════════════════════════════════════╗")
    print("║   Music Organizer — DJ Setup Mode    ║")
    print("╚══════════════════════════════════════╝")

    # Source
    source = _ask(
        "Where is your music library?",
        default=getattr(args, "source", None),
    )
    if not source or not os.path.isdir(source):
        print(f"Directory not found: {source}")
        sys.exit(1)

    # Destination
    dest = _ask(
        "Where should the organized library be created?",
        default=getattr(args, "destination", None),
    )
    if not dest:
        print("Destination is required.")
        sys.exit(1)

    # Mode
    mode = _ask(
        "How should files be handled?",
        choices=["copy", "move"],
        default="copy",
    )

    # Level
    level = _ask(
        "Choose organization style:",
        choices=["general", "specific", "both"],
        default="both",
    )

    # Profile
    profile = _ask(
        "Target workflow:",
        choices=["default", "cdj-safe"],
        default="default",
    )

    # Dry run
    dry_run_choice = _ask(
        "Preview only or apply changes?",
        choices=["preview (dry-run)", "apply"],
        default="preview (dry-run)",
    )
    dry_run = "preview" in dry_run_choice

    # Summary
    print("\n─── Summary ───")
    print(f"  Source:      {source}")
    print(f"  Destination: {dest}")
    print(f"  Mode:        {mode}")
    print(f"  Level:       {level}")
    print(f"  Profile:     {profile}")
    print(f"  Dry run:     {dry_run}")
    print("────────────────")

    confirm = input("\nProceed? [Y/n] ").strip().lower()
    if confirm in ("n", "no"):
        print("Cancelled.")
        sys.exit(0)

    # Inject answers into args and run organize
    args.source = source
    args.destination = dest
    args.mode = mode
    args.level = level
    args.profile = profile
    args.dry_run = dry_run
    args.interactive = False  # prevent recursion

    # Ensure optional attrs exist
    if not hasattr(args, "skip_existing"):
        args.skip_existing = False
    if not hasattr(args, "skip_unknown_only"):
        args.skip_unknown_only = False
    if not hasattr(args, "report"):
        args.report = None
    if not hasattr(args, "limit"):
        args.limit = None
    if not hasattr(args, "exclude_dir"):
        args.exclude_dir = None
    if not hasattr(args, "debug"):
        args.debug = False
    if not hasattr(args, "quiet"):
        args.quiet = False

    from .organize import run_organize
    run_organize(args)
