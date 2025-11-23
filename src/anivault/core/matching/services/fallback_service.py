"""Fallback strategy service for matching engine.

This module provides the FallbackStrategyService class that orchestrates
multiple fallback strategies in priority order.
"""

from __future__ import annotations

import logging
from anivault.core.matching.models import NormalizedQuery
from anivault.core.matching.strategies import FallbackStrategy
from anivault.core.statistics import StatisticsCollector
from anivault.services.tmdb import ScoredSearchResult
from anivault.shared.errors import ErrorCode

logger = logging.getLogger(__name__)


class FallbackStrategyService:
    """Service for orchestrating fallback strategies.

    This service:
    1. Manages multiple fallback strategies
    2. Applies them in priority order (lowest first)
    3. Handles strategy failures gracefully
    4. Logs strategy application and results

    Attributes:
        statistics: Statistics collector for performance tracking
        strategies: List of fallback strategies (sorted by priority)

    Example:
        >>> from anivault.core.matching.strategies import GenreBoostStrategy, PartialMatchStrategy
        >>>
        >>> stats = StatisticsCollector()
        >>> strategies = [GenreBoostStrategy(), PartialMatchStrategy()]
        >>> service = FallbackStrategyService(stats, strategies)
        >>>
        >>> enhanced = service.apply_strategies(candidates, query)
    """

    def __init__(
        self,
        statistics: StatisticsCollector,
        strategies: list[FallbackStrategy] | None = None,
    ) -> None:
        """Initialize fallback strategy service.

        Args:
            statistics: Statistics collector for performance tracking
            strategies: List of fallback strategies (will be sorted by priority)
        """
        self.statistics = statistics
        self._strategies: list[FallbackStrategy] = []

        if strategies:
            # Sort strategies by priority (ascending = lower priority first)
            self._strategies = sorted(strategies, key=lambda s: s.priority)
            logger.debug(
                "Initialized with %d strategies: %s",
                len(self._strategies),
                [type(s).__name__ for s in self._strategies],
            )

    def apply_strategies(
        self,
        candidates: list[ScoredSearchResult],
        query: NormalizedQuery,
    ) -> list[ScoredSearchResult]:
        """Apply all strategies in priority order.

        Strategies are applied sequentially, with each strategy receiving
        the output of the previous strategy. Failed strategies are logged
        and skipped (graceful degradation).

        Args:
            candidates: List of scored candidates
            query: Normalized query for matching

        Returns:
            Enhanced list of candidates after all strategies applied
            Returns original candidates if all strategies fail

        Note:
            - Strategies applied in ascending priority order
            - Exception in one strategy doesn't affect others
            - Empty candidate lists handled gracefully
        """
        if not candidates:
            logger.debug("No candidates to apply strategies to")
            return []

        if not self._strategies:
            logger.debug("No strategies configured")
            return candidates

        # Start with original candidates
        current_candidates = candidates

        logger.debug(
            "Applying %d fallback strategies to %d candidates",
            len(self._strategies),
            len(candidates),
        )

        # Apply each strategy in sequence
        for strategy in self._strategies:
            strategy_name = type(strategy).__name__

            try:
                # Record initial state
                before_count = len(current_candidates)
                before_top_score = (
                    current_candidates[0].confidence_score
                    if current_candidates
                    else 0.0
                )

                # Apply strategy
                current_candidates = strategy.apply(current_candidates, query)

                # Record result
                after_count = len(current_candidates)
                after_top_score = (
                    current_candidates[0].confidence_score
                    if current_candidates
                    else 0.0
                )

                # Log delta
                count_delta = after_count - before_count
                score_delta = after_top_score - before_top_score

                logger.debug(
                    "Strategy applied: %s (count: %d→%d [%+d], top_score: %.3f→%.3f [%+.3f])",
                    strategy_name,
                    before_count,
                    after_count,
                    count_delta,
                    before_top_score,
                    after_top_score,
                    score_delta,
                )

            except (KeyError, ValueError, TypeError, AttributeError, IndexError) as e:
                from anivault.shared.errors import AniVaultParsingError, ErrorContext

                # Data parsing errors during strategy execution
                context = ErrorContext(
                    operation="apply_fallback_strategy",
                    additional_data={
                        "strategy_name": strategy_name,
                        "error_type": "data_parsing",
                    },
                )
                error = AniVaultParsingError(
                    ErrorCode.DATA_PROCESSING_ERROR,
                    f"Failed to apply fallback strategy '{strategy_name}': {e}",
                    context,
                    original_error=e,
                )
                logger.exception(
                    "Strategy failed: %s (continuing with remaining strategies)",
                    strategy_name,
                )
                # Keep current candidates unchanged
            except Exception as e:
                from anivault.shared.errors import AniVaultError, ErrorContext

                # Unexpected errors
                context = ErrorContext(
                    operation="apply_fallback_strategy",
                    additional_data={
                        "strategy_name": strategy_name,
                        "error_type": "unexpected",
                    },
                )
                error = AniVaultError(
                    ErrorCode.DATA_PROCESSING_ERROR,
                    f"Unexpected error applying fallback strategy '{strategy_name}': {e}",
                    context,
                    original_error=e,
                )
                logger.exception(
                    "Strategy failed: %s (continuing with remaining strategies)",
                    strategy_name,
                )
                # Keep current candidates unchanged

        logger.debug(
            "Completed fallback strategies: %d candidates, top score: %.3f",
            len(current_candidates),
            current_candidates[0].confidence_score if current_candidates else 0.0,
        )

        return current_candidates

    def register_strategy(self, strategy: FallbackStrategy) -> None:
        """Register a new strategy dynamically.

        Args:
            strategy: Fallback strategy to register

        Note:
            Strategies are automatically sorted by priority after registration
        """
        self._strategies.append(strategy)
        self._strategies.sort(key=lambda s: s.priority)

        logger.debug(
            "Registered strategy: %s (priority: %d)",
            type(strategy).__name__,
            strategy.priority,
        )

    @property
    def strategy_count(self) -> int:
        """Get number of registered strategies.

        Returns:
            Number of strategies
        """
        return len(self._strategies)
