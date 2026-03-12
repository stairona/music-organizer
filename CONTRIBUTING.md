# Contributing to Music Organizer

Thank you for your interest in improving the project! This guide covers the essentials.

## Setup

1. **Clone and install**:
   ```bash
   git clone https://github.com/stairona/music-organizer.git
   cd music-organizer
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -e .[dev]
   ```

2. **Run tests** to ensure everything works:
   ```bash
   pytest
   ```

   All tests should pass before submitting changes.

## Adding New Genre Rules

The genre classification logic lives in `src/music_organizer/rules.py`.

### Steps:

1. **Add the specific genre** to the `SPECIFIC_GENRES` list.
2. **Map it to a general bucket** in the `GENERAL_MAP` dictionary.
   - Choose from existing buckets: `Electronic`, `Hip-Hop / Rap`, `R&B / Soul / Funk`,
     `Pop`, `Rock / Indie / Metal`, `Latin`, `Reggae / Dub / Dancehall`,
     `Jazz / Blues`, `Classical / Score`, `World`, or `Other / Unknown`.
3. **Add path keywords** (optional but recommended) to `PATH_KEYWORDS` for better
   fallback detection when metadata is missing. Use lowercase keys and exact specific
   genre values.

4. **Update `GENERAL_TO_SPECIFIC`** to include your new genre in the appropriate
   general bucket's example list (for documentation purposes).

5. **Test your changes**:
   ```bash
   pytest tests/test_classify.py -v
   ```

   Consider adding a unit test if you're adding significant new functionality.

### Example:

```python
# In SPECIFIC_GENRES
"New Genre",

# In GENERAL_MAP
"New Genre": "Electronic",

# In PATH_KEYWORDS
"new genre": "New Genre",
"newgenre": "New Genre",
```

## Pull Request Checklist

- [ ] All existing tests pass (`pytest`)
- [ ] New genres include both metadata and path keyword support
- [ ] `GENERAL_TO_SPECIFIC` updated
- [ ] Code formatted and readable
- [ ] No debug prints or temporary code left in

## Questions?

Open an issue to discuss major changes before implementing.
