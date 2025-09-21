"""Tests for data compression functionality.

This module tests the compression system for large metadata objects,
including data integrity, performance impact, and integration with
cache and database operations.
"""

import json
import time

from src.core.compression import CompressionManager
from src.core.database import AnimeMetadata
from src.core.metadata_cache import MetadataCache
from src.core.models import ParsedAnimeInfo, TMDBAnime


class TestCompressionManager:
    """Test cases for CompressionManager class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.compression_manager = CompressionManager(
            compression_level=6,
            min_size_threshold=50,  # Lower threshold for testing
            max_compression_ratio=0.8,
        )

    def test_should_compress_small_data(self) -> None:
        """Test that small data is not compressed."""
        small_data = "small"
        assert not self.compression_manager.should_compress(small_data)

    def test_should_compress_large_data(self) -> None:
        """Test that large data is compressed."""
        large_data = "x" * 1000  # 1KB of data
        assert self.compression_manager.should_compress(large_data)

    def test_compress_data_success(self) -> None:
        """Test successful data compression."""
        # Create large JSON data
        large_data = {
            "title": "Test Anime",
            "description": "x" * 1000,  # Large description
            "metadata": {"key": "value" * 100},
        }

        compressed_bytes, stats = self.compression_manager.compress_data(large_data)

        assert isinstance(compressed_bytes, bytes)
        assert stats.original_size > stats.compressed_size
        assert stats.compression_ratio < 1.0
        assert stats.compression_time_ms > 0

    def test_decompress_data_success(self) -> None:
        """Test successful data decompression."""
        original_data = {"test": "data", "large": "x" * 1000}

        compressed_bytes, _ = self.compression_manager.compress_data(original_data)
        decompressed_data, stats = self.compression_manager.decompress_data(
            compressed_bytes, expected_type="dict"
        )

        assert decompressed_data == original_data
        assert stats.decompression_time_ms > 0

    def test_compress_for_storage_success(self) -> None:
        """Test compression for storage format."""
        large_data = {"test": "x" * 1000}

        stored_data = self.compression_manager.compress_for_storage(large_data)

        assert isinstance(stored_data, str)
        assert len(stored_data) < len(json.dumps(large_data))

    def test_decompress_from_storage_success(self) -> None:
        """Test decompression from storage format."""
        original_data = {"test": "x" * 1000}

        stored_data = self.compression_manager.compress_for_storage(original_data)
        decompressed_data = self.compression_manager.decompress_from_storage(
            stored_data, expected_type="dict"
        )

        assert decompressed_data == original_data

    def test_decompress_from_storage_uncompressed(self) -> None:
        """Test decompression from uncompressed storage."""
        original_data = {"test": "small"}

        # This should not be compressed due to size
        stored_data = self.compression_manager.compress_for_storage(original_data)
        decompressed_data = self.compression_manager.decompress_from_storage(
            stored_data, expected_type="dict"
        )

        assert decompressed_data == original_data

    def test_compression_stats(self) -> None:
        """Test compression statistics tracking."""
        large_data = {"test": "x" * 1000}

        # Compress and decompress data
        self.compression_manager.compress_for_storage(large_data)
        self.compression_manager.decompress_from_storage(
            self.compression_manager.compress_for_storage(large_data), "dict"
        )

        stats = self.compression_manager.get_compression_stats()

        assert stats["total_compressions"] > 0
        assert stats["total_decompressions"] > 0
        assert stats["total_space_saved_bytes"] > 0
        assert stats["compression_efficiency"] > 0

    def test_reset_stats(self) -> None:
        """Test statistics reset."""
        large_data = {"test": "x" * 1000}
        self.compression_manager.compress_for_storage(large_data)

        self.compression_manager.reset_stats()
        stats = self.compression_manager.get_compression_stats()

        assert stats["total_compressions"] == 0
        assert stats["total_decompressions"] == 0


class TestCompressionIntegration:
    """Test integration of compression with cache and database."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.compression_manager = CompressionManager(
            min_size_threshold=50, max_compression_ratio=0.8
        )

    def test_tmdb_anime_compression(self) -> None:
        """Test compression of TMDBAnime objects with large raw_data."""
        large_raw_data = {
            "details": "x" * 1000,
            "cast": [{"name": "Actor " + str(i)} for i in range(100)],
            "crew": [{"name": "Crew " + str(i)} for i in range(50)],
        }

        anime = TMDBAnime(tmdb_id=12345, title="Test Anime", raw_data=large_raw_data)

        # Test that raw_data is large enough to compress
        raw_data_size = len(str(large_raw_data).encode("utf-8"))
        assert raw_data_size >= self.compression_manager.min_size_threshold

        # Test compression
        compressed_anime = self._apply_compression_to_tmdb_anime(anime)

        # Verify compression occurred
        compressed_raw_data_size = len(str(compressed_anime.raw_data).encode("utf-8"))
        assert compressed_raw_data_size < raw_data_size

        # Test decompression
        decompressed_anime = self._decompress_tmdb_anime(compressed_anime)

        # Verify data integrity
        assert decompressed_anime.tmdb_id == anime.tmdb_id
        assert decompressed_anime.title == anime.title
        assert decompressed_anime.raw_data == anime.raw_data

    def test_parsed_anime_info_compression(self) -> None:
        """Test compression of ParsedAnimeInfo objects with large raw_data."""
        large_raw_data = {
            "file_info": "x" * 1000,
            "metadata": [{"key": "value" + str(i)} for i in range(100)],
        }

        parsed_info = ParsedAnimeInfo(
            title="Test Anime", episode_title="Episode 1", raw_data=large_raw_data
        )

        # Test compression
        compressed_info = self._apply_compression_to_parsed_info(parsed_info)

        # Verify compression occurred
        original_size = len(str(large_raw_data).encode("utf-8"))
        compressed_size = len(str(compressed_info.raw_data).encode("utf-8"))
        assert compressed_size < original_size

        # Test decompression
        decompressed_info = self._decompress_parsed_info(compressed_info)

        # Verify data integrity
        assert decompressed_info.title == parsed_info.title
        assert decompressed_info.episode_title == parsed_info.episode_title
        assert decompressed_info.raw_data == parsed_info.raw_data

    def test_database_serialization_compression(self) -> None:
        """Test compression in database serialization."""
        large_raw_data = {"test": "x" * 2000}  # Larger data to ensure compression

        # Test AnimeMetadata serialization
        serialized_data = AnimeMetadata._serialize_json_field(large_raw_data)

        # Should be compressed due to size
        original_json = json.dumps(large_raw_data, ensure_ascii=False)
        assert len(serialized_data) < len(original_json)

        # Test deserialization
        deserialized_data = AnimeMetadata._parse_json_field(serialized_data, {})
        assert deserialized_data == large_raw_data

    def test_database_serialization_no_compression(self) -> None:
        """Test that small data is not compressed in database serialization."""
        small_raw_data = {"test": "small"}

        serialized_data = AnimeMetadata._serialize_json_field(small_raw_data)

        # Should not be compressed due to size
        original_json = json.dumps(small_raw_data, ensure_ascii=False)
        assert serialized_data == original_json

        # Test deserialization
        deserialized_data = AnimeMetadata._parse_json_field(serialized_data, {})
        assert deserialized_data == small_raw_data

    def test_cache_compression_integration(self) -> None:
        """Test compression integration with cache."""
        cache = MetadataCache(
            max_size=100, max_memory_mb=10, enable_db=False  # Disable DB for this test
        )

        large_raw_data = {"test": "x" * 1000}
        anime = TMDBAnime(tmdb_id=12345, title="Test Anime", raw_data=large_raw_data)

        # Store in cache
        cache.put("test_key", anime)

        # Retrieve from cache
        retrieved_anime = cache.get("test_key")

        # Verify data integrity
        assert retrieved_anime is not None
        assert retrieved_anime.tmdb_id == anime.tmdb_id
        assert retrieved_anime.title == anime.title
        assert retrieved_anime.raw_data == anime.raw_data

    def _apply_compression_to_tmdb_anime(self, anime: TMDBAnime) -> TMDBAnime:
        """Apply compression to TMDBAnime raw_data."""
        if anime.raw_data:
            compressed_raw_data = self.compression_manager.compress_for_storage(anime.raw_data)
            return TMDBAnime(
                tmdb_id=anime.tmdb_id,
                title=anime.title,
                original_title=anime.original_title,
                korean_title=anime.korean_title,
                overview=anime.overview,
                release_date=anime.release_date,
                poster_path=anime.poster_path,
                backdrop_path=anime.backdrop_path,
                first_air_date=anime.first_air_date,
                last_air_date=anime.last_air_date,
                status=anime.status,
                vote_average=anime.vote_average,
                vote_count=anime.vote_count,
                popularity=anime.popularity,
                genres=anime.genres,
                networks=anime.networks,
                production_companies=anime.production_companies,
                production_countries=anime.production_countries,
                spoken_languages=anime.spoken_languages,
                number_of_seasons=anime.number_of_seasons,
                number_of_episodes=anime.number_of_episodes,
                tagline=anime.tagline,
                homepage=anime.homepage,
                imdb_id=anime.imdb_id,
                external_ids=anime.external_ids,
                quality_score=anime.quality_score,
                search_strategy=anime.search_strategy,
                fallback_round=anime.fallback_round,
                raw_data=compressed_raw_data,
            )
        return anime

    def _decompress_tmdb_anime(self, anime: TMDBAnime) -> TMDBAnime:
        """Decompress TMDBAnime raw_data."""
        if anime.raw_data:
            decompressed_raw_data = self.compression_manager.decompress_from_storage(
                anime.raw_data, expected_type="dict"
            )
            return TMDBAnime(
                tmdb_id=anime.tmdb_id,
                title=anime.title,
                original_title=anime.original_title,
                korean_title=anime.korean_title,
                overview=anime.overview,
                release_date=anime.release_date,
                poster_path=anime.poster_path,
                backdrop_path=anime.backdrop_path,
                first_air_date=anime.first_air_date,
                last_air_date=anime.last_air_date,
                status=anime.status,
                vote_average=anime.vote_average,
                vote_count=anime.vote_count,
                popularity=anime.popularity,
                genres=anime.genres,
                networks=anime.networks,
                production_companies=anime.production_companies,
                production_countries=anime.production_countries,
                spoken_languages=anime.spoken_languages,
                number_of_seasons=anime.number_of_seasons,
                number_of_episodes=anime.number_of_episodes,
                tagline=anime.tagline,
                homepage=anime.homepage,
                imdb_id=anime.imdb_id,
                external_ids=anime.external_ids,
                quality_score=anime.quality_score,
                search_strategy=anime.search_strategy,
                fallback_round=anime.fallback_round,
                raw_data=decompressed_raw_data,
            )
        return anime

    def _apply_compression_to_parsed_info(self, info: ParsedAnimeInfo) -> ParsedAnimeInfo:
        """Apply compression to ParsedAnimeInfo raw_data."""
        if info.raw_data:
            compressed_raw_data = self.compression_manager.compress_for_storage(info.raw_data)
            return ParsedAnimeInfo(
                title=info.title,
                season=info.season,
                episode=info.episode,
                episode_title=info.episode_title,
                resolution=info.resolution,
                resolution_width=info.resolution_width,
                resolution_height=info.resolution_height,
                video_codec=info.video_codec,
                audio_codec=info.audio_codec,
                release_group=info.release_group,
                file_extension=info.file_extension,
                year=info.year,
                source=info.source,
                raw_data=compressed_raw_data,
            )
        return info

    def _decompress_parsed_info(self, info: ParsedAnimeInfo) -> ParsedAnimeInfo:
        """Decompress ParsedAnimeInfo raw_data."""
        if info.raw_data:
            decompressed_raw_data = self.compression_manager.decompress_from_storage(
                info.raw_data, expected_type="dict"
            )
            return ParsedAnimeInfo(
                title=info.title,
                season=info.season,
                episode=info.episode,
                episode_title=info.episode_title,
                resolution=info.resolution,
                resolution_width=info.resolution_width,
                resolution_height=info.resolution_height,
                video_codec=info.video_codec,
                audio_codec=info.audio_codec,
                release_group=info.release_group,
                file_extension=info.file_extension,
                year=info.year,
                source=info.source,
                raw_data=decompressed_raw_data,
            )
        return info


