"""Cache adapter for abstracting cache operations.

This module provides a protocol-based abstraction layer for cache operations,
allowing the matching engine to work with different cache backends without
direct coupling to implementation details.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Protocol, cast

from anivault.core.matching.cache_models import CachedSearchData
from anivault.services.cache import (
    SQLiteCacheDB,
)
from anivault.shared.constants import Cache
from anivault.shared.utils.dataclass_serialization import from_dict, to_dict

logger = logging.getLogger(__name__)


class CacheAdapterProtocol(Protocol):
    """Protocol for cache adapter implementations.

    This protocol defines the interface that all cache adapters must implement,
    providing a consistent API for cache operations regardless of the underlying
    storage backend.

    Attributes:
        language: Language code for cache key generation (e.g., 'ko-KR')

    Example:
        >>> cache_adapter: CacheAdapterProtocol = SQLiteCacheAdapter(db)
        >>> data = cache_adapter.get("search:movie:test", "search")
        >>> cache_adapter.set("search:movie:test", {"results": [...]}, "search")
    """

    language: str

    def get(
        self,
        key: str,
        cache_type: str = Cache.TYPE_SEARCH,
    ) -> CachedSearchData | None:
        """Retrieve cached data by key.

        Args:
            key: Cache key identifier
            cache_type: Type of cache (e.g., 'search', 'details')

        Returns:
            Strongly-typed cached data model, or None if not found or expired
        """

    def delete(self, key: str, cache_type: str = Cache.TYPE_SEARCH) -> None:
        """Delete cached data by key.

        Args:
            key: Cache key identifier
            cache_type: Type of cache (e.g., 'search', 'details')
        """

    def set(
        self,
        key: str,
        data: CachedSearchData,
        cache_type: str = Cache.TYPE_SEARCH,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store data in cache with optional TTL.

        Args:
            key: Cache key identifier
            data: Strongly-typed cached data model
            cache_type: Type of cache (e.g., 'search', 'details')
            ttl_seconds: Time-to-live in seconds (None for default TTL)
        """


