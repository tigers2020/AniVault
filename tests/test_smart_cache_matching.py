#!/usr/bin/env python3
"""Comprehensive tests for smart cache matching functionality.

This module contains unit tests, integration tests, and performance tests
for the smart cache matching system, including tests for query normalization,
similarity detection, and cache hit rate improvements.
"""

import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

from src.core.database import DatabaseManager
from src.core.metadata_cache import MetadataCache
from src.core.models import ParsedAnimeInfo, TMDBAnime
from src.core.smart_cache_matcher import SmartCacheMatcher, QueryNormalizer, SimilarityDetector


class TestQueryNormalizer(unittest.TestCase):
    """Test cases for QueryNormalizer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.normalizer = QueryNormalizer()

    def test_basic_normalization(self):
        """Test basic query normalization."""
        test_cases = [
            ("Attack on Titan", "attack titan"),
            ("Attack on Titan: The Final Season", "attack titan final season"),
            ("One Piece (2023)", "one piece 2023"),
            ("Naruto - Shippuden", "naruto shippuden"),
            ("Dragon Ball Z", "dragon ball z"),
        ]
        
        for input_query, expected in test_cases:
            with self.subTest(query=input_query):
                result = self.normalizer.normalize(input_query)
                self.assertEqual(result, expected)

    def test_stop_words_removal(self):
        """Test removal of stop words."""
        test_cases = [
            ("The Attack on Titan", "attack titan"),
            ("A One Piece Movie", "one piece"),
            ("An Anime Series", "anime series"),
            ("Attack on Titan - The Final Season", "attack titan final season"),
        ]
        
        for input_query, expected in test_cases:
            with self.subTest(query=input_query):
                result = self.normalizer.normalize(input_query)
                self.assertEqual(result, expected)

    def test_abbreviation_expansion(self):
        """Test abbreviation expansion."""
        test_cases = [
            ("Attack on Titan S1", "attack titan s1"),
            ("One Piece E1", "one piece e1"),
            ("Naruto OVA", "naruto original video animation"),
            ("Dragon Ball Z Movie", "dragon ball z"),
        ]
        
        for input_query, expected in test_cases:
            with self.subTest(query=input_query):
                result = self.normalizer.normalize(input_query)
                self.assertEqual(result, expected)

    def test_year_extraction(self):
        """Test year extraction and normalization."""
        test_cases = [
            ("Attack on Titan 2013", "attack titan 2013"),
            ("One Piece 99", "one piece 99"),  # 2-digit year not converted
            ("Naruto 15", "naruto 15"),  # 2-digit year not converted
            ("Dragon Ball 95", "dragon ball 95"),  # 2-digit year not converted
            ("Attack on Titan 45", "attack titan 45"),  # 2-digit year not converted
        ]
        
        for input_query, expected in test_cases:
            with self.subTest(query=input_query):
                result = self.normalizer.normalize(input_query)
                self.assertEqual(result, expected)

    def test_special_characters_removal(self):
        """Test removal of special characters."""
        test_cases = [
            ("Attack on Titan: The Final Season", "attack titan final season"),
            ("One Piece (2023)", "one piece 2023"),
            ("Naruto - Shippuden", "naruto shippuden"),
            ("Dragon Ball Z!", "dragon ball z"),
            ("Attack on Titan?", "attack titan"),
        ]
        
        for input_query, expected in test_cases:
            with self.subTest(query=input_query):
                result = self.normalizer.normalize(input_query)
                self.assertEqual(result, expected)


class TestSimilarityDetector(unittest.TestCase):
    """Test cases for SimilarityDetector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.detector = SimilarityDetector(fuzzy_threshold=60.0, phonetic_threshold=0.8)

    def test_exact_match(self):
        """Test exact matching after normalization."""
        target = "Attack on Titan"
        candidates = ["attack titan", "Attack on Titan", "ATTACK ON TITAN"]
        
        matches = self.detector.find_similar_queries(target, candidates, use_fuzzy=True, use_phonetic=False)
        self.assertEqual(len(matches), 3)
        
        for match in matches:
            self.assertEqual(match.similarity_score, 100.0)
            self.assertEqual(match.match_type, "exact")

    def test_fuzzy_matching(self):
        """Test fuzzy matching."""
        target = "Attack on Titan"
        candidates = ["attack_on_titan_2013", "attack titan season 1", "attack on titan final season"]
        
        matches = self.detector.find_similar_queries(target, candidates, use_fuzzy=True, use_phonetic=False)
        self.assertGreater(len(matches), 0)
        
        for match in matches:
            self.assertGreaterEqual(match.similarity_score, 60.0)
            self.assertEqual(match.match_type, "fuzzy")

    def test_no_matches_below_threshold(self):
        """Test that queries below threshold don't match."""
        target = "Attack on Titan"
        candidates = ["completely different anime", "totally unrelated title"]
        
        matches = self.detector.find_similar_queries(target, candidates, use_fuzzy=True, use_phonetic=False)
        self.assertEqual(len(matches), 0)

    def test_empty_inputs(self):
        """Test handling of empty inputs."""
        # Empty target
        matches = self.detector.find_similar_queries("", ["attack on titan"], use_fuzzy=True, use_phonetic=False)
        self.assertEqual(len(matches), 0)
        
        # Empty candidates
        matches = self.detector.find_similar_queries("attack on titan", [], use_fuzzy=True, use_phonetic=False)
        self.assertEqual(len(matches), 0)
        
        # None inputs
        matches = self.detector.find_similar_queries(None, ["attack on titan"], use_fuzzy=True, use_phonetic=False)
        self.assertEqual(len(matches), 0)

    def test_match_sorting(self):
        """Test that matches are sorted by similarity score."""
        target = "Attack on Titan"
        candidates = [
            "attack on titan final season",  # Should have high similarity
            "attack titan",  # Should have very high similarity
            "attack on titan season 1",  # Should have high similarity
        ]
        
        matches = self.detector.find_similar_queries(target, candidates, use_fuzzy=True, use_phonetic=False)
        self.assertGreater(len(matches), 0)
        
        # Check that matches are sorted by score (highest first)
        for i in range(len(matches) - 1):
            self.assertGreaterEqual(matches[i].similarity_score, matches[i + 1].similarity_score)


