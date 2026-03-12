"""
File operations: copy or move files to destination while handling collisions.

Ensures:
- Destination directories are created safely.
- Filename collisions are resolved by appending (1), (2), etc.
- No accidental overwrites.
- No recursive processing into destination folders.
"""

import os
import shutil
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def ensure_dir_exists(dir_path: str) -> None:
    """Create directory if it doesn't exist (including parents)."""
    os.makedirs(dir_path, exist_ok=True)


def get_unique_dest_path(dest_file: str) -> str:
    """
    Given a desired destination file path, return a unique path if the file exists.
    Appends (1), (2), ... before the extension.
    """
    if not os.path.exists(dest_file):
        return dest_file

    base, ext = os.path.splitext(dest_file)
    i = 1
    while True:
        candidate = f"{base} ({i}){ext}"
        if not os.path.exists(candidate):
            return candidate
        i += 1
        if i > 9999:  # safeguard
            raise RuntimeError(f"Too many duplicates for {dest_file}")


def compute_destination(
    src_file: str,
    dest_root: str,
    specific_genre: str,
    general_genre: str,
    level: str,
    create_dirs: bool = True,
) -> str:
    """
    Compute the destination file path based on classification level.

    Args:
        src_file: Source file path (basename preserved).
        dest_root: Root of destination tree.
        specific_genre: Detected specific genre.
        general_genre: Detected general bucket.
        level: "general", "specific", or "both".
        create_dirs: If True, create destination directories (default). Set False for dry-run/stats-only.

    Returns:
        Full destination file path (may be modified for uniqueness later).
    """
    filename = os.path.basename(src_file)

    if level == "general":
        # organize into general genre folder only
        genre_folder = general_genre
        dest_dir = os.path.join(dest_root, genre_folder)
    elif level == "specific":
        # organize into specific genre folder only
        genre_folder = specific_genre
        dest_dir = os.path.join(dest_root, genre_folder)
    else:  # both
        # nest specific under general
        dest_dir = os.path.join(dest_root, general_genre, specific_genre)

    if create_dirs:
        ensure_dir_exists(dest_dir)
    return os.path.join(dest_dir, filename)


def copy_file(src: str, dest: str, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Copy a file to destination, handling collisions.

    Returns:
        (success, final_dest_path)
    """
    if dry_run:
        return True, dest  # pretend success

    final_dest = get_unique_dest_path(dest)
    try:
        shutil.copy2(src, final_dest)  # copy2 preserves metadata
        return True, final_dest
    except Exception as e:
        logger.error(f"Error copying {src} to {dest}: {e}")
        return False, dest


def move_file(src: str, dest: str, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Move a file to destination, handling collisions.

    Returns:
        (success, final_dest_path)
    """
    if dry_run:
        return True, dest  # pretend success

    final_dest = get_unique_dest_path(dest)
    try:
        shutil.move(src, final_dest)
        return True, final_dest
    except Exception as e:
        logger.error(f"Error moving {src} to {dest}: {e}")
        return False, dest
