"""Compression functionality for cache system.

This module provides compression and decompression functionality for cache entries
to optimize memory usage.
"""

from __future__ import annotations

import logging
from typing import Any

from .compression import compression_manager
from .models import ParsedAnimeInfo, TMDBAnime

# Configure logging
logger = logging.getLogger(__name__)


class CacheCompression:
    """Compression functionality for cache system."""

    def __init__(self, enable_compression: bool = True, compression_threshold: int = 1024):
        """Initialize compression handler.

        Args:
            enable_compression: Whether to enable compression
            compression_threshold: Minimum size in bytes to consider compression
        """
        self.enable_compression = enable_compression
        self.compression_threshold = compression_threshold

    def apply_compression_if_needed(self, value: ParsedAnimeInfo | TMDBAnime) -> ParsedAnimeInfo | TMDBAnime | None:
        """Apply compression to value if beneficial.

        Args:
            value: Value to potentially compress

        Returns:
            Compressed value or None if compression not beneficial
        """
        if not self.enable_compression:
            return None

        try:
            # Calculate original size
            original_size = self._calculate_value_size(value)
            if original_size < self.compression_threshold:
                return None

            # Apply compression
            compressed_data = compression_manager.compress(value)
            if compressed_data is None:
                return None

            # Check if compression actually saved space
            compressed_size = len(compressed_data)
            if compressed_size >= original_size * 0.8:  # Less than 20% savings
                return None

            # Create a wrapper object to hold compressed data
            class CompressedValue:
                def __init__(self, data: bytes, original_type: type):
                    self.compressed_data = data
                    self.original_type = original_type

            return CompressedValue(compressed_data, type(value))

        except Exception as e:
            logger.warning(f"Compression failed for value: {e}")
            return None

    def decompress_if_needed(self, value: Any) -> ParsedAnimeInfo | TMDBAnime:
        """Decompress value if it's compressed.

        Args:
            value: Potentially compressed value

        Returns:
            Decompressed value
        """
        if not self.enable_compression:
            return value

        try:
            # Check if value is compressed
            if hasattr(value, 'compressed_data') and hasattr(value, 'original_type'):
                # Decompress
                decompressed = compression_manager.decompress(value.compressed_data, value.original_type)
                if decompressed is not None:
                    return decompressed

        except Exception as e:
            logger.warning(f"Decompression failed: {e}")

        return value

    def _calculate_value_size(self, value: ParsedAnimeInfo | TMDBAnime) -> int:
        """Calculate memory size of a value.

        Args:
            value: Value to calculate size for

        Returns:
            Estimated size in bytes
        """
        if isinstance(value, ParsedAnimeInfo):
            return self._calculate_parsed_info_size(value)
        elif isinstance(value, TMDBAnime):
            return self._calculate_tmdb_anime_size(value)
        else:
            return 1000  # Default estimate

    def _calculate_parsed_info_size(self, info: ParsedAnimeInfo) -> int:
        """Calculate memory size of ParsedAnimeInfo.

        Args:
            info: ParsedAnimeInfo instance

        Returns:
            Estimated size in bytes
        """
        size = 0
        for field_name in ['title', 'season', 'episode', 'year', 'quality', 'group', 'file_path']:
            value = getattr(info, field_name, None)
            if value is not None:
                size += len(str(value).encode('utf-8'))
        return size

    def _calculate_tmdb_anime_size(self, anime: TMDBAnime) -> int:
        """Calculate memory size of TMDBAnime.

        Args:
            anime: TMDBAnime instance

        Returns:
            Estimated size in bytes
        """
        size = 0
        for field_name in ['title', 'original_title', 'overview', 'poster_path', 'backdrop_path']:
            value = getattr(anime, field_name, None)
            if value is not None:
                size += len(str(value).encode('utf-8'))
        return size

    def is_compressed(self, value: Any) -> bool:
        """Check if value is compressed.

        Args:
            value: Value to check

        Returns:
            True if value is compressed
        """
        return hasattr(value, 'compressed_data') and hasattr(value, 'original_type')

    def get_compression_ratio(self, original_value: ParsedAnimeInfo | TMDBAnime, compressed_value: Any) -> float:
        """Calculate compression ratio.

        Args:
            original_value: Original uncompressed value
            compressed_value: Compressed value

        Returns:
            Compression ratio (0.0 to 1.0, lower is better)
        """
        if not self.is_compressed(compressed_value):
            return 1.0

        original_size = self._calculate_value_size(original_value)
        compressed_size = len(compressed_value.compressed_data)

        if original_size == 0:
            return 1.0

        return compressed_size / original_size

    def get_compression_savings(self, original_value: ParsedAnimeInfo | TMDBAnime, compressed_value: Any) -> int:
        """Calculate compression savings in bytes.

        Args:
            original_value: Original uncompressed value
            compressed_value: Compressed value

        Returns:
            Number of bytes saved
        """
        if not self.is_compressed(compressed_value):
            return 0

        original_size = self._calculate_value_size(original_value)
        compressed_size = len(compressed_value.compressed_data)

        return max(0, original_size - compressed_size)

    def get_compression_stats(self) -> dict[str, Any]:
        """Get compression statistics.

        Returns:
            Compression statistics
        """
        return {
            "compression_enabled": self.enable_compression,
            "compression_threshold": self.compression_threshold,
            "compression_manager_available": compression_manager is not None,
            "compression_manager_status": compression_manager.get_status() if compression_manager else None
        }
