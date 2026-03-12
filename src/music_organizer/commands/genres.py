"""
genres command — display all supported genres and their bucket mappings.
"""

from ..rules import GENERAL_BUCKETS, SPECIFIC_GENRES, GENERAL_MAP


def run_genres(args) -> None:
    """Print supported genres grouped by general bucket."""
    bucket_filter = args.bucket.lower() if args.bucket else None

    # Build bucket → specific list
    buckets = {b: [] for b in GENERAL_BUCKETS}
    for genre in SPECIFIC_GENRES:
        bucket = GENERAL_MAP.get(genre, "Other / Unknown")
        buckets[bucket].append(genre)

    for bucket, genres in buckets.items():
        if bucket_filter and bucket_filter not in bucket.lower():
            continue
        print(f"\n  {bucket}")
        print(f"  {'─' * len(bucket)}")
        if genres:
            for g in sorted(genres):
                print(f"    {g}")
        else:
            print("    (no specific genres)")

    total = len(SPECIFIC_GENRES)
    print(f"\n  Total: {total} specific genres across {len(GENERAL_BUCKETS)} buckets\n")