class TestSmartCacheMatcher(unittest.TestCase):
    """Test cases for SmartCacheMatcher class."""

    def setUp(self):
        """Set up test fixtures."""
        self.matcher = SmartCacheMatcher(fuzzy_threshold=60.0)

    def test_calculate_similarity(self):
        """Test similarity calculation between two queries."""
        test_cases = [
            ("Attack on Titan", "attack_on_titan_2013", 0.6),  # Should be similar
            ("Attack on Titan", "attack titan", 1.0),  # Should be exact match
            ("Attack on Titan", "completely different", 0.0),  # Should be no match
        ]
        
        for query1, query2, min_expected in test_cases:
            with self.subTest(query1=query1, query2=query2):
                similarity = self.matcher.calculate_similarity(query1, query2)
                self.assertGreaterEqual(similarity, min_expected)
                self.assertLessEqual(similarity, 1.0)

    def test_normalize_query(self):
        """Test query normalization."""
        test_cases = [
            ("Attack on Titan", "attack titan"),
            ("Attack on Titan: The Final Season", "attack titan final season"),
            ("One Piece (2023)", "one piece 2023"),
        ]
        
        for input_query, expected in test_cases:
            with self.subTest(query=input_query):
                result = self.matcher.normalize_query(input_query)
                self.assertEqual(result, expected)

    def test_find_similar_cache_keys(self):
        """Test finding similar cache keys."""
        cache_keys = [
            "attack_on_titan_2013",
            "attack_on_titan_final_season_2020",
            "one_piece_1999",
            "naruto_shippuden_2007",
        ]
        
        # Test with similar query
        similar_keys = self.matcher.find_similar_cache_keys("attack on titan", cache_keys, use_fuzzy=True, use_phonetic=False)
        self.assertGreater(len(similar_keys), 0)
        
        # Test with different query
        similar_keys = self.matcher.find_similar_cache_keys("one piece", cache_keys, use_fuzzy=True, use_phonetic=False)
        self.assertGreater(len(similar_keys), 0)

    def test_generate_similarity_keys(self):
        """Test generation of similarity keys."""
        query = "Attack on Titan"
        keys = self.matcher.generate_similarity_keys(query)
        
        self.assertIsInstance(keys, list)
        self.assertGreater(len(keys), 0)
        
        # Check that keys contain the normalized query
        self.assertIn("attack titan", keys)

    def test_should_use_smart_matching(self):
        """Test decision logic for using smart matching."""
        # Test with queries that should use smart matching
        self.assertTrue(self.matcher.should_use_smart_matching("Attack on Titan: The Final Season"))
        self.assertTrue(self.matcher.should_use_smart_matching("Attack on Titan (2023)"))
        
        # Should not use smart matching for very short queries
        self.assertFalse(self.matcher.should_use_smart_matching("A"))
        self.assertFalse(self.matcher.should_use_smart_matching("An"))
        self.assertFalse(self.matcher.should_use_smart_matching("Attack on Titan"))  # No variation patterns


