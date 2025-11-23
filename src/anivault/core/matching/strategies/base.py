"""Base strategy protocol for fallback matching.

This module defines the FallbackStrategy protocol that all concrete
fallback strategies must implement.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from anivault.core.matching.models import NormalizedQuery
from anivault.shared.models.tmdb_models import ScoredSearchResult


@runtime_checkable
class FallbackStrategy(Protocol):
    """Protocol for fallback matching strategies.

    All fallback strategies must implement this protocol to ensure
    consistent interface and enable strategy chaining.

    Attributes:
        priority: Execution priority (lower = earlier, default 100)
                  Strategies are applied in ascending priority order

    Example:
        >>> class MyStrategy:
        ...     priority = 50  # Runs before default strategies
        ...
        ...     def apply(self, candidates, query):
        ...         # Apply custom matching logic
        ...         return enhanced_candidates
    """

    priority: int = 100

    def apply(
        self,
        candidates: list[ScoredSearchResult],
        query: NormalizedQuery,
    ) -> list[ScoredSearchResult]:
        """Apply fallback strategy to candidates.

        Args:
            candidates: List of scored candidates (may be empty)
            query: Normalized query for matching

        Returns:
            Enhanced list of candidates (may include new candidates,
            re-scored candidates, or filtered candidates)
            Must return a NEW list (immutable operation)

        Note:
            - Must NOT modify input lists
            - Should handle empty candidate lists gracefully
            - May return empty list if no improvements possible
        """
        ...
