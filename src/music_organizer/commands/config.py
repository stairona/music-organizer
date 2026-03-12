"""
config command — show, initialize, or locate configuration.
"""

import json
import os
import sys

CONFIG_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
    "music-organizer",
)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "mode": "copy",
    "level": "both",
    "profile": "default",
    "collision_policy": "hash",
    "unknown_strategy": ["metadata", "path", "filename"],
    "custom_genres": {},
    "cdj_safe": {
        "max_folder_depth": 3,
        "max_files_per_folder": 500,
        "max_path_length": 180,
        "sanitize_filenames": True,
    },
    "exclude_dirs": [],
}


def run_config(args) -> None:
    """Execute the config subcommand."""
    action = args.config_action

    if action == "path":
        print(CONFIG_PATH)

    elif action == "init":
        if os.path.exists(CONFIG_PATH):
            print(f"Config already exists: {CONFIG_PATH}")
            overwrite = input("Overwrite with defaults? [y/N] ").strip().lower()
            if overwrite not in ("y", "yes"):
                print("Cancelled.")
                sys.exit(0)

        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        print(f"Config created: {CONFIG_PATH}")

    elif action == "show":
        if not os.path.exists(CONFIG_PATH):
            print(f"No config found at {CONFIG_PATH}")
            print("Run 'music-organizer config init' to create one.")
            sys.exit(0)

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        print(json.dumps(config, indent=2))
