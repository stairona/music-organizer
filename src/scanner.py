"""
File scanner – discovers audio files and prepares them for processing.
"""

import os
from typing import List, Tuple

from .tags import get_audio_files


def scan_source_directory(src_dir: str, limit: int = None, debug: bool = False) -> List[str]:
    """
    Scan the source directory and return a list of audio file paths.

    Args:
        src_dir: Root directory to scan recursively.
        limit: Optional maximum number of files to return (for testing).
        debug: Enable debug output.

    Returns:
        List of absolute file paths (strings).
    """
    if not os.path.isdir(src_dir):
        raise NotADirectoryError(f"Source directory does not exist: {src_dir}")

    if debug:
        print(f"[DEBUG] Scanning {src_dir} for audio files...")

    files = get_audio_files(src_dir, limit=limit, debug=debug)

    if debug:
        print(f"[DEBUG] Found {len(files)} audio file(s).")

    return files


def is_inside_dest(src_path: str, dest_dir: str) -> bool:
    """
    Check if a source path is already inside the destination directory.
    This prevents recursively processing files that were already moved/copied.
    """
    src_real = os.path.realpath(src_path)
    dest_real = os.path.realpath(dest_dir)
    return src_real.startswith(dest_real + os.sep) or src_real == dest_real
