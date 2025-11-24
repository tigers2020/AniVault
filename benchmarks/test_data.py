"""Test data generator for performance benchmarks.

This module generates realistic test data for benchmarking the AniVault
matching engine and cache operations.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

from anivault.core.matching.models import NormalizedQuery


def generate_queries(count: int = 1000) -> list[NormalizedQuery]:
    """Generate realistic NormalizedQuery objects for benchmarking.

    Args:
        count: Number of queries to generate

    Returns:
        List of NormalizedQuery objects with varied titles and years
    """
    # Realistic anime titles with different characteristics
    base_titles = [
        "Attack on Titan",
        "Demon Slayer",
        "My Hero Academia",
        "One Piece",
        "Naruto",
        "Sword Art Online",
        "Fullmetal Alchemist",
        "Death Note",
        "Tokyo Ghoul",
        "Hunter x Hunter",
        "Steins Gate",
        "Cowboy Bebop",
        "Neon Genesis Evangelion",
        "Code Geass",
        "Fate Stay Night",
        "Re Zero",
        "Overlord",
        "Konosuba",
        "Mob Psycho 100",
        "Dr Stone",
    ]

    # Generate variations
    queries = []
    for i in range(count):
        # Select base title
        base_title = base_titles[i % len(base_titles)]

        # Add variations
        variations = [
            base_title,
            f"{base_title} Season 2",
            f"{base_title} The Final Season",
            f"{base_title} OVA",
            base_title.upper(),
            base_title.lower(),
        ]

        title = variations[i % len(variations)]

        # Random year or None
        if i % 3 == 0:
            year = None
        else:
            year = random.randint(2000, 2024)

        queries.append(NormalizedQuery(title=title, year=year))

    return queries


def generate_cache_test_data(count: int = 1000) -> list[dict]:
    """Generate realistic cache data for benchmarking.

    Args:
        count: Number of cache entries to generate

    Returns:
        List of dictionaries suitable for SQLiteCacheDB.set()
    """
    cache_data = []

    for i in range(count):
        # Generate TMDB search result data
        data = {
            "id": 1000 + i,
            "title": f"Anime Title {i}",
            "name": f"Anime Name {i}",
            "release_date": "2020-01-01",
            "first_air_date": "2020-04-01",
            "popularity": random.uniform(10.0, 100.0),
            "vote_average": random.uniform(6.0, 9.5),
            "vote_count": random.randint(100, 10000),
            "overview": f"This is a test overview for anime {i}. " * 10,
            "original_language": "ja",
            "genre_ids": [16, 10759],  # Animation, Action & Adventure
            "media_type": "tv",
        }

        cache_entry = {
            "key": f"search:anime_title_{i}",
            "data": data,
            "cache_type": "search" if i % 2 == 0 else "details",
            "ttl_seconds": 86400,  # 24 hours
        }

        cache_data.append(cache_entry)

    return cache_data


def generate_anitopy_results(count: int = 100) -> list[dict]:
    """Generate realistic anitopy parsing results for find_match benchmarking.

    Args:
        count: Number of anitopy results to generate

    Returns:
        List of dictionaries mimicking anitopy.parse() output
    """
    anime_titles = [
        "Attack on Titan",
        "Demon Slayer",
        "My Hero Academia",
        "One Piece",
        "Naruto Shippuden",
        "Sword Art Online",
        "Fullmetal Alchemist Brotherhood",
        "Death Note",
        "Tokyo Ghoul",
        "Hunter x Hunter",
    ]

    results = []
    for i in range(count):
        title = anime_titles[i % len(anime_titles)]
        episode = (i % 24) + 1
        season = (i // 24) + 1

        result = {
            "anime_title": title,
            "episode_number": str(episode).zfill(2),
            "release_group": "SubsPlease" if i % 2 == 0 else "Erai-raws",
            "video_resolution": "1080p",
            "video_term": "BDRip" if i % 3 == 0 else "WEBRip",
            "file_extension": "mkv",
        }

        # Add season for some entries
        if season > 1:
            result["anime_season"] = str(season)

        # Add year for some entries
        if i % 2 == 0:
            result["anime_year"] = str(random.randint(2010, 2024))

        results.append(result)

    return results


if __name__ == "__main__":
    # Quick validation
    print("Generating test data...")

    queries = generate_queries(100)
    print(f"✅ Generated {len(queries)} NormalizedQuery objects")
    print(f"   Sample: {queries[0]}")

    cache_data = generate_cache_test_data(100)
    print(f"✅ Generated {len(cache_data)} cache entries")
    print(f"   Sample keys: {[c['key'] for c in cache_data[:3]]}")

    anitopy_results = generate_anitopy_results(50)
    print(f"✅ Generated {len(anitopy_results)} anitopy results")
    print(f"   Sample: {anitopy_results[0]}")
