"""
Reporting utilities: CSV logs and terminal summary.
"""

import csv
import sys
from collections import Counter
from typing import Dict, List, Tuple


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

    if debug:
        print(f"[DEBUG] CSV report written to: {csv_path}")


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
    Print a concise summary to the terminal.
    """
    print("\n" + "=" * 60)
    print("Music Organizer Summary")
    print("=" * 60)
    print(f"Total files scanned:        {total}")
    print(f"Successfully processed:     {processed}")
    print(f"Moved/Copied:               {moved_or_copied}")
    print(f"Unclassified (Unknown):     {unknown_count}")
    print("\nClassification reasons:")
    for reason, count in sorted(reason_counts.items()):
        print(f"  {reason}: {count}")

    print("\nTop General Genres:")
    for genre, cnt in general_counter.most_common(10):
        print(f"  {genre}: {cnt}")

    print("\nTop Specific Genres:")
    for genre, cnt in specific_counter.most_common(10):
        print(f"  {genre}: {cnt}")
    print("=" * 60)
