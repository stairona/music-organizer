"""
DJ presets for common mixing contexts.

Each preset provides recommended default values for classification level and output profile.
"""

from typing import Dict, Any

PRESETS: Dict[str, Dict[str, Any]] = {
    "club": {
        "level": "specific",
        "profile": "cdj-safe",
        "description": "Emphasizes house/techno subgenres for club DJs. Uses specific classification and CDJ-safe output.",
    },
    "latin": {
        "level": "specific",
        "profile": "default",
        "description": "Detailed Latin genre breakdown for Latin music specialists.",
    },
    "open-format": {
        "level": "general",
        "profile": "default",
        "description": "Broad general buckets for versatile open-format DJs.",
    },
    "festival": {
        "level": "specific",
        "profile": "cdj-safe",
        "description": "EDM-focused with emphasis on hard styles and big room for festival performances.",
    },
}


def get_preset(name: str) -> Dict[str, Any]:
    """
    Retrieve a preset configuration by name.
    Returns a dict with at least 'level' and 'profile' keys.
    Raises ValueError if preset name is unknown.
    """
    if name not in PRESETS:
        raise ValueError(f"Unknown preset: {name}")
    return PRESETS[name]