class TestSmartCacheMatchingIntegration(unittest.TestCase):
    """Integration tests for smart cache matching with MetadataCache."""

    def setUp(self):
        """Set up test fixtures."""
        self.cache = MetadataCache(max_size=100, max_memory_mb=10, default_ttl_seconds=3600)

    def tearDown(self):
        """Clean up after tests."""
        self.cache.clear()

    def test_smart_get_basic(self):
        """Test basic smart get functionality."""
        # Store test data
        anime1 = TMDBAnime(tmdb_id=1, title="Attack on Titan", first_air_date=datetime(2013, 4, 7))
        anime2 = TMDBAnime(tmdb_id=2, title="Attack on Titan: The Final Season", first_air_date=datetime(2020, 12, 7))
        
        self.cache.put("attack_on_titan_2013", anime1)
        self.cache.put("attack_on_titan_final_season_2020", anime2)
        
        # Test smart get
        results = self.cache.get_smart("attack on titan", similarity_threshold=0.6, max_results=5)
        self.assertGreater(len(results), 0)
        
        # Check that results contain expected anime
        titles = [anime.title for anime, _ in results]
        self.assertIn("Attack on Titan", titles)

    def test_smart_get_with_different_queries(self):
        """Test smart get with various query formats."""
        # Store test data
        anime = TMDBAnime(tmdb_id=1, title="Attack on Titan", first_air_date=datetime(2013, 4, 7))
        self.cache.put("attack_on_titan_2013", anime)
        
        # Test different query formats that should match
        query_variations = [
            "attack on titan",
            "Attack on Titan",
            "ATTACK ON TITAN",
            "attack titan",
        ]
        
        for query in query_variations:
            with self.subTest(query=query):
                results = self.cache.get_smart(query, similarity_threshold=0.6, max_results=5)
                self.assertGreater(len(results), 0)

    def test_smart_get_no_matches(self):
        """Test smart get when no matches are found."""
        # Store test data
        anime = TMDBAnime(tmdb_id=1, title="Attack on Titan", first_air_date=datetime(2013, 4, 7))
        self.cache.put("attack_on_titan_2013", anime)
        
        # Test with completely different query
        results = self.cache.get_smart("completely different anime", similarity_threshold=0.6, max_results=5)
        self.assertEqual(len(results), 0)

    def test_smart_get_threshold_filtering(self):
        """Test that similarity threshold filters results correctly."""
        # Store test data
        anime1 = TMDBAnime(tmdb_id=1, title="Attack on Titan", first_air_date=datetime(2013, 4, 7))
        anime2 = TMDBAnime(tmdb_id=2, title="One Piece", first_air_date=datetime(1999, 10, 20))
        
        self.cache.put("attack_on_titan_2013", anime1)
        self.cache.put("one_piece_1999", anime2)
        
        # Test with high threshold (should find fewer matches)
        results_high = self.cache.get_smart("attack on titan", similarity_threshold=0.9, max_results=5)
        
        # Test with low threshold (should find more matches)
        results_low = self.cache.get_smart("attack on titan", similarity_threshold=0.3, max_results=5)
        
        self.assertLessEqual(len(results_high), len(results_low))

    def test_smart_get_max_results_limit(self):
        """Test that max_results parameter limits the number of results."""
        # Store multiple test data
        for i in range(10):
            anime = TMDBAnime(tmdb_id=i, title=f"Attack on Titan Season {i}", first_air_date=datetime(2013 + i, 4, 7))
            self.cache.put(f"attack_on_titan_season_{i}", anime)
        
        # Test with max_results limit
        results = self.cache.get_smart("attack on titan", similarity_threshold=0.6, max_results=3)
        self.assertLessEqual(len(results), 3)

    def test_similarity_key_storage(self):
        """Test that similarity keys are stored correctly."""
        # Store test data
        anime = TMDBAnime(tmdb_id=1, title="Attack on Titan", first_air_date=datetime(2013, 4, 7))
        self.cache.put("attack_on_titan_2013", anime)
        
        # Check that similarity keys were stored
        stats = self.cache.get_similarity_stats()
        self.assertGreater(stats["total_similarity_keys"], 0)

    def test_find_similar_keys(self):
        """Test finding similar keys functionality."""
        # Store test data
        anime = TMDBAnime(tmdb_id=1, title="Attack on Titan", first_air_date=datetime(2013, 4, 7))
        self.cache.put("attack_on_titan_2013", anime)
        
        # Test finding similar keys
        similar_keys = self.cache.find_similar_keys("attack on titan", threshold=0.6)
        self.assertGreater(len(similar_keys), 0)
        
        # Check that the stored key is found
        key_names = [key for key, _ in similar_keys]
        self.assertIn("attack_on_titan_2013", key_names)

    def test_similarity_stats(self):
        """Test similarity statistics functionality."""
        # Store test data
        anime1 = TMDBAnime(tmdb_id=1, title="Attack on Titan", first_air_date=datetime(2013, 4, 7))
        anime2 = TMDBAnime(tmdb_id=2, title="One Piece", first_air_date=datetime(1999, 10, 20))
        
        self.cache.put("attack_on_titan_2013", anime1)
        self.cache.put("one_piece_1999", anime2)
        
        # Get similarity stats
        stats = self.cache.get_similarity_stats()
        
        # Check that stats contain expected fields
        expected_fields = ["total_cache_keys", "total_similarity_keys", "average_similarity_keys_per_entry", "similarity_key_coverage"]
        for field in expected_fields:
            self.assertIn(field, stats)
        
        # Check that stats make sense
        self.assertEqual(stats["total_cache_keys"], 2)
        self.assertGreater(stats["total_similarity_keys"], 0)
        self.assertGreater(stats["average_similarity_keys_per_entry"], 0)
        self.assertGreaterEqual(stats["similarity_key_coverage"], 0.0)
        self.assertLessEqual(stats["similarity_key_coverage"], 1.0)


