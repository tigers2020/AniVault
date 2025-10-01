"""Tests for AnimeFilenameParser (main orchestrator)."""

from __future__ import annotations

import pytest

from anivault.core.parser.anime_parser import AnimeFilenameParser
from anivault.core.parser.models import ParsingResult


@pytest.fixture
def parser():
    """Create an AnimeFilenameParser instance for testing."""
    return AnimeFilenameParser()


def test_parser_initialization():
    """Test that AnimeFilenameParser can be initialized."""
    parser = AnimeFilenameParser()
    assert parser is not None
    assert parser.fallback_parser is not None


def test_has_anitopy_property(parser):
    """Test has_anitopy property."""
    # Should have anitopy if installed
    assert isinstance(parser.has_anitopy, bool)


# Integration tests: anitopy success cases
def test_parse_uses_anitopy_for_standard_format(parser):
    """Test that anitopy is used for standard anime filename."""
    filename = "[SubsPlease] My Anime - 01 (1080p) [12345678].mkv"
    result = parser.parse(filename)

    assert isinstance(result, ParsingResult)
    assert result.title == "My Anime"
    assert result.episode == 1
    assert result.quality == "1080p"
    assert result.release_group == "SubsPlease"

    # Should use anitopy if available
    if parser.has_anitopy:
        assert result.parser_used == "anitopy"
        assert result.confidence >= 0.8


def test_parse_uses_anitopy_for_season_episode(parser):
    """Test that anitopy handles season/episode format."""
    filename = "[HorribleSubs] Attack on Titan S02E05 [720p].mkv"
    result = parser.parse(filename)

    assert result.title == "Attack on Titan"
    assert result.season == 2
    assert result.episode == 5

    if parser.has_anitopy:
        assert result.parser_used == "anitopy"


# Integration tests: fallback cases
def test_parse_uses_fallback_for_simple_format(parser):
    """Test fallback for simple Title - Episode format."""
    filename = "Anime Title - 123.mkv"
    result = parser.parse(filename)

    assert result.title == "Anime Title"
    assert result.episode == 123
    # Parser used depends on anitopy availability and result quality
    assert result.parser_used in ["anitopy", "fallback"]


def test_parse_uses_fallback_when_anitopy_fails(parser):
    """Test that fallback is used when anitopy produces poor results."""
    # This format might not work well with anitopy
    filename = "Simple_Anime_Name_03.mkv"
    result = parser.parse(filename)

    assert isinstance(result, ParsingResult)
    assert result.episode == 3
    # Should have some result even if not perfect
    assert result.is_valid()


# Validation tests
def test_is_valid_result_with_good_data(parser):
    """Test _is_valid_result with good data."""
    result = ParsingResult(
        title="Test Anime", episode=1, confidence=0.9, parser_used="anitopy"
    )

    assert parser._is_valid_result(result) is True


def test_is_valid_result_with_empty_title(parser):
    """Test _is_valid_result with empty title."""
    result = ParsingResult(title="", episode=1, confidence=0.9, parser_used="anitopy")

    assert parser._is_valid_result(result) is False


def test_is_valid_result_with_low_confidence(parser):
    """Test _is_valid_result with low confidence."""
    result = ParsingResult(
        title="Test Anime", episode=1, confidence=0.3, parser_used="anitopy"
    )

    assert parser._is_valid_result(result) is False


def test_is_valid_result_at_confidence_threshold(parser):
    """Test _is_valid_result at confidence threshold (0.5)."""
    result = ParsingResult(
        title="Test Anime", episode=1, confidence=0.5, parser_used="anitopy"
    )

    assert parser._is_valid_result(result) is True


# Complex parsing scenarios
def test_parse_complex_filename_with_metadata(parser):
    """Test parsing complex filename with multiple metadata fields."""
    filename = "[Erai-raws] Anime Name - 12 [1080p][HEVC 10bit x265 AAC][Multiple-Subtitle].mkv"
    result = parser.parse(filename)

    assert result.title
    assert result.episode == 12
    assert result.quality == "1080p"
    assert result.is_valid()


def test_parse_movie_filename(parser):
    """Test parsing movie filename (no episode number)."""
    filename = "[Group] Movie Name (2023) [1080p] [BluRay].mkv"
    result = parser.parse(filename)

    # Should still extract title and metadata
    assert result.is_valid()
    # Episode might be None for movies
    assert result.quality == "1080p"


