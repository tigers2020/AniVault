"""Benchmark tests for cache operations (migrated from benchmarks/benchmark_cache.py)."""

from __future__ import annotations

import pytest
from pathlib import Path

from anivault.services.sqlite_cache_db import SQLiteCacheDB


@pytest.fixture
def cache_db(tmp_path: Path) -> SQLiteCacheDB:
    """Create in-memory cache database."""
    # Use in-memory for speed
    cache_path = Path(":memory:")
    return SQLiteCacheDB(cache_path)


@pytest.fixture
def test_cache_entry() -> dict[str, any]:  # type: ignore[valid-type]
    """Generate test cache entry."""
    return {
        "key": "test_key_12345",
        "data": {
            "id": 1429,
            "name": "Attack on Titan",
            "seasons": [1, 2, 3, 4],
            "metadata": {"rating": 8.5, "popularity": 95.5},
        },
        "cache_type": "details",  # Must be 'search' or 'details'
        "ttl_seconds": 86400,
    }


def test_benchmark_cache_set(benchmark, cache_db, test_cache_entry) -> None:  # type: ignore[no-untyped-def]
    """Benchmark cache SET operation (serialization + write)."""
    result = benchmark(
        cache_db.set_cache,
        key=test_cache_entry["key"],
        data=test_cache_entry["data"],
        cache_type=test_cache_entry["cache_type"],
        ttl_seconds=test_cache_entry["ttl_seconds"],
    )
    # set_cache returns None on success


def test_benchmark_cache_get(benchmark, cache_db, test_cache_entry) -> None:  # type: ignore[no-untyped-def]
    """Benchmark cache GET operation (read + deserialization)."""
    # First, insert data
    cache_db.set_cache(
        key=test_cache_entry["key"],
        data=test_cache_entry["data"],
        cache_type=test_cache_entry["cache_type"],
        ttl_seconds=test_cache_entry["ttl_seconds"],
    )
    
    # Benchmark retrieval
    result = benchmark(cache_db.get, test_cache_entry["key"])
    assert result is not None
    assert result["id"] == 1429


def test_benchmark_cache_roundtrip(benchmark, cache_db) -> None:  # type: ignore[no-untyped-def]
    """Benchmark full cache roundtrip (set + get)."""
    test_data = {
        "key": "roundtrip_key",
        "data": {"id": 999, "name": "Test Anime"},
        "cache_type": "search",
        "ttl_seconds": 3600,
    }
    
    def roundtrip():  # type: ignore[no-untyped-def]
        cache_db.set_cache(
            key=test_data["key"],
            data=test_data["data"],
            cache_type=test_data["cache_type"],
            ttl_seconds=test_data["ttl_seconds"],
        )
        return cache_db.get(test_data["key"])
    
    result = benchmark(roundtrip)
    assert result is not None


def test_benchmark_cache_batch_operations(benchmark, cache_db) -> None:  # type: ignore[no-untyped-def]
    """Benchmark batch cache operations (100 items)."""
    def batch_ops():  # type: ignore[no-untyped-def]
        # Insert 100 entries
        for i in range(100):
            cache_db.set_cache(
                key=f"batch_key_{i}",
                data={"id": i, "name": f"Anime {i}"},
                cache_type="search",
                ttl_seconds=3600,
            )
        
        # Retrieve 100 entries
        results = []
        for i in range(100):
            results.append(cache_db.get(f"batch_key_{i}"))
        
        return results
    
    results = benchmark(batch_ops)
    assert len(results) == 100

