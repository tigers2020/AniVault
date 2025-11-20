"""Tests for the normalization module."""

from __future__ import annotations

import pytest

from anivault.core.normalization import (
    _detect_language,
    _extract_title_from_anitopy,
    _normalize_characters,
    _remove_metadata,
    normalize_query,
)


class TestNormalizeQuery:
    """Test the main normalize_query function."""

    def test_normalize_basic_english_title(self):
        """Test normalizing a basic English anime title."""
        filename = "[SubsPlease] Attack on Titan - 01 (1080p).mkv"
        title, language = normalize_query(filename)

        assert title == "Attack on Titan"
        assert language == "en"

    def test_normalize_japanese_title(self):
        """Test normalizing a Japanese anime title."""
        filename = "進撃の巨人 - 01 [1080p].mkv"
        title, language = normalize_query(filename)

        assert "進撃の巨人" in title
        assert language == "ja"

    def test_normalize_korean_title(self):
        """Test normalizing a Korean anime title."""
        filename = "신의 탑 - 01 [1080p].mkv"
        title, language = normalize_query(filename)

        assert "신의 탑" in title
        assert language == "ko"

    def test_normalize_with_fallback(self):
        """Test normalizing when anitopy fails."""
        # This should trigger fallback processing
        filename = "invalid filename with no structure"
        title, language = normalize_query(filename)

        assert isinstance(title, str)
        assert isinstance(language, str)
        assert language in ["ja", "ko", "en", "unknown"]


class TestExtractTitleFromAnitopy:
    """Test the _extract_title_from_anitopy function."""

    def test_extract_anime_title(self):
        """Test extracting anime_title from anitopy results."""
        parsed_data = {"anime_title": "Attack on Titan"}
        title = _extract_title_from_anitopy(parsed_data)

        assert title == "Attack on Titan"

    def test_extract_title_with_whitespace(self):
        """Test extracting title with extra whitespace."""
        parsed_data = {"anime_title": "  Attack on Titan  "}
        title = _extract_title_from_anitopy(parsed_data)

        assert title == "Attack on Titan"

    def test_extract_title_fallback_fields(self):
        """Test extracting title from fallback fields."""
        parsed_data = {"title": "Attack on Titan"}
        title = _extract_title_from_anitopy(parsed_data)

        assert title == "Attack on Titan"

    def test_extract_title_empty_result(self):
        """Test handling empty or missing title."""
        parsed_data = {}
        title = _extract_title_from_anitopy(parsed_data)

        assert title == ""

    def test_extract_title_none_value(self):
        """Test handling None title value."""
        parsed_data = {"anime_title": None}
        title = _extract_title_from_anitopy(parsed_data)

        assert title == ""


class TestRemoveMetadata:
    """Test the _remove_metadata function."""

    def test_remove_resolution_patterns(self):
        """Test removing resolution patterns."""
        title = "Attack on Titan [1080p] (720p)"
        cleaned = _remove_metadata(title)

        assert cleaned == "Attack on Titan"

    def test_remove_codec_patterns(self):
        """Test removing codec patterns."""
        title = "Attack on Titan [x264] (HEVC)"
        cleaned = _remove_metadata(title)

        assert cleaned == "Attack on Titan"

    def test_remove_release_group_patterns(self):
        """Test removing release group patterns."""
        title = "Attack on Titan [SubsPlease] (EMBER)"
        cleaned = _remove_metadata(title)

        assert cleaned == "Attack on Titan"

    def test_remove_episode_patterns(self):
        """Test removing episode patterns."""
        title = "Attack on Titan [E01] (Episode 1)"
        cleaned = _remove_metadata(title)

        assert cleaned == "Attack on Titan"

    def test_remove_season_patterns(self):
        """Test removing season patterns."""
        title = "Attack on Titan [S01] (Season 1)"
        cleaned = _remove_metadata(title)

        assert cleaned == "Attack on Titan"

    def test_remove_source_patterns(self):
        """Test removing source patterns."""
        title = "Attack on Titan [BluRay] (WEB)"
        cleaned = _remove_metadata(title)

        assert cleaned == "Attack on Titan"

    def test_remove_audio_patterns(self):
        """Test removing audio patterns."""
        title = "Attack on Titan [AAC] (5.1)"
        cleaned = _remove_metadata(title)

        assert cleaned == "Attack on Titan"

    def test_remove_hash_patterns(self):
        """Test removing hash patterns."""
        title = "Attack on Titan [12345678] (ABCDEFGH)"
        cleaned = _remove_metadata(title)

        assert cleaned == "Attack on Titan"

    def test_remove_multiple_patterns(self):
        """Test removing multiple types of patterns."""
        title = "[SubsPlease] Attack on Titan - 01 [1080p] [x264] [AAC].mkv"
        cleaned = _remove_metadata(title)

        assert cleaned == "Attack on Titan"

    def test_handle_empty_title(self):
        """Test handling empty title."""
        title = ""
        cleaned = _remove_metadata(title)

        assert cleaned == ""

    def test_handle_none_title(self):
        """Test handling None title."""
        title = None
        cleaned = _remove_metadata(title)

        assert cleaned is None


