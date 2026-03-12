# Changelog

All notable changes to the Music Organizer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Backend API scaffolding with FastAPI:
  - `app/backend/main.py`: FastAPI application entry point
  - `app/backend/models/`: Typed Pydantic models for requests/responses
  - `app/backend/services/`: Service orchestration layer (extracted from CLI)
  - `app/backend/routes/`: API route definitions
- Service layer with reusable functions:
  - `analyze_service`: returns structured `AnalyzeResult`
  - `organize_service`: returns structured `OrganizeResult`
- API endpoints (stubbed):
  - `POST /api/v1/analyze` – library analysis
  - `POST /api/v1/organize` – file organization
- Backend dependencies: `fastapi`, `pydantic`, `uvicorn`
- Tests for models and service layer (test_models.py, test_services.py)

### Added
- Run registry and multi-run undo history:
  - New append-only `run_history.json` under `~/.config/music-organizer/`
  - Store layer (`app/backend/store/`) with create_run, update_run_progress, finalize_run, list_runs, get_run, undo_run, migration from legacy journal
  - Typed models: `FileOperation`, `RunEntry`, `FullRunEntry`, `UndoResult`
  - `organize_service` now records every file operation in run history
  - Enhanced `music-organizer undo` to use run history with full migration support; falls back to legacy journal
  - migrate_legacy_journal() converts old single-journal format to new run entries
- New tests for run history store (test_store.py): 15 tests covering CRUD, undo, migration

### Technical
- Preserved existing CLI behavior unchanged
- Fixed backend route imports and organize endpoint request passthrough for `skip_unknown_only` and `on_collision`
- Package discovery now includes the new `app` package for editable installs
- Backend dependencies are mirrored in `requirements.txt`
- Fixed Phase 2 run-history bugs: repeat legacy journal migration, already-undone runs staying `completed`, and missing legacy journal import in `organize_service`
- All existing tests continue to pass (132 tests total)

---

## [2.0.0] - v2 CLI Rework

### Added
- Complete subcommand-based CLI architecture:
  - `analyze`: Scan library and show genre distribution without moving files
  - `organize`: Main command for copying/moving files into genre-folders
  - `genres`: Display all supported genres and bucket mappings
  - `undo`: Revert the last organize operation using journal
  - `config`: Initialize, show, or locate configuration file
- Interactive DJ workflow mode (`--interactive`): guided prompts for source/destination/mode/level/profile
- Undo journal system: JSON journal at `~/.config/music-organizer/journal.json` for safe rollback
- Config system: persistent `~/.config/music-organizer/config.json` with init/show/path commands
- CDJ-safe profile (`--profile cdj-safe`):
  - Filename sanitization (special characters stripped)
  - Max folder depth of 3
  - Path length warnings (>180 chars)
  - Folder count warnings (>500 files)
- Custom genre mapping: define your own keyword-to-genre mappings in `config.json` under `custom_genres`
- DJ presets (`--preset`): pre-configured workflows for different contexts
  - `club`: house/techno emphasis, specific + cdj-safe
  - `latin`: detailed Latin breakdown, specific + default
  - `open-format`: broad general buckets, general + default
  - `festival`: EDM-focused, specific + cdj-safe

### Improved
- Word-boundary regex matching in path keyword inference (reduces false positives like "pop" in "popcorn")
- Support for 80+ specific genres across 10 general buckets
- Enhanced path normalization (underscores, hyphens, dots → spaces)
- Default collision policy now uses content hashes to skip identical duplicates on reruns
- Copy mode now avoids metadata-preserving copies that can create `._*` sidecar files on external SSDs
- Analyze/organize summaries now print unknown filename token diagnostics to speed up custom mapping work

### Technical
- Proper Python package with `pyproject.toml` and entry point `music-organizer`
- Comprehensive test suite: 82 passing tests
- Logging throughout for observability and debugging

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
