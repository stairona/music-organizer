# Claude Code Prompts for music-organizer v2

Run these prompts **in order** inside Claude Code (terminal).
Each prompt assumes the previous one was completed and committed.

---

## Prompt 1 — CDJ-safe profile ✅ DONE (commit a995d9c)

> Read CLAUDE.md. Implement the CDJ-safe profile for the organize command. Add a `sanitize_filename()` function in `fileops.py` that strips special characters and truncates long filenames. Update `compute_destination()` to accept a `profile` parameter — when `profile="cdj-safe"`, apply filename sanitization, enforce max folder depth of 3, and warn if total path length exceeds 180 characters. In `commands/organize.py`, pass the profile through and add a warning if any single genre folder exceeds 500 files. Add tests for all new behavior. Run pytest — all tests must pass.

---

## Prompt 2 — Custom genre mapping from config

> Read CLAUDE.md. Add custom genre mapping support. When `config.json` has a `"custom_genres"` section (a dict mapping keyword strings to genre folder names), those mappings should be checked BEFORE the built-in rules in `classify_file()`. Load config in `classify.py` from `~/.config/music-organizer/config.json`. If the file doesn't exist or has no `custom_genres` key, skip gracefully. Add tests that mock a config with custom genres and verify they take priority over built-in rules. Run pytest — all tests must pass.

---

## Prompt 3 — DJ presets

> Read CLAUDE.md. Add DJ presets to the interactive mode and config system. Presets: `"club"` (emphasizes house/techno subgenres), `"latin"` (detailed Latin breakdown), `"open-format"` (broad general buckets), `"festival"` (EDM-focused). Each preset should set default values for `level`, `profile`, and optionally filter or reweight genre detail. Store preset definitions in a new file `src/music_organizer/presets.py`. Wire presets into `commands/interactive.py` as a prompt option and into `commands/organize.py` via `--preset NAME`. Add tests for each preset's defaults. Run pytest — all tests must pass.

---

## Prompt 4 — Merge and push

> Read CLAUDE.md. Run pytest to confirm all tests pass. Create or update `CHANGELOG.md` with a v2.0.0 entry summarizing: subcommand CLI (analyze, organize, genres, undo, config), interactive DJ workflow, journal/undo system, CDJ-safe profile, custom genre mapping, DJ presets. Then merge `v2-cli-rebuild` into `main` and push to GitHub. Verify the push succeeded.
