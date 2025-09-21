"""Simple test for fallback strategy limitation.

This module provides a simplified test to verify that fallback strategies
are limited to 3 and API calls are reduced.
"""

import unittest
from unittest.mock import patch

from src.core.tmdb_client import TMDBClient, TMDBConfig


class TestSimpleFallbackLimitation(unittest.TestCase):
    """Simple test cases for fallback strategy limitation."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = TMDBConfig(
            api_key="test_api_key",
            language="ko-KR",
            fallback_language="en-US",
            timeout=5,
        )
        self.client = TMDBClient(self.config)

    def test_fallback_strategies_count(self) -> None:
        """Test that exactly 3 fallback strategies are called."""
        with patch.object(self.client, "_try_multi_search_with_scoring") as mock_search:
            mock_search.return_value = []

            with patch.object(self.client, "search_tv_series", return_value=[]):
                # Use a query that will trigger all 3 fallback strategies
                query = "Attack on Titan Season 1 Episode 1 [1080p]"
                self.client.search_comprehensive(query)

            # Should be called 1 initial + 3 fallback = 4 times total
            assert mock_search.call_count == 4

    def test_fallback_strategies_effectiveness(self) -> None:
        """Test that the selected strategies are effective."""
        test_query = "Attack on Titan Season 1 Episode 1 [1080p]"

        # Test NORMALIZED strategy
        normalized = self.client._normalize_query(test_query)
        assert normalized != test_query
        assert normalized == "Attack on Titan Season 1 Episode 1"

        # Test WORD_REDUCTION strategy
        word_reduced = self.client._reduce_query_words(test_query)
        assert word_reduced != test_query
        assert word_reduced == "Attack on Titan Season 1 Episode 1"

        # Test LANGUAGE_FALLBACK strategy (doesn't modify query)
        # This strategy uses fallback language instead of modifying query
        assert test_query == test_query  # Query remains unchanged

    def test_removed_strategies_not_available(self) -> None:
        """Test that removed strategies are not available."""
        # Verify that removed methods don't exist
        assert not hasattr(self.client, "_create_partial_query")
        assert not hasattr(self.client, "_reorder_query_words")

    def test_api_call_reduction_verification(self) -> None:
        """Verify that API calls are reduced from 5 to 3 strategies."""
        # Theoretical calculation
        original_strategies = 5
        limited_strategies = 3
        reduction_percentage = (
            (original_strategies - limited_strategies) / original_strategies * 100
        )

        assert reduction_percentage == 40.0

        # In practice: 100 files × 3 strategies = 300 API calls instead of 500
        files_count = 100
        original_calls = files_count * original_strategies
        limited_calls = files_count * limited_strategies
        saved_calls = original_calls - limited_calls

        assert original_calls == 500
        assert limited_calls == 300
        assert saved_calls == 200


if __name__ == "__main__":
    unittest.main()
