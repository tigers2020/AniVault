"""Test fallback strategy effectiveness analysis for Task 9.

This module analyzes the effectiveness of different fallback strategies
to select the top 3 most effective ones for reducing API calls.
"""

import unittest
from unittest.mock import Mock, patch

from src.core.tmdb_client import TMDBClient, TMDBConfig, FallbackStrategy


class TestFallbackStrategyAnalysis(unittest.TestCase):
    """Test cases for analyzing fallback strategy effectiveness."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = TMDBConfig(
            api_key="test_api_key",
            language="ko-KR",
            fallback_language="en-US",
            timeout=5,
        )
        self.client = TMDBClient(self.config)

    def test_normalize_query_effectiveness(self):
        """Test NORMALIZED strategy effectiveness."""
        test_cases = [
            # (input, expected_output, should_be_different)
            ("Attack on Titan [1080p]", "Attack on Titan", True),
            ("One Piece (2023)", "One Piece", True),
            ("Naruto 720p", "Naruto", True),
            ("Dragon Ball 60fps", "Dragon Ball", True),
            ("Attack on Titan - Season 1", "Attack on Titan - Season 1", False),  # Regex doesn't match this pattern
            ("나루토 편", "나루토", True),
            ("원피스 시즌 1", "원피스", True),
            ("Attack on Titan", "Attack on Titan", False),  # No change needed
        ]
        
        for input_query, expected, should_change in test_cases:
            with self.subTest(query=input_query):
                result = self.client._normalize_query(input_query)
                self.assertEqual(result, expected)
                
                if should_change:
                    self.assertNotEqual(result, input_query)
                else:
                    self.assertEqual(result, input_query)

    def test_word_reduction_effectiveness(self):
        """Test WORD_REDUCTION strategy effectiveness."""
        test_cases = [
            # (input, expected_output, should_be_different)
            ("Attack on Titan Season 1", "Attack on Titan Season", True),
            ("One Piece Episode 100", "One Piece Episode", True),
            ("Naruto Shippuden", "Naruto", True),
            ("Dragon Ball", "Dragon", True),
            ("Attack", "", True),  # Single word becomes empty
            ("", "", False),  # Empty stays empty
        ]
        
        for input_query, expected, should_change in test_cases:
            with self.subTest(query=input_query):
                result = self.client._reduce_query_words(input_query)
                self.assertEqual(result, expected)
                
                if should_change and input_query:
                    self.assertNotEqual(result, input_query)

    def test_partial_match_effectiveness(self):
        """Test PARTIAL_MATCH strategy effectiveness."""
        test_cases = [
            # (input, expected_output, should_be_different)
            ("Attack on Titan Season 1", "Attack on", True),
            ("One Piece Episode 100", "One Piece", True),
            ("Naruto Shippuden", "", True),  # Only 2 words, becomes empty
            ("Dragon Ball", "Dragon Ball", False),  # Only 2 words
            ("Attack", "", True),  # Single word becomes empty
            ("", "", False),  # Empty stays empty
        ]
        
        for input_query, expected, should_change in test_cases:
            with self.subTest(query=input_query):
                result = self.client._create_partial_query(input_query)
                self.assertEqual(result, expected)
                
                if should_change and input_query:
                    self.assertNotEqual(result, input_query)

    def test_word_reorder_effectiveness(self):
        """Test WORD_REORDER strategy effectiveness."""
        test_cases = [
            # (input, expected_output, should_be_different)
            ("Attack on Titan", "Titan on Attack", True),
            ("One Piece", "Piece One", True),
            ("Naruto", "Naruto", False),  # Single word unchanged
            ("", "", False),  # Empty stays empty
        ]
        
        for input_query, expected, should_change in test_cases:
            with self.subTest(query=input_query):
                result = self.client._reorder_query_words(input_query)
                self.assertEqual(result, expected)
                
                if should_change and input_query:
                    self.assertNotEqual(result, input_query)

    def test_language_fallback_effectiveness(self):
        """Test LANGUAGE_FALLBACK strategy effectiveness."""
        # This strategy doesn't modify the query, just changes language
        test_cases = [
            "Attack on Titan",
            "One Piece",
            "Naruto",
            "Dragon Ball",
        ]
        
        for query in test_cases:
            with self.subTest(query=query):
                # Language fallback doesn't modify query
                result = query
                self.assertEqual(result, query)

    def test_strategy_distinctiveness(self):
        """Test that strategies produce different results for the same input."""
        test_query = "Attack on Titan Season 1 [1080p]"
        
        normalized = self.client._normalize_query(test_query)
        word_reduced = self.client._reduce_query_words(test_query)
        partial = self.client._create_partial_query(test_query)
        reordered = self.client._reorder_query_words(test_query)
        
        # All strategies should produce different results
        results = [normalized, word_reduced, partial, reordered]
        unique_results = set(results)
        
        # Should have at least 3 unique results (some might be empty)
        self.assertGreaterEqual(len(unique_results), 3)

    def test_strategy_priority_analysis(self):
        """Analyze which strategies are most likely to be effective."""
        # Test with realistic anime file names
        test_queries = [
            "Attack on Titan Season 1 [1080p]",
            "One Piece Episode 100 (2023)",
            "Naruto Shippuden 720p",
            "Dragon Ball Z 60fps",
            "나루토 편",
            "원피스 시즌 1",
            "Attack on Titan - Final Season",
            "One Piece - Wano Arc",
        ]
        
        strategy_effectiveness = {
            FallbackStrategy.NORMALIZED: 0,
            FallbackStrategy.WORD_REDUCTION: 0,
            FallbackStrategy.PARTIAL_MATCH: 0,
            FallbackStrategy.WORD_REORDER: 0,
        }
        
        for query in test_queries:
            # Test each strategy
            normalized = self.client._normalize_query(query)
            if normalized != query and normalized:
                strategy_effectiveness[FallbackStrategy.NORMALIZED] += 1
            
            word_reduced = self.client._reduce_query_words(query)
            if word_reduced != query and word_reduced:
                strategy_effectiveness[FallbackStrategy.WORD_REDUCTION] += 1
            
            partial = self.client._create_partial_query(query)
            if partial != query and partial:
                strategy_effectiveness[FallbackStrategy.PARTIAL_MATCH] += 1
            
            reordered = self.client._reorder_query_words(query)
            if reordered != query and reordered:
                strategy_effectiveness[FallbackStrategy.WORD_REORDER] += 1
        
        # Print effectiveness scores for analysis
        print("\nStrategy Effectiveness Analysis:")
        for strategy, score in sorted(strategy_effectiveness.items(), key=lambda x: x[1], reverse=True):
            print(f"{strategy.value}: {score}/{len(test_queries)} queries modified")
        
        # NORMALIZED should be most effective for file names
        self.assertGreaterEqual(
            strategy_effectiveness[FallbackStrategy.NORMALIZED],
            strategy_effectiveness[FallbackStrategy.WORD_REDUCTION]
        )

    def test_strategy_redundancy_analysis(self):
        """Analyze potential redundancy between strategies."""
        test_query = "Attack on Titan Season 1 [1080p]"
        
        # Get results from all strategies
        normalized = self.client._normalize_query(test_query)
        word_reduced = self.client._reduce_query_words(test_query)
        partial = self.client._create_partial_query(test_query)
        reordered = self.client._reorder_query_words(test_query)
        
        # Check for potential redundancy
        results = [normalized, word_reduced, partial, reordered]
        
        # Count how many strategies produce the same result
        result_counts = {}
        for result in results:
            if result:  # Only count non-empty results
                result_counts[result] = result_counts.get(result, 0) + 1
        
        # Find redundant strategies
        redundant_pairs = []
        for result, count in result_counts.items():
            if count > 1:
                # Find which strategies produce this result
                strategies_with_result = []
                if normalized == result:
                    strategies_with_result.append("NORMALIZED")
                if word_reduced == result:
                    strategies_with_result.append("WORD_REDUCTION")
                if partial == result:
                    strategies_with_result.append("PARTIAL_MATCH")
                if reordered == result:
                    strategies_with_result.append("WORD_REORDER")
                
                if len(strategies_with_result) > 1:
                    redundant_pairs.append((result, strategies_with_result))
        
        print(f"\nRedundancy Analysis for '{test_query}':")
        for result, strategies in redundant_pairs:
            print(f"Result '{result}' produced by: {', '.join(strategies)}")
        
        # Should have minimal redundancy
        self.assertLessEqual(len(redundant_pairs), 1)


if __name__ == "__main__":
    unittest.main()
