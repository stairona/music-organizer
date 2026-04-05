# Music Organizer Desktop — Testing Notes

**Test Date**: _____________
**Tester**: _____________
**Backend**: running on http://127.0.0.1:8000
**Desktop App**: `npm run tauri:dev` ( running)
**Spotify Playlist Used**: [URL]
**spotdl Version**: _____________ (output of `spotdl --version`)

---

## Test Flow

### 1. Download Test

- [ ] Backend accepts playlist URL without errors
- [ ] Download task created and appears in Active page
- [ ] Progress bar updates (percentage visible)
- [ ] Active task count in Home page updates
- [ ] Cancel button stops download
- [ ] Completed download appears in History page
- [ ] Files saved to correct destination folder

**Observed behavior**:

**Issues encountered**:

---

### 2. Organize Test

- [ ] Organize form accepts source folder
- [ ] Optional destination field works (blank = in-place)
- [ ] Mode (copy/move) functions correctly
- [ ] Genre level (general/specific) creates expected folder structure
- [ ] Profile selection works (default/CDJ-safe)
- [ ] "Dry run" preview shows correct stats without modifying files
- [ ] Actual organize completes without errors
- [ ] Organize summary shows moved/copied/unknown counts
- [ ] Warnings displayed if applicable

**Observed behavior**:

**Issues encountered**:

---

### 3. Full End-to-End

- [ ] Download → Organize → Verify final folder structure
- [ ] Files placed in appropriate genre subfolders
- [ ] Metadata preserved (or unknown files flagged)
- [ ] Duplicate handling (skip_existing checkbox) works

**Final folder structure**:

---

## Results Summary

### Passed Tests

1.
2.
3.

### Failed Tests

1.
2.
3.

### Notable Observations

-
-
-

---

## Next Steps / Recommendations

-
-
-
