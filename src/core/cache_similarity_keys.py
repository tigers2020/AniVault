"""Similarity key management for cache system.

This module provides functionality for managing similarity keys used in
smart cache matching and similarity-based operations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Set

from .cache_key_generator import get_cache_key_generator
from .smart_cache_matcher import smart_cache_matcher

# Configure logging
logger = logging.getLogger(__name__)


class CacheSimilarityKeys:
    """Similarity key management for cache system."""

    def __init__(self):
        """Initialize similarity key manager."""
        self._similarity_keys: Dict[str, Set[str]] = {}
        self._key_generator = get_cache_key_generator()

    def store_similarity_keys(self, key: str, value: Any) -> None:
        """Store similarity keys for a cache entry.

        Args:
            key: Cache key
            value: Cached value
        """
        try:
            # Generate similarity keys based on value content
            similarity_keys = self._generate_similarity_keys(value)
            
            if similarity_keys:
                self._similarity_keys[key] = similarity_keys
                logger.debug(f"Stored {len(similarity_keys)} similarity keys for cache key: {key}")

        except Exception as e:
            logger.warning(f"Failed to store similarity keys for key {key}: {e}")

    def remove_similarity_keys(self, key: str) -> None:
        """Remove similarity keys for a cache entry.

        Args:
            key: Cache key
        """
        if key in self._similarity_keys:
            del self._similarity_keys[key]
            logger.debug(f"Removed similarity keys for cache key: {key}")

    def get_similarity_keys(self, key: str) -> Set[str]:
        """Get similarity keys for a cache entry.

        Args:
            key: Cache key

        Returns:
            Set of similarity keys
        """
        return self._similarity_keys.get(key, set())

    def find_similar_keys(self, query: str, threshold: float = 0.8) -> List[tuple[str, float]]:
        """Find cache keys similar to a query.

        Args:
            query: Search query
            threshold: Similarity threshold

        Returns:
            List of tuples (key, similarity_score)
        """
        similar_keys = []
        
        try:
            for cache_key, similarity_keys in self._similarity_keys.items():
                # Calculate similarity using smart matcher
                max_similarity = 0.0
                
                for sim_key in similarity_keys:
                    similarity = smart_cache_matcher.calculate_similarity(query, sim_key)
                    max_similarity = max(max_similarity, similarity)
                
                if max_similarity >= threshold:
                    similar_keys.append((cache_key, max_similarity))

            # Sort by similarity (descending)
            similar_keys.sort(key=lambda x: x[1], reverse=True)
            
        except Exception as e:
            logger.warning(f"Failed to find similar keys for query '{query}': {e}")

        return similar_keys

    def update_similarity_keys(self, key: str, value: Any) -> None:
        """Update similarity keys for a cache entry.

        Args:
            key: Cache key
            value: Updated value
        """
        # Remove old keys
        self.remove_similarity_keys(key)
        
        # Store new keys
        self.store_similarity_keys(key, value)

    def clear_all_similarity_keys(self) -> None:
        """Clear all similarity keys."""
        self._similarity_keys.clear()
        logger.info("Cleared all similarity keys")

    def get_similarity_stats(self) -> Dict[str, Any]:
        """Get similarity key statistics.

        Returns:
            Similarity key statistics
        """
        total_keys = len(self._similarity_keys)
        total_similarity_keys = sum(len(keys) for keys in self._similarity_keys.values())
        
        return {
            "total_cache_keys": total_keys,
            "total_similarity_keys": total_similarity_keys,
            "average_similarity_keys_per_entry": total_similarity_keys / total_keys if total_keys > 0 else 0,
            "similarity_key_coverage": len(self._similarity_keys) / total_keys if total_keys > 0 else 0
        }

    def _generate_similarity_keys(self, value: Any) -> Set[str]:
        """Generate similarity keys for a value.

        Args:
            value: Value to generate keys for

        Returns:
            Set of similarity keys
        """
        similarity_keys = set()
        
        try:
            # Generate keys based on value type and content
            if hasattr(value, 'title'):
                title = getattr(value, 'title', '')
                if title:
                    # Add title variations
                    similarity_keys.add(title.lower())
                    similarity_keys.add(title.replace(' ', '').lower())
                    similarity_keys.add(title.replace('-', ' ').lower())
                    
                    # Add partial titles
                    words = title.split()
                    for i in range(len(words)):
                        partial = ' '.join(words[:i+1])
                        if len(partial) > 2:
                            similarity_keys.add(partial.lower())

            if hasattr(value, 'original_title'):
                original_title = getattr(value, 'original_title', '')
                if original_title and original_title != getattr(value, 'title', ''):
                    similarity_keys.add(original_title.lower())
                    similarity_keys.add(original_title.replace(' ', '').lower())

            if hasattr(value, 'file_path'):
                file_path = getattr(value, 'file_path', '')
                if file_path:
                    # Extract filename without extension
                    import os
                    filename = os.path.splitext(os.path.basename(file_path))[0]
                    similarity_keys.add(filename.lower())
                    similarity_keys.add(filename.replace('_', ' ').lower())
                    similarity_keys.add(filename.replace('-', ' ').lower())

            # Add season/episode information if available
            if hasattr(value, 'season') and hasattr(value, 'episode'):
                season = getattr(value, 'season', None)
                episode = getattr(value, 'episode', None)
                if season is not None and episode is not None:
                    similarity_keys.add(f"s{season:02d}e{episode:02d}")
                    similarity_keys.add(f"season {season} episode {episode}")

            # Add year information if available
            if hasattr(value, 'year'):
                year = getattr(value, 'year', None)
                if year:
                    similarity_keys.add(str(year))

            # Add quality information if available
            if hasattr(value, 'quality'):
                quality = getattr(value, 'quality', '')
                if quality:
                    similarity_keys.add(quality.lower())

        except Exception as e:
            logger.warning(f"Failed to generate similarity keys for value: {e}")

        return similarity_keys

    def get_keys_by_similarity_pattern(self, pattern: str) -> List[str]:
        """Get cache keys that match a similarity pattern.

        Args:
            pattern: Pattern to match

        Returns:
            List of matching cache keys
        """
        matching_keys = []
        pattern_lower = pattern.lower()
        
        try:
            for cache_key, similarity_keys in self._similarity_keys.items():
                for sim_key in similarity_keys:
                    if pattern_lower in sim_key or sim_key in pattern_lower:
                        matching_keys.append(cache_key)
                        break
                        
        except Exception as e:
            logger.warning(f"Failed to get keys by similarity pattern '{pattern}': {e}")

        return matching_keys

    def get_similarity_key_coverage(self) -> Dict[str, float]:
        """Get similarity key coverage statistics.

        Returns:
            Coverage statistics by key type
        """
        coverage = {
            "title_coverage": 0.0,
            "file_path_coverage": 0.0,
            "season_episode_coverage": 0.0,
            "year_coverage": 0.0,
            "quality_coverage": 0.0
        }
        
        if not self._similarity_keys:
            return coverage

        total_keys = len(self._similarity_keys)
        title_keys = 0
        file_path_keys = 0
        season_episode_keys = 0
        year_keys = 0
        quality_keys = 0

        for similarity_keys in self._similarity_keys.values():
            for sim_key in similarity_keys:
                if any(char.isdigit() for char in sim_key) and ('s' in sim_key or 'e' in sim_key):
                    season_episode_keys += 1
                elif sim_key.isdigit() and len(sim_key) == 4:
                    year_keys += 1
                elif any(quality in sim_key for quality in ['720p', '1080p', '4k', 'hd', 'sd']):
                    quality_keys += 1
                elif '.' in sim_key or '/' in sim_key or '\\' in sim_key:
                    file_path_keys += 1
                else:
                    title_keys += 1

        coverage["title_coverage"] = title_keys / total_keys if total_keys > 0 else 0.0
        coverage["file_path_coverage"] = file_path_keys / total_keys if total_keys > 0 else 0.0
        coverage["season_episode_coverage"] = season_episode_keys / total_keys if total_keys > 0 else 0.0
        coverage["year_coverage"] = year_keys / total_keys if total_keys > 0 else 0.0
        coverage["quality_coverage"] = quality_keys / total_keys if total_keys > 0 else 0.0

        return coverage
