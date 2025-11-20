"""Tests for cache entry Pydantic models."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from anivault.services.cache_models import CacheEntry


class TestCacheEntry:
    """Test suite for CacheEntry Pydantic model."""

    def test_cache_entry_valid_data(self) -> None:
        """Test CacheEntry with valid complete data."""
        # Given
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=7)

        # When
        entry = CacheEntry(
            cache_key="search:movie:test",
            key_hash="a" * 64,
            cache_type="search",
            response_data={"results": [{"id": 1}]},
            created_at=now,
            expires_at=expires,
            hit_count=5,
            last_accessed_at=now,
            response_size=1024,
            endpoint_category="tv",
        )

        # Then
        assert entry.cache_key == "search:movie:test"
        assert entry.key_hash == "a" * 64
        assert entry.cache_type == "search"
        assert entry.response_data == {"results": [{"id": 1}]}
        assert entry.created_at == now
        assert entry.expires_at == expires
        assert entry.hit_count == 5
        assert entry.last_accessed_at == now
        assert entry.response_size == 1024
        assert entry.endpoint_category == "tv"

    def test_cache_entry_minimal_data(self) -> None:
        """Test CacheEntry with only required fields."""
        # Given
        now = datetime.now(timezone.utc)

        # When
        entry = CacheEntry(
            cache_key="test",
            key_hash="b" * 64,
            cache_type="details",
            response_data={},
            created_at=now,
        )

        # Then
        assert entry.cache_key == "test"
        assert entry.expires_at is None
        assert entry.hit_count == 0
        assert entry.last_accessed_at is None
        assert entry.response_size == 0
        assert entry.endpoint_category is None

    def test_cache_entry_missing_required_field(self) -> None:
        """Test CacheEntry raises ValidationError for missing required field."""
        # When & Then
        with pytest.raises(ValidationError, match="cache_key"):
            CacheEntry(
                key_hash="c" * 64,
                cache_type="search",
                response_data={},
                created_at=datetime.now(timezone.utc),
            )

    def test_cache_entry_invalid_cache_type(self) -> None:
        """Test CacheEntry raises ValidationError for invalid cache_type."""
        # When & Then
        with pytest.raises(
            ValidationError, match=r"Input should be 'search' or 'details'"
        ):
            CacheEntry(
                cache_key="test",
                key_hash="d" * 64,
                cache_type="invalid",  # type: ignore[arg-type]
                response_data={},
                created_at=datetime.now(timezone.utc),
            )

    def test_cache_entry_key_hash_too_short(self) -> None:
        """Test CacheEntry raises ValidationError for key_hash too short."""
        # When & Then
        with pytest.raises(
            ValidationError,
            match=r"String should have at least 64 characters",
        ):
            CacheEntry(
                cache_key="test",
                key_hash="short",
                cache_type="search",
                response_data={},
                created_at=datetime.now(timezone.utc),
            )

    def test_cache_entry_key_hash_too_long(self) -> None:
        """Test CacheEntry raises ValidationError for key_hash too long."""
        # When & Then
        with pytest.raises(
            ValidationError,
            match=r"String should have at most 64 characters",
        ):
            CacheEntry(
                cache_key="test",
                key_hash="x" * 100,
                cache_type="search",
                response_data={},
                created_at=datetime.now(timezone.utc),
            )

    def test_cache_entry_key_hash_invalid_hex(self) -> None:
        """Test CacheEntry raises ValueError for non-hexadecimal key_hash."""
        # When & Then
        with pytest.raises(
            ValidationError,
            match=r"key_hash must be a valid hexadecimal string",
        ):
            CacheEntry(
                cache_key="test",
                key_hash="z" * 64,  # 'z' is not a valid hex character
                cache_type="search",
                response_data={},
                created_at=datetime.now(timezone.utc),
            )

    def test_cache_entry_key_hash_uppercase_normalized(self) -> None:
        """Test CacheEntry normalizes uppercase key_hash to lowercase."""
        # Given
        now = datetime.now(timezone.utc)
        uppercase_hash = "A" * 64

        # When
        entry = CacheEntry(
            cache_key="test",
            key_hash=uppercase_hash,
            cache_type="search",
            response_data={},
            created_at=now,
        )

        # Then
        assert entry.key_hash == "a" * 64  # Normalized to lowercase

    def test_cache_entry_negative_hit_count(self) -> None:
        """Test CacheEntry raises ValidationError for negative hit_count."""
        # When & Then
        with pytest.raises(
            ValidationError,
            match=r"Input should be greater than or equal to 0",
        ):
            CacheEntry(
                cache_key="test",
                key_hash="e" * 64,
                cache_type="search",
                response_data={},
                created_at=datetime.now(timezone.utc),
                hit_count=-1,
            )

    def test_cache_entry_negative_response_size(self) -> None:
        """Test CacheEntry raises ValidationError for negative response_size."""
        # When & Then
        with pytest.raises(
            ValidationError,
            match=r"Input should be greater than or equal to 0",
        ):
            CacheEntry(
                cache_key="test",
                key_hash="f" * 64,
                cache_type="search",
                response_data={},
                created_at=datetime.now(timezone.utc),
                response_size=-100,
            )

    def test_cache_entry_expires_before_created(self) -> None:
        """Test CacheEntry raises ValueError for expires_at before created_at."""
        # Given
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=1)

        # When & Then
        with pytest.raises(
            ValidationError,
            match=r"expires_at .* must not be before created_at",
        ):
            CacheEntry(
                cache_key="test",
                key_hash="7" * 64,  # Valid hex
                cache_type="search",
                response_data={},
                created_at=now,
                expires_at=past,
            )

    def test_cache_entry_is_expired_true(self) -> None:
        """Test is_expired() returns True for expired entry."""
        # Given
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)

        entry = CacheEntry(
            cache_key="test",
            key_hash="8" * 64,  # Valid hex
            cache_type="search",
            response_data={},
            created_at=past - timedelta(days=1),
            expires_at=past,
        )

        # When & Then
        assert entry.is_expired() is True

    def test_cache_entry_is_expired_false(self) -> None:
        """Test is_expired() returns False for valid entry."""
        # Given
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=1)

        entry = CacheEntry(
            cache_key="test",
            key_hash="9" * 64,  # Valid hex
            cache_type="search",
            response_data={},
            created_at=now,
            expires_at=future,
        )

        # When & Then
        assert entry.is_expired() is False

    def test_cache_entry_is_expired_no_expiration(self) -> None:
        """Test is_expired() returns False when expires_at is None."""
        # Given
        entry = CacheEntry(
            cache_key="test",
            key_hash="a" * 64,  # Valid hex (reuse 'a')
            cache_type="search",
            response_data={},
            created_at=datetime.now(timezone.utc),
            expires_at=None,
        )

        # When & Then
        assert entry.is_expired() is False

    def test_cache_entry_extra_fields_ignored(self) -> None:
        """Test CacheEntry ignores extra unknown fields."""
        # Given
        now = datetime.now(timezone.utc)

        # When
        entry = CacheEntry(
            cache_key="test",
            key_hash="b" * 64,  # Valid hex (reuse 'b')
            cache_type="search",
            response_data={},
            created_at=now,
            unknown_field="ignored",  # type: ignore[call-arg]
        )

        # Then
        assert not hasattr(entry, "unknown_field")
        assert entry.cache_key == "test"

    def test_cache_entry_empty_cache_key(self) -> None:
        """Test CacheEntry raises ValidationError for empty cache_key."""
        # When & Then
        with pytest.raises(
            ValidationError,
            match=r"String should have at least 1 character",
        ):
            CacheEntry(
                cache_key="",
                key_hash="l" * 64,
                cache_type="search",
                response_data={},
                created_at=datetime.now(timezone.utc),
            )

    def test_cache_entry_whitespace_stripped(self) -> None:
        """Test CacheEntry strips whitespace from string fields."""
        # Given
        now = datetime.now(timezone.utc)

        # When
        entry = CacheEntry(
            cache_key="  test  ",
            key_hash="c" * 64,  # Valid hex (reuse 'c')
            cache_type="search",
            response_data={},
            created_at=now,
        )

        # Then
        assert entry.cache_key == "test"  # Whitespace stripped
