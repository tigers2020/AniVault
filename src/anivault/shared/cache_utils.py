"""Cache utility functions for TMDB API request normalization.

This module provides utilities for generating consistent cache keys from TMDB API
request parameters. It ensures that identical API requests produce identical cache
keys regardless of parameter order or case variations.

Key Features:
    - Parameter normalization (lowercase, sorted, None removal)
    - SHA-256 hash generation for secure key storage
    - Support for both search and details API patterns

Example:
    >>> from anivault.shared.cache_utils import generate_cache_key
    >>> key, hash = generate_cache_key("search", None, {"query": "titan", "lang": "ko"})
    >>> print(key)
    'search:lang=ko:query=titan'

Author: AniVault Development Team
Date: 2025-01-06
"""

from __future__ import annotations

import hashlib
from typing import Any


def canonical_params(params: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize parameters for consistent cache key generation.

    Normalization rules:
        1. Remove None and empty string values
        2. Convert string keys to lowercase
        3. Convert string values to lowercase
        4. Keys are sorted in generate_cache_key()

    Args:
        params: Query parameters dictionary. Can be None.

    Returns:
        Normalized parameters dictionary with lowercase keys/values and
        None/empty values removed. Returns empty dict if params is None.

    Example:
        >>> canonical_params({"Lang": "KO", "query": None, "page": 1})
        {'lang': 'ko', 'page': 1}

        >>> canonical_params({"Query": "Attack", "Empty": ""})
        {'query': 'attack'}

        >>> canonical_params(None)
        {}

    Notes:
        - Non-string values (int, bool, etc.) are preserved as-is
        - Empty strings are treated as None and removed
        - Order is not guaranteed (sorting happens in generate_cache_key)
    """
    if not params:
        return {}

    # Remove None/empty values
    filtered = {k: v for k, v in params.items() if v is not None and v != ""}

    # Normalize keys and values
    normalized = {}
    for k, v in filtered.items():
        key_lower = k.lower()
        # Only lowercase string values, preserve other types
        value_lower = v.lower() if isinstance(v, str) else v
        normalized[key_lower] = value_lower

    return normalized


def generate_cache_key(
    object_type: str,
    object_id: str | int | None = None,
    params: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Generate cache key and SHA-256 hash from TMDB API request parameters.

    This function creates a canonical cache key from TMDB API request parameters,
    ensuring that identical requests produce identical keys regardless of parameter
    order or case variations.

    Cache key format:
        - With ID: "{object_type}:{object_id}:{sorted_params}"
        - Without ID: "{object_type}:{sorted_params}"

    Args:
        object_type: API endpoint type. Must be non-empty.
            Examples: "search", "details", "popular", "discover"
        object_id: TMDB object ID. Optional, required for details requests.
            Examples: 1429 (TV show ID), "550" (Movie ID as string)
        params: Query parameters dictionary. Optional.
            Examples: {"query": "titan", "lang": "ko", "page": 1}

    Returns:
        Tuple of (cache_key, key_hash):
            - cache_key: Human-readable key with sorted parameters
            - key_hash: SHA-256 hash (64 hex characters)

    Raises:
        ValueError: If object_type is empty or None

    Example:
        Basic search:
        >>> key, hash = generate_cache_key("search", None, {"query": "titan", "lang": "ko"})
        >>> print(key)
        'search:lang=ko:query=titan'
        >>> len(hash)
        64

        Details with ID:
        >>> key, hash = generate_cache_key("details", 1429, {"lang": "ko"})
        >>> print(key)
        'details:1429:lang=ko'

        Popular without params:
        >>> key, hash = generate_cache_key("popular", None, None)
        >>> print(key)
        'popular'

        Parameter order independence:
        >>> key1, _ = generate_cache_key("search", None, {"a": "1", "b": "2"})
        >>> key2, _ = generate_cache_key("search", None, {"b": "2", "a": "1"})
        >>> key1 == key2
        True

    Notes:
        - Parameters are automatically normalized (lowercase, sorted, None removed)
        - object_id is converted to string if provided as int
        - Empty params dict is treated same as None
        - SHA-256 hash is deterministic (same input = same hash)
    """
    # Validate object_type
    if not object_type:
        raise ValueError("object_type cannot be empty or None")

    # Normalize parameters
    normalized = canonical_params(params)

    # Build cache key parts
    parts = [object_type]

    if object_id is not None:
        parts.append(str(object_id))

    # Sort params and format as "key=value" pairs
    if normalized:
        sorted_params = sorted(normalized.items())
        param_str = ":".join(f"{k}={v}" for k, v in sorted_params)
        parts.append(param_str)

    # Join parts with colon separator
    cache_key = ":".join(parts)

    # Generate SHA-256 hash (64 hex characters)
    key_hash = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()

    return cache_key, key_hash
