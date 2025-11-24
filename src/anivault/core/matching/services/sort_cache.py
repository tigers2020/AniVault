"""Sort cache for optimizing candidate sorting operations.

This module provides the SortCache class that caches sorted candidate lists
to avoid repeated sorting computations for the same candidate sets.
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anivault.shared.models.tmdb_models import TMDBSearchResult

logger = logging.getLogger(__name__)


class SortCache:
    """Cache for sorted candidate lists to optimize repeated sorting operations.

    This cache stores:
    1. `sort_keys`: Pre-computed sort keys for candidates
    2. `sorted_lists`: Complete sorted candidate ID lists by sort criteria

    Attributes:
        sort_keys: Dictionary mapping (candidate_id, sort_criteria) -> sort_key
        sorted_lists: Dictionary mapping cache_key -> sorted candidate ID list

    Example:
        >>> cache = SortCache()
        >>> candidates = [TMDBSearchResult(id=1, ...), TMDBSearchResult(id=2, ...)]
        >>> sorted_ids = cache.get_or_compute_sorted(
        ...     candidates, "year_asc", year_sort_key_fn
        ... )
        >>> # Second call with same candidates returns cached result
        >>> sorted_ids = cache.get_or_compute_sorted(
        ...     candidates, "year_asc", year_sort_key_fn
        ... )
    """

    def __init__(self) -> None:
        """Initialize sort cache."""
        self.sort_keys: dict[tuple[int, str], tuple[int, int]] = {}
        self.sorted_lists: dict[str, list[int]] = {}

    def _generate_cache_key(
        self,
        candidates: list[TMDBSearchResult],
        sort_criteria: str,
    ) -> str:
        """Generate cache key for candidate list and sort criteria.

        Args:
            candidates: List of candidates to cache
            sort_criteria: Sort criteria identifier (e.g., "year_asc")

        Returns:
            Cache key string
        """
        # Create deterministic key from candidate IDs and sort criteria
        candidate_ids = sorted(c.id for c in candidates)
        ids_str = ",".join(str(id_) for id_ in candidate_ids)
        key_data = f"{ids_str}:{sort_criteria}"

        # Use hash for shorter key
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def get_or_compute_sorted(
        self,
        candidates: list[TMDBSearchResult],
        sort_criteria: str,
        sort_key_fn: callable,  # type: ignore[type-arg]
    ) -> list[TMDBSearchResult]:
        """Get sorted candidates from cache or compute and cache.

        Args:
            candidates: List of candidates to sort
            sort_criteria: Sort criteria identifier (e.g., "year_asc")
            sort_key_fn: Function to compute sort key for a candidate

        Returns:
            Sorted list of candidates
        """
        if not candidates:
            return candidates

        # Generate cache key
        cache_key = self._generate_cache_key(candidates, sort_criteria)

        # Check if sorted list is cached
        if cache_key in self.sorted_lists:
            logger.debug("Cache hit for sort criteria: %s", sort_criteria)
            sorted_ids = self.sorted_lists[cache_key]

            # Reconstruct sorted candidate list from cached IDs
            candidate_map = {c.id: c for c in candidates}
            sorted_candidates = [
                candidate_map[cid] for cid in sorted_ids if cid in candidate_map
            ]

            return sorted_candidates

        # Cache miss: compute sort keys and sort
        logger.debug("Cache miss for sort criteria: %s, computing...", sort_criteria)

        # Compute sort keys (with caching)
        sort_key_pairs: list[tuple[TMDBSearchResult, tuple[int, int]]] = []
        for candidate in candidates:
            key_tuple = (candidate.id, sort_criteria)

            if key_tuple in self.sort_keys:
                sort_key = self.sort_keys[key_tuple]
            else:
                sort_key = sort_key_fn(candidate)
                self.sort_keys[key_tuple] = sort_key

            sort_key_pairs.append((candidate, sort_key))

        # Sort by key
        sort_key_pairs.sort(key=lambda x: x[1])

        # Extract sorted candidates and IDs
        sorted_candidates = [candidate for candidate, _ in sort_key_pairs]
        sorted_ids = [c.id for c in sorted_candidates]

        # Cache sorted ID list
        self.sorted_lists[cache_key] = sorted_ids

        logger.debug(
            "Cached sorted list for criteria: %s (key: %s)",
            sort_criteria,
            cache_key,
        )

        return sorted_candidates

    def clear(self) -> None:
        """Clear all cached data."""
        self.sort_keys.clear()
        self.sorted_lists.clear()
        logger.debug("Sort cache cleared")

    def invalidate(self, sort_criteria: str | None = None) -> None:
        """Invalidate cache entries for specific criteria or all.

        Note: Since cache keys are hashes, we cannot directly match by criteria.
        This method clears all cache entries. For more precise invalidation,
        use clear() or implement criteria-to-key mapping.

        Args:
            sort_criteria: Specific criteria to invalidate, or None for all.
                          Currently, any non-None value clears all cache.
        """
        if sort_criteria is None:
            self.clear()
            return

        # For now, clear all cache when invalidating specific criteria
        # TODO: Implement criteria-to-key mapping for precise invalidation
        self.clear()
        logger.debug("Invalidated cache (cleared all entries)")