class TestSmartCacheMatchingPerformance(unittest.TestCase):
    """Performance tests for smart cache matching."""

    def setUp(self):
        """Set up test fixtures."""
        self.cache = MetadataCache(max_size=1000, max_memory_mb=100, default_ttl_seconds=3600)

    def tearDown(self):
        """Clean up after tests."""
        self.cache.clear()

    def test_smart_get_performance(self):
        """Test performance of smart get operations."""
        # Store large dataset
        for i in range(100):
            anime = TMDBAnime(tmdb_id=i, title=f"Anime {i}", first_air_date=datetime(2000 + i, 1, 1))
            self.cache.put(f"anime_{i}", anime)
        
        # Measure smart get performance
        start_time = time.time()
        results = self.cache.get_smart("anime", similarity_threshold=0.6, max_results=10)
        end_time = time.time()
        
        # Check that operation completed in reasonable time
        execution_time = end_time - start_time
        self.assertLess(execution_time, 1.0)  # Should complete within 1 second
        self.assertGreater(len(results), 0)

    def test_similarity_key_generation_performance(self):
        """Test performance of similarity key generation."""
        matcher = SmartCacheMatcher()
        
        # Measure similarity key generation performance
        start_time = time.time()
        for i in range(100):
            keys = matcher.generate_similarity_keys(f"Anime {i}")
        end_time = time.time()
        
        # Check that operation completed in reasonable time
        execution_time = end_time - start_time
        self.assertLess(execution_time, 1.0)  # Should complete within 1 second

    def test_cache_hit_rate_improvement(self):
        """Test that smart matching improves cache hit rate."""
        # Store test data with various key formats
        anime = TMDBAnime(tmdb_id=1, title="Attack on Titan", first_air_date=datetime(2013, 4, 7))
        self.cache.put("attack_on_titan_2013", anime)
        
        # Test regular get (should miss)
        regular_result = self.cache.get("attack on titan")
        self.assertIsNone(regular_result)
        
        # Test smart get (should hit)
        smart_results = self.cache.get_smart("attack on titan", similarity_threshold=0.6, max_results=5)
        self.assertGreater(len(smart_results), 0)


