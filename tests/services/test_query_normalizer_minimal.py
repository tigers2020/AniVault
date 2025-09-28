"""Minimal tests for query normalizer."""

from anivault.services.query_normalizer import QueryNormalizer


class TestQueryNormalizerMinimal:
    """Minimal test cases for QueryNormalizer."""

    def test_normalize_query_basic_cleaning(self):
        """Test basic query cleaning."""
        normalizer = QueryNormalizer()

        # Test basic cleaning
        result = normalizer.normalize_query("Attack on Titan (TV)")
        assert result == "Attack on Titan"

        # Test season removal
        result = normalizer.normalize_query("One Piece Season 1")
        assert result == "One Piece"

        # Test episode removal
        result = normalizer.normalize_query("Naruto Episode 1")
        assert result == "Naruto"

        # Test that exact matches get converted to variations
        result = normalizer.normalize_query("Attack on Titan")
        assert result == "Shingeki no Kyojin"

        # Test non-variation titles
        result = normalizer.normalize_query("Unknown Anime")
        assert result == "Unknown Anime"

    def test_normalize_query_variations(self):
        """Test title variations."""
        normalizer = QueryNormalizer()

        # Test title variation (exact match)
        result = normalizer.normalize_query("Attack on Titan")
        assert result == "Shingeki no Kyojin"

        # Test another variation
        result = normalizer.normalize_query("Bleach")
        assert result == "ブリーチ"

        # Test non-variation titles
        result = normalizer.normalize_query("Unknown Anime")
        assert result == "Unknown Anime"

    def test_calculate_similarity_exact(self):
        """Test exact similarity calculation."""
        normalizer = QueryNormalizer()

        # Exact match
        similarity = normalizer.calculate_similarity(
            "Attack on Titan",
            "Attack on Titan",
        )
        assert similarity == 1.0

        # No match
        similarity = normalizer.calculate_similarity("Attack on Titan", "One Piece")
        assert similarity == 0.0

    def test_generate_query_variants(self):
        """Test query variant generation."""
        normalizer = QueryNormalizer()

        variants = normalizer.generate_query_variants("Attack on Titan")
        assert "Attack on Titan" in variants
        assert len(variants) >= 1

    def test_get_stats(self):
        """Test statistics retrieval."""
        normalizer = QueryNormalizer()
        stats = normalizer.get_stats()

        assert "patterns_count" in stats
        assert "variations_count" in stats
        assert stats["patterns_count"] > 0
        assert stats["variations_count"] > 0
