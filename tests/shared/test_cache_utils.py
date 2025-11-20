"""Tests for cache utility functions.

This module tests the cache key generation and parameter normalization utilities
used for TMDB API request caching.

Test Coverage:
    - Parameter normalization (canonical_params)
    - Cache key generation (generate_cache_key)
    - Edge cases and error handling
    - Parameter order independence
    - Case insensitivity

Author: AniVault Development Team
Date: 2025-01-06
"""

import pytest

from anivault.shared.cache_utils import canonical_params, generate_cache_key


class TestCanonicalParams:
    """Test parameter normalization function."""

    def test_empty_params(self) -> None:
        """Test with None and empty dict."""
        assert canonical_params(None) == {}
        assert canonical_params({}) == {}

    def test_remove_none_values(self) -> None:
        """Test removal of None values."""
        params = {"lang": "ko", "query": None, "page": 1}
        result = canonical_params(params)
        assert "query" not in result
        assert result == {"lang": "ko", "page": 1}

    def test_remove_empty_string_values(self) -> None:
        """Test removal of empty string values."""
        params = {"lang": "ko", "query": "", "page": 1}
        result = canonical_params(params)
        assert "query" not in result
        assert result == {"lang": "ko", "page": 1}

    def test_lowercase_keys(self) -> None:
        """Test key normalization to lowercase."""
        params = {"Lang": "ko", "Query": "titan", "Page": 1}
        result = canonical_params(params)
        assert result == {"lang": "ko", "query": "titan", "page": 1}

    def test_lowercase_string_values(self) -> None:
        """Test string value normalization to lowercase."""
        params = {"lang": "KO-KR", "query": "ATTACK ON TITAN"}
        result = canonical_params(params)
        assert result == {"lang": "ko-kr", "query": "attack on titan"}

    def test_preserve_non_string_values(self) -> None:
        """Test that non-string values are preserved as-is."""
        params = {"page": 1, "adult": False, "count": 10}
        result = canonical_params(params)
        assert result == {"page": 1, "adult": False, "count": 10}

    def test_mixed_types(self) -> None:
        """Test mixed string and non-string values."""
        params = {
            "lang": "KO",
            "query": "Titan",
            "page": 2,
            "adult": True,
            "empty": None,
        }
        result = canonical_params(params)
        assert result == {
            "lang": "ko",
            "query": "titan",
            "page": 2,
            "adult": True,
        }


