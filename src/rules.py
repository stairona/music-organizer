"""
Genre classification rules and mappings.

This module defines:
- SPECIFIC_GENRES: list of detailed/subgenres
- GENERAL_MAP: mapping from specific genres to general buckets
- PATH_KEYWORDS: keywords that appear in folder/filenames to infer genre (used when metadata is missing)
"""

from typing import Dict, List

# Specific (detailed) genres we want to detect
SPECIFIC_GENRES = [
    # House variants
    "Afro House", "Amapiano", "Acid House", "Deep House", "Tech House",
    "Bass House", "Electro House", "Progressive House", "Disco House",
    "Organic House", "Funky House", "Slap House", "Tropical House",
    "Lo-Fi House", "House",

    # Techno
    "Melodic Techno", "Minimal Techno", "Hard Techno", "Acid Techno",
    "Hypertechno", "Techno",

    # Trance
    "Progressive Trance", "Psytrance", "Trance",

    # Bass / Garage / Dub
    "Drum And Bass", "UK Garage", "Dubstep", "Riddim", "Big Room",
    "Big Beat", "Electronica", "Chillwave", "Nightcore",

    # Hard styles
    "Frenchcore", "Hardstyle", "Hardcore", "Happy Hardcore", "Gabber", "EDM",

    # Other electronic
    "Witch House",

    # Hip-Hop / Rap variants
    "Rap", "Hip-Hop", "Grime", "Drill", "Trap", "Trap Latino",
    "Argentine Trap", "Chilean Trap",

    # R&B / Soul / Funk
    "R&B", "Soul", "Funk",

    # Pop variants
    "Dance Pop", "Brazilian Pop", "Colombian Pop", "French Pop",
    "German Pop", "Latin Pop", "Hyperpop", "Pop",

    # Indie / Rock / Metal
    "Indie Dance", "Indie Rock", "Indie", "New Wave", "Rock", "Metal",

    # Latin genres
    "Reggaeton", "Reggaeton Chileno", "Reggaeton Mexa", "Dembow",
    "Neoperreo", "Moombahton", "Latin Afrobeat", "Latin Afrobeats",
    "Latin House", "Latin R", "Urbano Latino", "Bachata", "Salsa Choke",
    "Salsa", "Vallenato", "Corridos Tumbados", "Corrido", "Timba",
    "Kizomba", "Champeta", "Techengue", "Latin",

    # Reggae / Dub / Dancehall
    "Reggae", "Dub", "Dancehall",

    # Jazz / Blues
    "Jazz House", "Vocal Jazz", "Jazz", "Blues",

    # Classical / Score
    "Classical", "Soundtrack",
]

# Build a lowercase mapping for quick lookup
SPECIFIC_GENRES_LOWER = {g.lower(): g for g in SPECIFIC_GENRES}

