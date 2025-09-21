#!/usr/bin/env python3
"""Create Test Data for Performance Analysis

This script creates sample data in the database for testing query performance.
"""

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.database import DatabaseManager
from core.models import ParsedAnimeInfo, TMDBAnime


def create_sample_tmdb_anime(tmdb_id: int) -> TMDBAnime:
    """Create a sample TMDB anime object."""
    return TMDBAnime(
        tmdb_id=tmdb_id,
        title=f"Test Anime {tmdb_id}",
        original_title=f"Test Anime Original {tmdb_id}",
        korean_title=f"테스트 애니메이션 {tmdb_id}",
        overview=f"This is a test anime with ID {tmdb_id} for performance testing.",
        poster_path=f"/poster_{tmdb_id}.jpg",
        backdrop_path=f"/backdrop_{tmdb_id}.jpg",
        first_air_date=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 1000)),
        last_air_date=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 100)),
        status="Ended",
        vote_average=random.uniform(5.0, 9.5),
        vote_count=random.randint(100, 10000),
        popularity=random.uniform(1.0, 100.0),
        number_of_seasons=random.randint(1, 5),
        number_of_episodes=random.randint(12, 200),
        genres=[
            {"id": random.randint(1, 20), "name": f"Genre {i}"} for i in range(random.randint(1, 3))
        ],
        networks=[
            {"id": random.randint(1, 10), "name": f"Network {i}"}
            for i in range(random.randint(1, 2))
        ],
        raw_data={"test": True, "tmdb_id": tmdb_id},
    )


def create_sample_parsed_anime_info(file_index: int) -> ParsedAnimeInfo:
    """Create a sample parsed anime info object."""
    return ParsedAnimeInfo(
        title=f"Test Series {file_index // 10 + 1}",
        season=random.randint(1, 3),
        episode=random.randint(1, 12),
        episode_title=f"Episode {random.randint(1, 12)}",
        resolution=f"{random.choice(['1080p', '720p', '480p'])}",
        resolution_width=random.choice([1920, 1280, 854]),
        resolution_height=random.choice([1080, 720, 480]),
        video_codec=random.choice(["H.264", "H.265", "AV1"]),
        audio_codec=random.choice(["AAC", "AC3", "DTS"]),
        release_group=random.choice(["GroupA", "GroupB", "GroupC"]),
        file_extension=random.choice([".mkv", ".mp4", ".avi"]),
        year=random.randint(2020, 2024),
        source=random.choice(["Web", "BluRay", "TV"]),
        raw_data={"test": True, "file_index": file_index},
    )


def create_test_data(
    db_manager: DatabaseManager, anime_count: int = 100, files_per_anime: int = 10
):
    """Create test data for performance analysis."""
    print(f"Creating {anime_count} anime records with {files_per_anime} files each...")

    # Create anime metadata
    anime_list = []
    for i in range(1, anime_count + 1):
        anime = create_sample_tmdb_anime(i)
        anime_list.append(anime)

    # Bulk insert anime metadata
    print(f"Inserting {len(anime_list)} anime metadata records...")
    inserted_count = db_manager.bulk_insert_anime_metadata(anime_list)
    print(f"Inserted {inserted_count} anime metadata records")

    # Create parsed files
    file_data_list = []
    file_index = 1

    for anime in anime_list:
        for j in range(files_per_anime):
            file_path = f"/test/path/anime_{anime.tmdb_id}/episode_{j+1:02d}.mkv"
            filename = f"episode_{j+1:02d}.mkv"
            file_size = random.randint(100 * 1024 * 1024, 2 * 1024 * 1024 * 1024)  # 100MB to 2GB
            created_at = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 365))
            modified_at = created_at + timedelta(hours=random.randint(1, 24))
            parsed_info = create_sample_parsed_anime_info(file_index)
            file_hash = f"test_hash_{file_index:08x}"

            file_data_list.append(
                (
                    file_path,
                    filename,
                    file_size,
                    created_at,
                    modified_at,
                    parsed_info,
                    file_hash,
                    anime.tmdb_id,
                )
            )
            file_index += 1

    # Bulk insert parsed files
    print(f"Inserting {len(file_data_list)} parsed file records...")
    inserted_count = db_manager.bulk_insert_parsed_files(file_data_list)
    print(f"Inserted {inserted_count} parsed file records")

    # Get final counts
    stats = db_manager.get_database_stats()
    print("\nFinal database stats:")
    print(f"  Anime metadata: {stats['anime_metadata_count']}")
    print(f"  Parsed files: {stats['parsed_files_count']}")


def main():
    """Main function to create test data."""
    try:
        # Initialize database manager
        db_manager = DatabaseManager()

        # Create test data
        create_test_data(db_manager, anime_count=100, files_per_anime=10)

        print("\nTest data creation completed successfully!")

    except Exception as e:
        print(f"Error creating test data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
