"""
File operations: copy or move files to destination while handling collisions.

Ensures:
- Destination directories are created safely.
- Filename collisions are resolved by appending (1), (2), etc.
- No accidental overwrites.
- No recursive processing into destination folders.
"""

import os
import re
import shutil
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str, max_length: int = 60) -> str:
    """
    Sanitize a filename for CDJ safety.

    - Removes special characters (anything not alphanumeric, space, hyphen, underscore, or period).
    - Preserves file extension.
    - Shortens to max_length (total including extension).
    - Strips leading/trailing whitespace and dots from the name part.
    - Also strips whitespace from the extension.

    Args:
        filename: Original filename.
        max_length: Maximum total filename length (default 60).

    Returns:
        Sanitized filename.
    """
    # Strip leading/trailing whitespace from the whole filename
    filename = filename.strip()

    # Separate name and extension
    name, ext = os.path.splitext(filename)

    # Remove special characters from name: keep alphanumeric, space, hyphen, underscore, period.
    # Delete any character not in allowed set.
    allowed_pattern = r'[^a-zA-Z0-9\s\-_.]'
    name = re.sub(allowed_pattern, '', name)

    # Strip leading/trailing whitespace and dots from name
    name = name.strip(' .')

    # If empty after sanitization, use a default
    if not name:
        name = "untitled"

    # Also ensure extension is free of whitespace (strip) and remove any disallowed chars (keep dot and alphanum)
    # ext starts with '.'; we want to keep dot and alphanumeric (maybe also allow other safe chars? but typically just alnum)
    # Remove whitespace from extension
    ext = ext.strip()
    # Remove disallowed characters from extension (keep dot and alphanumeric)
    ext = re.sub(r'[^a-zA-Z0-9\.]', '', ext)
    # Ensure extension still has a dot; if empty, set to '.mp3'? But unlikely.

    # Combine and enforce length
    combined = name + ext
    if len(combined) > max_length:
        # Truncate name to fit max_length - len(ext)
        allowed_name_len = max_length - len(ext)
        if allowed_name_len <= 0:
            # Extension itself is longer than max_length; truncate extension
            combined = combined[:max_length]
        else:
            name = name[:allowed_name_len]
            combined = name + ext

    return combined


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
    profile: str = "default",
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
        profile: Output profile ("default" or "cdj-safe").

    Returns:
        Full destination file path (may be modified for uniqueness later).
    """
    filename = os.path.basename(src_file)

    # Apply CDJ-safe sanitization if profile is cdj-safe
    if profile == "cdj-safe":
        filename = sanitize_filename(filename, max_length=60)

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

    # CDJ-safe: enforce folder depth limit of 3 levels
    if profile == "cdj-safe":
        rel_dir = os.path.relpath(dest_dir, dest_root)
        if rel_dir != '.':
            components = rel_dir.split(os.sep)
            if len(components) > 3:
                # Truncate to first 3 components
                new_rel = os.path.join(*components[:3])
                new_dest_dir = os.path.join(dest_root, new_rel)
                logger.warning(f"CDJ-safe: Folder depth exceeds 3 levels; truncating: {rel_dir} -> {new_rel}")
                dest_dir = new_dest_dir

    dest_path = os.path.join(dest_dir, filename)

    # CDJ-safe warnings
    if profile == "cdj-safe":
        # Check full path length (absolute path)
        full_path = os.path.abspath(dest_path)
        if len(full_path) > 180:
            logger.warning(f"CDJ-safe: Path exceeds 180 characters ({len(full_path)}): {full_path}")

    if create_dirs:
        ensure_dir_exists(dest_dir)
    return dest_path


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
