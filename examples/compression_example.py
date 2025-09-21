"""Example demonstrating data compression for large metadata objects.

This example shows how the compression system automatically reduces
memory usage and improves performance for large metadata objects
like TMDB anime data and parsed file information.
"""

import json
import time

from src.core.compression import compression_manager
from src.core.database import AnimeMetadata
from src.core.metadata_cache import MetadataCache
from src.core.models import ParsedAnimeInfo, TMDBAnime


def create_large_tmdb_anime():
    """Create a TMDBAnime object with large raw_data."""
    large_raw_data = {
        "details": {
            "overview": "A" * 5000,  # Large overview text
            "cast": [
                {
                    "id": i,
                    "name": f"Voice Actor {i}",
                    "character": f"Character {i}",
                    "profile_path": f"/profile_{i}.jpg",
                    "biography": "Detailed biography " + "x" * 100,
                }
                for i in range(100)  # 100 cast members
            ],
            "crew": [
                {
                    "id": i,
                    "name": f"Crew Member {i}",
                    "department": "Production",
                    "job": f"Job {i}",
                    "biography": "Detailed biography " + "x" * 100,
                }
                for i in range(50)  # 50 crew members
            ],
            "seasons": [
                {
                    "id": i,
                    "name": f"Season {i}",
                    "overview": "Season overview " + "x" * 500,
                    "episode_count": 12,
                    "episodes": [
                        {
                            "id": j,
                            "name": f"Episode {j}",
                            "overview": "Episode overview " + "x" * 300,
                            "air_date": "2023-01-01",
                            "runtime": 24,
                        }
                        for j in range(12)
                    ],
                }
                for i in range(5)  # 5 seasons
            ],
            "reviews": [
                {
                    "id": i,
                    "author": f"Reviewer {i}",
                    "content": "Detailed review content " + "x" * 1000,
                    "rating": 8.5,
                }
                for i in range(20)  # 20 reviews
            ],
        }
    }

    return TMDBAnime(
        tmdb_id=12345,
        title="Attack on Titan",
        original_title="進撃の巨人",
        korean_title="진격의 거인",
        overview="A detailed overview of the anime series...",
        poster_path="/poster.jpg",
        backdrop_path="/backdrop.jpg",
        status="Ended",
        vote_average=8.8,
        vote_count=15000,
        popularity=95.5,
        number_of_seasons=4,
        number_of_episodes=75,
        raw_data=large_raw_data,
    )


def create_large_parsed_info():
    """Create a ParsedAnimeInfo object with large raw_data."""
    large_raw_data = {
        "file_analysis": {
            "video_streams": [
                {
                    "index": i,
                    "codec": "h264",
                    "resolution": "1920x1080",
                    "bitrate": 8000,
                    "duration": 1440,
                    "metadata": "Detailed stream metadata " + "x" * 200,
                }
                for i in range(3)  # Multiple video streams
            ],
            "audio_streams": [
                {
                    "index": i,
                    "codec": "aac",
                    "channels": 6,
                    "bitrate": 256,
                    "language": f"Language {i}",
                    "metadata": "Detailed audio metadata " + "x" * 200,
                }
                for i in range(5)  # Multiple audio tracks
            ],
            "subtitles": [
                {
                    "index": i,
                    "language": f"Subtitle {i}",
                    "format": "ass",
                    "content": "Subtitle content " + "x" * 500,
                }
                for i in range(10)  # Multiple subtitle tracks
            ],
            "processing_log": [
                f"Processing step {i}: " + "x" * 100 for i in range(50)  # 50 processing steps
            ],
        }
    }

    return ParsedAnimeInfo(
        title="Attack on Titan",
        episode_title="The Beginning",
        episode_number=1,
        season_number=1,
        year=2013,
        resolution="1920x1080",
        video_codec="h264",
        audio_codec="aac",
        release_group="Erai-raws",
        file_extension="mkv",
        source="Blu-ray",
        raw_data=large_raw_data,
    )


def demonstrate_compression_basic():
    """Demonstrate basic compression functionality."""
    print("=== Basic Compression Demo ===")

    # Create large data
    large_data = {
        "title": "Test Anime",
        "description": "x" * 10000,  # 10KB of data
        "metadata": [{"key": f"value{i}"} for i in range(1000)],
    }

    # Measure original size
    original_json = json.dumps(large_data, ensure_ascii=False)
    original_size = len(original_json.encode("utf-8"))
    print(f"Original size: {original_size:,} bytes")

    # Compress data
    start_time = time.time()
    compressed_data = compression_manager.compress_for_storage(large_data)
    compression_time = time.time() - start_time

    compressed_size = len(compressed_data)
    print(f"Compressed size: {compressed_size:,} bytes")
    print(f"Compression time: {compression_time:.4f} seconds")

    # Calculate savings
    savings = original_size - compressed_size
    savings_percent = (savings / original_size) * 100
    print(f"Space saved: {savings:,} bytes ({savings_percent:.1f}%)")

    # Decompress data
    start_time = time.time()
    decompressed_data = compression_manager.decompress_from_storage(
        compressed_data, expected_type="dict"
    )
    decompression_time = time.time() - start_time

    print(f"Decompression time: {decompression_time:.4f} seconds")

    # Verify integrity
    assert decompressed_data == large_data
    print("✓ Data integrity verified")

    # Show compression stats
    stats = compression_manager.get_compression_stats()
    print("\nCompression Stats:")
    print(f"  Total compressions: {stats['total_compressions']}")
    print(f"  Total decompressions: {stats['total_decompressions']}")
    print(f"  Average compression ratio: {stats['average_compression_ratio']:.3f}")
    print(f"  Compression efficiency: {stats['compression_efficiency']:.1f}%")