class TestCompressionPerformance:
    """Test performance impact of compression."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.compression_manager = CompressionManager(
            min_size_threshold=50, max_compression_ratio=0.8
        )

    def test_compression_performance(self) -> None:
        """Test that compression improves performance for large data."""
        large_data = {
            "title": "Test Anime",
            "description": "x" * 10000,  # 10KB of data
            "metadata": [{"key": "value" + str(i)} for i in range(1000)],
        }

        # Measure compression time
        start_time = time.time()
        compressed_data = self.compression_manager.compress_for_storage(large_data)
        compression_time = time.time() - start_time

        # Measure decompression time
        start_time = time.time()
        decompressed_data = self.compression_manager.decompress_from_storage(
            compressed_data, expected_type="dict"
        )
        decompression_time = time.time() - start_time

        # Verify data integrity
        assert decompressed_data == large_data

        # Verify compression is beneficial
        original_size = len(json.dumps(large_data, ensure_ascii=False))
        compressed_size = len(compressed_data)
        compression_ratio = compressed_size / original_size

        assert compression_ratio < 0.8  # Should save at least 20%
        assert compression_time < 1.0  # Should be fast
        assert decompression_time < 1.0  # Should be fast

    def test_compression_memory_savings(self) -> None:
        """Test memory savings from compression."""
        large_data = {"test": "x" * 5000}  # 5KB of data

        # Original size
        original_size = len(json.dumps(large_data, ensure_ascii=False))

        # Compressed size
        compressed_data = self.compression_manager.compress_for_storage(large_data)
        compressed_size = len(compressed_data)

        # Calculate savings
        savings = original_size - compressed_size
        savings_percent = (savings / original_size) * 100

        assert savings > 0
        assert savings_percent > 20  # Should save at least 20%


class TestCompressionEdgeCases:
    """Test edge cases for compression functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.compression_manager = CompressionManager(
            min_size_threshold=50, max_compression_ratio=0.8
        )

    def test_compress_empty_data(self) -> None:
        """Test compression of empty data."""
        empty_data = {}

        result = self.compression_manager.compress_for_storage(empty_data)

        # Should handle empty data gracefully
        assert result is not None

    def test_compress_none_data(self) -> None:
        """Test compression of None data."""
        result = self.compression_manager.compress_for_storage(None)

        # Should handle None gracefully
        assert result is None

    def test_compress_non_compressible_data(self) -> None:
        """Test compression of data that doesn't compress well."""
        # Random binary-like data that doesn't compress well
        non_compressible = "".join([chr(i % 256) for i in range(1000)])

        result = self.compression_manager.compress_for_storage(non_compressible)

        # Should handle non-compressible data gracefully
        assert result is not None

    def test_decompress_invalid_data(self) -> None:
        """Test decompression of invalid data."""
        invalid_data = "invalid_base64_data"

        # Should handle invalid data gracefully
        result = self.compression_manager.decompress_from_storage(invalid_data, expected_type="str")

        assert result == invalid_data  # Should return original data

    def test_compression_with_special_characters(self) -> None:
        """Test compression with special characters and Unicode."""
        special_data = {
            "unicode": "测试数据 🎌",
            "special_chars": "!@#$%^&*()_+-=[]{}|;':\",./<>?",
            "newlines": "line1\nline2\r\nline3",
            "tabs": "col1\tcol2\tcol3",
        }

        compressed = self.compression_manager.compress_for_storage(special_data)
        decompressed = self.compression_manager.decompress_from_storage(
            compressed, expected_type="dict"
        )

        assert decompressed == special_data
