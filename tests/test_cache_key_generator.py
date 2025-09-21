"""Comprehensive tests for cache key generation system.

This module tests the simplified cache key generation logic to ensure
deterministic behavior, no collisions, and improved cache hit rates.
"""

import pytest

from src.core.cache_key_generator import CacheKeyGenerator, get_cache_key_generator


class TestCacheKeyGenerator:
    """Test cases for CacheKeyGenerator class."""

    def test_tmdb_search_key_generation(self) -> None:
        """Test TMDB search key generation with various inputs."""
        generator = CacheKeyGenerator()

        # Test basic search key
        key1 = generator.generate_tmdb_search_key("Attack on Titan", "ko-KR")
        key2 = generator.generate_tmdb_search_key("Attack on Titan", "ko-KR")
        assert key1 == key2, "Same inputs should generate identical keys"

        # Test with different languages
        key3 = generator.generate_tmdb_search_key("Attack on Titan", "en-US")
        assert key1 != key3, "Different languages should generate different keys"

        # Test with normalized queries
        key4 = generator.generate_tmdb_search_key("  attack on titan  ", "ko-KR")
        assert key1 == key4, "Normalized queries should generate same keys"

        # Test with special characters
        key5 = generator.generate_tmdb_search_key("Attack on Titan: Final Season", "ko-KR")
        key6 = generator.generate_tmdb_search_key("Attack on Titan Final Season", "ko-KR")
        assert key5 == key6, "Special characters should be normalized consistently"

    def test_tmdb_multi_key_generation(self) -> None:
        """Test TMDB multi search key generation."""
        generator = CacheKeyGenerator()

        # Test basic multi key
        key1 = generator.generate_tmdb_multi_key("One Piece", "ko-KR", "KR", False)
        key2 = generator.generate_tmdb_multi_key("One Piece", "ko-KR", "KR", False)
        assert key1 == key2, "Same inputs should generate identical keys"

        # Test with different parameters
        key3 = generator.generate_tmdb_multi_key("One Piece", "en-US", "US", True)
        assert key1 != key3, "Different parameters should generate different keys"

        # Test include_adult flag
        key4 = generator.generate_tmdb_multi_key("One Piece", "ko-KR", "KR", True)
        assert key1 != key4, "Different include_adult values should generate different keys"

    def test_tmdb_details_key_generation(self) -> None:
        """Test TMDB details key generation."""
        generator = CacheKeyGenerator()

        # Test basic details key
        key1 = generator.generate_tmdb_details_key("tv", 12345, "ko-KR")
        key2 = generator.generate_tmdb_details_key("tv", 12345, "ko-KR")
        assert key1 == key2, "Same inputs should generate identical keys"

        # Test with different media types
        key3 = generator.generate_tmdb_details_key("movie", 12345, "ko-KR")
        assert key1 != key3, "Different media types should generate different keys"

        # Test with different IDs
        key4 = generator.generate_tmdb_details_key("tv", 67890, "ko-KR")
        assert key1 != key4, "Different IDs should generate different keys"

    def test_tmdb_series_key_generation(self) -> None:
        """Test TMDB series key generation."""
        generator = CacheKeyGenerator()

        # Test basic series key
        key1 = generator.generate_tmdb_series_key(12345, "ko-KR")
        key2 = generator.generate_tmdb_series_key(12345, "ko-KR")
        assert key1 == key2, "Same inputs should generate identical keys"

        # Test with different languages
        key3 = generator.generate_tmdb_series_key(12345, "en-US")
        assert key1 != key3, "Different languages should generate different keys"

    def test_tmdb_anime_key_generation(self) -> None:
        """Test TMDB anime key generation."""
        generator = CacheKeyGenerator()

        # Test basic anime key
        key1 = generator.generate_tmdb_anime_key(12345)
        key2 = generator.generate_tmdb_anime_key(12345)
        assert key1 == key2, "Same inputs should generate identical keys"

        # Test with different IDs
        key3 = generator.generate_tmdb_anime_key(67890)
        assert key1 != key3, "Different IDs should generate different keys"

    def test_file_key_generation(self) -> None:
        """Test file key generation."""
        generator = CacheKeyGenerator()

        # Test basic file key
        key1 = generator.generate_file_key("/path/to/anime.mkv")
        key2 = generator.generate_file_key("/path/to/anime.mkv")
        assert key1 == key2, "Same inputs should generate identical keys"

        # Test with different paths
        key3 = generator.generate_file_key("/different/path/anime.mkv")
        assert key1 != key3, "Different paths should generate different keys"

        # Test path normalization
        key4 = generator.generate_file_key("\\path\\to\\anime.mkv")  # Windows path
        key5 = generator.generate_file_key("/path/to/anime.mkv")  # Unix path
        assert key4 == key5, "Normalized paths should generate same keys"

    def test_anime_metadata_key_generation(self) -> None:
        """Test anime metadata key generation."""
        generator = CacheKeyGenerator()

        # Test basic metadata key
        key1 = generator.generate_anime_metadata_key(12345)
        key2 = generator.generate_anime_metadata_key(12345)
        assert key1 == key2, "Same inputs should generate identical keys"

        # Test with different IDs
        key3 = generator.generate_anime_metadata_key(67890)
        assert key1 != key3, "Different IDs should generate different keys"

    def test_parsed_file_meta_key_generation(self) -> None:
        """Test parsed file metadata key generation."""
        generator = CacheKeyGenerator()

        # Test basic parsed file meta key
        key1 = generator.generate_parsed_file_meta_key(123)
        key2 = generator.generate_parsed_file_meta_key(123)
        assert key1 == key2, "Same inputs should generate identical keys"

        # Test with different IDs
        key3 = generator.generate_parsed_file_meta_key(456)
        assert key1 != key3, "Different IDs should generate different keys"

    def test_key_normalization(self) -> None:
        """Test key normalization functionality."""
        generator = CacheKeyGenerator()

        # Test query normalization
        query1 = "  Attack on Titan  "
        query2 = "attack on titan"
        key1 = generator.generate_tmdb_search_key(query1, "ko-KR")
        key2 = generator.generate_tmdb_search_key(query2, "ko-KR")
        assert key1 == key2, "Normalized queries should generate same keys"

        # Test special character removal
        query3 = "Attack on Titan: Final Season!"
        query4 = "Attack on Titan Final Season"
        key3 = generator.generate_tmdb_search_key(query3, "ko-KR")
        key4 = generator.generate_tmdb_search_key(query4, "ko-KR")
        assert key3 == key4, "Special characters should be normalized consistently"

    def test_key_hashing(self) -> None:
        """Test key hashing for long keys."""
        generator = CacheKeyGenerator(use_hashing=True)

        # Create a very long query that should trigger hashing
        long_query = "A" * 300  # 300 characters
        key = generator.generate_tmdb_search_key(long_query, "ko-KR")

        # Key should be hashed and shorter than original
        assert len(key) < len(long_query), "Hashed key should be shorter than original"
        assert "search:" in key, "Hashed key should contain prefix"

        # Same long query should generate same hashed key
        key2 = generator.generate_tmdb_search_key(long_query, "ko-KR")
        assert key == key2, "Same long query should generate same hashed key"

    def test_no_hashing_mode(self) -> None:
        """Test key generation without hashing."""
        generator = CacheKeyGenerator(use_hashing=False)

        # Even long queries should not be hashed
        long_query = "A" * 300
        key = generator.generate_tmdb_search_key(long_query, "ko-KR")

        # Key should contain the full query
        assert (
            long_query.lower().strip() in key
        ), "Key should contain full query when hashing disabled"

    def test_key_collision_detection(self) -> None:
        """Test that different inputs don't generate colliding keys."""
        generator = CacheKeyGenerator()

        # Generate keys for various different inputs
        keys = set()

        # Different search queries
        keys.add(generator.generate_tmdb_search_key("Attack on Titan", "ko-KR"))
        keys.add(generator.generate_tmdb_search_key("One Piece", "ko-KR"))
        keys.add(generator.generate_tmdb_search_key("Naruto", "ko-KR"))

        # Different media types
        keys.add(generator.generate_tmdb_details_key("tv", 123, "ko-KR"))
        keys.add(generator.generate_tmdb_details_key("movie", 123, "ko-KR"))

        # Different IDs
        keys.add(generator.generate_tmdb_anime_key(123))
        keys.add(generator.generate_tmdb_anime_key(456))

        # Different file paths (using different names to avoid normalization conflicts)
        keys.add(generator.generate_file_key("/path1/anime1.mkv"))
        keys.add(generator.generate_file_key("/path2/anime2.mkv"))

        # All keys should be unique (3 search + 2 details + 2 tmdb + 2 file = 9)
        assert len(keys) == 9, f"Expected 9 unique keys, got {len(keys)}: {keys}"

    def test_semantic_equivalence(self) -> None:
        """Test that semantically equivalent inputs generate same keys."""
        generator = CacheKeyGenerator()

        # Test case variations
        queries = [
            "Attack on Titan",
            "attack on titan",
            "  Attack on Titan  ",
            "Attack on Titan:",
            "Attack on Titan!",
            "Attack on Titan?",
        ]

        keys = [generator.generate_tmdb_search_key(q, "ko-KR") for q in queries]

        # All should generate the same key
        assert all(
            key == keys[0] for key in keys
        ), "Semantically equivalent queries should generate same keys"

    def test_key_info_extraction(self) -> None:
        """Test key information extraction for debugging."""
        generator = CacheKeyGenerator()

        key = generator.generate_tmdb_search_key("Test Query", "ko-KR")
        info = generator.extract_key_info(key)

        assert info["type"] == "search"
        assert "raw" in info
        assert "parts" in info
        assert "is_hashed" in info

    def test_global_generator_instance(self) -> None:
        """Test global generator instance."""
        generator1 = get_cache_key_generator()
        generator2 = get_cache_key_generator()

        # Should return the same instance
        assert generator1 is generator2, "Global generator should return same instance"

        # Should work correctly
        key1 = generator1.generate_tmdb_search_key("Test", "ko-KR")
        key2 = generator2.generate_tmdb_search_key("Test", "ko-KR")
        assert key1 == key2, "Global generator should work consistently"

    def test_edge_cases(self) -> None:
        """Test edge cases and error conditions."""
        generator = CacheKeyGenerator()

        # Empty query
        key1 = generator.generate_tmdb_search_key("", "ko-KR")
        key2 = generator.generate_tmdb_search_key("", "ko-KR")
        assert key1 == key2, "Empty queries should generate consistent keys"

        # None-like values (should be handled gracefully)
        key3 = generator.generate_tmdb_search_key("   ", "ko-KR")
        key4 = generator.generate_tmdb_search_key("", "ko-KR")
        assert key3 == key4, "Whitespace-only queries should be normalized to empty"

    def test_performance_with_many_keys(self) -> None:
        """Test performance with many key generations."""
        generator = CacheKeyGenerator()

        # Generate many keys to test performance
        keys = []
        for i in range(1000):
            key = generator.generate_tmdb_search_key(f"Query {i}", "ko-KR")
            keys.append(key)

        # All keys should be unique
        assert len(set(keys)) == 1000, "All generated keys should be unique"

        # Keys should be deterministic
        for i in range(1000):
            key = generator.generate_tmdb_search_key(f"Query {i}", "ko-KR")
            assert key == keys[i], f"Key {i} should be deterministic"


