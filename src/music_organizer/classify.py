"""
Genre classification engine.

Applies the fallback strategy:
1. Embedded metadata tags (via tags.read_genre)
2. Source folder names (path components)
3. Filename keywords
4. Unknown

Also handles general vs specific classification levels.
"""

import json
import os
import re
import logging
from typing import Dict, List, Optional, Tuple

from .tags import read_genre, get_audio_format
from .rules import (
    SPECIFIC_GENRES_LOWER,
    PATH_KEYWORDS,
    GENERAL_MAP,
    genre_matches_keyword,
)

logger = logging.getLogger(__name__)

# Cache for custom genre mappings loaded from config file
_CUSTOM_GENRES_CACHE: Optional[Dict[str, str]] = None


def normalize_genre_string(genre: str) -> str:
    """
    Clean up a raw genre string: trim, lowercase, remove extra punctuation.
    """
    if not genre:
        return ""
    # Remove brackets, quotes, parentheses content if they're just decoration
    genre = re.sub(r'[\(\[].*?[\)\]]', '', genre)  # Remove parentheticals
    genre = genre.strip(" '\".,;:/\\-—_")
    return genre


def _get_custom_genres() -> Dict[str, str]:
    """
    Load custom genre mappings from the config file.
    Uses a cache to avoid repeated disk I/O.
    Returns a dict mapping lowercase keywords to genre names.
    """
    global _CUSTOM_GENRES_CACHE
    if _CUSTOM_GENRES_CACHE is not None:
        return _CUSTOM_GENRES_CACHE

    # Build config path (same logic as in config.py)
    config_dir = os.path.join(
        os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
        "music-organizer",
    )
    config_path = os.path.join(config_dir, "config.json")

    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            custom = config.get("custom_genres", {})
            # Normalize keys to lowercase for case-insensitive matching
            _CUSTOM_GENRES_CACHE = {k.lower(): v for k, v in custom.items()}
        else:
            _CUSTOM_GENRES_CACHE = {}
    except Exception:
        # Any error (permission, parse, etc.) results in empty mapping
        _CUSTOM_GENRES_CACHE = {}

    return _CUSTOM_GENRES_CACHE


def infer_genre_from_path(path: str) -> Optional[str]:
    """
    Try to detect genre from folder names and filename keywords.
    Uses word-boundary regex matching to avoid false positives.
    Prefers longer (more specific) keyword matches when multiple overlap.
    Checks custom genre mappings first (from config), then falls back to built-in rules.
    Returns a specific genre if confident, else None.
    """
    # Lowercase and normalize common separators to spaces so multi-word keywords match
    # e.g., "deep_house" -> "deep house"
    path_lower = path.lower()
    # Replace separators with spaces: underscores, hyphens, dots, commas, semicolons, parentheses, brackets
    path_normalized = re.sub(r'[_\-\.,;\(\)\[\]]', ' ', path_lower)

    # 1. Check custom genres first (takes priority)
    custom_genres = _get_custom_genres()
    if custom_genres:
        custom_matches: List[Tuple[str, int]] = []
        for keyword, mapped_genre in custom_genres.items():
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, path_normalized):
                custom_matches.append((mapped_genre, len(keyword)))
        if custom_matches:
            # Sort by keyword length descending (most specific first), then alphabetically
            custom_matches.sort(key=lambda x: (-x[1], x[0]))
            return custom_matches[0][0]

    # 2. Fallback to built-in PATH_KEYWORDS
    matches: List[Tuple[str, int]] = []
    for keyword, mapped_genre in PATH_KEYWORDS.items():
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, path_normalized):
            matches.append((mapped_genre, len(keyword)))

    if not matches:
        return None

    # Sort by keyword length descending (most specific first), then alphabetically
    matches.sort(key=lambda x: (-x[1], x[0]))
    return matches[0][0]


def classify_file(
    filepath: str,
    level: str = "general",
    debug: bool = False,
    _force_metadata_genre: Optional[str] = None,
) -> Tuple[str, str, str]:
    """
    Classify a single audio file.

    Args:
        filepath: Absolute path to the audio file.
        level: "general", "specific", or "both". Determines output specificity.
        debug: Enable debug output.
        _force_metadata_genre: For testing; bypass actual tag reading.

    Returns:
        (specific_genre, general_genre, reason)
        reason is one of: "metadata", "path", "filename", "unknown"
    """
    reason = "unknown"
    specific = None
    general = "Other / Unknown"

    # 1. Check embedded metadata
    if _force_metadata_genre is not None:
        raw_meta = _force_metadata_genre
    else:
        raw_meta = read_genre(filepath, debug=debug)

    if raw_meta:
        normalized = normalize_genre_string(raw_meta)
        if normalized:
            matches = genre_matches_keyword(normalized)
            if matches:
                # If multiple matches, pick the first
                specific = matches[0]
                reason = "metadata"
                if debug:
                    logger.debug(f"{filepath}: metadata gave {specific} (from '{raw_meta}')")

    # 2. Fallback: path/folder name inference
    if not specific:
        specific = infer_genre_from_path(filepath)
        if specific:
            reason = "path"
            if debug:
                logger.debug(f"{filepath}: path inference gave {specific}")

    # 3. If still unresolved, mark as Unknown
    if not specific:
        specific = "Unknown"
        reason = "unknown"

    # Determine general bucket
    if specific != "Unknown":
        general = GENERAL_MAP.get(specific, "Other / Unknown")
    else:
        general = "Other / Unknown"

    return specific, general, reason