class TestNormalizeCharacters:
    """Test the _normalize_characters function."""

    def test_unicode_normalization(self):
        """Test Unicode normalization."""
        title = "Attack on Titan"  # Already normalized
        normalized = _normalize_characters(title)

        assert normalized == "Attack on Titan"

    def test_fullwidth_to_halfwidth_conversion(self):
        """Test converting full-width characters to half-width."""
        title = "Attack on Titan（1080p）"
        normalized = _normalize_characters(title)

        assert normalized == "Attack on Titan(1080p)"

    def test_bracket_standardization(self):
        """Test standardizing different bracket types."""
        title = "Attack on Titan【1080p】"
        normalized = _normalize_characters(title)

        assert normalized == "Attack on Titan[1080p]"

    def test_whitespace_cleanup(self):
        """Test cleaning up extra whitespace."""
        title = "Attack  on   Titan"
        normalized = _normalize_characters(title)

        assert normalized == "Attack on Titan"

    def test_handle_empty_title(self):
        """Test handling empty title."""
        title = ""
        normalized = _normalize_characters(title)

        assert normalized == ""

    def test_handle_none_title(self):
        """Test handling None title."""
        title = None
        normalized = _normalize_characters(title)

        assert normalized is None


class TestDetectLanguage:
    """Test the _detect_language function."""

    def test_detect_japanese_hiragana(self):
        """Test detecting Japanese with hiragana."""
        title = "あたっくおんたいたん"
        language = _detect_language(title)

        assert language == "ja"

    def test_detect_japanese_katakana(self):
        """Test detecting Japanese with katakana."""
        title = "アタックオンタイタン"
        language = _detect_language(title)

        assert language == "ja"

    def test_detect_japanese_kanji(self):
        """Test detecting Japanese with kanji."""
        title = "進撃の巨人"
        language = _detect_language(title)

        assert language == "ja"

    def test_detect_japanese_mixed(self):
        """Test detecting Japanese with mixed characters."""
        title = "進撃の巨人 アタックオンタイタン"
        language = _detect_language(title)

        assert language == "ja"

    def test_detect_korean(self):
        """Test detecting Korean."""
        title = "신의 탑"
        language = _detect_language(title)

        assert language == "ko"

    def test_detect_english(self):
        """Test detecting English."""
        title = "Attack on Titan"
        language = _detect_language(title)

        assert language == "en"

    def test_detect_english_mixed(self):
        """Test detecting English with numbers and symbols."""
        title = "Attack on Titan S01E01"
        language = _detect_language(title)

        assert language == "en"

    def test_detect_unknown_empty(self):
        """Test detecting unknown language for empty string."""
        title = ""
        language = _detect_language(title)

        assert language == "unknown"

    def test_detect_unknown_none(self):
        """Test detecting unknown language for None."""
        title = None
        language = _detect_language(title)

        assert language == "unknown"

    def test_detect_unknown_symbols(self):
        """Test detecting unknown language for symbols only."""
        title = "!@#$%^&*()"
        language = _detect_language(title)

        assert language == "unknown"

    def test_detect_ambiguous_case(self):
        """Test detecting language in ambiguous cases."""
        # Mixed content that doesn't meet thresholds
        title = "Attack 巨人 Titan"
        language = _detect_language(title)

        # Should detect based on presence of specific characters
        assert language in ["ja", "en"]


class TestIntegration:
    """Integration tests for the normalization pipeline."""

    def test_full_pipeline_english(self):
        """Test the complete normalization pipeline with English content."""
        filename = "[SubsPlease] Attack on Titan - 01 (1080p) [x264] [AAC].mkv"
        title, language = normalize_query(filename)

        assert title == "Attack on Titan"
        assert language == "en"

    def test_full_pipeline_japanese(self):
        """Test the complete normalization pipeline with Japanese content."""
        filename = "【SubsPlease】進撃の巨人 - 01 [1080p] [x264].mkv"
        title, language = normalize_query(filename)

        assert "進撃の巨人" in title
        assert language == "ja"

    def test_full_pipeline_korean(self):
        """Test the complete normalization pipeline with Korean content."""
        filename = "[SubsPlease] 신의 탑 - 01 (1080p) [x264].mkv"
        title, language = normalize_query(filename)

        assert "신의 탑" in title
        assert language == "ko"

    def test_full_pipeline_complex_metadata(self):
        """Test the complete pipeline with complex metadata patterns."""
        filename = "[HorribleSubs] One Piece - 1000 [1080p] [x265] [AAC] [5.1] [BluRay] [12345678].mkv"
        title, language = normalize_query(filename)

        assert title == "One Piece"
        assert language == "en"

    def test_full_pipeline_edge_cases(self):
        """Test the complete pipeline with edge cases."""
        # Test with minimal content
        filename = "Anime.mkv"
        title, language = normalize_query(filename)

        assert title == "Anime"
        assert language == "en"

        # Test with no structure
        filename = "random text without structure"
        title, language = normalize_query(filename)

        assert isinstance(title, str)
        assert isinstance(language, str)
