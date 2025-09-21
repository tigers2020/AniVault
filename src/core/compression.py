"""Data compression utilities for large metadata objects.

This module provides compression and decompression functionality for large
metadata objects to reduce memory usage and improve transfer performance.
"""

import base64
import json
import zlib
from dataclasses import dataclass
from typing import Any

try:
    import orjson

    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False

from .logging_utils import logger


@dataclass
class CompressionStats:
    """Statistics for compression operations."""

    original_size: int
    compressed_size: int
    compression_ratio: float
    compression_time_ms: float
    decompression_time_ms: float

    @property
    def space_saved(self) -> int:
        """Calculate bytes saved through compression."""
        return self.original_size - self.compressed_size

    @property
    def space_saved_percent(self) -> float:
        """Calculate percentage of space saved."""
        if self.original_size == 0:
            return 0.0
        return (self.space_saved / self.original_size) * 100


class CompressionManager:
    """Manages compression and decompression of large metadata objects."""

    def __init__(
        self,
        compression_level: int = 6,
        min_size_threshold: int = 1024,  # 1KB minimum for compression
        max_compression_ratio: float = 0.8,
    ) -> None:  # Only compress if we save at least 20%
        """Initialize the compression manager.

        Args:
            compression_level: zlib compression level (1-9, 6 is default)
            min_size_threshold: Minimum size in bytes to consider compression
            max_compression_ratio: Maximum compression ratio to accept (0.8 = 20% savings)
        """
        self.compression_level = compression_level
        self.min_size_threshold = min_size_threshold
        self.max_compression_ratio = max_compression_ratio
        self._stats = {
            "total_compressions": 0,
            "total_decompressions": 0,
            "total_original_bytes": 0,
            "total_compressed_bytes": 0,
            "total_compression_time_ms": 0.0,
            "total_decompression_time_ms": 0.0,
            "compressions_skipped": 0,
            "compressions_rejected": 0,
        }

    def should_compress(
        self, data: str | bytes | dict[str, Any], estimated_size: int | None = None
    ) -> bool:
        """Determine if data should be compressed.

        Args:
            data: Data to evaluate for compression
            estimated_size: Pre-calculated size estimate

        Returns:
            True if data should be compressed
        """
        if estimated_size is None:
            estimated_size = self._estimate_size(data)

        # Skip compression for small data
        if estimated_size < self.min_size_threshold:
            self._stats["compressions_skipped"] += 1
            return False

        return True

    def compress_data(self, data: str | bytes | dict[str, Any]) -> tuple[bytes, CompressionStats]:
        """Compress data using zlib compression.

        Args:
            data: Data to compress

        Returns:
            Tuple of (compressed_bytes, compression_stats)

        Raises:
            ValueError: If compression fails or doesn't meet efficiency threshold
        """
        import time

        start_time = time.time()

        # Convert data to bytes (optimized JSON serialization)
        if isinstance(data, dict):
            if ORJSON_AVAILABLE:
                data_bytes = orjson.dumps(data)
            else:
                data_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        elif isinstance(data, str):
            data_bytes = data.encode("utf-8")
        else:
            data_bytes = data

        original_size = len(data_bytes)

        # Check if compression is worthwhile
        if not self.should_compress(data, original_size):
            raise ValueError(f"Data too small for compression: {original_size} bytes")

        try:
            # Compress the data
            compressed_bytes = zlib.compress(data_bytes, self.compression_level)
            compressed_size = len(compressed_bytes)

            compression_time_ms = (time.time() - start_time) * 1000

            # Calculate compression ratio
            compression_ratio = compressed_size / original_size

            # Check if compression meets efficiency threshold
            if compression_ratio > self.max_compression_ratio:
                self._stats["compressions_rejected"] += 1
                raise ValueError(f"Compression ratio too high: {compression_ratio:.2f}")

            # Create stats
            stats = CompressionStats(
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compression_ratio,
                compression_time_ms=compression_time_ms,
                decompression_time_ms=0.0,  # Will be set during decompression
            )

            # Update internal stats
            self._stats["total_compressions"] += 1
            self._stats["total_original_bytes"] += original_size
            self._stats["total_compressed_bytes"] += compressed_size
            self._stats["total_compression_time_ms"] += compression_time_ms

            logger.debug(
                f"Compressed data: {original_size} -> {compressed_size} bytes "
                f"({stats.space_saved_percent:.1f}% saved) in {compression_time_ms:.2f}ms"
            )

            return compressed_bytes, stats

        except Exception as e:
            logger.error(f"Compression failed: {e}")
            raise

    def decompress_data(
        self, compressed_bytes: bytes, expected_type: str = "str"
    ) -> tuple[str | bytes | dict[str, Any], CompressionStats]:
        """Decompress data using zlib decompression.

        Args:
            compressed_bytes: Compressed data
            expected_type: Expected data type ('str', 'bytes', 'dict')

        Returns:
            Tuple of (decompressed_data, compression_stats)

        Raises:
            ValueError: If decompression fails
        """
        import time

        start_time = time.time()

        try:
            # Decompress the data
            decompressed_bytes = zlib.decompress(compressed_bytes)
            decompression_time_ms = (time.time() - start_time) * 1000

            # Convert back to expected type
            if expected_type == "str":
                decompressed_data = decompressed_bytes.decode("utf-8")
            elif expected_type == "dict":
                decompressed_data = json.loads(decompressed_bytes.decode("utf-8"))
            else:  # bytes
                decompressed_data = decompressed_bytes

            # Create stats
            stats = CompressionStats(
                original_size=len(decompressed_bytes),
                compressed_size=len(compressed_bytes),
                compression_ratio=len(compressed_bytes) / len(decompressed_bytes),
                compression_time_ms=0.0,  # Not available during decompression
                decompression_time_ms=decompression_time_ms,
            )

            # Update internal stats
            self._stats["total_decompressions"] += 1
            self._stats["total_decompression_time_ms"] += decompression_time_ms

            logger.debug(
                f"Decompressed data: {len(compressed_bytes)} -> {len(decompressed_bytes)} bytes "
                f"in {decompression_time_ms:.2f}ms"
            )

            return decompressed_data, stats

        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            raise

    def compress_for_storage(self, data: str | dict[str, Any]) -> str:
        """Compress data for storage in database text fields.

        Args:
            data: Data to compress

        Returns:
            Base64-encoded compressed data as string
        """
        if data is None:
            return None

        try:
            compressed_bytes, stats = self.compress_data(data)

            # Encode as base64 for storage in text fields
            encoded_data = base64.b64encode(compressed_bytes).decode("ascii")

            logger.debug(
                f"Prepared data for storage: {stats.original_size} -> {stats.compressed_size} bytes "
                f"({stats.space_saved_percent:.1f}% saved)"
            )

            return encoded_data

        except ValueError:
            # If compression is not worthwhile, return original data as JSON string
            if isinstance(data, dict):
                if ORJSON_AVAILABLE:
                    return orjson.dumps(data).decode("utf-8")
                else:
                    return json.dumps(data, ensure_ascii=False)
            return str(data)

    def decompress_from_storage(
        self, stored_data: str, expected_type: str = "dict"
    ) -> str | dict[str, Any]:
        """Decompress data from database storage.

        Args:
            stored_data: Base64-encoded compressed data or JSON string
            expected_type: Expected data type ('str', 'dict')

        Returns:
            Decompressed data
        """
        try:
            # Try to decode as base64 first (compressed data)
            compressed_bytes = base64.b64decode(stored_data.encode("ascii"))
            decompressed_data, _ = self.decompress_data(compressed_bytes, expected_type)
            return decompressed_data

        except (base64.binascii.Error, ValueError, UnicodeDecodeError):
            # If base64 decoding fails, assume it's uncompressed JSON
            try:
                if expected_type == "dict":
                    return json.loads(stored_data)
                return stored_data
            except json.JSONDecodeError:
                # If JSON parsing fails, return as string
                return stored_data

    def _estimate_size(self, data: str | bytes | dict[str, Any]) -> int:
        """Estimate the size of data in bytes.

        Args:
            data: Data to estimate size for

        Returns:
            Estimated size in bytes
        """
        if isinstance(data, bytes):
            return len(data)
        elif isinstance(data, str):
            return len(data.encode("utf-8"))
        elif isinstance(data, dict):
            if ORJSON_AVAILABLE:
                return len(orjson.dumps(data))
            else:
                return len(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        else:
            return len(str(data).encode("utf-8"))

    def get_compression_stats(self) -> dict[str, Any]:
        """Get compression statistics.

        Returns:
            Dictionary of compression statistics
        """
        total_original = self._stats["total_original_bytes"]
        total_compressed = self._stats["total_compressed_bytes"]

        return {
            "total_compressions": self._stats["total_compressions"],
            "total_decompressions": self._stats["total_decompressions"],
            "total_original_bytes": total_original,
            "total_compressed_bytes": total_compressed,
            "total_space_saved_bytes": total_original - total_compressed,
            "average_compression_ratio": (
                (total_compressed / total_original) if total_original > 0 else 0.0
            ),
            "total_compression_time_ms": self._stats["total_compression_time_ms"],
            "total_decompression_time_ms": self._stats["total_decompression_time_ms"],
            "average_compression_time_ms": (
                self._stats["total_compression_time_ms"] / self._stats["total_compressions"]
                if self._stats["total_compressions"] > 0
                else 0.0
            ),
            "average_decompression_time_ms": (
                self._stats["total_decompression_time_ms"] / self._stats["total_decompressions"]
                if self._stats["total_decompressions"] > 0
                else 0.0
            ),
            "compressions_skipped": self._stats["compressions_skipped"],
            "compressions_rejected": self._stats["compressions_rejected"],
            "compression_efficiency": (
                (total_original - total_compressed) / total_original * 100
                if total_original > 0
                else 0.0
            ),
        }

    def reset_stats(self) -> None:
        """Reset compression statistics."""
        self._stats = {
            "total_compressions": 0,
            "total_decompressions": 0,
            "total_original_bytes": 0,
            "total_compressed_bytes": 0,
            "total_compression_time_ms": 0.0,
            "total_decompression_time_ms": 0.0,
            "compressions_skipped": 0,
            "compressions_rejected": 0,
        }
        logger.info("Compression statistics reset")


# Global compression manager instance
compression_manager = CompressionManager()
