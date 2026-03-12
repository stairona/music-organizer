"""
Reporting utilities: CSV logs and terminal summary.
"""

import csv
import logging
from collections import Counter
from typing import Dict, List

logger = logging.getLogger(__name__)


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
    logger.info("\nClassification reasons:")
    for reason, count in sorted(reason_counts.items()):
        logger.info(f"  {reason}: {count}")

    logger.info("\nTop General Genres:")
    for genre, cnt in general_counter.most_common(10):
        logger.info(f"  {genre}: {cnt}")

    logger.info("\nTop Specific Genres:")
    for genre, cnt in specific_counter.most_common(10):
        logger.info(f"  {genre}: {cnt}")
    logger.info("=" * 60)
