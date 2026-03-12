"""
File scanner – discovers audio files and prepares them for processing.
"""

import os
import logging
from typing import List, Optional

from .tags import get_audio_files

logger = logging.getLogger(__name__)


def scan_source_directory(
    src_dir: str,
    limit: Optional[int] = None,
    debug: bool = False,
    exclude_dirs: Optional[List[str]] = None,
) -> List[str]:
    """
    Scan the source directory and return a list of audio file paths.

    Args:
        src_dir: Root directory to scan recursively.
        limit: Optional maximum number of files to return (for testing).
        debug: Enable debug output.
        exclude_dirs: List of directory names to exclude (e.g., ['temp', 'incomplete']).

    Returns:
        List of absolute file paths (strings).
    """
    if not os.path.isdir(src_dir):
        raise NotADirectoryError(f"Source directory does not exist: {src_dir}")

    if debug:
        logger.debug(f"Scanning {src_dir} for audio files...")
        if exclude_dirs:
            logger.debug(f"Excluding directories: {exclude_dirs}")

    files = get_audio_files(src_dir, limit=limit, debug=debug, exclude_dirs=exclude_dirs)

    if debug:
        logger.debug(f"Found {len(files)} audio file(s).")

    return files


def is_inside_dest(src_path: str, dest_dir: str) -> bool:
    """
    Check if a source path is already inside the destination directory.
    This prevents recursively processing files that were already moved/copied.
    """
    src_real = os.path.realpath(src_path)
    dest_real = os.path.realpath(dest_dir)
    return src_real.startswith(dest_real + os.sep) or src_real == dest_real