def demonstrate_tmdb_anime_compression():
    """Demonstrate compression of TMDBAnime objects."""
    print("\n=== TMDBAnime Compression Demo ===")

    # Create large TMDB anime data
    anime = create_large_tmdb_anime()

    # Measure original size
    original_size = len(str(anime.raw_data).encode("utf-8"))
    print(f"Original raw_data size: {original_size:,} bytes")

    # Apply compression
    start_time = time.time()
    compressed_raw_data = compression_manager.compress_for_storage(anime.raw_data)
    compression_time = time.time() - start_time

    compressed_size = len(compressed_raw_data)
    print(f"Compressed raw_data size: {compressed_size:,} bytes")
    print(f"Compression time: {compression_time:.4f} seconds")

    # Calculate savings
    savings = original_size - compressed_size
    savings_percent = (savings / original_size) * 100
    print(f"Space saved: {savings:,} bytes ({savings_percent:.1f}%)")

    # Decompress and verify
    start_time = time.time()
    decompressed_raw_data = compression_manager.decompress_from_storage(
        compressed_raw_data, expected_type="dict"
    )
    decompression_time = time.time() - start_time

    print(f"Decompression time: {decompression_time:.4f} seconds")

    # Verify integrity
    assert decompressed_raw_data == anime.raw_data
    print("✓ TMDBAnime data integrity verified")


def demonstrate_parsed_info_compression():
    """Demonstrate compression of ParsedAnimeInfo objects."""
    print("\n=== ParsedAnimeInfo Compression Demo ===")

    # Create large parsed info data
    parsed_info = create_large_parsed_info()

    # Measure original size
    original_size = len(str(parsed_info.raw_data).encode("utf-8"))
    print(f"Original raw_data size: {original_size:,} bytes")

    # Apply compression
    start_time = time.time()
    compressed_raw_data = compression_manager.compress_for_storage(parsed_info.raw_data)
    compression_time = time.time() - start_time

    compressed_size = len(compressed_raw_data)
    print(f"Compressed raw_data size: {compressed_size:,} bytes")
    print(f"Compression time: {compression_time:.4f} seconds")

    # Calculate savings
    savings = original_size - compressed_size
    savings_percent = (savings / original_size) * 100
    print(f"Space saved: {savings:,} bytes ({savings_percent:.1f}%)")

    # Decompress and verify
    start_time = time.time()
    decompressed_raw_data = compression_manager.decompress_from_storage(
        compressed_raw_data, expected_type="dict"
    )
    decompression_time = time.time() - start_time

    print(f"Decompression time: {decompression_time:.4f} seconds")

    # Verify integrity
    assert decompressed_raw_data == parsed_info.raw_data
    print("✓ ParsedAnimeInfo data integrity verified")


def demonstrate_database_compression():
    """Demonstrate compression in database operations."""
    print("\n=== Database Compression Demo ===")

    # Create large anime data
    anime = create_large_tmdb_anime()

    # Test database serialization with compression
    print("Testing database serialization...")

    start_time = time.time()
    serialized_genres = AnimeMetadata._serialize_json_field(anime.genres)
    serialized_networks = AnimeMetadata._serialize_json_field(anime.networks)
    serialized_raw_data = AnimeMetadata._serialize_json_field(anime.raw_data)
    serialization_time = time.time() - start_time

    print(f"Serialization time: {serialization_time:.4f} seconds")

    # Measure serialized sizes
    original_raw_data_size = len(json.dumps(anime.raw_data, ensure_ascii=False))
    serialized_raw_data_size = len(serialized_raw_data)

    print(f"Original raw_data JSON size: {original_raw_data_size:,} bytes")
    print(f"Serialized raw_data size: {serialized_raw_data_size:,} bytes")

    if serialized_raw_data_size < original_raw_data_size:
        savings = original_raw_data_size - serialized_raw_data_size
        savings_percent = (savings / original_raw_data_size) * 100
        print(f"Database storage savings: {savings:,} bytes ({savings_percent:.1f}%)")

    # Test deserialization
    start_time = time.time()
    deserialized_genres = AnimeMetadata._parse_json_field(serialized_genres, [])
    deserialized_networks = AnimeMetadata._parse_json_field(serialized_networks, [])
    deserialized_raw_data = AnimeMetadata._parse_json_field(serialized_raw_data, {})
    deserialization_time = time.time() - start_time

    print(f"Deserialization time: {deserialization_time:.4f} seconds")

    # Verify integrity
    assert deserialized_genres == anime.genres
    assert deserialized_networks == anime.networks
    assert deserialized_raw_data == anime.raw_data
    print("✓ Database compression integrity verified")


