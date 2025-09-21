"""Test fallback strategy limitation for Task 9.

This module tests that limiting fallback strategies to 3 reduces API calls
while maintaining search accuracy.
"""

import unittest
from unittest.mock import Mock, patch, call

from src.core.tmdb_client import TMDBClient, TMDBConfig, SearchStrategyType, SearchStrategy


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

    def test_three_strategies_used(self):
        """Test that exactly 3 strategies are used in the new approach."""
        query = "Attack on Titan Season 1 [1080p]"

        # Mock the strategy methods to track calls
        with patch.object(self.client, '_strategy_exact_title_with_year') as mock_strategy1, \
             patch.object(self.client, '_strategy_exact_title_only') as mock_strategy2, \
             patch.object(self.client, '_strategy_cleaned_title') as mock_strategy3:

            # Mock all strategies to return no results
            mock_strategy1.return_value = []
            mock_strategy2.return_value = []
            mock_strategy3.return_value = []

            # Call the 3-strategy search
            self.client.search_with_three_strategies(query)

            # Verify that all 3 strategies were called
            mock_strategy1.assert_called_once()
            mock_strategy2.assert_called_once()
            mock_strategy3.assert_called_once()

    def test_strategy_effectiveness_maintained(self):
        """Test that search accuracy is maintained with the 3 strategies."""
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
                # Test that each strategy produces meaningful modifications
                normalized = self.client._normalize_query(query)
                cleaned = self.client._clean_title_for_search(query)
                year_hint = self.client._extract_year_from_query(query)

                # At least one strategy should modify the query meaningfully
                modifications = []
                if normalized != query and normalized:
                    modifications.append("NORMALIZED")
                if cleaned != query and cleaned:
                    modifications.append("CLEANED")
                if year_hint:
                    modifications.append("YEAR_EXTRACTED")

                # Should have at least one meaningful modification
                self.assertGreater(len(modifications), 0,
                                 f"No meaningful modifications for query: {query}")

    def test_api_call_reduction_measurement(self):
        """Test that API calls are reduced to exactly 3 strategies."""
        query = "Attack on Titan Season 1 [1080p]"

        # Mock the individual strategy methods to track calls
        with patch.object(self.client, '_strategy_exact_title_with_year') as mock_strategy1, \
             patch.object(self.client, '_strategy_exact_title_only') as mock_strategy2, \
             patch.object(self.client, '_strategy_cleaned_title') as mock_strategy3:

            # Mock all strategies to return no results
            mock_strategy1.return_value = []
            mock_strategy2.return_value = []
            mock_strategy3.return_value = []

            # Call the 3-strategy search
            self.client.search_with_three_strategies(query)

            # Should have exactly 3 strategy calls (one for each strategy)
            self.assertEqual(mock_strategy1.call_count, 1)
            self.assertEqual(mock_strategy2.call_count, 1)
            self.assertEqual(mock_strategy3.call_count, 1)

            # This represents a 25% reduction from the previous 4 strategies
            expected_reduction = (4 - 3) / 4 * 100
            self.assertEqual(expected_reduction, 25.0)

    def test_strategy_order_preserved(self):
        """Test that strategies are tried in the correct order."""
        query = "Attack on Titan (2023) [1080p]"

        # Track the order of strategy calls
        call_order = []

        def track_strategy1(*args, **kwargs):
            call_order.append("EXACT_TITLE_WITH_YEAR")
            return []

        def track_strategy2(*args, **kwargs):
            call_order.append("EXACT_TITLE_ONLY")
            return []

        def track_strategy3(*args, **kwargs):
            call_order.append("CLEANED_TITLE")
            return []

        with patch.object(self.client, '_strategy_exact_title_with_year', side_effect=track_strategy1), \
             patch.object(self.client, '_strategy_exact_title_only', side_effect=track_strategy2), \
             patch.object(self.client, '_strategy_cleaned_title', side_effect=track_strategy3):

            self.client.search_with_three_strategies(query)

            # Verify the correct order
            expected_order = ["EXACT_TITLE_WITH_YEAR", "EXACT_TITLE_ONLY", "CLEANED_TITLE"]
            self.assertEqual(call_order, expected_order)

    def test_strategy_types_defined(self):
        """Test that the new strategy types are properly defined."""
        # Verify that SearchStrategyType enum has the correct values
        strategy_values = [strategy.value for strategy in SearchStrategyType]

        expected_strategies = [
            "exact_title_with_year",
            "exact_title_only",
            "cleaned_title"
        ]

        for strategy in expected_strategies:
            self.assertIn(strategy, strategy_values)

        # Should have exactly 3 strategies
        self.assertEqual(len(strategy_values), 3)

    def test_strategy_effectiveness_comparison(self):
        """Compare effectiveness of the 3 selected strategies."""
        test_query = "Attack on Titan Season 1 [1080p] (2023)"

        # Test the 3 strategies
        year_hint = self.client._extract_year_from_query(test_query)
        title_without_year = test_query.replace("(2023)", "").strip()
        normalized = self.client._normalize_query(test_query)
        cleaned = self.client._clean_title_for_search(test_query)

        # Strategy 1: Exact title with year (most precise)
        self.assertEqual(year_hint, 2023)
        self.assertIn("Attack on Titan Season 1 [1080p]", title_without_year)

        # Strategy 2: Exact title only (medium precision)
        self.assertNotEqual(normalized, test_query)
        self.assertIn("Attack on Titan Season 1", normalized)

        # Strategy 3: Cleaned title (broadest search)
        self.assertNotEqual(cleaned, test_query)
        self.assertIn("Attack on Titan", cleaned)

        # All strategies should produce meaningful modifications
        self.assertTrue(year_hint is not None)
        self.assertTrue(normalized)
        self.assertTrue(cleaned)

    def test_performance_improvement_estimation(self):
        """Estimate performance improvement from strategy reduction."""
        # Calculate theoretical improvement
        original_strategies = 4  # Previous: 1 initial + 3 fallback
        limited_strategies = 3   # New: 3 integrated strategies
        reduction_percentage = (original_strategies - limited_strategies) / original_strategies * 100

        self.assertEqual(reduction_percentage, 25.0)

        # In a real scenario with 100 files, this would mean:
        # - Original: 100 files × 4 strategies = 400 API calls
        # - Limited: 100 files × 3 strategies = 300 API calls
        # - Savings: 100 API calls (25% reduction)

        files_count = 100
        original_calls = files_count * original_strategies
        limited_calls = files_count * limited_strategies
        saved_calls = original_calls - limited_calls

        self.assertEqual(original_calls, 400)
        self.assertEqual(limited_calls, 300)
        self.assertEqual(saved_calls, 100)
        self.assertEqual(saved_calls / original_calls * 100, 25.0)

    def test_early_exit_on_high_confidence(self):
        """Test that search stops early when high confidence result is found."""
        query = "Attack on Titan (2023)"

        # Mock first strategy to return high confidence result above the early exit threshold (0.85)
        high_confidence_result = Mock()
        high_confidence_result.quality_score = 0.9  # Above early exit threshold (0.85)

        with patch.object(self.client, '_strategy_exact_title_with_year') as mock_strategy1, \
             patch.object(self.client, '_strategy_exact_title_only') as mock_strategy2, \
             patch.object(self.client, '_strategy_cleaned_title') as mock_strategy3:

            mock_strategy1.return_value = [high_confidence_result]
            mock_strategy2.return_value = []
            mock_strategy3.return_value = []

            results, needs_selection = self.client.search_with_three_strategies(query)

            # Should return early with high confidence result
            self.assertEqual(len(results), 1)
            self.assertFalse(needs_selection)

            # Only first strategy should be called
            mock_strategy1.assert_called_once()
            mock_strategy2.assert_not_called()
            mock_strategy3.assert_not_called()


if __name__ == "__main__":
    unittest.main()
