"""
Reporting utilities: CSV logs and terminal summary.
"""

import csv
import logging
import os
import re
from collections import Counter
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_UNKNOWN_TOKEN_STOPWORDS = {
    "the", "and", "feat", "ft", "featuring", "original", "mix", "radio",
    "edit", "remix", "extended", "version", "official", "audio", "with",
    "from", "for", "your", "you", "are", "this", "that", "out", "mp3",
    "flac", "wav", "aiff", "aac", "ogg", "m4a", "track", "song"
}


def summarize_unknown_tokens(paths: List[str], limit: int = 10) -> List[tuple[str, int]]:
    """Extract frequent filename tokens from unknown files for mapping/debugging."""
    tokens: Counter = Counter()
    for path in paths:
        name = os.path.basename(path).lower()
        name = re.sub(r'\.[a-z0-9]+$', '', name)
        name = re.sub(r'[^a-z0-9]+', ' ', name)
        for token in name.split():
            if len(token) < 3 or token in _UNKNOWN_TOKEN_STOPWORDS or token.isdigit():
                continue
            tokens[token] += 1
    return tokens.most_common(limit)


def summarize_unknown_artifacts(paths: List[str]) -> Dict[str, int]:
    """Return counts for common filename artifacts seen in unknown files."""
    counts: Counter = Counter()
    for path in paths:
        basename = os.path.basename(path).lower()
        if "{ext}" in basename:
            counts["placeholder_ext"] += 1
        if "getmp3" in basename:
            counts["getmp3"] += 1
        if basename.startswith("._"):
            counts["appledouble"] += 1
    return dict(counts)


def write_csv_report(
    csv_path: str,
    records: List[Dict[str, str]],
    debug: bool = False,
) -> None:
    """
    Write a CSV file with columns:
    source_path, detected_specific_genre, detected_general_genre,
    classification_reason, destination_path
    """
    if not csv_path:
        return

    fieldnames = [
        "source_path",
        "detected_specific_genre",
        "detected_general_genre",
        "classification_reason",
        "destination_path",
    ]

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    logger.debug(f"CSV report written to: {csv_path}")


def print_summary(
    total: int,
    processed: int,
    moved_or_copied: int,
    unknown_count: int,
    reason_counts: Dict[str, int],
    specific_counter: Counter,
    general_counter: Counter,
    unknown_sources: Optional[List[str]] = None,
    skipped_counts: Optional[Dict[str, int]] = None,
) -> None:
    """
    Print a concise summary to the terminal using logging.
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("Music Organizer Summary")
    logger.info("=" * 60)
    logger.info(f"Total files scanned:        {total}")
    logger.info(f"Successfully processed:     {processed}")
    logger.info(f"Moved/Copied:               {moved_or_copied}")
    logger.info(f"Unclassified (Unknown):     {unknown_count}")
    if skipped_counts:
        logger.info("\nSkipped files:")
        for reason, count in sorted(skipped_counts.items()):
            logger.info(f"  {reason}: {count}")
    logger.info("\nClassification reasons:")
    for reason, count in sorted(reason_counts.items()):
        logger.info(f"  {reason}: {count}")

    logger.info("\nTop General Genres:")
    for genre, cnt in general_counter.most_common(10):
        logger.info(f"  {genre}: {cnt}")

    logger.info("\nTop Specific Genres:")
    for genre, cnt in specific_counter.most_common(10):
        logger.info(f"  {genre}: {cnt}")
    if unknown_sources:
        logger.info("\nUnknown diagnostics:")
        artifacts = summarize_unknown_artifacts(unknown_sources)
        for name, count in sorted(artifacts.items()):
            logger.info(f"  {name}: {count}")
        top_tokens = summarize_unknown_tokens(unknown_sources)
        if top_tokens:
            logger.info("\nTop Unknown Filename Tokens:")
            for token, count in top_tokens:
                logger.info(f"  {token}: {count}")
    logger.info("=" * 60)