# Mapping from specific genre to general bucket
GENERAL_MAP: Dict[str, str] = {
    # Electronic / House
    "Afro House": "Electronic",
    "Amapiano": "Electronic",
    "Acid House": "Electronic",
    "Deep House": "Electronic",
    "Tech House": "Electronic",
    "Bass House": "Electronic",
    "Electro House": "Electronic",
    "Progressive House": "Electronic",
    "Disco House": "Electronic",
    "Organic House": "Electronic",
    "Funky House": "Electronic",
    "Slap House": "Electronic",
    "Tropical House": "Electronic",
    "Lo-Fi House": "Electronic",
    "House": "Electronic",

    # Techno
    "Melodic Techno": "Electronic",
    "Minimal Techno": "Electronic",
    "Hard Techno": "Electronic",
    "Acid Techno": "Electronic",
    "Hypertechno": "Electronic",
    "Techno": "Electronic",

    # Trance
    "Progressive Trance": "Electronic",
    "Psytrance": "Electronic",
    "Trance": "Electronic",

    # Bass / Garage
    "Drum And Bass": "Electronic",
    "UK Garage": "Electronic",
    "Dubstep": "Electronic",
    "Riddim": "Electronic",
    "Big Room": "Electronic",
    "Big Beat": "Electronic",
    "Electronica": "Electronic",
    "Chillwave": "Electronic",
    "Nightcore": "Electronic",

    # Hard styles
    "Frenchcore": "Electronic",
    "Hardstyle": "Electronic",
    "Hardcore": "Electronic",
    "Happy Hardcore": "Electronic",
    "Gabber": "Electronic",
    "EDM": "Electronic",

    # Other electronic
    "Witch House": "Electronic",

    # Hip-Hop / Rap
    "Rap": "Hip-Hop / Rap",
    "Hip-Hop": "Hip-Hop / Rap",
    "Grime": "Hip-Hop / Rap",
    "Drill": "Hip-Hop / Rap",
    "Trap": "Hip-Hop / Rap",
    "Trap Latino": "Hip-Hop / Rap",
    "Argentine Trap": "Hip-Hop / Rap",
    "Chilean Trap": "Hip-Hop / Rap",

    # R&B / Soul / Funk
    "R&B": "R&B / Soul / Funk",
    "Soul": "R&B / Soul / Funk",
    "Funk": "R&B / Soul / Funk",

    # Pop
    "Dance Pop": "Pop",
    "Brazilian Pop": "Pop",
    "Colombian Pop": "Pop",
    "French Pop": "Pop",
    "German Pop": "Pop",
    "Latin Pop": "Pop",
    "Hyperpop": "Pop",
    "Pop": "Pop",

    # Indie / Rock / Metal
    "Indie Dance": "Rock / Indie / Metal",
    "Indie Rock": "Rock / Indie / Metal",
    "Indie": "Rock / Indie / Metal",
    "New Wave": "Rock / Indie / Metal",
    "Rock": "Rock / Indie / Metal",
    "Metal": "Rock / Indie / Metal",

    # Latin
    "Reggaeton": "Latin",
    "Reggaeton Chileno": "Latin",
    "Reggaeton Mexa": "Latin",
    "Dembow": "Latin",
    "Neoperreo": "Latin",
    "Moombahton": "Latin",
    "Latin Afrobeat": "Latin",
    "Latin Afrobeats": "Latin",
    "Latin House": "Latin",
    "Latin R": "Latin",
    "Urbano Latino": "Latin",
    "Bachata": "Latin",
    "Salsa Choke": "Latin",
    "Salsa": "Latin",
    "Vallenato": "Latin",
    "Corridos Tumbados": "Latin",
    "Corrido": "Latin",
    "Timba": "Latin",
    "Kizomba": "Latin",
    "Champeta": "Latin",
    "Techengue": "Latin",
    "Latin": "Latin",

    # Reggae / Dub / Dancehall
    "Reggae": "Reggae / Dub / Dancehall",
    "Dub": "Reggae / Dub / Dancehall",
    "Dancehall": "Reggae / Dub / Dancehall",

    # Jazz / Blues
    "Jazz House": "Jazz / Blues",
    "Vocal Jazz": "Jazz / Blues",
    "Jazz": "Jazz / Blues",
    "Blues": "Jazz / Blues",

    # Classical / Score
    "Classical": "Classical / Score",
    "Soundtrack": "Classical / Score",
}

# Ensure all specific genres have a general mapping
for genre in SPECIFIC_GENRES:
    if genre not in GENERAL_MAP:
        GENERAL_MAP[genre] = "Other / Unknown"

