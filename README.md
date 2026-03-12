# Music Organizer

A Python tool that automatically organizes music files by genre using metadata tags.

## Overview

This utility scans a directory of music files, reads their embedded metadata to detect the genre, and automatically sorts files into corresponding genre folders. It's designed for music enthusiasts and collectors who want to quickly organize large music libraries without manual sorting.

> **Note:** This project is currently in initial setup phase. The `src/main.py` implementation is pending. See the [CLAUDE.md](CLAUDE.md) for development instructions.

## Planned Features

- Read audio metadata using the `mutagen` library
- Detect genre automatically from ID3 tags and other metadata formats
- Sort files into genre-specific folders
- Handle large music libraries efficiently
- Provide a summary of processed files and any issues encountered
- Support for common audio formats: MP3, FLAC, M4A, OGG, etc.

## Problem It Solves

Manual music organization is time-consuming and error-prone. This tool automates the process by:
- Eliminating the need to manually listen to or inspect each file
- Ensuring consistent genre classification based on actual metadata
- Handling thousands of files quickly
- Preserving original file structure if desired (copy vs move modes)

## Tech Stack

- **Python 3.8+**
- **mutagen** – Audio metadata library (supports MP3, FLAC, M4A, OGG, Opus, WavPack, and more)

## Development Status

**Stage:** Scaffolded, implementation pending

The project structure is in place:
```
music-organizer/
├── src/
│   └── main.py          # To be implemented
├── docs/
├── tests/
├── requirements.txt     # mutagen pinned to 1.47.0
├── .gitignore
└── README.md
```

The implementation will follow the specifications in `CLAUDE.md`, which outlines:
- Clean, modular Python code
- Error handling and safe file operations (no automatic deletion without confirmation)
- Clear progress reporting

## Installation (for when implementation is complete)

```bash
# Clone and enter directory
git clone https://github.com/stairona/music-organizer.git
cd music-organizer

# Optional: create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage (planned)

```bash
python src/main.py /path/to/your/music/library
```

Options may include:
- `--dry-run` to preview without moving files
- `--copy` to copy instead of move
- `--verbose` for detailed output

## Contributing

This project is developed with Claude Code following the guidelines in `CLAUDE.md`. Contributions and suggestions are welcome.

## License

MIT