class TestGenerateCacheKey:
    """Test cache key generation function."""

    def test_basic_search_key(self) -> None:
        """Test basic search cache key generation."""
        key, key_hash = generate_cache_key(
            "search",
            None,
            {"query": "titan", "lang": "ko"},
        )
        assert key == "search:lang=ko:query=titan"
        assert len(key_hash) == 64  # SHA-256 hash length

    def test_details_with_id(self) -> None:
        """Test details request with object ID."""
        key, key_hash = generate_cache_key("details", 1429, {"lang": "ko"})
        assert key == "details:1429:lang=ko"
        assert len(key_hash) == 64

    def test_popular_without_params(self) -> None:
        """Test popular request without parameters."""
        key, key_hash = generate_cache_key("popular", None, None)
        assert key == "popular"
        assert len(key_hash) == 64

    def test_parameter_order_independence(self) -> None:
        """Test that parameter order doesn't affect cache key."""
        key1, hash1 = generate_cache_key(
            "search",
            None,
            {"lang": "ko", "query": "titan", "page": 1},
        )
        key2, hash2 = generate_cache_key(
            "search",
            None,
            {"query": "titan", "page": 1, "lang": "ko"},
        )
        key3, hash3 = generate_cache_key(
            "search",
            None,
            {"page": 1, "lang": "ko", "query": "titan"},
        )

        assert key1 == key2 == key3
        assert hash1 == hash2 == hash3

    def test_case_insensitivity(self) -> None:
        """Test that parameter keys and string values are case-insensitive."""
        key1, hash1 = generate_cache_key(
            "search",
            None,
            {"Lang": "KO", "Query": "TITAN"},
        )
        key2, hash2 = generate_cache_key(
            "search",
            None,
            {"lang": "ko", "query": "titan"},
        )
        key3, hash3 = generate_cache_key(
            "search",
            None,
            {"LANG": "ko", "QUERY": "Titan"},
        )

        assert key1 == key2 == key3
        assert hash1 == hash2 == hash3

    def test_none_removal(self) -> None:
        """Test that None values are removed from cache key."""
        key1, hash1 = generate_cache_key(
            "search",
            None,
            {"lang": "ko", "query": "titan", "page": None},
        )
        key2, hash2 = generate_cache_key(
            "search",
            None,
            {"lang": "ko", "query": "titan"},
        )

        assert key1 == key2
        assert hash1 == hash2

    def test_empty_string_removal(self) -> None:
        """Test that empty strings are removed from cache key."""
        key1, hash1 = generate_cache_key(
            "search",
            None,
            {"lang": "ko", "query": "titan", "filter": ""},
        )
        key2, hash2 = generate_cache_key(
            "search",
            None,
            {"lang": "ko", "query": "titan"},
        )

        assert key1 == key2
        assert hash1 == hash2

    def test_integer_object_id(self) -> None:
        """Test object ID as integer."""
        key, _ = generate_cache_key("details", 1429, {"lang": "ko"})
        assert "1429" in key
        assert key == "details:1429:lang=ko"

    def test_string_object_id(self) -> None:
        """Test object ID as string."""
        key, _ = generate_cache_key("details", "1429", {"lang": "ko"})
        assert "1429" in key
        assert key == "details:1429:lang=ko"

    def test_hash_determinism(self) -> None:
        """Test that same input produces same hash."""
        _, hash1 = generate_cache_key("search", None, {"query": "titan"})
        _, hash2 = generate_cache_key("search", None, {"query": "titan"})
        assert hash1 == hash2

    def test_different_inputs_different_hashes(self) -> None:
        """Test that different inputs produce different hashes."""
        _, hash1 = generate_cache_key("search", None, {"query": "titan"})
        _, hash2 = generate_cache_key("search", None, {"query": "naruto"})
        assert hash1 != hash2

    def test_empty_object_type_raises_error(self) -> None:
        """Test that empty object_type raises ValueError."""
        with pytest.raises(ValueError, match="object_type cannot be empty"):
            generate_cache_key("", None, {"query": "titan"})

    def test_none_object_type_raises_error(self) -> None:
        """Test that None object_type raises ValueError."""
        with pytest.raises(ValueError, match="object_type cannot be empty"):
            generate_cache_key(None, None, {"query": "titan"})  # type: ignore[arg-type]

    def test_empty_params_dict(self) -> None:
        """Test with empty params dict."""
        key, _ = generate_cache_key("popular", None, {})
        assert key == "popular"

    def test_complex_params(self) -> None:
        """Test with complex real-world parameters."""
        key, key_hash = generate_cache_key(
            "discover",
            None,
            {
                "sort_by": "popularity.desc",
                "with_genres": "16",
                "lang": "ko-KR",
                "page": 1,
                "include_adult": False,
            },
        )
        # Parameters should be sorted alphabetically
        assert "include_adult=False" in key
        assert "lang=ko-kr" in key
        assert "page=1" in key
        assert "sort_by=popularity.desc" in key
        assert "with_genres=16" in key
        assert len(key_hash) == 64

    def test_real_world_search_example(self) -> None:
        """Test real-world search example from documentation."""
        key, _ = generate_cache_key(
            "search",
            None,
            {"query": "Attack on Titan", "lang": "ko-KR"},
        )
        # Should be normalized
        assert key == "search:lang=ko-kr:query=attack on titan"

    def test_real_world_details_example(self) -> None:
        """Test real-world details example from documentation."""
        key, _ = generate_cache_key("details", 1429, {"lang": "ko-KR"})
        assert key == "details:1429:lang=ko-kr"

    def test_real_world_discover_example(self) -> None:
        """Test real-world discover example from documentation."""
        key, _ = generate_cache_key(
            "discover",
            None,
            {"genre": "16", "sort": "popularity.desc"},
        )
        # Parameters sorted
        assert key == "discover:genre=16:sort=popularity.desc"