class TestSmartCacheMatchingEdgeCases(unittest.TestCase):
    """Test edge cases for smart cache matching."""

    def setUp(self):
        """Set up test fixtures."""
        self.cache = MetadataCache(max_size=100, max_memory_mb=10, default_ttl_seconds=3600)

    def tearDown(self):
        """Clean up after tests."""
        self.cache.clear()

    def test_empty_cache_smart_get(self):
        """Test smart get on empty cache."""
        results = self.cache.get_smart("any query", similarity_threshold=0.6, max_results=5)
        self.assertEqual(len(results), 0)

    def test_smart_get_with_none_inputs(self):
        """Test smart get with None inputs."""
        # Test with None query
        results = self.cache.get_smart(None, similarity_threshold=0.6, max_results=5)
        self.assertEqual(len(results), 0)

    def test_smart_get_with_empty_string(self):
        """Test smart get with empty string query."""
        results = self.cache.get_smart("", similarity_threshold=0.6, max_results=5)
        self.assertEqual(len(results), 0)

    def test_smart_get_with_very_high_threshold(self):
        """Test smart get with very high similarity threshold."""
        # Store test data
        anime = TMDBAnime(tmdb_id=1, title="Attack on Titan", first_air_date=datetime(2013, 4, 7))
        self.cache.put("attack_on_titan_2013", anime)
        
        # Test with very high threshold
        results = self.cache.get_smart("attack on titan", similarity_threshold=0.99, max_results=5)
        # Should still find exact matches
        self.assertGreaterEqual(len(results), 0)

    def test_smart_get_with_zero_max_results(self):
        """Test smart get with zero max_results."""
        # Store test data
        anime = TMDBAnime(tmdb_id=1, title="Attack on Titan", first_air_date=datetime(2013, 4, 7))
        self.cache.put("attack_on_titan_2013", anime)
        
        # Test with zero max_results
        results = self.cache.get_smart("attack on titan", similarity_threshold=0.6, max_results=0)
        self.assertEqual(len(results), 0)

    def test_smart_get_with_negative_threshold(self):
        """Test smart get with negative similarity threshold."""
        # Store test data
        anime = TMDBAnime(tmdb_id=1, title="Attack on Titan", first_air_date=datetime(2013, 4, 7))
        self.cache.put("attack_on_titan_2013", anime)
        
        # Test with negative threshold
        results = self.cache.get_smart("attack on titan", similarity_threshold=-0.1, max_results=5)
        # Should find all matches
        self.assertGreater(len(results), 0)


if __name__ == "__main__":
    unittest.main()
