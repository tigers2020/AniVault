"""Optimized quality score calculation for TMDB search results."""

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any


@dataclass
class QualityScoreConfig:
    """Configuration for quality score calculation."""

    similarity_weight: float = 0.6
    year_weight: float = 0.2
    language_weight: float = 0.2


class OptimizedQualityCalculator:
    """Optimized quality score calculator with performance improvements."""

    def __init__(self, config: QualityScoreConfig):
        """Initialize the calculator with configuration."""
        self.config = config

        # Pre-compile regex patterns for better performance
        self._bracket_pattern = re.compile(r"\[.*?\]")
        self._parentheses_pattern = re.compile(r"\(.*?\)")
        self._resolution_pattern = re.compile(r"[0-9]+p", re.IGNORECASE)
        self._interlaced_pattern = re.compile(r"[0-9]+i", re.IGNORECASE)
        self._fps_pattern = re.compile(r"[0-9]+fps", re.IGNORECASE)
        self._word_pattern = re.compile(r"\b\w+\b")

        # Cache for year differences (common cases)
        self._year_diff_cache: dict[tuple[int, int], float] = {}

        # Cache for language code splitting
        self._language_cache: dict[str, str] = {}

    def calculate_quality_score(
        self, result: dict[str, Any], query: str, language: str, year_hint: int | None = None
    ) -> float:
        """Calculate optimized quality score for a search result.

        Args:
            result: TMDB search result
            query: Original search query
            language: Language code
            year_hint: Year hint from filename parsing

        Returns:
            Quality score between 0.0 and 1.0
        """
        # Extract title and year from result
        title = result.get("title") or result.get("name", "")
        original_title = result.get("original_title") or result.get("original_name", "")
        release_date = result.get("release_date") or result.get("first_air_date", "")

        # Extract year from release date (cached)
        result_year = self._extract_year_cached(release_date)

        # Calculate component scores
        similarity_score = self._calculate_similarity_score_optimized(query, title, original_title)
        year_score = self._calculate_year_score_optimized(result_year, year_hint)
        language_score = self._calculate_language_score_optimized(result, language)

        # Calculate weighted total
        total_score = (
            similarity_score * self.config.similarity_weight
            + year_score * self.config.year_weight
            + language_score * self.config.language_weight
        )

        return min(1.0, max(0.0, total_score))

    @lru_cache(maxsize=1000)
    def _extract_year_cached(self, release_date: str) -> int | None:
        """Extract year from release date with caching."""
        if not release_date:
            return None

        try:
            return int(release_date.split("-")[0])
        except (ValueError, IndexError):
            return None

    def _calculate_similarity_score_optimized(
        self, query: str, title: str, original_title: str
    ) -> float:
        """Calculate optimized similarity score between query and titles."""
        # Normalize query and titles using cached normalization
        query_tokens = self._normalize_query_tokens_optimized(query)
        title_tokens = self._normalize_query_tokens_optimized(title)
        original_tokens = self._normalize_query_tokens_optimized(original_title)

        # Calculate Jaccard similarity for both titles
        title_similarity = self._jaccard_similarity_optimized(query_tokens, title_tokens)
        original_similarity = self._jaccard_similarity_optimized(query_tokens, original_tokens)

        # Use the higher similarity
        return max(title_similarity, original_similarity)

    @lru_cache(maxsize=2000)
    def _normalize_query_tokens_optimized(self, text: str) -> tuple[str, ...]:
        """Optimized token normalization with pre-compiled regex patterns."""
        if not text:
            return tuple()

        # Apply all regex patterns in sequence
        text = self._bracket_pattern.sub("", text)
        text = self._parentheses_pattern.sub("", text)
        text = self._resolution_pattern.sub("", text)
        text = self._interlaced_pattern.sub("", text)
        text = self._fps_pattern.sub("", text)

        # Split into tokens and normalize
        tokens = self._word_pattern.findall(text.lower())
        return tuple(tokens)

    def _jaccard_similarity_optimized(self, set1: tuple[str, ...], set2: tuple[str, ...]) -> float:
        """Optimized Jaccard similarity calculation."""
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0

        # Convert to sets for intersection/union operations
        set1_set = set(set1)
        set2_set = set(set2)

        # Calculate intersection and union in one pass
        intersection = len(set1_set.intersection(set2_set))
        union = len(set1_set) + len(set2_set) - intersection

        return intersection / union if union > 0 else 0.0

    def _calculate_year_score_optimized(
        self, result_year: int | None, year_hint: int | None
    ) -> float:
        """Optimized year match score calculation."""
        if not result_year or not year_hint:
            return 0.5  # Neutral score if no year info

        # Use cached year difference calculation
        year_diff = abs(result_year - year_hint)

        # Check cache first
        cache_key = (result_year, year_hint)
        if cache_key in self._year_diff_cache:
            return self._year_diff_cache[cache_key]

        # Calculate score
        if year_diff == 0:
            score = 1.0
        elif year_diff == 1:
            score = 0.8  # ±1 year gets partial credit
        elif year_diff <= 3:
            score = 0.5  # ±3 years gets some credit
        else:
            score = 0.0  # Too far apart

        # Cache the result
        self._year_diff_cache[cache_key] = score
        return score

    def _calculate_language_score_optimized(self, result: dict[str, Any], language: str) -> float:
        """Optimized language match score calculation."""
        # Get language code (cached)
        lang_code = self._get_language_code_cached(language)

        # Check if result has translations for the requested language
        translations = result.get("translations", {}).get("translations", [])

        for translation in translations:
            if translation.get("iso_639_1") == lang_code:
                return 1.0

        # Check if original language matches
        original_language = result.get("original_language", "")
        if original_language == lang_code:
            return 0.8

        return 0.5  # Neutral score for other languages

    @lru_cache(maxsize=100)
    def _get_language_code_cached(self, language: str) -> str:
        """Get language code with caching."""
        return language.split("-")[0]

    def clear_caches(self) -> None:
        """Clear all internal caches."""
        self._extract_year_cached.cache_clear()
        self._normalize_query_tokens_optimized.cache_clear()
        self._get_language_code_cached.cache_clear()
        self._year_diff_cache.clear()
        self._language_cache.clear()

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics for monitoring."""
        return {
            "year_extraction_cache": self._extract_year_cached.cache_info().currsize,
            "token_normalization_cache": self._normalize_query_tokens_optimized.cache_info().currsize,
            "language_code_cache": self._get_language_code_cached.cache_info().currsize,
            "year_diff_cache": len(self._year_diff_cache),
            "language_cache": len(self._language_cache),
        }


class QualityScoreCalculatorFactory:
    """Factory for creating quality score calculators."""

    @staticmethod
    def create_optimized_calculator(
        similarity_weight: float = 0.6, year_weight: float = 0.2, language_weight: float = 0.2
    ) -> OptimizedQualityCalculator:
        """Create an optimized quality score calculator."""
        config = QualityScoreConfig(
            similarity_weight=similarity_weight,
            year_weight=year_weight,
            language_weight=language_weight,
        )
        return OptimizedQualityCalculator(config)

    @staticmethod
    def create_legacy_calculator() -> "LegacyQualityCalculator":
        """Create a legacy quality score calculator for comparison."""
        return LegacyQualityCalculator()


class LegacyQualityCalculator:
    """Legacy quality score calculator for performance comparison."""

    def __init__(
        self, similarity_weight: float = 0.6, year_weight: float = 0.2, language_weight: float = 0.2
    ):
        """Initialize the legacy calculator."""
        self.similarity_weight = similarity_weight
        self.year_weight = year_weight
        self.language_weight = language_weight

    def calculate_quality_score(
        self, result: dict[str, Any], query: str, language: str, year_hint: int | None = None
    ) -> float:
        """Calculate quality score using legacy method."""
        # Extract title and year from result
        title = result.get("title") or result.get("name", "")
        original_title = result.get("original_title") or result.get("original_name", "")
        release_date = result.get("release_date") or result.get("first_air_date", "")

        # Extract year from release date
        result_year = None
        if release_date:
            try:
                result_year = int(release_date.split("-")[0])
            except (ValueError, IndexError):
                pass

        # 1. Similarity score
        similarity_score = self._calculate_similarity_score(query, title, original_title)

        # 2. Year match score
        year_score = self._calculate_year_score(result_year, year_hint)

        # 3. Language match score
        language_score = self._calculate_language_score(result, language)

        # Calculate weighted total
        total_score = (
            similarity_score * self.similarity_weight
            + year_score * self.year_weight
            + language_score * self.language_weight
        )

        return min(1.0, max(0.0, total_score))

    def _calculate_similarity_score(self, query: str, title: str, original_title: str) -> float:
        """Calculate similarity score between query and titles."""
        # Normalize query and titles
        query_tokens = self._normalize_query_tokens(query)
        title_tokens = self._normalize_query_tokens(title)
        original_tokens = self._normalize_query_tokens(original_title)

        # Calculate Jaccard similarity for both titles
        title_similarity = self._jaccard_similarity(query_tokens, title_tokens)
        original_similarity = self._jaccard_similarity(query_tokens, original_tokens)

        # Use the higher similarity
        return max(title_similarity, original_similarity)

    def _normalize_query_tokens(self, text: str) -> set[str]:
        """Normalize text to tokens, removing brackets, resolution, release group tags."""
        if not text:
            return set()

        # Remove common anime file tags
        import re

        text = re.sub(r"\[.*?\]", "", text)  # Remove [tags]
        text = re.sub(r"\(.*?\)", "", text)  # Remove (tags)
        text = re.sub(r"[0-9]+p", "", text, flags=re.IGNORECASE)  # Remove resolution
        text = re.sub(r"[0-9]+i", "", text, flags=re.IGNORECASE)  # Remove interlaced
        text = re.sub(r"[0-9]+fps", "", text, flags=re.IGNORECASE)  # Remove fps

        # Split into tokens and normalize
        tokens = re.findall(r"\b\w+\b", text.lower())
        return set(tokens)

    def _jaccard_similarity(self, set1: set[str], set2: set[str]) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        return intersection / union if union > 0 else 0.0

    def _calculate_year_score(self, result_year: int | None, year_hint: int | None) -> float:
        """Calculate year match score."""
        if not result_year or not year_hint:
            return 0.5  # Neutral score if no year info

        year_diff = abs(result_year - year_hint)

        if year_diff == 0:
            return 1.0
        elif year_diff == 1:
            return 0.8  # ±1 year gets partial credit
        elif year_diff <= 3:
            return 0.5  # ±3 years gets some credit
        else:
            return 0.0  # Too far apart

    def _calculate_language_score(self, result: dict[str, Any], language: str) -> float:
        """Calculate language match score."""
        # Check if result has translations for the requested language
        translations = result.get("translations", {}).get("translations", [])

        for translation in translations:
            if translation.get("iso_639_1") == language.split("-")[0]:
                return 1.0

        # Check if original language matches
        original_language = result.get("original_language", "")
        if original_language == language.split("-")[0]:
            return 0.8

        return 0.5  # Neutral score for other languages