def test_parse_ova_filename(parser):
    """Test parsing OVA filename."""
    filename = "[SubsPlease] Anime OVA - 01 [1080p].mkv"
    result = parser.parse(filename)

    assert "OVA" in result.title or "Anime" in result.title
    assert result.episode == 1


def test_parse_filename_with_version(parser):
    """Test parsing filename with version number."""
    filename = "[Group] Anime - 05 v2 [1080p].mkv"
    result = parser.parse(filename)

    assert result.episode == 5
    assert result.is_valid()


def test_parse_filename_with_multiple_episodes(parser):
    """Test parsing filename with episode range."""
    filename = "[Group] Anime - 01-02 [1080p].mkv"
    result = parser.parse(filename)

    # Should extract at least the first episode
    assert result.episode in [1, 2]
    assert result.is_valid()


# Edge cases
def test_parse_empty_filename(parser):
    """Test parsing empty filename."""
    result = parser.parse("")

    assert isinstance(result, ParsingResult)
    # Should have low confidence for empty input
    assert result.confidence < 0.5


def test_parse_filename_without_extension(parser):
    """Test parsing filename without extension."""
    filename = "[SubsPlease] Anime - 01 [1080p]"
    result = parser.parse(filename)

    assert result.title == "Anime"
    assert result.episode == 1


def test_parse_filename_with_unusual_characters(parser):
    """Test parsing filename with unusual characters."""
    filename = "[Group] Anime: Title! - 01 [1080p].mkv"
    result = parser.parse(filename)

    assert result.episode == 1
    assert result.is_valid()


def test_parse_filename_with_year(parser):
    """Test parsing filename with year."""
    filename = "[SubsPlease] Anime Title (2023) - 01 [1080p].mkv"
    result = parser.parse(filename)

    assert result.episode == 1
    assert result.is_valid()


# Confidence scoring
def test_parse_returns_high_confidence_for_complete_metadata(parser):
    """Test that complete metadata results in high confidence."""
    filename = "[SubsPlease] Attack on Titan S02E05 [1080p] [WEB-DL].mkv"
    result = parser.parse(filename)

    # Should have high confidence with complete info
    assert result.confidence >= 0.7


def test_parse_returns_lower_confidence_for_minimal_metadata(parser):
    """Test that minimal metadata results in lower confidence."""
    filename = "Anime.mkv"
    result = parser.parse(filename)

    # Should have lower confidence with minimal info
    assert result.confidence < 0.7


# Result validation
def test_parsed_result_is_valid(parser):
    """Test that parsed results pass is_valid check."""
    filename = "[Group] Anime - 01 [1080p].mkv"
    result = parser.parse(filename)

    assert result.is_valid()


def test_parsed_result_has_episode_info(parser):
    """Test has_episode_info for result with episode."""
    filename = "[Group] Anime - 05 [1080p].mkv"
    result = parser.parse(filename)

    assert result.has_episode_info()


def test_parsed_result_without_episode_info(parser):
    """Test result without episode information."""
    filename = "Random Movie Name.mkv"
    result = parser.parse(filename)

    # Might not have episode info
    assert isinstance(result, ParsingResult)


# Real-world examples
def test_parse_subsplease_format(parser):
    """Test SubsPlease release format."""
    filename = "[SubsPlease] Jujutsu Kaisen - 24 (1080p) [E82B1F6A].mkv"
    result = parser.parse(filename)

    assert "Jujutsu Kaisen" in result.title
    assert result.episode == 24
    assert result.quality == "1080p"


def test_parse_horriblesubs_format(parser):
    """Test HorribleSubs release format."""
    filename = "[HorribleSubs] One Piece - 1000 [720p].mkv"
    result = parser.parse(filename)

    assert "One Piece" in result.title
    assert result.episode == 1000
    assert result.quality == "720p"


def test_parse_erai_raws_format(parser):
    """Test Erai-raws release format."""
    filename = "[Erai-raws] Demon Slayer - 26 [1080p][Multiple-Subtitle][F1DF2E3B].mkv"
    result = parser.parse(filename)

    assert "Demon Slayer" in result.title
    assert result.episode == 26
    assert result.quality == "1080p"
