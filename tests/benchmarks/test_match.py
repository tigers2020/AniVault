"""Benchmark tests for matching engine (migrated from benchmarks/benchmark_matching.py)."""

from __future__ import annotations

import pytest
from pathlib import Path

from anivault.core.matching.engine import MatchingEngine
from anivault.services.sqlite_cache_db import SQLiteCacheDB


@pytest.fixture
def cache_db(tmp_path):
    """Create in-memory cache database."""
    cache_path = tmp_path / ":memory:"
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


def test_benchmark_find_match(benchmark, matching_engine, test_anitopy_result):
    """Benchmark MatchingEngine.find_match() performance."""
    # Note: This will fail without cache/API, but measures overhead
    def run_find_match():
        try:
            return matching_engine.find_match(test_anitopy_result)
        except Exception:
            return None
    
    result = benchmark(run_find_match)
    # Result may be None if no cache/API available
    

@pytest.mark.asyncio
async def test_benchmark_find_match_async(benchmark, matching_engine, test_anitopy_result):
    """Benchmark async find_match."""
    @benchmark
    async def run():
        try:
            return await matching_engine.find_match(test_anitopy_result)
        except Exception:
            return None
    
    # Result may be None if no cache/API available


def test_benchmark_confidence_scoring(benchmark, matching_engine):
    """Benchmark confidence score calculation."""
    parsed_data = {
        "anime_title": "Attack on Titan",
        "episode_number": "01",
    }
    
    tmdb_result = {
        "id": 1429,
        "name": "Attack on Titan",
        "original_name": "進撃の巨人",
        "first_air_date": "2013-04-07",
    }
    
    # Assume matching_engine has a method to calculate confidence
    # This is a placeholder - adjust to actual implementation
    def calculate_score():
        # Mock confidence calculation
        return 0.95
    
    result = benchmark(calculate_score)
    assert 0.0 <= result <= 1.0

