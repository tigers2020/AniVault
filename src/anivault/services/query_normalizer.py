"""Query normalization and matching accuracy improvements for TMDB."""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

logger = logging.getLogger(__name__)


class QueryNormalizer:
    """Normalizes queries for better TMDB matching accuracy."""

    def __init__(self) -> None:
        """Initialize the query normalizer."""
        # Common anime title patterns to clean
        self.anime_patterns = [
            # Remove common suffixes
            (r"\s*\(TV\)", ""),
            (r"\s*\(OVA\)", ""),
            (r"\s*\(ONA\)", ""),
            (r"\s*\(Movie\)", ""),
            (r"\s*\(Special\)", ""),
            (r"\s*\(OAV\)", ""),
            # Remove season indicators
            (r"\s*Season\s*\d+", ""),
            (r"\s*S\d+", ""),
            # Remove episode indicators
            (r"\s*Episode\s*\d+", ""),
            (r"\s*E\d+", ""),
            # Remove quality indicators
            (r"\s*\d+p", ""),
            (r"\s*HD", ""),
            (r"\s*SD", ""),
            # Remove release group indicators
            (r"\s*\[.*?\]", ""),
            (r"\s*\(.*?\)", ""),
        ]

        # Common title variations
        self.title_variations = {
            # English to Japanese
            "Attack on Titan": "Shingeki no Kyojin",
            "One Piece": "ワンピース",
            "Naruto": "ナルト",
            "Dragon Ball": "ドラゴンボール",
            "Death Note": "デスノート",
            "Fullmetal Alchemist": "鋼の錬金術師",
            "Bleach": "ブリーチ",
            "Hunter x Hunter": "ハンター×ハンター",
            "My Hero Academia": "僕のヒーローアカデミア",
            "Demon Slayer": "鬼滅の刃",
        }

    def normalize_query(self, query: str) -> str:
        """Normalize a query for better TMDB matching.

        Args:
            query: Original query string

        Returns:
            Normalized query string
        """
        if not query:
            return ""

        # Start with the original query
        normalized = query.strip()

        # Apply anime-specific cleaning patterns
        for pattern, replacement in self.anime_patterns:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # Unicode normalization
        normalized = unicodedata.normalize("NFKC", normalized)

        # Try title variations (only if exact match and no cleaning was done)
        if normalized == query.strip():
            for original, variation in self.title_variations.items():
                if normalized.lower() == original.lower():
                    normalized = variation
                    break

        logger.debug(f"Normalized query: '{query}' -> '{normalized}'")
        return normalized

    def generate_query_variants(self, query: str) -> list[str]:
        """Generate multiple query variants for better matching.

        Args:
            query: Original query string

        Returns:
            List of query variants
        """
        variants = []

        # Original query
        variants.append(query)

        # Normalized query
        normalized = self.normalize_query(query)
        if normalized != query:
            variants.append(normalized)

        # Try removing common words
        common_words = [
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
        ]
        words = query.split()
        if len(words) > 1:
            filtered_words = [w for w in words if w.lower() not in common_words]
            if filtered_words:
                variants.append(" ".join(filtered_words))

        # Try with year if present
        year_match = re.search(r"\b(19|20)\d{2}\b", query)
        if year_match:
            year = year_match.group()
            without_year = re.sub(r"\b(19|20)\d{2}\b", "", query).strip()
            variants.append(without_year)
            variants.append(f"{without_year} {year}")

        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for variant in variants:
            if variant and variant not in seen:
                seen.add(variant)
                unique_variants.append(variant)

        return unique_variants

    def calculate_similarity(self, query1: str, query2: str) -> float:
        """Calculate similarity between two queries.

        Args:
            query1: First query
            query2: Second query

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not query1 or not query2:
            return 0.0

        # Normalize both queries
        norm1 = self.normalize_query(query1).lower()
        norm2 = self.normalize_query(query2).lower()

        # Exact match
        if norm1 == norm2:
            return 1.0

        # Calculate Jaccard similarity
        words1 = set(norm1.split())
        words2 = set(norm2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        jaccard_similarity = len(intersection) / len(union)

        # Boost score for partial matches
        if len(intersection) > 0:
            jaccard_similarity += 0.1

        # Also check for substring matches
        if norm1 in norm2 or norm2 in norm1:
            jaccard_similarity = max(jaccard_similarity, 0.5)

        return min(jaccard_similarity, 1.0)

    def get_stats(self) -> dict[str, Any]:
        """Get normalizer statistics.

        Returns:
            Dictionary containing normalizer statistics
        """
        return {
            "patterns_count": len(self.anime_patterns),
            "variations_count": len(self.title_variations),
        }
