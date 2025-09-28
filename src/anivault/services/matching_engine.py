"""Advanced matching engine for TMDB with accuracy optimization."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from anivault.services.query_normalizer import QueryNormalizer
from anivault.services.tmdb_client import TMDBClient

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of a TMDB matching operation."""

    tmdb_id: int | None
    title: str | None
    original_title: str | None
    overview: str | None
    first_air_date: str | None
    popularity: float | None
    vote_average: float | None
    vote_count: int | None
    confidence: float
    match_type: str  # 'exact', 'high', 'medium', 'low', 'none'
    query_used: str
    fallback_attempts: int = 0


@dataclass
class MatchingConfig:
    """Configuration for matching engine."""

    min_confidence: float = 0.7
    max_fallback_attempts: int = 3
    use_language_hints: bool = True
    use_year_hints: bool = True
    enable_query_variants: bool = True
    cache_results: bool = True


class MatchingEngine:
    """Advanced matching engine for TMDB with accuracy optimization."""

    def __init__(self, tmdb_client: TMDBClient, config: MatchingConfig | None = None):
        """Initialize the matching engine.

        Args:
            tmdb_client: TMDB client instance
            config: Matching configuration
        """
        self.tmdb_client = tmdb_client
        self.config = config or MatchingConfig()
        self.normalizer = QueryNormalizer()
        self.cache: dict[str, MatchResult] = {}
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "successful_matches": 0,
            "fallback_attempts": 0,
        }

    def match_anime(
        self,
        title: str,
        year: int | None = None,
        language: str = "en-US",
    ) -> MatchResult:
        """Match an anime title with TMDB.

        Args:
            title: Anime title to match
            year: Release year hint
            language: Language preference

        Returns:
            Match result with confidence score
        """
        self.stats["total_queries"] += 1

        # Check cache first
        cache_key = f"{title}|{year}|{language}"
        if self.config.cache_results and cache_key in self.cache:
            self.stats["cache_hits"] += 1
            logger.debug(f"Cache hit for: {title}")
            return self.cache[cache_key]

        # Generate query variants
        query_variants = self.normalizer.generate_query_variants(title)
        if not self.config.enable_query_variants:
            query_variants = [title]

        best_match = None
        best_confidence = 0.0
        fallback_attempts = 0

        # Try each query variant
        for query in query_variants:
            if not query.strip():
                continue

            try:
                # Search TMDB
                search_results = self.tmdb_client.search_tv(query)

                if not search_results:
                    continue

                # Evaluate each result
                for result in search_results[:5]:  # Check top 5 results
                    match_result = self._evaluate_match(
                        query,
                        result,
                        title,
                        year,
                        language,
                    )

                    if match_result.confidence > best_confidence:
                        best_match = match_result
                        best_confidence = match_result.confidence

                # If we found a high-confidence match, use it
                if best_confidence >= 0.9:
                    break

            except Exception as e:
                logger.warning(f"Search failed for query '{query}': {e}")
                continue

        # If no good match found, try fallback strategies
        if not best_match or best_confidence < self.config.min_confidence:
            best_match = self._try_fallback_strategies(title, year, language)
            if best_match:
                fallback_attempts = best_match.fallback_attempts

        # Create final result
        if not best_match:
            best_match = MatchResult(
                tmdb_id=None,
                title=None,
                original_title=None,
                overview=None,
                first_air_date=None,
                popularity=None,
                vote_average=None,
                vote_count=None,
                confidence=0.0,
                match_type="none",
                query_used=title,
                fallback_attempts=fallback_attempts,
            )

        # Update stats
        if best_match.confidence > 0:
            self.stats["successful_matches"] += 1
        self.stats["fallback_attempts"] += fallback_attempts

        # Cache result
        if self.config.cache_results:
            self.cache[cache_key] = best_match

        logger.debug(
            f"Match result for '{title}': confidence={best_match.confidence:.2f}, "
            f"type={best_match.match_type}, attempts={fallback_attempts}",
        )

        return best_match

    def _evaluate_match(
        self,
        query: str,
        result: dict[str, Any],
        original_title: str,
        year: int | None,
        language: str,
    ) -> MatchResult:
        """Evaluate a TMDB search result.

        Args:
            query: Query used for search
            result: TMDB search result
            original_title: Original title being matched
            year: Release year hint
            language: Language preference

        Returns:
            Match result with confidence score
        """
        tmdb_title = result.get("name", "")
        original_tmdb_title = result.get("original_name", "")
        overview = result.get("overview", "")
        first_air_date = result.get("first_air_date", "")
        popularity = result.get("popularity", 0.0)
        vote_average = result.get("vote_average", 0.0)
        vote_count = result.get("vote_count", 0)

        # Calculate confidence score
        confidence = self._calculate_confidence(
            query,
            tmdb_title,
            original_tmdb_title,
            original_title,
            year,
            first_air_date,
        )

        # Determine match type
        match_type = self._determine_match_type(confidence)

        return MatchResult(
            tmdb_id=result.get("id"),
            title=tmdb_title,
            original_title=original_tmdb_title,
            overview=overview,
            first_air_date=first_air_date,
            popularity=popularity,
            vote_average=vote_average,
            vote_count=vote_count,
            confidence=confidence,
            match_type=match_type,
            query_used=query,
        )

    def _calculate_confidence(
        self,
        query: str,
        tmdb_title: str,
        original_tmdb_title: str,
        original_title: str,
        year: int | None,
        first_air_date: str,
    ) -> float:
        """Calculate confidence score for a match.

        Args:
            query: Query used for search
            tmdb_title: TMDB title
            original_tmdb_title: TMDB original title
            original_title: Original title being matched
            year: Release year hint
            first_air_date: TMDB first air date

        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.0

        # Title similarity (highest weight)
        title_similarity = self.normalizer.calculate_similarity(
            original_title,
            tmdb_title,
        )
        confidence += title_similarity * 0.4

        # Original title similarity
        if original_tmdb_title:
            original_similarity = self.normalizer.calculate_similarity(
                original_title,
                original_tmdb_title,
            )
            confidence += original_similarity * 0.3

        # Query similarity
        query_similarity = self.normalizer.calculate_similarity(query, tmdb_title)
        confidence += query_similarity * 0.2

        # Year matching bonus
        if year and first_air_date:
            try:
                tmdb_year = int(first_air_date[:4])
                if abs(tmdb_year - year) <= 1:  # Within 1 year
                    confidence += 0.1
            except (ValueError, IndexError):
                pass

        # Popularity bonus (slight boost for popular shows)
        if hasattr(self, "_popularity_bonus"):
            confidence += self._popularity_bonus * 0.05

        return min(confidence, 1.0)

    def _determine_match_type(self, confidence: float) -> str:
        """Determine match type based on confidence.

        Args:
            confidence: Confidence score

        Returns:
            Match type string
        """
        if confidence >= 0.95:
            return "exact"
        if confidence >= 0.85:
            return "high"
        if confidence >= 0.70:
            return "medium"
        if confidence >= 0.50:
            return "low"
        return "none"

    def _try_fallback_strategies(
        self,
        title: str,
        year: int | None,
        language: str,
    ) -> MatchResult | None:
        """Try fallback matching strategies.

        Args:
            title: Original title
            year: Release year hint
            language: Language preference

        Returns:
            Match result or None
        """
        fallback_attempts = 0

        # Strategy 1: Remove common words and try again
        words = title.split()
        if len(words) > 2:
            # Remove common words
            common_words = {
                "the",
                "a",
                "an",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "with",
                "by",
            }
            filtered_words = [w for w in words if w.lower() not in common_words]
            if filtered_words:
                fallback_query = " ".join(filtered_words)
                fallback_attempts += 1
                try:
                    search_results = self.tmdb_client.search_tv(fallback_query)
                    if search_results:
                        result = self._evaluate_match(
                            fallback_query,
                            search_results[0],
                            title,
                            year,
                            language,
                        )
                        result.fallback_attempts = fallback_attempts
                        return result
                except Exception:
                    pass

        # Strategy 2: Try with year
        if year:
            fallback_query = f"{title} {year}"
            fallback_attempts += 1
            try:
                search_results = self.tmdb_client.search_tv(fallback_query)
                if search_results:
                    result = self._evaluate_match(
                        fallback_query,
                        search_results[0],
                        title,
                        year,
                        language,
                    )
                    result.fallback_attempts = fallback_attempts
                    return result
            except Exception:
                pass

        # Strategy 3: Try partial title (first 3 words)
        words = title.split()
        if len(words) > 3:
            partial_title = " ".join(words[:3])
            fallback_attempts += 1
            try:
                search_results = self.tmdb_client.search_tv(partial_title)
                if search_results:
                    result = self._evaluate_match(
                        partial_title,
                        search_results[0],
                        title,
                        year,
                        language,
                    )
                    result.fallback_attempts = fallback_attempts
                    return result
            except Exception:
                pass

        return None

    def get_stats(self) -> dict[str, Any]:
        """Get matching engine statistics.

        Returns:
            Dictionary containing engine statistics
        """
        total_queries = self.stats["total_queries"]
        cache_hit_rate = self.stats["cache_hits"] / max(1, total_queries)
        success_rate = self.stats["successful_matches"] / max(1, total_queries)
        avg_fallback_attempts = self.stats["fallback_attempts"] / max(1, total_queries)

        return {
            "total_queries": total_queries,
            "cache_hits": self.stats["cache_hits"],
            "cache_hit_rate": cache_hit_rate,
            "successful_matches": self.stats["successful_matches"],
            "success_rate": success_rate,
            "fallback_attempts": self.stats["fallback_attempts"],
            "avg_fallback_attempts": avg_fallback_attempts,
            "cache_size": len(self.cache),
        }

    def clear_cache(self) -> None:
        """Clear the matching cache."""
        self.cache.clear()
        logger.info("Matching cache cleared")