# Path keywords that suggest a genre (lowercase keys)
# These are used when metadata is missing or unreliable
PATH_KEYWORDS: Dict[str, str] = {
    # Electronic / House
    "house": "House",
    "afro house": "Afro House",
    "amapiano": "Amapiano",
    "deep house": "Deep House",
    "tech house": "Tech House",
    "bass house": "Bass House",
    "electro house": "Electro House",
    "progressive house": "Progressive House",
    "disco house": "Disco House",
    "organic house": "Organic House",
    "funky house": "Funky House",
    "slap house": "Slap House",
    "tropical house": "Tropical House",
    "lo-fi house": "Lo-Fi House",
    "lofi house": "Lo-Fi House",

    # Techno
    "techno": "Techno",
    "melodic techno": "Melodic Techno",
    "minimal techno": "Minimal Techno",
    "hard techno": "Hard Techno",
    "acid techno": "Acid Techno",
    "hypertechno": "Hypertechno",

    # Trance
    "trance": "Trance",
    "progressive trance": "Progressive Trance",
    "psytrance": "Psytrance",
    "psy trance": "Psytrance",

    # Bass / Garage
    "drum and bass": "Drum And Bass",
    "drum & bass": "Drum And Bass",
    "dnb": "Drum And Bass",
    "uk garage": "UK Garage",
    "garage": "UK Garage",
    "dubstep": "Dubstep",
    "riddim": "Riddim",
    "big room": "Big Room",
    "bigbeat": "Big Beat",
    "big beat": "Big Beat",
    "electronica": "Electronica",
    "chillwave": "Chillwave",
    "nightcore": "Nightcore",

    # Hard styles
    "frenchcore": "Frenchcore",
    "hardstyle": "Hardstyle",
    "hardcore": "Hardcore",
    "happy hardcore": "Happy Hardcore",
    "gabber": "Gabber",
    "edm": "EDM",

    # Other electronic
    "witch house": "Witch House",

    # Hip-Hop / Rap
    "rap": "Rap",
    "hip hop": "Hip-Hop",
    "hip-hop": "Hip-Hop",
    "grime": "Grime",
    "drill": "Drill",
    "trap": "Trap",
    "trap latino": "Trap Latino",
    "latino trap": "Trap Latino",
    "argentine trap": "Argentine Trap",
    "chilean trap": "Chilean Trap",

    # R&B / Soul / Funk
    "rnb": "R&B",
    "r&b": "R&B",
    "soul": "Soul",
    "funk": "Funk",

    # Pop
    "dance pop": "Dance Pop",
    "brazilian pop": "Brazilian Pop",
    "colombian pop": "Colombian Pop",
    "french pop": "French Pop",
    "german pop": "German Pop",
    "latin pop": "Latin Pop",
    "hyperpop": "Hyperpop",
    "pop": "Pop",

    # Indie / Rock / Metal
    "indie dance": "Indie Dance",
    "indie rock": "Indie Rock",
    "indie": "Indie",
    "new wave": "New Wave",
    "rock": "Rock",
    "metal": "Metal",

    # Latin
    "reggaeton": "Reggaeton",
    "reggaeton chileno": "Reggaeton Chileno",
    "reggaeton mexa": "Reggaeton Mexa",
    "dembow": "Dembow",
    "neoperreo": "Neoperreo",
    "moombaton": "Moombahton",
    "latin afrobeat": "Latin Afrobeat",
    "latin afrobeats": "Latin Afrobeats",
    "latin house": "Latin House",
    "latin r": "Latin R",
    "urbano latino": "Urbano Latino",
    "bachata": "Bachata",
    "salsa choke": "Salsa Choke",
    "salsa": "Salsa",
    "vallenato": "Vallenato",
    "corridos tumbados": "Corridos Tumbados",
    "corrido": "Corrido",
    "timba": "Timba",
    "kizomba": "Kizomba",
    "champeta": "Champeta",
    "techengue": "Techengue",
    "latin": "Latin",

    # Reggae / Dub / Dancehall
    "reggae": "Reggae",
    "dub": "Dub",
    "dancehall": "Dancehall",

    # Jazz / Blues
    "jazz house": "Jazz House",
    "vocal jazz": "Vocal Jazz",
    "jazz": "Jazz",
    "blues": "Blues",

    # Classical / Score
    "classical": "Classical",
    "classical music": "Classical",
    "soundtrack": "Soundtrack",
    "score": "Classical",
    "orchestral": "Classical",
    "symphony": "Classical",
    "piano": "Classical",  # Could be ambiguous, but often solo piano pieces are classical
    "instrumental": "Classical",  # Fallback for purely instrumental

    # Fallbacks
    "unknown": "Other / Unknown",
    "misc": "Other / Unknown",
    "various": "Other / Unknown",
}

# General bucket names (for directory creation and reporting)
GENERAL_BUCKETS = [
    "Electronic",
    "Hip-Hop / Rap",
    "R&B / Soul / Funk",
    "Pop",
    "Rock / Indie / Metal",
    "Latin",
    "Reggae / Dub / Dancehall",
    "Jazz / Blues",
    "Classical / Score",
    "Other / Unknown",
]

# Mapping from general bucket to example specific genres (for documentation/help)
GENERAL_TO_SPECIFIC: Dict[str, List[str]] = {
    "Electronic": ["House", "Techno", "Trance", "Drum And Bass", "Dubstep", "EDM"],
    "Hip-Hop / Rap": ["Rap", "Trap", "Drill", "Grime"],
    "R&B / Soul / Funk": ["R&B", "Soul", "Funk"],
    "Pop": ["Pop", "Dance Pop", "Latin Pop", "Hyperpop"],
    "Rock / Indie / Metal": ["Rock", "Indie", "Metal", "Indie Rock"],
    "Latin": ["Reggaeton", "Bachata", "Salsa", "Latin", "Moombahton"],
    "Reggae / Dub / Dancehall": ["Reggae", "Dancehall", "Dub"],
    "Jazz / Blues": ["Jazz", "Blues", "Vocal Jazz"],
    "Classical / Score": ["Classical", "Soundtrack", "Instrumental"],
    "Other / Unknown": [],
}


def get_general_for_specific(specific: str) -> str:
    """Return the general bucket for a given specific genre."""
    return GENERAL_MAP.get(specific, "Other / Unknown")


def genre_matches_keyword(genre_name: str) -> List[str]:
    """
    Check if a genre string (from metadata or path) matches any of our known specific genres.
    Returns list of matching specific genres (could be multiple if ambiguous).
    """
    if not genre_name:
        return []

    normalized = genre_name.lower().strip()

    # Direct match with specific genres (case-insensitive)
    if normalized in SPECIFIC_GENRES_LOWER:
        return [SPECIFIC_GENRES_LOWER[normalized]]

    # Check for known keywords within the genre string
    matches = []
    for keyword, mapped_genre in PATH_KEYWORDS.items():
        if keyword in normalized:
            matches.append(mapped_genre)

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            unique.append(m)

    return unique