class TestCacheKeyIntegration:
    """Integration tests for cache key generation with real data."""

    def test_real_anime_queries(self) -> None:
        """Test with real anime query examples."""
        generator = CacheKeyGenerator()

        # Real anime titles with various formats
        anime_titles = [
            "Attack on Titan",
            "One Piece",
            "Naruto",
            "Demon Slayer: Kimetsu no Yaiba",
            "My Hero Academia",
            "Death Note",
            "Fullmetal Alchemist: Brotherhood",
            "Hunter x Hunter",
            "Dragon Ball Z",
            "Spirited Away",
        ]

        keys = []
        for title in anime_titles:
            key = generator.generate_tmdb_search_key(title, "ko-KR")
            keys.append(key)

        # All keys should be unique
        assert len(set(keys)) == len(anime_titles), "All anime titles should generate unique keys"

        # Keys should be deterministic
        for i, title in enumerate(anime_titles):
            key = generator.generate_tmdb_search_key(title, "ko-KR")
            assert key == keys[i], f"Key for '{title}' should be deterministic"

    def test_file_path_variations(self) -> None:
        """Test with various file path formats."""
        generator = CacheKeyGenerator()

        # Different file path formats
        file_paths = [
            "/home/user/anime/Attack on Titan S01E01.mkv",
            "C:\\Users\\user\\anime\\One Piece\\episode_001.mp4",
            "/anime/Naruto/season_1/episode_01.avi",
            "D:/Anime/Demon Slayer/S01E01.mkv",
            "/media/anime/My Hero Academia/season_1/episode_01.mkv",
        ]

        keys = []
        for path in file_paths:
            key = generator.generate_file_key(path)
            keys.append(key)

        # All keys should be unique
        assert len(set(keys)) == len(file_paths), "All file paths should generate unique keys"

        # Keys should be deterministic
        for i, path in enumerate(file_paths):
            key = generator.generate_file_key(path)
            assert key == keys[i], f"Key for '{path}' should be deterministic"

    def test_language_variations(self) -> None:
        """Test with different language codes."""
        generator = CacheKeyGenerator()

        languages = ["ko-KR", "en-US", "ja-JP", "zh-CN", "es-ES", "fr-FR"]
        query = "Attack on Titan"

        keys = []
        for lang in languages:
            key = generator.generate_tmdb_search_key(query, lang)
            keys.append(key)

        # All keys should be unique
        assert len(set(keys)) == len(languages), "Different languages should generate unique keys"

        # Keys should be deterministic
        for i, lang in enumerate(languages):
            key = generator.generate_tmdb_search_key(query, lang)
            assert key == keys[i], f"Key for language '{lang}' should be deterministic"


if __name__ == "__main__":
    pytest.main([__file__])
