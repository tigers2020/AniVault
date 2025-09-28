"""Tests for query normalizer."""

from anivault.services.query_normalizer import QueryNormalizer


class TestQueryNormalizer:
    """Test cases for QueryNormalizer."""

    def test_normalize_query_basic(self):
        """Test basic query normalization."""
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

        # Test title variation (exact match)
        result = normalizer.normalize_query("Attack on Titan")
        assert result == "Shingeki no Kyojin"

        # Test non-variation titles
        result = normalizer.normalize_query("Unknown Anime")
        assert result == "Unknown Anime"

    def test_normalize_query_anime_patterns(self):
        """Test anime-specific pattern cleaning."""
        normalizer = QueryNormalizer()

        # Test OVA removal
        result = normalizer.normalize_query("Bleach (OVA)")
        assert result == "Bleach"

        # Test quality indicator removal
        result = normalizer.normalize_query("Death Note 1080p")
        assert result == "Death Note"

        # Test release group removal
        result = normalizer.normalize_query("Fullmetal Alchemist [Fansub]")
        assert result == "Fullmetal Alchemist"

        # Test title variation (exact match)
        result = normalizer.normalize_query("Bleach")
        assert result == "ブリーチ"

        # Test non-variation titles
        result = normalizer.normalize_query("Unknown Anime")
        assert result == "Unknown Anime"

    def test_normalize_query_unicode(self):
        """Test Unicode normalization."""
        normalizer = QueryNormalizer()

        # Test Unicode normalization
        result = normalizer.normalize_query("鬼滅の刃")
        assert result == "鬼滅の刃"

        # Test extra whitespace
        result = normalizer.normalize_query("  Hunter x Hunter  ")
        assert result == "Hunter x Hunter"

        # Test title variation (exact match)
        result = normalizer.normalize_query("Hunter x Hunter")
        assert result == "ハンター×ハンター"

        # Test non-variation titles
        result = normalizer.normalize_query("Unknown Anime")
        assert result == "Unknown Anime"

    def test_generate_query_variants(self):
        """Test query variant generation."""
        normalizer = QueryNormalizer()

        variants = normalizer.generate_query_variants("Attack on Titan")
        assert "Attack on Titan" in variants
        assert len(variants) >= 1

        # Test with year
        variants = normalizer.generate_query_variants("One Piece 1999")
        assert "One Piece 1999" in variants
        assert "One Piece" in variants

    def test_calculate_similarity(self):
        """Test similarity calculation."""
        normalizer = QueryNormalizer()

        # Exact match
        similarity = normalizer.calculate_similarity(
            "Attack on Titan",
            "Attack on Titan",
        )
        assert similarity == 1.0

        # Partial match (substring)
        similarity = normalizer.calculate_similarity("Attack", "Attack on Titan")
        assert similarity >= 0.5  # Should be at least 0.5 due to substring match

        # No match
        similarity = normalizer.calculate_similarity("Attack on Titan", "One Piece")
        assert similarity == 0.0

    def test_get_stats(self):
        """Test statistics retrieval."""
        normalizer = QueryNormalizer()
        stats = normalizer.get_stats()

        assert "patterns_count" in stats
        assert "variations_count" in stats
        assert stats["patterns_count"] > 0
        assert stats["variations_count"] > 0