class SQLiteCacheAdapter:
    """SQLite-based implementation of cache adapter protocol.

    This adapter wraps SQLiteCacheDB to provide a simplified, protocol-compliant
    interface for cache operations. It includes security features like key length
    validation and automatic hashing of overly long keys.

    Attributes:
        backend: SQLiteCacheDB instance for actual storage operations
        language: Language code for cache key generation (e.g., 'ko-KR', 'en-US')
        MAX_KEY_LENGTH: Maximum allowed cache key length (256 characters)

    Security:
        - Cache keys exceeding MAX_KEY_LENGTH are automatically hashed
        - Prevents potential DoS attacks via extremely long keys
        - Maintains key uniqueness through SHA-256 hashing

    Example:
        >>> # SQLiteCacheDB is imported at runtime
        >>> db = SQLiteCacheDB(Path("cache.db"))
        >>> adapter = SQLiteCacheAdapter(db, language="ko-KR")
        >>> adapter.set("search:anime:test", {"results": []})
        >>> data = adapter.get("search:anime:test")
    """

    MAX_KEY_LENGTH = 256  # Maximum cache key length before hashing

    def __init__(self, backend: Any, language: str = "ko-KR") -> None:
        """Initialize cache adapter with SQLite backend.

        Args:
            backend: Cache backend instance (SQLiteCacheDB or compatible)
            language: Language code for cache key generation (default: 'ko-KR')
        """
        # Import at runtime to avoid dependency layer violation

        if not isinstance(backend, SQLiteCacheDB):
            msg = f"Expected SQLiteCacheDB, got {type(backend)}"
            raise TypeError(msg)

        self.backend = backend
        self.language = language

    def get(
        self,
        key: str,
        cache_type: str = Cache.TYPE_SEARCH,
    ) -> CachedSearchData | None:
        """Retrieve cached data by key.

        Args:
            key: Cache key identifier (will be enhanced with language)
            cache_type: Type of cache (default: 'search')

        Returns:
            Strongly-typed cached data model, or None if not found or expired

        Example:
            >>> data = adapter.get("attack on titan", "search")
            >>> if data:
            ...     for result in data.results:
            ...         print(result.title)
        """
        # Enhance key with language for language-sensitive caching
        enhanced_key = self._enhance_key_with_language(key)
        validated_key = self._validate_key(enhanced_key)

        try:
            cached_dict = self.backend.get(validated_key, cache_type)

            if cached_dict is not None:
                logger.debug(
                    "Cache hit: key=%s (length=%d), type=%s",
                    key[:50],  # Log only first 50 chars
                    len(key),
                    cache_type,
                )
                # Deserialize dict to dataclass (type-safe!)

                return cast("CachedSearchData", from_dict(CachedSearchData, cached_dict))

            logger.debug(
                "Cache miss: key=%s (length=%d), type=%s",
                key[:50],
                len(key),
                cache_type,
            )
            return None

        except (KeyError, ValueError, TypeError, AttributeError, IndexError):
            # Data parsing errors during cache deserialization
            logger.exception(
                "Cache get operation failed (parsing error) for key=%s, type=%s",
                key[:50],
                cache_type,
            )
            return None
        except Exception:  # pylint: disable=broad-exception-caught
            # Unexpected errors (includes Pydantic validation errors)
            logger.exception(
                "Cache get operation failed (unexpected error) for key=%s, type=%s",
                key[:50],
                cache_type,
            )
            return None

    def delete(self, key: str, cache_type: str = Cache.TYPE_SEARCH) -> None:
        """Delete cached data by key.

        Args:
            key: Cache key identifier (will be enhanced with language)
            cache_type: Type of cache (default: 'search')

        Example:
            >>> adapter.delete("attack on titan", "search")
        """
        # Enhance key with language
        enhanced_key = self._enhance_key_with_language(key)
        validated_key = self._validate_key(enhanced_key)

        try:
            self.backend.delete(validated_key, cache_type)

            logger.debug(
                "Cache delete: key=%s (length=%d), type=%s",
                key[:50],
                len(key),
                cache_type,
            )

        except (KeyError, ValueError, TypeError):
            # Data parsing errors during cache delete
            logger.exception(
                "Cache delete operation failed (parsing error) for key=%s, type=%s",
                key[:50],
                cache_type,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            # Unexpected errors
            logger.exception(
                "Cache delete operation failed (unexpected error) for key=%s, type=%s",
                key[:50],
                cache_type,
            )

    def set(
        self,
        key: str,
        data: CachedSearchData,
        cache_type: str = Cache.TYPE_SEARCH,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store data in cache with optional TTL.

        Args:
            key: Cache key identifier (will be enhanced with language)
            data: Strongly-typed cached data model
            cache_type: Type of cache (default: 'search')
            ttl_seconds: Time-to-live in seconds (None for default TTL)

        Example:
            >>> from anivault.core.matching.cache_models import CachedSearchData
            >>> cached_data = CachedSearchData(results=[], language="ko-KR")
            >>> adapter.set("attack on titan", cached_data, "search", 3600)
        """
        # Enhance key with language for language-sensitive caching
        enhanced_key = self._enhance_key_with_language(key)
        validated_key = self._validate_key(enhanced_key)

        try:
            # Serialize dataclass to dict for backend storage

            data_dict = to_dict(data)

            self.backend.set_cache(
                key=validated_key,
                data=data_dict,
                cache_type=cache_type,
                ttl_seconds=ttl_seconds,
            )

            logger.debug(
                "Cache set: key=%s (length=%d), type=%s, ttl=%s",
                key[:50],
                len(key),
                cache_type,
                ttl_seconds,
            )

        except (KeyError, ValueError, TypeError, AttributeError):
            # Data parsing errors during cache serialization
            logger.exception(
                "Cache set operation failed (parsing error) for key=%s, type=%s",
                key[:50],
                cache_type,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            # Unexpected errors
            logger.exception(
                "Cache set operation failed (unexpected error) for key=%s, type=%s",
                key[:50],
                cache_type,
            )

    def _validate_key(self, key: str) -> str:
        """Validate and process cache key.

        If the key exceeds MAX_KEY_LENGTH, it is replaced with its SHA-256 hash
        to prevent potential DoS attacks via extremely long keys while maintaining
        uniqueness.

        Args:
            key: Original cache key

        Returns:
            Validated key (original if within length limit, hash otherwise)

        Example:
            >>> adapter = SQLiteCacheAdapter(backend)
            >>> short_key = adapter._validate_key("short")
            >>> short_key
            'short'
            >>> long_key = "a" * 300
            >>> hashed = adapter._validate_key(long_key)
            >>> len(hashed)
            64  # SHA-256 hash length
        """
        if len(key) > self.MAX_KEY_LENGTH:
            # Hash overly long keys to prevent DoS
            hashed_key = hashlib.sha256(key.encode("utf-8")).hexdigest()

            logger.warning(
                "Cache key exceeds MAX_KEY_LENGTH (%d > %d), using hash: %s",
                len(key),
                self.MAX_KEY_LENGTH,
                hashed_key[:16],  # Log only prefix
            )

            return hashed_key

        return key

    def _enhance_key_with_language(self, key: str) -> str:
        """Enhance cache key with language for language-sensitive caching.

        Args:
            key: Original cache key (e.g., normalized title)

        Returns:
            Enhanced key with language suffix (e.g., "title:lang=ko-KR")

        Example:
            >>> adapter = SQLiteCacheAdapter(backend, language="ko-KR")
            >>> enhanced = adapter._enhance_key_with_language("attack on titan")
            >>> enhanced
            'attack on titan:lang=ko-KR'
        """
        return f"{key}:lang={self.language}"