def demonstrate_cache_compression():
    """Demonstrate compression in cache operations."""
    print("\n=== Cache Compression Demo ===")

    # Create cache without database
    cache = MetadataCache(max_size=100, max_memory_mb=50, enable_db=False)

    # Create large anime data
    anime = create_large_tmdb_anime()

    # Store in cache (should apply compression automatically)
    print("Storing large anime data in cache...")
    start_time = time.time()
    cache.put("large_anime", anime)
    storage_time = time.time() - start_time
    print(f"Storage time: {storage_time:.4f} seconds")

    # Get cache stats
    stats = cache.get_stats()
    print(f"Cache memory usage: {stats.memory_usage_bytes:,} bytes")
    print(f"Cache size: {stats.cache_size} entries")

    # Retrieve from cache (should decompress automatically)
    print("Retrieving anime data from cache...")
    start_time = time.time()
    retrieved_anime = cache.get("large_anime")
    retrieval_time = time.time() - start_time
    print(f"Retrieval time: {retrieval_time:.4f} seconds")

    # Verify integrity
    assert retrieved_anime is not None
    assert retrieved_anime.tmdb_id == anime.tmdb_id
    assert retrieved_anime.title == anime.title
    assert retrieved_anime.raw_data == anime.raw_data
    print("✓ Cache compression integrity verified")

    # Show cache performance
    print(f"Cache hit rate: {stats.hit_rate:.1f}%")
    print(f"Cache miss rate: {stats.miss_rate:.1f}%")


def demonstrate_performance_comparison():
    """Demonstrate performance comparison with and without compression."""
    print("\n=== Performance Comparison Demo ===")

    # Create multiple large objects
    animes = [create_large_tmdb_anime() for _ in range(10)]

    # Test without compression (original data)
    print("Testing with original (uncompressed) data...")
    start_time = time.time()
    uncompressed_sizes = []
    for anime in animes:
        size = len(str(anime.raw_data).encode("utf-8"))
        uncompressed_sizes.append(size)
    uncompressed_total = sum(uncompressed_sizes)
    uncompressed_time = time.time() - start_time

    print(f"Total uncompressed size: {uncompressed_total:,} bytes")
    print(f"Processing time: {uncompressed_time:.4f} seconds")

    # Test with compression
    print("\nTesting with compressed data...")
    start_time = time.time()
    compressed_sizes = []
    for anime in animes:
        compressed_data = compression_manager.compress_for_storage(anime.raw_data)
        size = len(compressed_data)
        compressed_sizes.append(size)
    compressed_total = sum(compressed_sizes)
    compression_time = time.time() - start_time

    print(f"Total compressed size: {compressed_total:,} bytes")
    print(f"Compression time: {compression_time:.4f} seconds")

    # Calculate overall savings
    total_savings = uncompressed_total - compressed_total
    savings_percent = (total_savings / uncompressed_total) * 100

    print("\nOverall Performance:")
    print(f"  Space saved: {total_savings:,} bytes ({savings_percent:.1f}%)")
    print(f"  Compression overhead: {compression_time:.4f} seconds")
    print(f"  Space efficiency: {compressed_total / uncompressed_total:.3f}")


def main():
    """Run all compression demonstrations."""
    print("Data Compression System Demonstration")
    print("=" * 50)

    try:
        # Reset compression stats
        compression_manager.reset_stats()

        # Run demonstrations
        demonstrate_compression_basic()
        demonstrate_tmdb_anime_compression()
        demonstrate_parsed_info_compression()
        demonstrate_database_compression()
        demonstrate_cache_compression()
        demonstrate_performance_comparison()

        # Final stats
        print("\n=== Final Compression Statistics ===")
        stats = compression_manager.get_compression_stats()
        print(f"Total compressions: {stats['total_compressions']}")
        print(f"Total decompressions: {stats['total_decompressions']}")
        print(f"Total space saved: {stats['total_space_saved_bytes']:,} bytes")
        print(f"Average compression ratio: {stats['average_compression_ratio']:.3f}")
        print(f"Compression efficiency: {stats['compression_efficiency']:.1f}%")
        print(f"Average compression time: {stats['average_compression_time_ms']:.2f} ms")
        print(f"Average decompression time: {stats['average_decompression_time_ms']:.2f} ms")

        print("\n✓ All compression demonstrations completed successfully!")

    except Exception as e:
        print(f"✗ Error during demonstration: {e}")
        raise


if __name__ == "__main__":
    main()
