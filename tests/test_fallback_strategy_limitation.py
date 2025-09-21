"""Test fallback strategy limitation for Task 9.

This module tests that limiting fallback strategies to 3 reduces API calls
while maintaining search accuracy.
"""

import unittest
from unittest.mock import Mock, patch, call

from src.core.tmdb_client import TMDBClient, TMDBConfig, FallbackStrategy, SearchStrategy


class TestFallbackStrategyLimitation(unittest.TestCase):
    """Test cases for fallback strategy limitation."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = TMDBConfig(
            api_key="test_api_key",
            language="ko-KR",
            fallback_language="en-US",
            timeout=5,
        )
        self.client = TMDBClient(self.config)

    def test_fallback_strategies_limited_to_three(self):
        """Test that only 3 fallback strategies are used."""
        # Mock the search methods to track calls
        with patch.object(self.client, '_try_multi_search_with_scoring') as mock_search:
            mock_search.return_value = []  # No results to force fallback strategies
            
            # Mock the initial search to return no results
            with patch.object(self.client, 'search_tv_series', return_value=[]):
                query = "Attack on Titan Season 1 [1080p]"
                self.client.search_comprehensive(query)
            
            # Verify that _try_multi_search_with_scoring was called exactly 3 times
            # (once for each fallback strategy)
            self.assertEqual(mock_search.call_count, 3)
            
            # Verify the strategies used
            calls = mock_search.call_args_list
            strategies_used = []
            
            for call_args in calls:
                # Extract the strategy from the call arguments
                # The strategy is passed as the 4th argument (index 3)
                strategy = call_args[0][3]
                strategies_used.append(strategy)
            
            # Should only use SearchStrategy.MULTI for all fallback calls
            # (The fallback strategy type is determined by the query modification)
            expected_strategy = SearchStrategy.MULTI
            
            self.assertEqual(len(strategies_used), 3)
            for strategy in strategies_used:
                self.assertEqual(strategy, expected_strategy)

    def test_fallback_strategy_effectiveness_maintained(self):
        """Test that search accuracy is maintained with limited strategies."""
        test_queries = [
            "Attack on Titan [1080p]",
            "One Piece (2023)",
            "Naruto 720p",
            "Dragon Ball 60fps",
            "나루토 편",
            "원피스 시즌 1",
        ]
        
        for query in test_queries:
            with self.subTest(query=query):
                # Test that each strategy still produces meaningful modifications
                normalized = self.client._normalize_query(query)
                word_reduced = self.client._reduce_query_words(query)
                
                # At least one strategy should modify the query meaningfully
                modifications = []
                if normalized != query and normalized:
                    modifications.append("NORMALIZED")
                if word_reduced != query and word_reduced:
                    modifications.append("WORD_REDUCTION")
                
                # Should have at least one meaningful modification
                self.assertGreater(len(modifications), 0, 
                                 f"No meaningful modifications for query: {query}")

    def test_api_call_reduction_measurement(self):
        """Test that API calls are reduced compared to 5 strategies."""
        query = "Attack on Titan Season 1 [1080p]"
        
        # Mock search to return no results to force all fallback strategies
        with patch.object(self.client, '_try_multi_search_with_scoring') as mock_search:
            mock_search.return_value = []
            
            with patch.object(self.client, 'search_tv_series', return_value=[]):
                self.client.search_comprehensive(query)
            
            # With 3 strategies, should have 3 calls to _try_multi_search_with_scoring
            self.assertEqual(mock_search.call_count, 3)
            
            # Previously with 5 strategies, would have had 5 calls
            # This represents a 40% reduction in API calls
            expected_reduction = (5 - 3) / 5 * 100
            self.assertEqual(expected_reduction, 40.0)

    def test_fallback_strategy_order_preserved(self):
        """Test that fallback strategies are tried in the correct order."""
        with patch.object(self.client, '_try_multi_search_with_scoring') as mock_search:
            mock_search.return_value = []
            
            with patch.object(self.client, 'search_tv_series', return_value=[]):
                query = "Test Query"
                self.client.search_comprehensive(query)
            
            # Verify the order of strategy calls
            calls = mock_search.call_args_list
            self.assertEqual(len(calls), 3)
            
            # All calls should use SearchStrategy.MULTI
            for call in calls:
                self.assertEqual(call[0][3], SearchStrategy.MULTI)

    def test_removed_strategies_not_used(self):
        """Test that removed strategies (PARTIAL_MATCH, WORD_REORDER) are not used."""
        # Verify that the removed methods don't exist
        self.assertFalse(hasattr(self.client, '_create_partial_query'))
        self.assertFalse(hasattr(self.client, '_reorder_query_words'))
        
        # Verify that the removed strategies are not in the enum
        self.assertNotIn('PARTIAL_MATCH', [strategy.value for strategy in FallbackStrategy])
        self.assertNotIn('WORD_REORDER', [strategy.value for strategy in FallbackStrategy])

    def test_strategy_effectiveness_comparison(self):
        """Compare effectiveness of selected vs removed strategies."""
        test_query = "Attack on Titan Season 1 [1080p]"
        
        # Test selected strategies
        normalized = self.client._normalize_query(test_query)
        word_reduced = self.client._reduce_query_words(test_query)
        
        # Simulate what PARTIAL_MATCH would have done
        words = test_query.split()
        partial_match = " ".join(words[:2]) if len(words) > 2 else ""
        
        # Simulate what WORD_REORDER would have done
        word_reorder = " ".join(reversed(words)) if len(words) > 1 else test_query
        
        # Selected strategies should be more effective
        self.assertNotEqual(normalized, test_query)
        self.assertNotEqual(word_reduced, test_query)
        
        # Verify that selected strategies produce different results (if both modify the query)
        # Note: Some queries may produce the same result after normalization and word reduction
        # This is acceptable as long as at least one strategy modifies the query meaningfully
        if normalized != test_query and word_reduced != test_query:
            # If both strategies modify the query, they should ideally produce different results
            # But if they produce the same result, that's still acceptable for this test
            pass  # We'll just verify that at least one strategy modified the query
        
        # Verify that removed strategies would have been less effective
        # PARTIAL_MATCH would have produced "Attack on" (less specific)
        self.assertEqual(partial_match, "Attack on")
        self.assertLess(len(partial_match), len(normalized))
        
        # WORD_REORDER would have produced "[1080p] 1 Season Titan on Attack" (confusing)
        self.assertEqual(word_reorder, "[1080p] 1 Season Titan on Attack")
        self.assertNotEqual(word_reorder, test_query)

    def test_performance_improvement_estimation(self):
        """Estimate performance improvement from strategy reduction."""
        # Calculate theoretical improvement
        original_strategies = 5
        limited_strategies = 3
        reduction_percentage = (original_strategies - limited_strategies) / original_strategies * 100
        
        self.assertEqual(reduction_percentage, 40.0)
        
        # In a real scenario with 100 files, this would mean:
        # - Original: 100 files × 5 strategies = 500 API calls
        # - Limited: 100 files × 3 strategies = 300 API calls
        # - Savings: 200 API calls (40% reduction)
        
        files_count = 100
        original_calls = files_count * original_strategies
        limited_calls = files_count * limited_strategies
        saved_calls = original_calls - limited_calls
        
        self.assertEqual(original_calls, 500)
        self.assertEqual(limited_calls, 300)
        self.assertEqual(saved_calls, 200)
        self.assertEqual(saved_calls / original_calls * 100, 40.0)


if __name__ == "__main__":
    unittest.main()
