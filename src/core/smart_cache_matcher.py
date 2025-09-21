"""
Smart Cache Matching Module

This module provides query normalization and similarity detection capabilities
for intelligent cache matching that can find semantically similar queries
even when they have slight variations in formatting, punctuation, or word order.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    # Fallback to difflib if rapidfuzz is not available
    import difflib

try:
    import jellyfish
    JELLYFISH_AVAILABLE = True
except ImportError:
    JELLYFISH_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class SimilarityMatch:
    """Represents a similarity match result."""
    key: str
    similarity_score: float
    match_type: str  # 'exact', 'fuzzy', 'phonetic'
    normalized_query: str


class QueryNormalizer:
    """Handles query normalization for consistent cache key generation."""
    
    # Common stop words for movie/anime titles
    STOP_WORDS: Set[str] = {
        "the", "a", "an", "and", "of", "in", "for", "with", "on", "is", "it", 
        "to", "from", "by", "at", "as", "or", "but", "not", "this", "that", 
        "which", "who", "what", "when", "where", "why", "how", "mkv", "mp4", 
        "avi", "bluray", "dvdrip", "webrip", "x264", "x265", "hd", "fhd", 
        "uhd", "1080p", "720p", "2160p", "tv", "ova", "ona", "movie", "special"
    }
    
    # Common abbreviations and their expansions
    ABBREVIATIONS: Dict[str, str] = {
        "pt": "part",
        "vol": "volume",
        "ep": "episode",
        "ch": "chapter",
        "s": "season",
        "ss": "season",
        "oav": "ova",
        "oad": "ova",
        "sp": "special",
        "ova": "original video animation",
        "ona": "original net animation"
    }
    
    def __init__(self, remove_stop_words: bool = True, expand_abbreviations: bool = True):
        """Initialize the query normalizer.
        
        Args:
            remove_stop_words: Whether to remove common stop words
            expand_abbreviations: Whether to expand common abbreviations
        """
        self.remove_stop_words = remove_stop_words
        self.expand_abbreviations = expand_abbreviations
    
    def normalize(self, query: str) -> str:
        """Normalize a query string for consistent matching.
        
        Args:
            query: Original query string
            
        Returns:
            Normalized query string
        """
        if not query:
            return ""
        
        # Convert to lowercase and strip whitespace
        normalized = query.lower().strip()
        
        # Remove file extensions and quality indicators
        normalized = self._remove_quality_indicators(normalized)
        
        # Remove punctuation and special characters, keep alphanumeric and spaces
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        # Normalize whitespace (multiple spaces to single space)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Extract and standardize year
        normalized = self._extract_year(normalized)
        
        # Expand abbreviations if enabled
        if self.expand_abbreviations:
            normalized = self._expand_abbreviations(normalized)
        
        # Remove stop words if enabled
        if self.remove_stop_words:
            normalized = self._remove_stop_words(normalized)
        
        return normalized
    
    def _remove_quality_indicators(self, query: str) -> str:
        """Remove common quality indicators and file extensions."""
        # Pattern for quality indicators in parentheses or as separate words
        quality_patterns = [
            r'\([^)]*(?:1080p|720p|2160p|hd|fhd|uhd|bluray|dvdrip|webrip|x264|x265)[^)]*\)',
            r'\b(?:1080p|720p|2160p|hd|fhd|uhd|bluray|dvdrip|webrip|x264|x265)\b',
            r'\.(?:mkv|mp4|avi|mov|wmv|flv|webm|m4v)$'
        ]
        
        for pattern in quality_patterns:
            query = re.sub(pattern, '', query, flags=re.IGNORECASE)
        
        return query
    
    def _extract_year(self, query: str) -> str:
        """Extract and standardize year information."""
        # Look for years in various formats: (2023), 2023, '23, etc.
        year_patterns = [
            r'\((\d{4})\)',  # (2023)
            r'\b(\d{4})\b',  # 2023
            r"'(\d{2})\b",   # '23
        ]
        
        years = []
        for pattern in year_patterns:
            matches = re.findall(pattern, query)
            years.extend(matches)
        
        # Remove year patterns from query
        for pattern in year_patterns:
            query = re.sub(pattern, '', query)
        
        # Add standardized year at the end if found
        if years:
            # Convert 2-digit years to 4-digit (assuming 20xx for years > 50, 19xx otherwise)
            full_years = []
            for year in years:
                if len(year) == 2:
                    year_int = int(year)
                    if year_int > 50:
                        full_years.append(f"19{year}")
                    else:
                        full_years.append(f"20{year}")
                else:
                    full_years.append(year)
            
            # Use the most recent year if multiple found
            if full_years:
                latest_year = max(full_years)
                query = f"{query} {latest_year}".strip()
        
        return query
    
    def _expand_abbreviations(self, query: str) -> str:
        """Expand common abbreviations."""
        words = query.split()
        expanded_words = []
        
        for word in words:
            if word in self.ABBREVIATIONS:
                expanded_words.append(self.ABBREVIATIONS[word])
            else:
                expanded_words.append(word)
        
        return ' '.join(expanded_words)
    
    def _remove_stop_words(self, query: str) -> str:
        """Remove common stop words."""
        words = query.split()
        filtered_words = [word for word in words if word not in self.STOP_WORDS]
        return ' '.join(filtered_words)


class SimilarityDetector:
    """Handles similarity detection between queries using various algorithms."""
    
    def __init__(self, fuzzy_threshold: float = 60.0, phonetic_threshold: float = 0.8):
        """Initialize the similarity detector.
        
        Args:
            fuzzy_threshold: Minimum fuzzy matching score (0-100)
            phonetic_threshold: Minimum phonetic matching score (0-1)
        """
        self.fuzzy_threshold = fuzzy_threshold
        self.phonetic_threshold = phonetic_threshold
        self.normalizer = QueryNormalizer()
    
    def find_similar_queries(
        self, 
        target_query: str, 
        candidate_queries: List[str],
        use_fuzzy: bool = True,
        use_phonetic: bool = True
    ) -> List[SimilarityMatch]:
        """Find queries similar to the target query.
        
        Args:
            target_query: Query to find matches for
            candidate_queries: List of candidate queries to check
            use_fuzzy: Whether to use fuzzy matching
            use_phonetic: Whether to use phonetic matching
            
        Returns:
            List of similarity matches sorted by score (highest first)
        """
        if not target_query or not candidate_queries:
            return []
        
        normalized_target = self.normalizer.normalize(target_query)
        matches = []
        
        for candidate in candidate_queries:
            normalized_candidate = self.normalizer.normalize(candidate)
            
            # Skip if already normalized to the same string
            if normalized_target == normalized_candidate:
                matches.append(SimilarityMatch(
                    key=candidate,
                    similarity_score=100.0,
                    match_type='exact',
                    normalized_query=normalized_candidate
                ))
                continue
            
            # Fuzzy matching
            if use_fuzzy:
                fuzzy_score = self._calculate_fuzzy_similarity(normalized_target, normalized_candidate)
                if fuzzy_score >= self.fuzzy_threshold:
                    matches.append(SimilarityMatch(
                        key=candidate,
                        similarity_score=fuzzy_score,
                        match_type='fuzzy',
                        normalized_query=normalized_candidate
                    ))
                    continue
            
            # Phonetic matching
            if use_phonetic and JELLYFISH_AVAILABLE:
                phonetic_score = self._calculate_phonetic_similarity(normalized_target, normalized_candidate)
                if phonetic_score >= self.phonetic_threshold:
                    matches.append(SimilarityMatch(
                        key=candidate,
                        similarity_score=phonetic_score * 100,  # Convert to 0-100 scale
                        match_type='phonetic',
                        normalized_query=normalized_candidate
                    ))
        
        # Sort by similarity score (highest first)
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        return matches
    
    def _calculate_fuzzy_similarity(self, query1: str, query2: str) -> float:
        """Calculate fuzzy similarity between two normalized queries."""
        if not RAPIDFUZZ_AVAILABLE:
            # Fallback to difflib
            matcher = difflib.SequenceMatcher(None, query1, query2)
            return matcher.ratio() * 100
        
        # Use rapidfuzz for better performance and accuracy
        # token_set_ratio is most robust for handling word order changes
        return fuzz.token_set_ratio(query1, query2)
    
    def _calculate_phonetic_similarity(self, query1: str, query2: str) -> float:
        """Calculate phonetic similarity between two normalized queries."""
        if not JELLYFISH_AVAILABLE:
            return 0.0
        
        # Generate phonetic codes for both queries
        phonetic1 = jellyfish.metaphone(query1)
        phonetic2 = jellyfish.metaphone(query2)
        
        # If phonetic codes are identical, it's a perfect match
        if phonetic1 == phonetic2:
            return 1.0
        
        # Calculate similarity based on phonetic code similarity
        if phonetic1 and phonetic2:
            # Use Jaro-Winkler similarity for phonetic codes
            return jellyfish.jaro_winkler_similarity(phonetic1, phonetic2)
        
        return 0.0


class SmartCacheMatcher:
    """Main class for smart cache matching functionality."""
    
    def __init__(
        self,
        fuzzy_threshold: float = 60.0,
        phonetic_threshold: float = 0.8,
        max_similarity_matches: int = 5
    ):
        """Initialize the smart cache matcher.
        
        Args:
            fuzzy_threshold: Minimum fuzzy matching score (0-100)
            phonetic_threshold: Minimum phonetic matching score (0-1)
            max_similarity_matches: Maximum number of similarity matches to return
        """
        self.normalizer = QueryNormalizer()
        self.similarity_detector = SimilarityDetector(fuzzy_threshold, phonetic_threshold)
        self.max_similarity_matches = max_similarity_matches
        
        # Log availability of optional libraries
        if not RAPIDFUZZ_AVAILABLE:
            logger.warning("rapidfuzz not available, falling back to difflib for fuzzy matching")
        if not JELLYFISH_AVAILABLE:
            logger.warning("jellyfish not available, phonetic matching disabled")
    
    def normalize_query(self, query: str) -> str:
        """Normalize a query for consistent matching.
        
        Args:
            query: Original query string
            
        Returns:
            Normalized query string
        """
        return self.normalizer.normalize(query)
    
    def find_similar_cache_keys(
        self,
        target_query: str,
        cache_keys: List[str],
        use_fuzzy: bool = True,
        use_phonetic: bool = True
    ) -> List[SimilarityMatch]:
        """Find cache keys similar to the target query.
        
        Args:
            target_query: Query to find matches for
            cache_keys: List of existing cache keys
            use_fuzzy: Whether to use fuzzy matching
            use_phonetic: Whether to use phonetic matching
            
        Returns:
            List of similarity matches sorted by score (highest first)
        """
        matches = self.similarity_detector.find_similar_queries(
            target_query, cache_keys, use_fuzzy, use_phonetic
        )
        
        # Limit the number of matches returned
        return matches[:self.max_similarity_matches]
    
    def generate_similarity_keys(self, query: str) -> List[str]:
        """Generate multiple similarity keys for a query.
        
        Args:
            query: Original query string
            
        Returns:
            List of similarity keys that could match this query
        """
        normalized = self.normalize_query(query)
        keys = [normalized]  # Always include normalized version
        
        # Add phonetic key if available
        if JELLYFISH_AVAILABLE:
            phonetic_key = jellyfish.metaphone(normalized)
            if phonetic_key:
                keys.append(f"phonetic:{phonetic_key}")
        
        return keys
    
    def calculate_similarity(self, query1: str, query2: str) -> float:
        """Calculate similarity between two queries.
        
        Args:
            query1: First query string
            query2: Second query string
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not query1 or not query2:
            return 0.0
            
        # Normalize both queries
        norm1 = self.normalize_query(query1)
        norm2 = self.normalize_query(query2)
        
        # Exact match after normalization
        if norm1 == norm2:
            return 1.0
        
        # Use similarity detector to find matches
        # Try both directions to find the best match
        matches1 = self.similarity_detector.find_similar_queries(
            query2, [query1], use_fuzzy=True, use_phonetic=True
        )
        matches2 = self.similarity_detector.find_similar_queries(
            query1, [query2], use_fuzzy=True, use_phonetic=True
        )
        
        # Use the direction that found matches
        matches = matches1 if matches1 else matches2
        
        if matches:
            # Return the highest similarity score as a float between 0.0 and 1.0
            return matches[0].similarity_score / 100.0
        
        return 0.0

    def should_use_smart_matching(self, query: str) -> bool:
        """Determine if smart matching should be used for a query.
        
        Args:
            query: Query string to evaluate
            
        Returns:
            True if smart matching should be used
        """
        normalized = self.normalize_query(query)
        
        # Use smart matching if:
        # 1. Query has multiple words (more likely to have variations)
        # 2. Query contains common variation patterns
        # 3. Query is not too short (avoid false positives)
        
        word_count = len(normalized.split())
        has_variation_patterns = any(pattern in query.lower() for pattern in [
            '(', ')', '.', '_', '-', 'the ', 'a ', 'an '
        ])
        
        return word_count >= 2 and (has_variation_patterns or word_count >= 3)


# Global instance for easy access
smart_cache_matcher = SmartCacheMatcher()
