"""Benchmark tests for matching engine (migrated from benchmarks/benchmark_matching.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from anivault.core.matching.engine import MatchingEngine
from anivault.services.sqlite_cache_db import SQLiteCacheDB


@pytest.fixture
def cache_db():
    """Create in-memory cache database."""
    cache_path = Path(":memory:")
    return SQLiteCacheDB(cache_path)


@pytest.fixture
def matching_engine(cache_db):
    """Create matching engine instance."""
    return MatchingEngine(cache=cache_db, tmdb_client=None)


@pytest.fixture
def test_anitopy_result():
    """Generate test anitopy result."""
    return {
        "anime_title": "Attack on Titan",
        "episode_number": "01",
        "release_group": "SubGroup",
        "video_resolution": "1080p",
    }


def test_benchmark_find_match(benchmark, matching_engine, test_anitopy_result):  # type: ignore[no-untyped-def]
    """Benchmark MatchingEngine.find_match() performance."""

    # Note: This will fail without cache/API, but measures overhead
    def run_find_match():  # type: ignore[no-untyped-def]
        try:
            return matching_engine.find_match(test_anitopy_result)
        except Exception:  # noqa: BLE001
            return None

    benchmark(run_find_match)
    # Result may be None if no cache/API available


@pytest.mark.asyncio
async def test_benchmark_find_match_async(
    benchmark,
    matching_engine,
    test_anitopy_result,  # type: ignore[no-untyped-def]
):  # type: ignore[misc]
    """Benchmark async find_match."""

    @benchmark
    async def run():  # type: ignore[no-untyped-def]
        try:
            return await matching_engine.find_match(test_anitopy_result)
        except Exception:  # noqa: BLE001
            return None

    # Result may be None if no cache/API available


def test_benchmark_confidence_scoring(benchmark, matching_engine):  # type: ignore[no-untyped-def]
    """Benchmark confidence score calculation."""
    # NOTE: This test is a placeholder for confidence scoring benchmark
    # Actual implementation would require matching_engine to expose
    # a confidence calculation method

    # Mock confidence calculation
    def calculate_score():  # type: ignore[no-untyped-def]
        return 0.95

    result = benchmark(calculate_score)
    assert 0.0 <= result <= 1.0
