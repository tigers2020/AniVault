"""File hash calculation for subtitle matching.

Extracted from subtitle_matcher.py for reuse across subtitle and index modules.
Uses streaming to minimize memory usage for large files.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Chunk size for streaming file hash calculation (64KB)
HASH_CHUNK_SIZE = 65536


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file's contents using streaming.

    Reads the file in chunks to minimize memory usage,
    making it suitable for large subtitle files.

    Args:
        file_path: Path to the file to hash.

    Returns:
        Hexadecimal string representation of the SHA256 hash.

    Raises:
        OSError: If the file cannot be read.
        FileNotFoundError: If the file does not exist.

    Example:
        >>> from pathlib import Path
        >>> hash1 = calculate_file_hash(Path("subtitle1.srt"))
        >>> hash2 = calculate_file_hash(Path("subtitle2.srt"))
        >>> hash1 == hash2  # True if files have identical content
        True

    Note:
        Empty files return SHA256("") =
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    """
    sha256_hash = hashlib.sha256()

    try:
        with file_path.open("rb") as f:
            while True:
                chunk = f.read(HASH_CHUNK_SIZE)
                if not chunk:
                    break
                sha256_hash.update(chunk)
    except FileNotFoundError:
        logger.exception("File not found for hashing: %s", file_path)
        raise
    except OSError:
        logger.exception("Error reading file for hashing %s", file_path)
        raise

    return sha256_hash.hexdigest()


__all__ = ["HASH_CHUNK_SIZE", "calculate_file_hash"]
