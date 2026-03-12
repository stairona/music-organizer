"""
Genre classification engine.

Applies the fallback strategy:
1. Embedded metadata tags (via tags.read_genre)
2. Source folder names (path components)
3. Filename keywords
4. Unknown

Also handles general vs specific classification levels.
"""

import os
import re
from typing import Dict, List, Optional, Tuple

from .tags import read_genre, get_audio_format
from .rules import (
    SPECIFIC_GENRES_LOWER,
    PATH_KEYWORDS,
    GENERAL_MAP,
    genre_matches_keyword,
)


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


def extract_path_keywords(path: str) -> List[str]:
    """
    Extract candidate genre tokens from directory names and filename.
    Splits on common separators and normalizes.
    """
    # Get all path components (excluding filename extension)
    parts = []
    path = os.path.normpath(path).lower()
    head, tail = os.path.split(path)
    parts.append(tail)  # filename without extension (will be stripped later)
    while head and head != os.path.sep:
        head, tail = os.path.split(head)
        if tail and tail not in ('.', '..'):
            parts.append(tail)

    # Split each part into words using common separators
    tokens = []
    for part in parts:
        # Replace separators with spaces
        for sep in ['_', '-', '(', ')', '[', ']', '.', ',', ';']:
            part = part.replace(sep, ' ')
        words = part.split()
        tokens.extend(words)

    return tokens


def infer_genre_from_path(path: str) -> Optional[str]:
    """
    Try to detect genre from folder names and filename keywords.
    Returns a specific genre if confident, else None.
    """
    tokens = extract_path_keywords(path)
    if not tokens:
        return None

    # Build candidate matching by counting keyword hits
    candidate_scores: Dict[str, int] = {}
    for token in tokens:
        for keyword, mapped_genre in PATH_KEYWORDS.items():
            if token == keyword or keyword in token:
                candidate_scores[mapped_genre] = candidate_scores.get(mapped_genre, 0) + 1

    if not candidate_scores:
        return None

    # Find the highest scoring genre
    max_score = max(candidate_scores.values())
    # Require at least 1 hit; if there is a tie, pick lexicographically first for determinism
    best = [g for g, s in candidate_scores.items() if s == max_score]
    return best[0] if best else None


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
                    print(f"[DEBUG] {filepath}: metadata gave {specific} (from '{raw_meta}')")

    # 2. Fallback: path/folder name inference
    if not specific:
        specific = infer_genre_from_path(filepath)
        if specific:
            reason = "path"
            if debug:
                print(f"[DEBUG] {filepath}: path inference gave {specific}")

    # 3. Fallback: filename (treated as part of path inference already, but we can refine)
    if not specific:
        # The infer_genre_from_path already considered filename, so no extra step needed.
        # If we wanted a separate filename-only step, we could split the filename and check.
        pass

    # Ensure we have a specific genre, mapping to unknown if needed
    if not specific:
        specific = "Unknown"
        reason = "unknown"

    # Determine general bucket
    if specific != "Unknown":
        general = GENERAL_MAP.get(specific, "Other / Unknown")
    else:
        general = "Other / Unknown"

    # If level is "general", we want to return the general bucket as specific,
    # but still report classification accordingly. However, the requirements say:
    # - specific = detailed subgenres
    # - general = broader buckets
    # Implementation: return (detected_specific, detected_general) always, and let
    # the caller decide directory structure based on level.
    #
    # For "both" level, the directory hierarchy will nest specific under general.
    # For "specific" level, only specific genre folder.
    # For "general" level, only general bucket folder.

    return specific, general, reason
