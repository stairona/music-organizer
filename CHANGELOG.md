# Changelog

All notable changes to the Music Organizer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - Phase 2 (In Progress)

### Added
- `--stats-only` mode: Analyze library and print genre distribution without copying/moving files
- Enhanced genre coverage with world music genres:
  - Folk, World, Arabic, Indian, Bhangra, African, Greek, Celtic (all under `World` bucket)
  - K-Pop, J-Pop, C-Pop (under `Pop` bucket)
- Comprehensive documentation:
  - `CONTRIBUTING.md` with setup, testing, and genre rule addition guide
  - `CHANGELOG.md` to track project history

### Improved
- Genre classification accuracy with extensive path keyword mappings
- Word boundary matching to reduce false positives (e.g., "pop" in "popcorn")

## [1.0.0] - Phase 1

### Added
- Core music organization functionality:
  - Recursive scanning of music libraries with audio file detection
  - Metadata-based genre extraction using `mutagen` library
  - Path/filename keyword inference as fallback when metadata is missing
  - Three classification levels: `--level general`, `--level specific`, `--level both`
- File operations:
  - Safe copy mode (default) and move mode
  - Automatic duplicate handling with renaming (`song (1).mp3`)
  - `--skip-existing` option to avoid overwriting
  - `--dry-run` for safe previewing
- Command-line options:
  - `--report` for CSV output with full processing log
  - `--limit` for testing on subsets
  - `--exclude-dir` to skip unwanted directories
  - `--skip-unknown-only` for targeted re-classification
  - `--debug` for detailed decision tracing
  - `--quiet` for minimal output
- Performance optimizations for large libraries (streaming, one-at-a-time processing)
- Comprehensive test suite with 37 passing tests covering:
  - Genre string normalization
  - Path-based genre inference
  - File classification logic
  - File operations and collision handling
  - Directory scanning with exclusions

### Technical
- Proper Python package structure (`src/music_organizer/`)
- Pytest-based testing with fixtures
- Logging throughout for observability
- Support for 80+ specific genres across 10 general buckets
