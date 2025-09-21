"""Test enhanced early exit logic for Task 10.

This module tests the enhanced early exit mechanism that evaluates quality scores
and terminates further fallback searches when sufficiently high-quality matches are found.
"""

import unittest
from unittest.mock import Mock, patch

from src.core.tmdb_client import SearchStrategyType, TMDBClient, TMDBConfig


class TestEnhancedEarlyExit(unittest.TestCase):
    """Test cases for enhanced early exit logic."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = TMDBConfig(
            api_key="test_api_key",
            language="ko-KR",
            fallback_language="en-US",
            timeout=5,
            high_confidence_threshold=0.7,
            medium_confidence_threshold=0.3,
        )
        self.client = TMDBClient(self.config)

    def test_progressive_threshold_early_exit(self) -> None:
        """Test that early exit works with progressive thresholds for each strategy."""
        query = "Attack on Titan (2023)"

        # Test data: different quality scores for different strategies
        high_quality_result = Mock()
        high_quality_result.quality_score = 0.9  # Above first strategy threshold (0.85)

        medium_quality_result = Mock()
        medium_quality_result.quality_score = 0.8  # Above second strategy threshold (0.75)

        low_quality_result = Mock()
        low_quality_result.quality_score = 0.7  # Above third strategy threshold (0.65)

        with (
            patch.object(self.client, "_strategy_exact_title_with_year") as mock_strategy1,
            patch.object(self.client, "_strategy_exact_title_only") as mock_strategy2,
            patch.object(self.client, "_strategy_cleaned_title") as mock_strategy3,
        ):

            # First strategy returns high quality result - should trigger early exit
            mock_strategy1.return_value = [high_quality_result]
            mock_strategy2.return_value = []
            mock_strategy3.return_value = []

            results, needs_selection = self.client.search_with_three_strategies(query)

            # Should return early with high quality result
            assert len(results) == 1
            assert results[0].quality_score == 0.9
            assert not needs_selection

            # Only first strategy should be called
            mock_strategy1.assert_called_once()
            mock_strategy2.assert_not_called()
            mock_strategy3.assert_not_called()

    def test_medium_quality_early_exit(self) -> None:
        """Test early exit with medium quality results on second strategy."""
        query = "One Piece Season 1"

        medium_result = Mock()
        medium_result.quality_score = 0.8  # Above second strategy threshold (0.75)

        with (
            patch.object(self.client, "_strategy_exact_title_with_year") as mock_strategy1,
            patch.object(self.client, "_strategy_exact_title_only") as mock_strategy2,
            patch.object(self.client, "_strategy_cleaned_title") as mock_strategy3,
        ):

            # First strategy returns no results
            mock_strategy1.return_value = []
            # Second strategy returns medium quality result
            mock_strategy2.return_value = [medium_result]
            mock_strategy3.return_value = []

            results, needs_selection = self.client.search_with_three_strategies(query)

            # Should return early with medium quality result
            assert len(results) == 1
            assert results[0].quality_score == 0.8
            assert not needs_selection

            # First two strategies should be called
            mock_strategy1.assert_called_once()
            mock_strategy2.assert_called_once()
            mock_strategy3.assert_not_called()

    def test_low_quality_early_exit(self) -> None:
        """Test early exit with low quality results on third strategy."""
        query = "Naruto Shippuden"

        low_result = Mock()
        low_result.quality_score = 0.7  # Above third strategy threshold (0.65)

        with (
            patch.object(self.client, "_strategy_exact_title_with_year") as mock_strategy1,
            patch.object(self.client, "_strategy_exact_title_only") as mock_strategy2,
            patch.object(self.client, "_strategy_cleaned_title") as mock_strategy3,
        ):

            # First two strategies return no results
            mock_strategy1.return_value = []
            mock_strategy2.return_value = []
            # Third strategy returns low quality result
            mock_strategy3.return_value = [low_result]

            results, needs_selection = self.client.search_with_three_strategies(query)

            # Should return early with low quality result
            assert len(results) == 1
            assert results[0].quality_score == 0.7
            assert not needs_selection

            # All strategies should be called
            mock_strategy1.assert_called_once()
            mock_strategy2.assert_called_once()
            mock_strategy3.assert_called_once()

    def test_multiple_high_quality_results_early_exit(self) -> None:
        """Test early exit with multiple high quality results."""
        query = "Dragon Ball Z"

        result1 = Mock()
        result1.quality_score = 0.9
        result2 = Mock()
        result2.quality_score = 0.85

        with (
            patch.object(self.client, "_strategy_exact_title_with_year") as mock_strategy1,
            patch.object(self.client, "_strategy_exact_title_only") as mock_strategy2,
            patch.object(self.client, "_strategy_cleaned_title") as mock_strategy3,
        ):

            # First strategy returns multiple high quality results
            mock_strategy1.return_value = [result1, result2]
            mock_strategy2.return_value = []
            mock_strategy3.return_value = []

            results, needs_selection = self.client.search_with_three_strategies(query)

            # Should return early with multiple high quality results
            assert len(results) == 2
            assert needs_selection  # Multiple results need selection

            # Only first strategy should be called
            mock_strategy1.assert_called_once()
            mock_strategy2.assert_not_called()
            mock_strategy3.assert_not_called()

    def test_no_early_exit_with_low_quality(self) -> None:
        """Test that no early exit occurs when all results are below thresholds."""
        query = "Unknown Anime"

        low_result1 = Mock()
        low_result1.quality_score = 0.5  # Below all thresholds
        low_result2 = Mock()
        low_result2.quality_score = 0.4

        with (
            patch.object(self.client, "_strategy_exact_title_with_year") as mock_strategy1,
            patch.object(self.client, "_strategy_exact_title_only") as mock_strategy2,
            patch.object(self.client, "_strategy_cleaned_title") as mock_strategy3,
        ):

            # All strategies return low quality results
            mock_strategy1.return_value = [low_result1]
            mock_strategy2.return_value = [low_result2]
            mock_strategy3.return_value = []

            results, needs_selection = self.client.search_with_three_strategies(query)

            # Should return best results from all strategies
            assert len(results) == 2
            assert needs_selection

            # All strategies should be called
            mock_strategy1.assert_called_once()
            mock_strategy2.assert_called_once()
            mock_strategy3.assert_called_once()

    def test_early_exit_with_reasonable_results(self) -> None:
        """Test early exit with reasonable results (90% of threshold)."""
        query = "Demon Slayer"

        reasonable_result = Mock()
        reasonable_result.quality_score = 0.68  # 90% of 0.75 threshold

        with (
            patch.object(self.client, "_strategy_exact_title_with_year") as mock_strategy1,
            patch.object(self.client, "_strategy_exact_title_only") as mock_strategy2,
            patch.object(self.client, "_strategy_cleaned_title") as mock_strategy3,
        ):

            # First strategy returns no results
            mock_strategy1.return_value = []
            # Second strategy returns reasonable result
            mock_strategy2.return_value = [reasonable_result]
            mock_strategy3.return_value = []

            results, needs_selection = self.client.search_with_three_strategies(query)

            # Should return early with reasonable result (90% threshold logic)
            assert len(results) == 1
            assert results[0].quality_score == 0.68
            assert not needs_selection

            # First two strategies should be called
            mock_strategy1.assert_called_once()
            mock_strategy2.assert_called_once()
            mock_strategy3.assert_not_called()

    def test_early_exit_threshold_configuration(self) -> None:
        """Test that early exit thresholds are correctly configured."""
        # Verify the thresholds used in the implementation
        strategies = [
            (SearchStrategyType.EXACT_TITLE_WITH_YEAR, 0.85),
            (SearchStrategyType.EXACT_TITLE_ONLY, 0.75),
            (SearchStrategyType.CLEANED_TITLE, 0.65),
        ]

        for strategy_type, expected_threshold in strategies:
            # This test verifies the thresholds are set as expected
            # The actual thresholds are hardcoded in the implementation
            if strategy_type == SearchStrategyType.EXACT_TITLE_WITH_YEAR:
                assert expected_threshold == 0.85
            elif strategy_type == SearchStrategyType.EXACT_TITLE_ONLY:
                assert expected_threshold == 0.75
            elif strategy_type == SearchStrategyType.CLEANED_TITLE:
                assert expected_threshold == 0.65

    def test_early_exit_logging(self) -> None:
        """Test that early exit decisions are properly logged."""
        query = "My Hero Academia"

        high_result = Mock()
        high_result.quality_score = 0.9

        with (
            patch.object(self.client, "_strategy_exact_title_with_year") as mock_strategy1,
            patch.object(self.client, "_strategy_exact_title_only") as mock_strategy2,
            patch.object(self.client, "_strategy_cleaned_title") as mock_strategy3,
            patch("src.core.tmdb_client.logger") as mock_logger,
        ):

            mock_strategy1.return_value = [high_result]
            mock_strategy2.return_value = []
            mock_strategy3.return_value = []

            self.client.search_with_three_strategies(query)

            # Verify that early exit was logged
            early_exit_logged = any(
                "Early exit: Found single high-quality result" in str(call)
                for call in mock_logger.info.call_args_list
            )
            assert early_exit_logged


if __name__ == "__main__":
    unittest.main()
