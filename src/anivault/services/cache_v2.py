"""Cache v2 implementation for AniVault.

This module provides a high-performance, file-based JSON caching system
optimized for TMDB API responses. It uses orjson for fast serialization
and includes TTL support with automatic cleanup.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

try:
    import orjson
except ImportError:
    orjson = None  # type: ignore[assignment]

from anivault.core.statistics import StatisticsCollector
from anivault.shared.constants import Cache
from anivault.shared.errors import (
    DomainError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)
from anivault.shared.logging import log_operation_error, log_operation_success

logger = logging.getLogger(__name__)


class CacheEntry(BaseModel):
    """Schema for cache entries with metadata and TTL support.

    This model defines the structure of cached data, including the actual
    data payload, creation timestamp, and expiration information.

    Attributes:
        data: The actual cached data payload.
        created_at: ISO timestamp when the entry was created.
        expires_at: ISO timestamp when the entry expires (None for no expiration).
        cache_type: Type of cache entry ('search' or 'details').
        key_hash: SHA-256 hash of the original key for verification.
    """

    model_config = ConfigDict(
        # Optimize JSON serialization for cache performance
        json_encoders={
            # Custom encoders for specific types if needed
        },
        # Use orjson for better performance in cache operations
        json_schema_extra={
            "example": {
                "data": {"title": "Attack on Titan", "id": 12345},
                "created_at": "2024-01-01T00:00:00Z",
                "expires_at": "2024-01-08T00:00:00Z",
                "cache_type": "search",
                "key_hash": "abc123...",
            },
        },
    )

    data: dict[str, Any] = Field(..., description="The cached data payload")
    created_at: str = Field(..., description="ISO timestamp when entry was created")
    expires_at: str | None = Field(None, description="ISO timestamp when entry expires")
    cache_type: str = Field(
        ...,
        description="Type of cache entry ('search' or 'details')",
    )
    key_hash: str = Field(..., description="SHA-256 hash of the original key")


class JSONCacheV2:
    """High-performance JSON cache with TTL support and automatic cleanup.

    This cache system is optimized for storing TMDB API responses with
    separate subdirectories for different types of cached data. It uses
    orjson for fast serialization and includes comprehensive error handling.

    Args:
        cache_dir: Base directory path where cache files will be stored.
                  Subdirectories 'search/' and 'details/' will be created.
    """

    def __init__(
        self,
        cache_dir: Path | str,
        statistics: StatisticsCollector | None = None,
    ) -> None:
        """Initialize the cache with directory structure.

        Args:
            cache_dir: Base directory path for cache storage.
                      Will create subdirectories for different cache types.
            statistics: Optional statistics collector for performance tracking.

        Raises:
            InfrastructureError: If orjson library is not installed or directory creation fails.
        """
        context = ErrorContext(
            operation="initialize_cache",
            additional_data={"cache_dir": str(cache_dir)},
        )

        if orjson is None:
            error = InfrastructureError(
                code=ErrorCode.DEPENDENCY_MISSING,  # noqa: F823
                message="orjson library is not installed. Install it with: pip install orjson",
                context=context,
            )
            log_operation_error(
                logger=logger,
                operation="initialize_cache",
                error=error,
                additional_context={"cache_dir": str(cache_dir)},
            )
            raise error from error

        try:
            self.cache_dir = Path(cache_dir)
            self.search_dir = self.cache_dir / "search"
            self.details_dir = self.cache_dir / "details"
            self.statistics = statistics or StatisticsCollector()

            # Create cache directories
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.search_dir.mkdir(parents=True, exist_ok=True)
            self.details_dir.mkdir(parents=True, exist_ok=True)

            # Cleanup expired entries on startup
            try:
                purged_count = self.purge_expired()
                if purged_count > 0:
                    logger.info(
                        "Cleaned up %d expired cache entries on startup",
                        purged_count,
                    )
            except Exception as e:
                # Boundary: Accept any Exception, convert to safe logging
                from anivault.shared.errors import AniVaultError, ErrorCode

                # Convert generic exception to AniVaultError for type safety
                anivault_error = AniVaultError(
                    ErrorCode.CACHE_ERROR,
                    f"Cleanup failed: {e!s}",
                    context,
                )

                log_operation_error(
                    logger=logger,
                    operation="cleanup_expired_on_startup",
                    error=anivault_error,
                    additional_context=context,
                )
                logger.warning(
                    "Failed to cleanup expired entries on startup: %s",
                    str(e),
                )

            log_operation_success(
                logger=logger,
                operation="initialize_cache",
                duration_ms=0,
                context=context,
            )

            logger.debug(
                "Initialized JSONCacheV2 with directories: %s, %s, %s",
                self.cache_dir,
                self.search_dir,
                self.details_dir,
            )

        except Exception as e:
            error = InfrastructureError(
                code=ErrorCode.DIRECTORY_CREATION_FAILED,
                message=f"Failed to initialize cache directory: {cache_dir}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="initialize_cache",
                error=error,
                additional_context=context,
            )
            raise error from error

    def _generate_file_path(
        self,
        key: str,
        cache_type: str = Cache.TYPE_SEARCH,
    ) -> Path:
        """Generate cache file path from key and cache type.

        Args:
            key: The cache key (will be normalized and hashed).
            cache_type: Type of cache ('search' or 'details').

        Returns:
            Path object pointing to the cache file.

        Raises:
            DomainError: If cache_type is invalid.
        """
        context = ErrorContext(
            operation="generate_file_path",
            additional_data={"key": key, "cache_type": cache_type},
        )

        # Normalize the key (remove special characters, convert to lowercase)
        normalized_key = key.lower().strip()

        # Generate SHA-256 hash
        key_hash = hashlib.sha256(normalized_key.encode("utf-8")).hexdigest()

        # Select appropriate directory
        if cache_type == Cache.TYPE_SEARCH:
            cache_dir = self.search_dir
        elif cache_type == Cache.TYPE_DETAILS:
            cache_dir = self.details_dir
        else:
            error = DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid cache_type: {cache_type}. Must be 'search' or 'details'",
                context=context,
            )
            log_operation_error(
                logger=logger,
                operation="generate_file_path",
                error=error,
                additional_context=context,
            )
            raise error from error

        # Return file path with .json extension
        return cache_dir / f"{key_hash}.json"

    def set_cache(
        self,
        key: str,
        data: dict[str, Any],
        cache_type: str = Cache.TYPE_SEARCH,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store data in the cache with optional TTL.

        Args:
            key: Unique identifier for the cache entry.
            data: Dictionary containing the data to cache.
            cache_type: Type of cache ('search' or 'details').
            ttl_seconds: Time-to-live in seconds (None for no expiration).

        Raises:
            InfrastructureError: If file I/O operations fail.
            DomainError: If cache_type is invalid or data validation fails.
        """
        context = ErrorContext(
            operation="cache_set",
            additional_data={
                "key": key,
                "cache_type": cache_type,
                "ttl_seconds": ttl_seconds,
            },
        )

        try:
            # Generate file path
            cache_file = self._generate_file_path(key, cache_type)

            # Calculate timestamps
            now = datetime.now(timezone.utc)
            created_at = now.isoformat()
            expires_at = None

            if ttl_seconds is not None and ttl_seconds >= 0:
                expires_at = now + timedelta(seconds=ttl_seconds)
                expires_at_str = expires_at.isoformat()
            else:
                expires_at_str = None

            # Generate key hash for verification
            key_hash = hashlib.sha256(key.lower().strip().encode("utf-8")).hexdigest()

            # Create cache entry
            entry = CacheEntry(
                data=data,
                created_at=created_at,
                expires_at=expires_at_str,
                cache_type=cache_type,
                key_hash=key_hash,
            )

            # Serialize with orjson using model_dump_json for better performance
            try:
                json_data = entry.model_dump_json()
            except (orjson.JSONEncodeError, ValueError) as e:
                error = DomainError(  # noqa: F823
                    code=ErrorCode.CACHE_SERIALIZATION_ERROR,
                    message=f"Failed to serialize cache data for key '{key}': {e!s}",
                    context=ErrorContext(
                        operation="cache_set",
                        additional_data={
                            "key": key,
                            "cache_type": cache_type,
                            "data_size": len(str(data)),
                            "json_error": str(e),
                        },
                    ),
                    original_error=e,
                )
                log_operation_error(
                    logger=logger,
                    error=error,
                    operation="cache_set",
                    additional_context=context.additional_data if context else None,
                )
                raise error from error

            # Write to cache file
            try:
                with open(cache_file, "wb") as f:
                    # Boundary: Convert str to bytes for binary write
                    json_bytes = json_data.encode("utf-8")
                    f.write(json_bytes)
            except OSError as e:
                # Boundary: Accept any exception, convert to safe type
                from anivault.shared.errors import DomainError

                error = DomainError(
                    code=ErrorCode.FILE_WRITE_ERROR,
                    message=f"Failed to write cache file for key '{key}': {e!s}",
                    context=ErrorContext(
                        operation="cache_set",
                        additional_data={
                            "key": key,
                            "cache_type": cache_type,
                            "file_path": str(cache_file),
                            "file_size": len(json_data),
                            "io_error": str(e),
                        },
                    ),
                    original_error=e,
                )
                log_operation_error(
                    logger=logger,
                    error=error,
                    operation="cache_set",
                    additional_context=context.additional_data if context else None,
                )
                raise error from error

            # Record cache operation
            self.statistics.record_cache_operation("set", hit=False, key=key)

            log_operation_success(
                logger=logger,
                operation="cache_set",
                duration_ms=0,
                context=context,
            )

            logger.debug(
                "Cached data for key '%s' (%s) in %s",
                key,
                cache_type,
                cache_file,
            )

        except DomainError:
            # Re-raise domain errors (like invalid cache_type) as they are validation errors
            raise
        except Exception as e:
            error = InfrastructureError(
                code=ErrorCode.FILE_WRITE_ERROR,
                message=f"Failed to cache data for key '{key}': {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="cache_set",
                error=error,
                additional_context=context,
            )
            raise error from error

    def get(  # noqa: PLR0911
        self,
        key: str,
        cache_type: str = Cache.TYPE_SEARCH,
    ) -> dict[str, Any] | None:
        """Retrieve data from the cache.

        Args:
            key: Unique identifier for the cache entry.
            cache_type: Type of cache ('search' or 'details').

        Returns:
            The cached data if found and not expired, None otherwise.

        Raises:
            InfrastructureError: If file I/O operations fail.
            DomainError: If cache_type is invalid.
        """
        context = ErrorContext(
            operation="cache_get",
            additional_data={"key": key, "cache_type": cache_type},
        )

        try:
            # Generate file path
            cache_file = self._generate_file_path(key, cache_type)

            if not cache_file.exists():
                self.statistics.record_cache_miss(cache_type)
                return None  # Cache miss

            # Read and parse the cache file
            try:
                with open(cache_file, "rb") as f:
                    json_data = f.read()
            except OSError as e:
                error = InfrastructureError(
                    code=ErrorCode.FILE_READ_ERROR,
                    message=f"Failed to read cache file for key '{key}': {e!s}",
                    context=ErrorContext(
                        operation="cache_get",
                        additional_data={
                            "key": key,
                            "cache_type": cache_type,
                            "file_path": str(cache_file),
                            "io_error": str(e),
                        },
                    ),
                    original_error=e,
                )
                log_operation_error(
                    logger=logger,
                    error=error,
                    operation="cache_get",
                    additional_context=context.additional_data if context else None,
                )
                return None

            # Deserialize with orjson
            try:
                entry_dict = orjson.loads(json_data)
                entry = CacheEntry.model_validate(entry_dict)
            except orjson.JSONDecodeError as e:
                # Handle corrupted cache file
                self._handle_corrupted_cache_file(cache_file, key, e, context)
                return None

            # Verify key hash
            expected_hash = hashlib.sha256(
                key.lower().strip().encode("utf-8"),
            ).hexdigest()
            if entry.key_hash != expected_hash:
                logger.warning(
                    "Key hash mismatch for '%s', treating as cache miss",
                    key,
                )
                return None

            # Check expiration
            if entry.expires_at is not None:
                try:
                    expires_at = datetime.fromisoformat(
                        entry.expires_at.replace("Z", "+00:00"),
                    )
                    if datetime.now(timezone.utc) > expires_at:
                        logger.debug("Cache entry expired for key '%s'", key)
                        # Delete expired file
                        cache_file.unlink()
                        return None
                except ValueError as e:
                    logger.warning(
                        "Invalid expiration timestamp for key '%s': %s",
                        key,
                        str(e),
                    )
                    return None

            logger.debug("Cache hit for key '%s' (%s)", key, cache_type)
            self.statistics.record_cache_hit(cache_type)
            return entry.data

        except FileNotFoundError:
            self.statistics.record_cache_miss(cache_type)
            return None  # Cache miss
        except DomainError:
            # Re-raise domain errors (like invalid cache_type) as they are validation errors
            raise
        except Exception as e:
            # Try to clean up corrupted file
            try:
                if "cache_file" in locals() and cache_file.exists():
                    cache_file.unlink()
            except (OSError, NameError):
                pass

            # Log the error but don't raise it for cache operations
            # Cache misses are not considered errors
            error = InfrastructureError(
                code=ErrorCode.FILE_READ_ERROR,
                message=f"Failed to read cache data for key '{key}': {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="cache_get",
                error=error,
                additional_context=context,
            )
            return None

    def _handle_corrupted_cache_file(
        self,
        cache_file: Path,
        key: str,
        json_error: orjson.JSONDecodeError,
        context: ErrorContext,
    ) -> None:
        """Handle corrupted cache file by backing it up and logging the error.

        Args:
            cache_file: Path to the corrupted cache file
            key: Cache key that failed to load
            json_error: The JSON decode error that occurred
            context: Error context for logging
        """
        try:
            # Create backup filename with timestamp
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_file = cache_file.with_suffix(f".corrupted.{timestamp}.json")

            # Move corrupted file to backup location
            cache_file.rename(backup_file)

            # Log the corruption event
            logger.warning(
                "Cache file corrupted for key '%s', backed up to %s. "
                "JSON decode error: %s",
                key,
                backup_file,
                str(json_error),
            )

            # Create domain error for the corruption
            error = DomainError(
                code=ErrorCode.CACHE_CORRUPTED,
                message=f"Cache file corrupted for key '{key}': {json_error!s}",
                context=ErrorContext(
                    operation="cache_get",
                    additional_data={
                        "key": key,
                        "file_path": str(cache_file),
                        "backup_path": str(backup_file),
                        "file_size": (
                            cache_file.stat().st_size if cache_file.exists() else 0
                        ),
                        "json_error": str(json_error),
                    },
                ),
                original_error=json_error,
            )

            log_operation_error(
                logger=logger,
                error=error,
                operation="cache_get",
                additional_context=context.additional_data if context else None,
            )

        except OSError:
            # If backup fails, just log and continue
            logger.exception(
                "Failed to backup corrupted cache file %s",
                cache_file,
            )

    def delete(self, key: str, cache_type: str = Cache.TYPE_SEARCH) -> bool:
        """Delete a specific cache entry.

        Args:
            key: Unique identifier for the cache entry.
            cache_type: Type of cache ('search' or 'details').

        Returns:
            True if the entry was deleted, False if it didn't exist.

        Raises:
            InfrastructureError: If file I/O operations fail.
            DomainError: If cache_type is invalid.
        """
        context = ErrorContext(
            operation="cache_delete",
            additional_data={"key": key, "cache_type": cache_type},
        )

        try:
            cache_file = self._generate_file_path(key, cache_type)
            if cache_file.exists():
                cache_file.unlink()
                logger.debug("Deleted cache entry for key '%s' (%s)", key, cache_type)
                return True
            return False
        except DomainError:
            # Re-raise domain errors (like invalid cache_type) as they are validation errors
            raise
        except Exception as e:
            error = InfrastructureError(
                code=ErrorCode.FILE_DELETE_ERROR,
                message=f"Error deleting cache entry for key '{key}': {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="cache_delete",
                error=error,
                context=context,
            )
            return False

    def clear(self, cache_type: str | None = None) -> int:
        """Clear cache entries.

        Args:
            cache_type: Type of cache to clear ('search', 'details', or None for all).

        Returns:
            Number of files deleted.

        Raises:
            InfrastructureError: If file I/O operations fail.
            DomainError: If cache_type is invalid.
        """
        context = ErrorContext(
            operation="cache_clear",
            additional_data={"cache_type": cache_type},
        )

        deleted_count = 0

        try:
            if cache_type is None:
                # Clear all cache types
                for cache_dir in [self.search_dir, self.details_dir]:
                    for cache_file in cache_dir.glob("*.json"):
                        cache_file.unlink()
                        deleted_count += 1
            elif cache_type in ["search", "details"]:
                # Clear specific cache type
                cache_dir = (
                    self.search_dir
                    if cache_type == Cache.TYPE_SEARCH
                    else self.details_dir
                )
                for cache_file in cache_dir.glob("*.json"):
                    cache_file.unlink()
                    deleted_count += 1
            else:
                error = DomainError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Invalid cache_type: {cache_type}",
                    context=context,
                )
                log_operation_error(
                    logger=logger,
                    operation="cache_clear",
                    error=error,
                    additional_context=context,
                )
                raise error from error

            log_operation_success(
                logger=logger,
                operation="cache_clear",
                duration_ms=0,
                context=context,
            )

            logger.info(
                "Cleared %d cache entries (%s)",
                deleted_count,
                cache_type or "all",
            )

        except DomainError:
            # Re-raise domain errors (like invalid cache_type) as they are validation errors
            raise
        except Exception as e:
            error = InfrastructureError(
                code=ErrorCode.FILE_DELETE_ERROR,
                message=f"Error clearing cache: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="cache_clear",
                error=error,
                additional_context=context,
            )
            raise error from error

        return deleted_count

    def get_cache_info(self, cache_type: str | None = None) -> dict[str, Any]:
        """Get information about the cache.

        Args:
            cache_type: Type of cache to analyze ('search', 'details', or None for all).

        Returns:
            Dictionary containing cache statistics and information.

        Raises:
            InfrastructureError: If file I/O operations fail.
            DomainError: If cache_type is invalid.
        """
        context = ErrorContext(
            operation="get_cache_info",
            additional_data={"cache_type": cache_type},
        )

        total_files = 0
        valid_entries = 0
        expired_entries = 0
        total_size = 0

        try:
            if cache_type is None:
                cache_dirs = [self.search_dir, self.details_dir]
            elif cache_type in ["search", "details"]:
                cache_dirs = [
                    self.search_dir
                    if cache_type == Cache.TYPE_SEARCH
                    else self.details_dir,
                ]
            else:
                error = DomainError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Invalid cache_type: {cache_type}",
                    context=context,
                )
                log_operation_error(
                    logger=logger,
                    operation="get_cache_info",
                    error=error,
                    additional_context=context,
                )
                raise error from error

            for cache_dir in cache_dirs:
                for cache_file in cache_dir.glob("*.json"):
                    total_files += 1
                    total_size += cache_file.stat().st_size

                    try:
                        # Try to read and validate the cache entry
                        with open(cache_file, "rb") as f:
                            json_data = f.read()

                        entry_dict = orjson.loads(json_data)
                        entry = CacheEntry.model_validate(entry_dict)

                        # Check if expired
                        if entry.expires_at is not None:
                            expires_at = datetime.fromisoformat(
                                entry.expires_at.replace("Z", "+00:00"),
                            )
                            if datetime.now(timezone.utc) > expires_at:
                                expired_entries += 1
                            else:
                                valid_entries += 1
                        else:
                            valid_entries += 1

                    except Exception:
                        # Corrupted or invalid file
                        expired_entries += 1

            log_operation_success(
                logger=logger,
                operation="get_cache_info",
                duration_ms=0,
                context=context,
            )

        except DomainError:
            # Re-raise domain errors (like invalid cache_type) as they are validation errors
            raise
        except Exception as e:
            error = InfrastructureError(
                code=ErrorCode.FILE_READ_ERROR,
                message=f"Error getting cache info: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="get_cache_info",
                error=error,
                additional_context=context,
            )
            raise error from error

        return {
            "total_files": total_files,
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "total_size_bytes": total_size,
            "cache_directory": str(self.cache_dir),
            "cache_type": cache_type or "all",
        }

    def purge_expired(self, cache_type: str | None = None) -> int:
        """Remove all expired cache entries.

        Args:
            cache_type: Type of cache to purge ('search', 'details', or None for all).

        Returns:
            Number of expired entries removed.

        Raises:
            InfrastructureError: If file I/O operations fail.
            DomainError: If cache_type is invalid.
        """
        context = ErrorContext(
            operation="purge_expired",
            additional_data={"cache_type": cache_type},
        )

        purged_count = 0

        try:
            if cache_type is None:
                cache_dirs = [self.search_dir, self.details_dir]
            elif cache_type in ["search", "details"]:
                cache_dirs = [
                    self.search_dir
                    if cache_type == Cache.TYPE_SEARCH
                    else self.details_dir,
                ]
            else:
                error = DomainError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Invalid cache_type: {cache_type}",
                    context=context,
                )
                log_operation_error(
                    logger=logger,
                    operation="purge_expired",
                    error=error,
                    additional_context=context,
                )
                raise error from error

            for cache_dir in cache_dirs:
                for cache_file in cache_dir.glob("*.json"):
                    try:
                        # Read and check expiration
                        with open(cache_file, "rb") as f:
                            json_data = f.read()

                        entry_dict = orjson.loads(json_data)
                        entry = CacheEntry.model_validate(entry_dict)

                        # Check if expired
                        if entry.expires_at is not None:
                            expires_at = datetime.fromisoformat(
                                entry.expires_at.replace("Z", "+00:00"),
                            )
                            if datetime.now(timezone.utc) > expires_at:
                                cache_file.unlink()
                                purged_count += 1

                    except Exception:
                        # Corrupted file, remove it
                        cache_file.unlink()
                        purged_count += 1

            log_operation_success(
                logger=logger,
                operation="purge_expired",
                duration_ms=0,
                context=context,
            )

            logger.info(
                "Purged %d expired cache entries (%s)",
                purged_count,
                cache_type or "all",
            )

        except DomainError:
            # Re-raise domain errors (like invalid cache_type) as they are validation errors
            raise
        except Exception as e:
            error = InfrastructureError(
                code=ErrorCode.FILE_DELETE_ERROR,
                message=f"Error purging expired cache entries: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="purge_expired",
                error=error,
                additional_context=context,
            )
            raise error from error

        return purged_count
