# Music Organizer

Automatically organize large music libraries by genre using embedded metadata, folder names, and filename patterns.

## What Problem Does This Solve?

Manually sorting thousands of music files is impossible. This tool reads audio file metadata, infers genre from folder/filename patterns, and safely copies or moves files into organized folder structures. It handles messy real-world collections and dramatically reduces the amount of music ending up in "Unknown."

## Features

- **Multiple audio format support**: MP3, M4A, AAC, FLAC, OGG, OPUS, WAV, AIFF, WMA
- **Three genre classification levels**:
  - `--level general`: Broad buckets (Electronic, Pop, Latin, etc.)
  - `--level specific`: Detailed subgenres (e.g., Deep House, Reggaeton, Melodic Techno)
  - `--level both`: Nests specific under general (recommended for maximum organization)
- **Aggressive unknown reduction**: Falls back to path/filename keywords when metadata is missing
- **Safe operations**:
  - `--dry-run` preview before any changes
  - `--mode copy` (default) preserves originals
  - `--mode move` relocates files (use with care)
- **Collision handling**: Automatically renames duplicates (e.g., `song (1).mp3`)
- **CSV reporting**: Full log of every decision and destination
- **Performance**: Efficient for libraries with tens of thousands of tracks
- **Debug mode**: See exactly why each file was classified a certain way

## Supported Genres

The tool recognizes 80+ specific genres across 9 general buckets:

- **Electronic**: House, Techno, Trance, Drum And Bass, Dubstep, EDM, etc.
- **Hip-Hop / Rap**: Rap, Trap, Drill, Grime, and regional variants
- **R&B / Soul / Funk**
- **Pop**: Dance Pop, Latin Pop, Hyperpop, etc.
- **Rock / Indie / Metal**
- **Latin**: Reggaeton, Bachata, Salsa, Moombahton, Corridos, etc.
- **Reggae / Dub / Dancehall**
- **Jazz / Blues**
- **Classical / Score**

Unknown files are placed in "Other / Unknown". See `src/rules.py` for the complete genre list.

## Installation

```bash
# Clone and enter
git clone https://github.com/stairona/music-organizer.git
cd music-organizer

# Optional virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt
```

## Basic Usage

```bash
# Dry-run copy into organized structure (safe first step)
python -m music_organizer.scanner "/Volumes/Music/Massive Library" "/Volumes/Organized Music" --dry-run --level both

# Actually copy files (default mode)
python -m music_organizer.scanner "/Volumes/Music/Massive Library" "/Volumes/Organized Music" --mode copy --level both

# Move instead of copy (irreversible, use with caution)
python -m music_organizer.scanner "/Volumes/Music/Massive Library" "/Volumes/Organized Music" --mode move --level both

# Generate a CSV report
python -m music_organizer.scanner "/src" "/dest" --mode copy --level both --report "organization_log.csv"

# Process only the Unknown files (after initial run)
python -m music_organizer.scanner "/src" "/dest" --mode copy --level both --skip-unknown-only

# Limit to first 100 files for quick testing
python -m music_organizer.scanner "/src" "/dest" --mode copy --limit 100

# Enable debug output to see classification decisions
python -m music_organizer.scanner "/src" "/dest" --mode copy --debug
```

## Recommended First Command (Safe Dry-Run)

**macOS**:

```bash
cd /Users/nicolasaguirre/Development/light-projects/music-organizer
python -m music_organizer.scanner "/Volumes/YourMusic" "/Volumes/OrganizedMusic" --dry-run --level both --report "dry_run_report.csv"
```

This will:
- Scan your music library without touching any files
- Show how files would be classified and where they would go
- Generate `dry_run_report.csv` with complete details
- Print a summary of proposed organization

Review the CSV and summary before running for real.

## Output Structure

```
/destination/
├── Electronic/
│   ├── Deep House/
│   ├── Progressive House/
│   ├── Techno/
│   └── ...
├── Pop/
│   ├── Dance Pop/
│   └── Pop/
├── Latin/
│   ├── Reggaeton/
│   ├── Bachata/
│   └── ...
└── Other Unknown/
    └── Unknown/
```

For `--level both`, the hierarchy is: `General/Specific/`. For `--level general` it's `General/`. For `--level specific` it's `Specific/`.

## How It Works

1. **Metadata extraction**: Uses `mutagen` to read embedded ID3/vorbis/MP4 tags.
2. **Keyword inference**: If metadata is missing, blank, or too vague, scans parent folder names and filename for known genre keywords (e.g., "techno", "reggaeton", "house").
3. **Conservative defaults**: Only assigns a specific genre if confidence is high. Ambiguous cases go to "Unknown" rather than guessing wrong.
4. **Collision handling**: Duplicate filenames in a genre folder get `(1)`, `(2)` appended automatically.
5. **Recursion guard**: Will not process files already inside the destination tree.

## Advanced: Improving Unknown Rate

If too many files end up Unknown:

1. Run with `--debug` to see exactly which files are unknown and why.
2. Use `--skip-unknown-only` to process only the unknown files after initial pass.
3. Extend `src/rules.py` – add keywords to `PATH_KEYWORDS` or specific genres to `SPECIFIC_GENRES`.
4. Re-run with `--mode copy` to a new destination or after manual review.

## Project Structure

```
music-organizer/
├── src/
│   ├── main.py           # CLI entry point
│   ├── scanner.py        # File discovery
│   ├── tags.py           # Metadata reading (mutagen)
│   ├── classify.py       # Genre inference engine
│   ├── rules.py          # Genre definitions & mappings
│   ├── fileops.py        # Copy/move with collision handling
│   └── reporting.py      # CSV + summary
├── docs/
├── tests/
├── requirements.txt
├── .gitignore
└── README.md
```

## Error Handling & Safety

- Files are never deleted or overwritten accidentally.
- Duplicate names are automatically renamed.
- The tool skips files that are already in the destination to avoid recursion.
- If copying/moving fails for a particular file, the error is printed but processing continues.
- The `--dry-run` flag is strongly recommended for first runs.

## Performance Notes

- Expect ~10–30k files per minute on a modern MacBook Air/Pro (SSD to SSD copy).
- Memory usage is low; files are processed one-at-a-time.
- Using `--limit` for initial testing is wise.

## Troubleshooting

**No files found**: Ensure your source path is correct and contains audio files with supported extensions. Hidden/system folders are skipped.

**All files become Unknown**: Run with `--debug` to inspect metadata extraction. Add missing keywords to `rules.py` to improve your collection's specific folder names.

**Permission denied**: Ensure you have read access to source and write access to destination. Use absolute paths.

**Slow performance**: Large libraries take time. The tool shows progress every 100 files. Copying an entire library of thousands of files will take several minutes.

## License

MIT
