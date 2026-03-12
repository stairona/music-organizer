"""
Audio metadata extraction using mutagen.

Supports: MP3, M4A/MP4/AAC, FLAC, OGG, OPUS, WAV, AIFF, WMA.
"""

import os
import logging
from typing import Optional, List

from mutagen import File
from mutagen.easyid3 import EasyID3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.wavpack import WavPack
from mutagen.aiff import AIFF
from mutagen.asf import ASF

logger = logging.getLogger(__name__)


def should_ignore_filename(filename: str) -> bool:
    """Return True for hidden or system files that should never be processed."""
    return filename.startswith('.') or filename == 'Thumbs.db'


def get_audio_format(filepath: str) -> str:
    """Return the audio format category based on file extension."""
    ext = os.path.splitext(filepath)[1].lower()
    mapping = {
        '.mp3': 'mp3',
        '.m4a': 'mp4',
        '.mp4': 'mp4',
        '.aac': 'mp4',
        '.flac': 'flac',
        '.ogg': 'ogg',
        '.opus': 'ogg',
        '.wav': 'wav',
        '.aiff': 'aiff',
        '.aif': 'aiff',
        '.wma': 'asf',
    }
    return mapping.get(ext, 'unknown')


def read_genre(filepath: str, debug: bool = False) -> Optional[str]:
    """
    Extract genre from audio file metadata.
    Returns the genre string if found, otherwise None.
    """
    try:
        audio = File(filepath, easy=True)
        if audio is None:
            if debug:
                logger.debug(f"mutagen could not parse: {filepath}")
            return None

        # --- MP3 (EasyID3) ---
        if isinstance(audio, EasyID3):
            # EasyID3 normalizes genre to 'genre' tag
            genre_list = audio.get('genre', [])
            if genre_list:
                genre = str(genre_list[0]).strip()
                if debug:
                    logger.debug(f"MP3 genre from {filepath}: {genre}")
                return genre if genre else None

        # --- MP4/M4A/AAC ---
        if isinstance(audio, MP4):
            # MP4 tags: '©gen' is the genre
            genre_list = audio.get('©gen', [])
            if genre_list:
                genre = str(genre_list[0]).strip()
                if debug:
                    logger.debug(f"MP4 genre from {filepath}: {genre}")
                return genre if genre else None

        # --- FLAC / OGG / OPUS (Vorbis comments) ---
        if isinstance(audio, (FLAC, OggVorbis, WavPack)):
            # Vorbis-style tags: 'GENRE' or 'genre'
            for key in ('genre', 'GENRE'):
                if key in audio:
                    genre = str(audio[key][0]).strip()
                    if debug:
                        logger.debug(f"FLAC/OGG genre from {filepath}: {genre}")
                    return genre if genre else None

        # --- WAV ---
        if get_audio_format(filepath) == 'wav':
            # WAV files typically use INFO:IRE or other tags. mutagen returns a generic dict.
            # Attempt common keys
            for key in ('genre', 'GENRE', 'INFO:IRE'):
                if key in audio:
                    genre = str(audio[key][0]).strip()
                    if debug:
                        logger.debug(f"WAV genre from {filepath}: {genre}")
                    return genre if genre else None

        # --- AIFF ---
        if isinstance(audio, AIFF):
            for key in ('genre', 'GENRE'):
                if key in audio:
                    genre = str(audio[key][0]).strip()
                    if debug:
                        logger.debug(f"AIFF genre from {filepath}: {genre}")
                    return genre if genre else None

        # --- WMA / ASF ---
        if isinstance(audio, ASF):
            # WM/Genre is the tag
            if 'WM/Genre' in audio:
                genre = str(audio['WM/Genre'][0]).strip()
                if debug:
                    logger.debug(f"WMA genre from {filepath}: {genre}")
                return genre if genre else None

    except Exception as e:
        if debug:
            logger.debug(f"Error reading genre from {filepath}: {e}")
        return None

    return None


def get_audio_files(
    src_dir: str,
    limit: Optional[int] = None,
    debug: bool = False,
    exclude_dirs: Optional[List[str]] = None,
) -> List[str]:
    """
    Recursively find audio files in src_dir with supported extensions.
    Returns a list of absolute paths.

    Args:
        src_dir: Root directory to scan.
        limit: Optional maximum number of files.
        debug: Enable debug output.
        exclude_dirs: List of directory names to exclude (e.g., ['temp', 'incomplete']).
    """
    supported_exts = {
        '.mp3', '.m4a', '.mp4', '.aac',
        '.flac',
        '.ogg', '.opus',
        '.wav',
        '.aiff', '.aif',
        '.wma'
    }

    if exclude_dirs is None:
        exclude_dirs = []

    files = []
    for root, dirnames, filenames in os.walk(src_dir):
        # Skip hidden directories and excluded directory names
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in exclude_dirs]
        for fname in filenames:
            if should_ignore_filename(fname):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext in supported_exts:
                files.append(os.path.join(root, fname))
                if limit and len(files) >= limit:
                    return files
    return files
