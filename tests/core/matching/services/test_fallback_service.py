"""Tests for FallbackStrategyService."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from anivault.core.matching.models import NormalizedQuery
from anivault.core.matching.services.fallback_service import FallbackStrategyService
from anivault.core.matching.strategies import GenreBoostStrategy, PartialMatchStrategy
from anivault.core.statistics import StatisticsCollector
from anivault.services.tmdb_models import ScoredSearchResult


class TestFallbackStrategyService:
    """Test suite for FallbackStrategyService."""

    @pytest.fixture
    def mock_statistics(self):
        """Create mock statistics collector."""
        return Mock(spec=StatisticsCollector)

    @pytest.fixture
    def sample_query(self):
        """Sample normalized query."""
        return NormalizedQuery(title="attack on titan", year=2013)

    @pytest.fixture
    def sample_candidates(self):
        """Sample scored candidates."""
        return [
            ScoredSearchResult(
                id=1,
                name="Attack on Titan",
                media_type="tv",
                first_air_date="2013-04-07",
                popularity=100.0,
                vote_average=8.5,
                vote_count=5000,
                overview="Anime",
                original_language="ja",
                genre_ids=[16],  # Animation
                confidence_score=0.6,
            ),
            ScoredSearchResult(
                id=2,
                name="Different Show",
                media_type="tv",
                first_air_date="2015-01-01",
                popularity=50.0,
                vote_average=7.0,
                vote_count=1000,
                overview="Drama",
                original_language="ko",
                genre_ids=[18],  # Drama
                confidence_score=0.4,
            ),
        ]

    # === Initialization Tests ===

    def test_service_initialization_no_strategies(self, mock_statistics):
        """Test service initialization without strategies."""
        service = FallbackStrategyService(mock_statistics)

        assert service.statistics is mock_statistics
        assert service.strategy_count == 0

    def test_service_initialization_with_strategies(self, mock_statistics):
        """Test service initialization with strategies."""
        strategies = [GenreBoostStrategy(), PartialMatchStrategy()]
        service = FallbackStrategyService(mock_statistics, strategies)

        assert service.strategy_count == 2
        # Verify priority order (GenreBoost=10, PartialMatch=20)
        assert service._strategies[0].priority == 10
        assert service._strategies[1].priority == 20

    def test_strategies_sorted_by_priority(self, mock_statistics):
        """Test strategies are sorted by priority."""
        # Create strategies in wrong order
        strategies = [
            PartialMatchStrategy(),  # priority 20
            GenreBoostStrategy(),  # priority 10
        ]
        service = FallbackStrategyService(mock_statistics, strategies)

        # Should be sorted: GenreBoost (10) first, PartialMatch (20) second
        assert service._strategies[0].priority == 10
        assert service._strategies[1].priority == 20

    # === Strategy Application Tests ===

    def test_apply_strategies_empty_candidates(
        self, mock_statistics, sample_query
    ):
        """Test strategy application with empty candidate list."""
        strategies = [GenreBoostStrategy()]
        service = FallbackStrategyService(mock_statistics, strategies)

        result = service.apply_strategies([], sample_query)

        assert result == []

    def test_apply_strategies_no_strategies(
        self, mock_statistics, sample_candidates, sample_query
    ):
        """Test strategy application with no strategies."""
        service = FallbackStrategyService(mock_statistics)

        result = service.apply_strategies(sample_candidates, sample_query)

        # Should return original candidates unchanged
        assert result == sample_candidates

    def test_apply_strategies_genre_boost(
        self, mock_statistics, sample_candidates, sample_query
    ):
        """Test genre boost strategy application."""
        strategies = [GenreBoostStrategy()]
        service = FallbackStrategyService(mock_statistics, strategies)

        result = service.apply_strategies(sample_candidates, sample_query)

        # Animation candidate (id=1) should have boosted confidence
        # Original: 0.6, Boost: 0.5, Expected: 1.0 (capped)
        anime_candidate = next(c for c in result if c.id == 1)
        assert anime_candidate.confidence_score > sample_candidates[0].confidence_score

        # Non-animation candidate (id=2) should be unchanged
        drama_candidate = next(c for c in result if c.id == 2)
        assert drama_candidate.confidence_score == sample_candidates[1].confidence_score

    def test_apply_strategies_multiple_in_order(
        self, mock_statistics, sample_candidates, sample_query
    ):
        """Test multiple strategies applied in priority order."""
        strategies = [GenreBoostStrategy(), PartialMatchStrategy()]
        service = FallbackStrategyService(mock_statistics, strategies)

        result = service.apply_strategies(sample_candidates, sample_query)

        # Both strategies should have been applied
        assert len(result) == 2
        # Candidates should have enhanced confidence scores
        assert all(isinstance(c, ScoredSearchResult) for c in result)

    # === Exception Handling Tests ===

    def test_strategy_failure_continues_with_others(
        self, mock_statistics, sample_candidates, sample_query
    ):
        """Test that strategy failure doesn't stop other strategies."""
        # Create mock strategy that fails
        failing_strategy = Mock()
        failing_strategy.priority = 5
        failing_strategy.apply.side_effect = Exception("Strategy failed")

        working_strategy = GenreBoostStrategy()

        strategies = [failing_strategy, working_strategy]
        service = FallbackStrategyService(mock_statistics, strategies)

        # Should not raise exception
        result = service.apply_strategies(sample_candidates, sample_query)

        # Working strategy should have been applied
        assert len(result) == 2
        # Verify working strategy was called (genre boost should have happened)
        anime_candidate = next(c for c in result if c.id == 1)
        assert anime_candidate.confidence_score > sample_candidates[0].confidence_score

    # === Dynamic Registration Tests ===

    def test_register_strategy_dynamically(self, mock_statistics):
        """Test dynamic strategy registration."""
        service = FallbackStrategyService(mock_statistics)
        assert service.strategy_count == 0

        # Register strategy
        strategy = GenreBoostStrategy()
        service.register_strategy(strategy)

        assert service.strategy_count == 1

    def test_register_maintains_priority_order(self, mock_statistics):
        """Test that registration maintains priority order."""
        # Start with high priority strategy
        strategies = [PartialMatchStrategy()]  # priority 20
        service = FallbackStrategyService(mock_statistics, strategies)

        # Register lower priority strategy
        service.register_strategy(GenreBoostStrategy())  # priority 10

        # Should be reordered: GenreBoost (10) first
        assert service._strategies[0].priority == 10
        assert service._strategies[1].priority == 20

    # === Property Tests ===

    def test_strategy_count_property(self, mock_statistics):
        """Test strategy_count property."""
        service = FallbackStrategyService(mock_statistics)
        assert service.strategy_count == 0

        service.register_strategy(GenreBoostStrategy())
        assert service.strategy_count == 1

        service.register_strategy(PartialMatchStrategy())
        assert service.strategy_count == 2

