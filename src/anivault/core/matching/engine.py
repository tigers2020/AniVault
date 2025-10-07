"""Multi-stage matching engine for finding anime titles in TMDB.

This module provides the core matching functionality that uses normalized queries
to search TMDB and find potential matches using various strategies including
fuzzy matching, year-based filtering, and confidence scoring.
"""

from __future__ import annotations

import logging
from typing import Any

from rapidfuzz import fuzz

from anivault.core.matching.scoring import calculate_confidence_score
from anivault.core.normalization import normalize_query_from_anitopy
from anivault.core.statistics import StatisticsCollector
from anivault.services.sqlite_cache_db import SQLiteCacheDB
from anivault.services.tmdb_client import TMDBClient
from anivault.shared.constants import ConfidenceThresholds

logger = logging.getLogger(__name__)

# Confidence thresholds for fallback strategies - now imported from shared constants


# Genre-based filtering constants
ANIMATION_GENRE_ID = 16  # TMDB Animation genre ID
ANIMATION_BOOST = (
    0.5  # Strong boost for confirmed animation (ensures anime is prioritized)
)
# NOTE: No penalty for non-animation to avoid false negatives when genre_ids missing
# The boost is strong enough (0.5) to ensure animation always wins over non-animation


class MatchingEngine:
    """Multi-stage matching engine for finding anime titles in TMDB.

    This engine orchestrates the entire matching process by:
    1. Normalizing the input query
    2. Searching TMDB with caching
    3. Scoring candidates using fuzzy matching
    4. Filtering and sorting by year
    5. Returning the best match

    Args:
        cache: Cache v2 instance for storing TMDB search results
        tmdb_client: TMDB client for API calls
    """

    def __init__(
        self,
        cache: SQLiteCacheDB,
        tmdb_client: TMDBClient,
        statistics: StatisticsCollector | None = None,
    ):
        """Initialize the matching engine.

        Args:
            cache: SQLite cache database for storing TMDB search results
            tmdb_client: TMDB client for API calls
            statistics: Optional statistics collector for performance tracking
        """
        self.cache = cache
        self.tmdb_client = tmdb_client
        self.statistics = statistics or StatisticsCollector()

    async def _search_tmdb(
        self,
        normalized_query: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Search TMDB with caching support.

        This method first checks the cache for existing search results.
        On a cache miss, it calls the TMDB API to search for both TV and Movie
        results, combines them, and stores the combined list in the cache.

        Args:
            normalized_query: Normalized query containing title and metadata

        Returns:
            List of TMDB search results with media_type field
        """
        # Use normalized title + language as cache key (language-sensitive caching)
        title = normalized_query.get("title", "")

        # Check if title is empty before doing anything
        if not title:
            logger.warning("Empty title in normalized query, skipping TMDB search")
            return []

        # Include language in cache key to avoid serving wrong-language cached results
        language = getattr(self.tmdb_client, "language", "ko-KR")
        cache_key = f"{title}:lang={language}"

        # Check cache first
        cached_data = self.cache.get(cache_key, "search")
        if cached_data is not None:
            logger.debug("Cache hit for search query: %s", cache_key)
            self.statistics.record_cache_hit("search")

            # Extract results from cached dict
            if isinstance(cached_data, dict) and "results" in cached_data:
                cached_results = cached_data["results"]

                # Type validation for cached results
                if not isinstance(cached_results, list):
                    logger.warning(
                        "Invalid cached results type: %s, expected list, clearing cache",
                        type(cached_results),
                    )
                    self.cache.delete(cache_key, "search")
                    return []

                # Validate that all items in the list are dicts
                for i, item in enumerate(cached_results):
                    if not isinstance(item, dict):
                        logger.warning(
                            "Invalid cached item type at index %d: %s, expected dict, clearing cache",
                            i,
                            type(item),
                        )
                        self.cache.delete(cache_key, "search")
                        return []

                return cached_results
            logger.warning("Invalid cached data structure, clearing cache")
            self.cache.delete(cache_key, "search")
            return []

        # Cache miss - search TMDB
        logger.debug("Cache miss for search query: %s (language: %s)", title, language)
        self.statistics.record_cache_miss("search")

        try:
            # Search TMDB for both TV and movies
            self.statistics.record_api_call("tmdb_search", success=True)
            results = await self.tmdb_client.search_media(title)

            # Store results in cache (7 days TTL)
            # Wrap list results in dict for CacheEntry compatibility
            cache_data = {"results": results}
            self.cache.set_cache(
                key=cache_key,
                data=cache_data,
                cache_type="search",
                ttl_seconds=7 * 24 * 60 * 60,  # 7 days
            )

            logger.debug("Found %d results for query: %s", len(results), title)
            return results

        except Exception as e:
            logger.exception("TMDB search failed for query '%s'", title)
            self.statistics.record_api_call("tmdb_search", success=False, error=str(e))
            return []

    def _score_candidates(
        self,
        candidates: list[dict[str, Any]],
        normalized_title: str,
    ) -> list[dict[str, Any]]:
        """Score candidates using fuzzy matching.

        This method iterates through a list of TMDB candidates and calculates
        a title similarity score for each using fuzzywuzzy.

        Args:
            candidates: List of TMDB search results
            normalized_title: Normalized title to match against

        Returns:
            List of candidates with added 'title_score' field
        """
        if not normalized_title:
            logger.warning("Empty normalized title, returning unscored candidates")
            return candidates

        scored_candidates = []

        for candidate in candidates:
            # Extract titles from candidate (try both localized and original)
            localized_title = candidate.get("title", "") or candidate.get("name", "")
            original_title = candidate.get("original_title", "") or candidate.get(
                "original_name",
                "",
            )

            if not localized_title and not original_title:
                logger.debug("Skipping candidate with no title")
                continue

            # Calculate fuzzy match score against BOTH localized and original titles
            # Use the higher score (handles both Korean filenames and Japanese romanization)
            scores = []
            if localized_title:
                scores.append(
                    fuzz.ratio(normalized_title.lower(), localized_title.lower()),
                )
            if original_title:
                scores.append(
                    fuzz.ratio(normalized_title.lower(), original_title.lower()),
                )

            title_score = max(scores) if scores else 0

            # Add score to candidate
            candidate_with_score = candidate.copy()
            candidate_with_score["title_score"] = title_score

            scored_candidates.append(candidate_with_score)

            logger.debug(
                "Scored candidate '%s' (original: '%s') against '%s': %d",
                localized_title,
                original_title[:30] if original_title else "N/A",
                normalized_title,
                title_score,
            )

        # Sort by title score (highest first)
        scored_candidates.sort(key=lambda x: x.get("title_score", 0), reverse=True)

        logger.debug("Scored %d candidates", len(scored_candidates))
        return scored_candidates

    def _filter_and_sort_by_year(
        self,
        candidates: list[dict[str, Any]],
        year_hint: str | None,
    ) -> list[dict[str, Any]]:
        """Filter and sort candidates by year match.

        This method processes a list of scored candidates, filtering and sorting
        them based on how well their release year matches the provided year hint.

        Args:
            candidates: List of scored candidates
            year_hint: Year hint from normalized query (optional)

        Returns:
            List of candidates filtered and sorted by year match
        """
        if not year_hint:
            logger.debug("No year hint provided, returning candidates as-is")
            return candidates

        try:
            target_year = int(year_hint)
        except (ValueError, TypeError):
            logger.warning("Invalid year hint: %s", year_hint)
            return candidates

        filtered_candidates = []

        for candidate in candidates:
            # Extract year from candidate
            candidate_year = None

            # Try different year fields
            for year_field in ["first_air_date", "release_date", "year"]:
                year_value = candidate.get(year_field)
                if year_value:
                    try:
                        if isinstance(year_value, str):
                            # Extract year from date string (YYYY-MM-DD)
                            candidate_year = int(year_value.split("-")[0])
                        else:
                            candidate_year = int(year_value)
                        break
                    except (ValueError, TypeError, AttributeError):
                        continue

            if candidate_year is None:
                logger.debug(
                    "No year found for candidate: %s",
                    candidate.get("title", ""),
                )
                # Include candidates without year but with lower priority
                candidate_with_year = candidate.copy()
                candidate_with_year["year_score"] = 0
                candidate_with_year["year_diff"] = 999  # High difference for sorting
                filtered_candidates.append(candidate_with_year)
                continue

            # Calculate year difference
            year_diff = abs(candidate_year - target_year)

            # Add year score (lower difference = higher score)
            candidate_with_year = candidate.copy()
            candidate_with_year["year_score"] = max(0, 100 - year_diff)
            candidate_with_year["year_diff"] = year_diff

            filtered_candidates.append(candidate_with_year)

            logger.debug(
                "Year match for '%s': %d vs %d (diff: %d, score: %d)",
                candidate.get("title", ""),
                candidate_year,
                target_year,
                year_diff,
                candidate_with_year["year_score"],
            )

        # Sort by year score (highest first), then by title score
        filtered_candidates.sort(
            key=lambda x: (x.get("year_score", 0), x.get("title_score", 0)),
            reverse=True,
        )

        logger.debug("Filtered %d candidates by year", len(filtered_candidates))
        return filtered_candidates

    def _calculate_confidence_scores(
        self,
        candidates: list[dict[str, Any]],
        normalized_query: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Calculate confidence scores for all candidates.

        This method uses the confidence scoring system to evaluate each candidate
        and add a confidence_score field to each candidate.

        Args:
            candidates: List of TMDB search results
            normalized_query: Normalized query containing title, year, and language

        Returns:
            List of candidates with added 'confidence_score' field
        """
        scored_candidates = []

        for candidate in candidates:
            try:
                # Type validation for candidate
                if not isinstance(candidate, dict):
                    logger.warning(
                        "Invalid candidate type: %s, expected dict, skipping",
                        type(candidate),
                    )
                    continue

                # Calculate confidence score using the scoring system
                confidence_score = calculate_confidence_score(
                    normalized_query,
                    candidate,
                )

                # Add confidence score to candidate
                candidate_with_confidence = candidate.copy()
                candidate_with_confidence["confidence_score"] = confidence_score

                scored_candidates.append(candidate_with_confidence)

                logger.debug(
                    "Confidence score for '%s': %.3f",
                    candidate.get("title", ""),
                    confidence_score,
                )

            except Exception as e:
                logger.warning(
                    "Error calculating confidence score for candidate '%s': %s",
                    candidate.get("title", ""),
                    str(e),
                )
                # Add candidate with 0 confidence score
                candidate_with_confidence = candidate.copy()
                candidate_with_confidence["confidence_score"] = 0.0
                scored_candidates.append(candidate_with_confidence)

        # Sort by confidence score (highest first)
        scored_candidates.sort(key=lambda x: x.get("confidence_score", 0), reverse=True)

        logger.debug(
            "Calculated confidence scores for %d candidates",
            len(scored_candidates),
        )
        return scored_candidates

    async def find_match(self, anitopy_result: dict[str, Any]) -> dict[str, Any] | None:
        """Find the best match for an anime title using multi-stage matching with fallback strategies.

        This method orchestrates the entire matching process by delegating to specialized methods.

        Args:
            anitopy_result: Result from anitopy.parse() containing anime metadata

        Returns:
            Best matching TMDB result with confidence metadata or None if no good match found
        """
        self.statistics.start_timing("matching_operation")

        try:
            # Step 1: Validate and normalize input
            normalized_query = self._validate_and_normalize_input(anitopy_result)
            if not normalized_query:
                return None

            # Step 2: Search for candidates
            candidates = await self._search_for_candidates(normalized_query)
            if not candidates:
                return None

            # Step 3: Score and rank candidates
            scored_candidates = self._score_and_rank_candidates(
                candidates,
                normalized_query,
            )
            if not scored_candidates:
                return None

            # Step 4: Apply fallback strategies if needed
            best_candidate = self._apply_fallback_if_needed(
                scored_candidates,
                normalized_query,
            )

            # Step 5: Validate final confidence
            if not self._validate_final_confidence(best_candidate):
                return None

            # Step 6: Add metadata and return result
            result = self._add_matching_metadata(
                best_candidate,
                normalized_query,
                candidates,
                scored_candidates,
            )
            self._record_successful_match(result, candidates)
            self.statistics.end_timing("matching_operation")

            return result

        except Exception:
            logger.exception("Error in find_match")
            self.statistics.record_match_failure()
            self.statistics.end_timing("matching_operation")
            return None

    def _validate_and_normalize_input(
        self,
        anitopy_result: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Validate and normalize the input query.

        Args:
            anitopy_result: Result from anitopy.parse() containing anime metadata

        Returns:
            Normalized query dictionary or None if validation fails
        """
        normalized_query = normalize_query_from_anitopy(anitopy_result)
        if not normalized_query:
            logger.warning("Failed to normalize query from anitopy result")
            return None

        title = normalized_query.get("title", "")
        if not title:
            logger.warning("No title found in normalized query")
            return None

        logger.info("Searching for match: %s", title)
        return normalized_query

    async def _search_for_candidates(
        self,
        normalized_query: dict[str, Any],
    ) -> list[dict[str, Any]] | None:
        """Search for TMDB candidates.

        Args:
            normalized_query: Normalized query containing title and metadata

        Returns:
            List of TMDB candidates or None if no candidates found
        """
        title = normalized_query.get("title", "")
        candidates = await self._search_tmdb(normalized_query)

        if not candidates:
            logger.info("No candidates found for: %s", title)
            return None

        return candidates

    def _score_and_rank_candidates(
        self,
        candidates: list[dict[str, Any]],
        normalized_query: dict[str, Any],
    ) -> list[dict[str, Any]] | None:
        """Score and rank candidates by confidence.

        Args:
            candidates: List of TMDB candidates
            normalized_query: Normalized query containing title and metadata

        Returns:
            List of scored and ranked candidates or None if scoring fails
        """
        title = normalized_query.get("title", "")
        scored_candidates = self._calculate_confidence_scores(
            candidates,
            normalized_query,
        )

        if not scored_candidates:
            logger.info("No scored candidates for: %s", title)
            return None

        return scored_candidates

    def _apply_fallback_if_needed(
        self,
        scored_candidates: list[dict[str, Any]],
        normalized_query: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply fallback strategies if confidence is too low.

        Args:
            scored_candidates: List of scored candidates
            normalized_query: Normalized query containing title and metadata

        Returns:
            Best candidate after applying fallback strategies
        """
        best_candidate = scored_candidates[0]
        best_confidence = best_candidate.get("confidence_score", 0.0)

        logger.info(
            "Best candidate for '%s': '%s' (confidence: %.3f)",
            normalized_query.get("title", ""),
            best_candidate.get("title", ""),
            best_confidence,
        )

        if best_confidence < ConfidenceThresholds.HIGH:
            logger.info(
                "Low confidence (%.3f < %.3f), applying fallback strategies",
                best_confidence,
                ConfidenceThresholds.HIGH,
            )

            fallback_candidates = self._apply_fallback_strategies(
                scored_candidates,
                normalized_query,
            )

            if fallback_candidates:
                best_candidate = fallback_candidates[0]
                best_confidence = best_candidate.get("confidence_score", 0.0)
                logger.info("Fallback improved confidence to %.3f", best_confidence)

        return best_candidate

    def _validate_final_confidence(self, best_candidate: dict[str, Any]) -> bool:
        """Validate that the final confidence meets minimum threshold.

        Args:
            best_candidate: The best candidate to validate

        Returns:
            True if confidence is acceptable, False otherwise
        """
        best_confidence = best_candidate.get("confidence_score", 0.0)

        if best_confidence < ConfidenceThresholds.LOW:
            logger.warning(
                "Very low confidence (%.3f < %.3f), returning None",
                best_confidence,
                ConfidenceThresholds.LOW,
            )
            return False

        return True

    def _add_matching_metadata(
        self,
        best_candidate: dict[str, Any],
        normalized_query: dict[str, Any],
        candidates: list[dict[str, Any]],
        scored_candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Add metadata about the matching process to the result.

        Args:
            best_candidate: The best matching candidate
            normalized_query: Normalized query containing title and metadata
            candidates: Original list of candidates
            scored_candidates: List of scored candidates

        Returns:
            Candidate with added matching metadata
        """
        title = normalized_query.get("title", "")
        best_confidence = best_candidate.get("confidence_score", 0.0)

        best_candidate["matching_metadata"] = {
            "original_title": title,
            "year_hint": normalized_query.get("year"),
            "language": normalized_query.get("language"),
            "total_candidates": len(candidates),
            "scored_candidates": len(scored_candidates),
            "confidence_score": best_confidence,
            "confidence_level": self._get_confidence_level(best_confidence),
            "used_fallback": best_confidence < ConfidenceThresholds.HIGH,
        }

        logger.info(
            "Found best match for '%s': '%s' (confidence: %.3f, level: %s)",
            title,
            best_candidate.get("title", ""),
            best_confidence,
            best_candidate["matching_metadata"]["confidence_level"],
        )

        return best_candidate

    def _record_successful_match(
        self,
        result: dict[str, Any],
        candidates: list[dict[str, Any]],
    ) -> None:
        """Record statistics for successful match.

        Args:
            result: The successful match result
            candidates: Original list of candidates
        """
        best_confidence = result.get("confidence_score", 0.0)
        used_fallback = result.get("matching_metadata", {}).get("used_fallback", False)

        self.statistics.record_match_success(
            confidence=best_confidence,
            candidates_count=len(candidates),
            used_fallback=used_fallback,
        )

    def _apply_fallback_strategies(
        self,
        candidates: list[dict[str, Any]],
        normalized_query: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Apply fallback strategies to improve matching.

        This method implements various fallback strategies when primary matching
        yields low confidence results. Strategies include genre-based filtering
        and partial substring matching.

        Args:
            candidates: List of scored candidates
            normalized_query: Normalized query containing title and metadata

        Returns:
            List of candidates after applying fallback strategies
        """
        logger.debug("Applying fallback strategies to %d candidates", len(candidates))

        # Stage 1: Apply genre-based filtering
        genre_filtered_candidates = self._apply_genre_filter(candidates)

        # Check if genre filtering improved confidence
        if genre_filtered_candidates:
            best_confidence = genre_filtered_candidates[0].get("confidence_score", 0.0)
            if best_confidence >= ConfidenceThresholds.HIGH:
                logger.debug(
                    "Genre filtering produced high confidence match: %.3f",
                    best_confidence,
                )
                return genre_filtered_candidates

        # Stage 2: Apply partial substring matching
        partial_matched_candidates = self._apply_partial_substring_match(
            genre_filtered_candidates,
            normalized_query,
        )

        logger.debug(
            "Fallback strategies completed, returning %d candidates",
            len(partial_matched_candidates),
        )
        return partial_matched_candidates

    def _apply_genre_filter(
        self,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Apply genre-based filtering to boost animation candidates.

        This method iterates through candidates and boosts the confidence score
        of any candidate that has the Animation genre (ID 16) in its genre_ids list.

        Args:
            candidates: List of scored candidates

        Returns:
            List of candidates with updated confidence scores, sorted by new scores
        """
        if not candidates:
            logger.debug("No candidates to apply genre filter to")
            return candidates

        logger.debug("Applying genre filter to %d candidates", len(candidates))

        boosted_candidates = []

        for candidate in candidates:
            # Create a copy to avoid modifying the original
            boosted_candidate = candidate.copy()

            # Check if candidate has genre information
            genre_ids = candidate.get("genre_ids", [])
            if not genre_ids:
                # Try to get genre_ids from nested tmdb_data if available
                tmdb_data = candidate.get("tmdb_data", {})
                genre_ids = tmdb_data.get("genre_ids", [])

            # Apply genre boost for confirmed animation (no penalty to avoid false negatives)
            current_confidence = boosted_candidate.get("confidence_score", 0.0)

            if ANIMATION_GENRE_ID in genre_ids:
                # Boost for animation genre
                new_confidence = min(1.0, current_confidence + ANIMATION_BOOST)
                boosted_candidate["confidence_score"] = new_confidence

                # Animation threshold: 0.2 (lenient for cross-script fuzzy matching)
                if new_confidence >= 0.2:
                    boosted_candidates.append(boosted_candidate)
                    logger.debug(
                        "✅ Applied animation boost to '%s': %.3f -> %.3f (passed threshold 0.2)",
                        candidate.get("title", "")[:40],
                        current_confidence,
                        new_confidence,
                    )
                else:
                    logger.debug(
                        "❌ Animation candidate '%s' rejected: %.3f < 0.2",
                        candidate.get("title", "")[:40],
                        new_confidence,
                    )
            # Non-animation: require much higher confidence (0.8) to avoid false positives
            # This filters out quiz shows, variety shows, live-action, etc.
            elif current_confidence >= 0.8:
                boosted_candidates.append(boosted_candidate)
                logger.debug(
                    "✅ Non-animation candidate '%s' accepted: %.3f >= 0.8",
                    candidate.get("title", "")[:40],
                    current_confidence,
                )
            else:
                logger.debug(
                    "❌ Non-animation candidate '%s' rejected: %.3f < 0.8 (genre_ids: %s)",
                    candidate.get("title", "")[:40],
                    current_confidence,
                    genre_ids if genre_ids else "empty",
                )

        # Sort by confidence score (highest first)
        boosted_candidates.sort(
            key=lambda x: x.get("confidence_score", 0),
            reverse=True,
        )

        logger.debug("Genre filter applied to %d candidates", len(boosted_candidates))
        return boosted_candidates

    def _apply_partial_substring_match(
        self,
        candidates: list[dict[str, Any]],
        normalized_query: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Apply partial substring matching to improve matching for abbreviated titles.

        This method uses fuzzywuzzy's partial_ratio to calculate new confidence scores
        for candidates, which is useful for cases like 'OP' matching 'One Piece' or
        'KNY' matching 'Kimetsu no Yaiba'.

        Args:
            candidates: List of scored candidates
            normalized_query: Normalized query containing title and metadata

        Returns:
            List of candidates with updated confidence scores based on partial matching
        """
        if not candidates:
            logger.debug("No candidates to apply partial substring matching to")
            return candidates

        title = normalized_query.get("title", "")
        if not title:
            logger.debug("No title in normalized query for partial substring matching")
            return candidates

        logger.debug(
            "Applying partial substring matching to %d candidates for title: %s",
            len(candidates),
            title,
        )

        partial_matched_candidates = []

        for candidate in candidates:
            # Create a copy to avoid modifying the original
            partial_candidate = candidate.copy()

            # Extract candidate title
            candidate_title = candidate.get("title", "") or candidate.get("name", "")
            if not candidate_title:
                logger.debug("Skipping candidate with no title for partial matching")
                partial_matched_candidates.append(partial_candidate)
                continue

            # Calculate partial ratio score
            partial_score = fuzz.partial_ratio(title.lower(), candidate_title.lower())

            # Convert partial score (0-100) to confidence score (0.0-1.0)
            partial_confidence = partial_score / 100.0

            # Use the higher of the original confidence or partial confidence
            original_confidence = partial_candidate.get("confidence_score", 0.0)
            new_confidence = max(original_confidence, partial_confidence)
            partial_candidate["confidence_score"] = new_confidence

            # Add partial matching metadata
            partial_candidate["partial_match_score"] = partial_score
            partial_candidate["used_partial_matching"] = (
                partial_confidence > original_confidence
            )

            logger.debug(
                "Partial match for '%s' vs '%s': %d (confidence: %.3f -> %.3f)",
                title,
                candidate_title,
                partial_score,
                original_confidence,
                new_confidence,
            )

            partial_matched_candidates.append(partial_candidate)

        # Sort by confidence score (highest first)
        partial_matched_candidates.sort(
            key=lambda x: x.get("confidence_score", 0),
            reverse=True,
        )

        logger.debug(
            "Partial substring matching applied to %d candidates",
            len(partial_matched_candidates),
        )
        return partial_matched_candidates

    def _get_confidence_level(self, confidence_score: float) -> str:
        """Get confidence level description based on score.

        Args:
            confidence_score: Confidence score between 0.0 and 1.0

        Returns:
            Confidence level description
        """
        if confidence_score >= ConfidenceThresholds.HIGH:
            return "high"
        if confidence_score >= ConfidenceThresholds.MEDIUM:
            return "medium"
        if confidence_score >= ConfidenceThresholds.LOW:
            return "low"
        return "very_low"

    def get_cache_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics for GUI display.

        Returns:
            Dictionary containing cache statistics:
            - hit_ratio: Cache hit ratio percentage (0.0-100.0)
            - total_requests: Total cache requests (hits + misses)
            - cache_items: Total items in cache
            - cache_mode: Current cache mode (hybrid/db-only/json-only)
            - cache_type: Primary cache type (SQLite/JSON/Hybrid)
        """
        # Get cache hit ratio from statistics
        hit_ratio = self.statistics.get_cache_hit_ratio()
        total_requests = (
            self.statistics.metrics.cache_hits + self.statistics.metrics.cache_misses
        )

        # Get cache item count from SQLite if available
        cache_items = 0
        if hasattr(self, "db_cache") and self.db_cache:
            try:
                cache_info = self.db_cache.get_cache_info()
                cache_items = cache_info.get("total_files", 0)
            except OSError as e:
                logger.warning("Failed to get cache item count: %s", e)

        # Determine primary cache type for display
        cache_mode = getattr(self, "cache_mode", "json-only")
        if cache_mode == "hybrid":
            cache_type = "Hybrid"
        elif cache_mode == "db-only":
            cache_type = "SQLite"
        elif cache_mode == "json-only":
            cache_type = "JSON"
        else:
            cache_type = "Unknown"

        return {
            "hit_ratio": hit_ratio,
            "total_requests": total_requests,
            "cache_items": cache_items,
            "cache_mode": cache_mode,
            "cache_type": cache_type,
        }
