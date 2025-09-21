"""Simplified cache key generation system for AniVault.

This module provides a centralized, efficient, and deterministic cache key
generation system that improves cache hit rates and maintainability.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


class CacheKeyGenerator:
    """Centralized cache key generation with simplified, deterministic logic.

    This class provides methods to generate consistent cache keys for different
    types of data, using hashing for long keys and maintaining semantic equivalence.
    """

    # Key prefixes for different data types
    PREFIXES = {
        "tmdb_search": "search",
        "tmdb_multi": "multi",
        "tmdb_details": "details",
        "tmdb_series": "series",
        "tmdb_anime": "tmdb",
        "parsed_file": "file",
        "anime_metadata": "anime",
        "parsed_file_meta": "parsed",
    }

    # Maximum key length before hashing
    MAX_KEY_LENGTH = 200

    def __init__(self, use_hashing: bool = True) -> None:
        """Initialize the cache key generator.

        Args:
            use_hashing: Whether to use hashing for long keys
        """
        self.use_hashing = use_hashing

    def generate_tmdb_search_key(self, query: str, language: str = "ko-KR") -> str:
        """Generate cache key for TMDB search results.

        Args:
            query: Search query string
            language: Language code

        Returns:
            Generated cache key
        """
        # Normalize query to ensure consistency
        normalized_query = self._normalize_query(query)
        key = f"{self.PREFIXES['tmdb_search']}:{normalized_query}:{language}"
        return self._finalize_key(key)

    def generate_tmdb_multi_key(
        self, query: str, language: str = "ko-KR", region: str = "KR", include_adult: bool = False
    ) -> str:
        """Generate cache key for TMDB multi search results.

        Args:
            query: Search query string
            language: Language code
            region: Region code
            include_adult: Whether to include adult content

        Returns:
            Generated cache key
        """
        normalized_query = self._normalize_query(query)
        adult_flag = "1" if include_adult else "0"
        key = f"{self.PREFIXES['tmdb_multi']}:{normalized_query}:{language}:{region}:{adult_flag}"
        return self._finalize_key(key)

    def generate_tmdb_details_key(
        self, media_type: str, media_id: int, language: str = "ko-KR"
    ) -> str:
        """Generate cache key for TMDB details.

        Args:
            media_type: Type of media (movie, tv, etc.)
            media_id: TMDB media ID
            language: Language code

        Returns:
            Generated cache key
        """
        key = f"{self.PREFIXES['tmdb_details']}:{media_type}:{media_id}:{language}"
        return self._finalize_key(key)

    def generate_tmdb_series_key(self, series_id: int, language: str = "ko-KR") -> str:
        """Generate cache key for TMDB series details.

        Args:
            series_id: TMDB series ID
            language: Language code

        Returns:
            Generated cache key
        """
        key = f"{self.PREFIXES['tmdb_series']}:{series_id}:{language}"
        return self._finalize_key(key)

    def generate_tmdb_anime_key(self, tmdb_id: int) -> str:
        """Generate cache key for TMDB anime data.

        Args:
            tmdb_id: TMDB anime ID

        Returns:
            Generated cache key
        """
        key = f"{self.PREFIXES['tmdb_anime']}:{tmdb_id}"
        return self._finalize_key(key)

    def generate_file_key(self, file_path: str) -> str:
        """Generate cache key for parsed file data.

        Args:
            file_path: Path to the file

        Returns:
            Generated cache key
        """
        # Normalize file path for consistency
        normalized_path = self._normalize_file_path(file_path)
        key = f"{self.PREFIXES['parsed_file']}:{normalized_path}"
        return self._finalize_key(key)

    def generate_anime_metadata_key(self, tmdb_id: int) -> str:
        """Generate cache key for anime metadata.

        Args:
            tmdb_id: TMDB anime ID

        Returns:
            Generated cache key
        """
        key = f"{self.PREFIXES['anime_metadata']}:{tmdb_id}"
        return self._finalize_key(key)

    def generate_parsed_file_meta_key(self, file_id: int) -> str:
        """Generate cache key for parsed file metadata.

        Args:
            file_id: Database file ID

        Returns:
            Generated cache key
        """
        key = f"{self.PREFIXES['parsed_file_meta']}:{file_id}"
        return self._finalize_key(key)

    def _normalize_query(self, query: str) -> str:
        """Normalize search query for consistent key generation.

        Args:
            query: Original query string

        Returns:
            Normalized query string
        """
        if not query:
            return ""

        # Convert to lowercase and strip whitespace
        normalized = query.lower().strip()

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        # Remove special characters that might cause issues
        # Keep alphanumeric, spaces, and common punctuation
        import re

        normalized = re.sub(r"[^\w\s\-\.]", "", normalized)

        return normalized

    def _normalize_file_path(self, file_path: str) -> str:
        """Normalize file path for consistent key generation.

        Args:
            file_path: Original file path

        Returns:
            Normalized file path
        """
        if not file_path:
            return ""

        # Normalize path separators
        import os

        normalized = os.path.normpath(file_path)

        # Convert to lowercase for case-insensitive systems
        normalized = normalized.lower()

        return normalized

    def _finalize_key(self, key: str) -> str:
        """Finalize the cache key, applying hashing if necessary.

        Args:
            key: Base cache key

        Returns:
            Final cache key
        """
        if not self.use_hashing or len(key) <= self.MAX_KEY_LENGTH:
            return key

        # Use SHA-256 for hashing long keys
        hash_obj = hashlib.sha256(key.encode("utf-8"))
        hash_hex = hash_obj.hexdigest()[:16]  # Use first 16 characters

        # Include key type prefix for debugging
        key_type = key.split(":")[0] if ":" in key else "unknown"
        return f"{key_type}:{hash_hex}"

    def extract_key_info(self, key: str) -> dict[str, Any]:
        """Extract information from a cache key for debugging.

        Args:
            key: Cache key to analyze

        Returns:
            Dictionary with key information
        """
        if ":" not in key:
            return {"type": "unknown", "raw": key}

        parts = key.split(":")
        key_type = parts[0]

        info = {
            "type": key_type,
            "raw": key,
            "parts": parts,
            "is_hashed": len(key) <= 20 and key_type in self.PREFIXES.values(),
        }

        return info


# Global instance for easy access
cache_key_generator = CacheKeyGenerator()


def get_cache_key_generator() -> CacheKeyGenerator:
    """Get the global cache key generator instance.

    Returns:
        CacheKeyGenerator instance
    """
    return cache_key_generator
