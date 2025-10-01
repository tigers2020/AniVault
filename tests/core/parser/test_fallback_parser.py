"""Tests for FallbackParser."""

from __future__ import annotations

import pytest

from anivault.core.parser.fallback_parser import FallbackParser
from anivault.core.parser.models import ParsingResult


@pytest.fixture
def parser():
    """Create a FallbackParser instance for testing."""
    return FallbackParser()


def test_parser_initialization():
    """Test that FallbackParser can be initialized."""
    parser = FallbackParser()
    assert parser is not None


# Pattern 1 tests: [Group] Title - Episode
def test_parse_pattern1_basic(parser):
    """Test parsing with pattern 1: [Group] Title - Episode."""
    filename = "[SubsPlease] My Anime - 01 [1080p].mkv"
    result = parser.parse(filename)

    assert result.title == "My Anime"
    assert result.episode == 1
    assert result.release_group == "SubsPlease"
    assert result.quality == "1080p"
    assert result.parser_used == "fallback"


def test_parse_pattern1_with_version(parser):
    """Test parsing with pattern 1 including version."""
    filename = "[HorribleSubs] Anime Title - 05 v2 [720p].mkv"
    result = parser.parse(filename)

    assert result.title == "Anime Title"
    assert result.episode == 5
    assert result.release_group == "HorribleSubs"


# Pattern 2 tests: Title S##E##
def test_parse_pattern2_season_episode(parser):
    """Test parsing with pattern 2: Title S##E##."""
    filename = "Attack on Titan S02E05 [1080p].mkv"
    result = parser.parse(filename)

    assert result.title == "Attack on Titan"
    assert result.season == 2
    assert result.episode == 5
    assert result.quality == "1080p"


def test_parse_pattern2_lowercase(parser):
    """Test parsing with pattern 2 using lowercase."""
    filename = "my anime s01e03 [720p].mkv"
    result = parser.parse(filename)

    assert result.title == "my anime"
    assert result.season == 1
    assert result.episode == 3


# Pattern 3 tests: Title - ##
def test_parse_pattern3_simple(parser):
    """Test parsing with pattern 3: Title - ##."""
    filename = "One Piece - 1001.mkv"
    result = parser.parse(filename)

    assert result.title == "One Piece"
    assert result.episode == 1001


def test_parse_pattern3_with_quality(parser):
    """Test parsing with pattern 3 including quality."""
    filename = "Naruto - 220 [1080p].mkv"
    result = parser.parse(filename)

    assert result.title == "Naruto"
    assert result.episode == 220
    assert result.quality == "1080p"


# Pattern 4 tests: Title EP## or Title Episode ##
def test_parse_pattern4_ep(parser):
    """Test parsing with pattern 4: Title EP##."""
    filename = "Bleach EP100 [BluRay].mkv"
    result = parser.parse(filename)

    assert result.title == "Bleach"
    assert result.episode == 100
    assert result.source == "BluRay"


def test_parse_pattern4_episode(parser):
    """Test parsing with pattern 4: Title Episode ##."""
    filename = "Hunter x Hunter Episode 05.mkv"
    result = parser.parse(filename)

    assert result.title == "Hunter x Hunter"
    assert result.episode == 5


# Pattern 5 tests: Title_##
def test_parse_pattern5_underscore(parser):
    """Test parsing with pattern 5: Title_##."""
    filename = "My_Anime_Title_03.mkv"
    result = parser.parse(filename)

    assert "Anime" in result.title or "My" in result.title
    assert result.episode == 3


# Pattern 6 tests: Title.##
def test_parse_pattern6_dot(parser):
    """Test parsing with pattern 6: Title.##."""
    filename = "Anime.Name.12.mkv"
    result = parser.parse(filename)

    assert "Anime" in result.title
    assert result.episode == 12


# Secondary information extraction tests
def test_extract_quality_various_resolutions(parser):
    """Test quality extraction for various resolutions."""
    test_cases = [
        ("Anime - 01 [2160p].mkv", "2160p"),
        ("Anime - 01 [1080p].mkv", "1080p"),
        ("Anime - 01 [720p].mkv", "720p"),
        ("Anime - 01 [480p].mkv", "480p"),
        ("Anime - 01 [360p].mkv", "360p"),
    ]

    for filename, expected_quality in test_cases:
        result = parser.parse(filename)
        assert result.quality == expected_quality


def test_extract_source_various_types(parser):
    """Test source extraction for various source types."""
    test_cases = [
        ("Anime - 01 [BluRay].mkv", "BluRay"),
        ("Anime - 01 [Blu-ray].mkv", "Blu-ray"),
        ("Anime - 01 [BDRip].mkv", "BDRip"),
        ("Anime - 01 [WEB-DL].mkv", "WEB-DL"),
        ("Anime - 01 [WEBRip].mkv", "WEBRip"),
        ("Anime - 01 [HDTV].mkv", "HDTV"),
    ]

    for filename, expected_source in test_cases:
        result = parser.parse(filename)
        assert result.source == expected_source


def test_extract_codec_various_types(parser):
    """Test codec extraction for various codec types."""
    test_cases = [
        ("Anime - 01 [H.264].mkv", "H.264"),
        ("Anime - 01 [H.265].mkv", "H.265"),
        ("Anime - 01 [HEVC].mkv", "HEVC"),
        ("Anime - 01 [x264].mkv", "x264"),
        ("Anime - 01 [x265].mkv", "x265"),
        ("Anime - 01 [10bit].mkv", "10bit"),
    ]

    for filename, expected_codec in test_cases:
        result = parser.parse(filename)
        assert result.codec == expected_codec


def test_extract_audio_various_types(parser):
    """Test audio extraction for various audio types."""
    test_cases = [
        ("Anime - 01 [AAC].mkv", "AAC"),
        ("Anime - 01 [FLAC].mkv", "FLAC"),
        ("Anime - 01 [5.1].mkv", "5.1"),
        ("Anime - 01 [2.0].mkv", "2.0"),
    ]

    for filename, expected_audio in test_cases:
        result = parser.parse(filename)
        assert result.audio == expected_audio


def test_extract_multiple_metadata(parser):
    """Test extraction of multiple metadata fields at once."""
    filename = "[SubsPlease] Anime - 05 [1080p] [WEB-DL] [H.264] [AAC].mkv"
    result = parser.parse(filename)

    assert result.title == "Anime"
    assert result.episode == 5
    assert result.quality == "1080p"
    assert result.source == "WEB-DL"
    assert result.codec == "H.264"
    assert result.audio == "AAC"
    assert result.release_group == "SubsPlease"


# Edge cases and error handling
def test_parse_no_match(parser):
    """Test parsing when no pattern matches."""
    filename = "random_string_without_patterns.mkv"
    result = parser.parse(filename)

    # Should return the filename as title with low confidence
    assert result.title == filename
    assert result.confidence < 0.5
    assert result.parser_used == "fallback"


def test_parse_empty_filename(parser):
    """Test parsing with empty filename."""
    result = parser.parse("")

    assert isinstance(result, ParsingResult)
    assert result.confidence < 0.5


def test_parse_leading_zeros_in_episode(parser):
    """Test that leading zeros in episode numbers are handled."""
    filename = "Anime - 001 [1080p].mkv"
    result = parser.parse(filename)

    assert result.episode == 1


def test_parse_leading_zeros_in_season(parser):
    """Test that leading zeros in season numbers are handled."""
    filename = "Anime S01E05.mkv"
    result = parser.parse(filename)

    assert result.season == 1
    assert result.episode == 5


# Title cleaning tests
def test_clean_title_removes_trailing_separators(parser):
    """Test that title cleaning removes trailing separators."""
    filename = "[Group] Anime. Title... - 01.mkv"
    result = parser.parse(filename)

    # Title should not have trailing dots
    assert not result.title.endswith(".")


def test_clean_title_replaces_underscores(parser):
    """Test that underscores in titles are replaced with spaces."""
    filename = "My_Anime_Title - 01.mkv"
    result = parser.parse(filename)

    # Underscores should be replaced with spaces
    assert "_" not in result.title or result.title == filename


def test_clean_title_removes_multiple_spaces(parser):
    """Test that multiple consecutive spaces are collapsed."""
    filename = "Anime  Title - 01.mkv"
    result = parser.parse(filename)

    # Should not have multiple consecutive spaces
    assert "  " not in result.title


# Confidence scoring tests
def test_confidence_high_with_all_info(parser):
    """Test confidence is high when all information is present."""
    filename = "[Group] Anime S01E05 [1080p] [BluRay] [H.264].mkv"
    result = parser.parse(filename)

    # Should have high confidence with title, season, episode, and metadata
    assert result.confidence >= 0.8


def test_confidence_medium_with_partial_info(parser):
    """Test confidence is medium with partial information."""
    filename = "Anime - 05.mkv"
    result = parser.parse(filename)

    # Should have medium confidence with just title and episode
    assert 0.5 <= result.confidence < 0.8


def test_confidence_low_with_minimal_info(parser):
    """Test confidence is low with minimal information."""
    filename = "random_file.mkv"
    result = parser.parse(filename)

    # Should have low confidence when no pattern matches
    assert result.confidence < 0.5


def test_result_is_valid(parser):
    """Test that result with title is valid."""
    filename = "[Group] Valid Anime - 01.mkv"
    result = parser.parse(filename)

    assert result.is_valid()


def test_result_has_episode_info(parser):
    """Test has_episode_info helper method."""
    filename = "Anime - 05.mkv"
    result = parser.parse(filename)

    assert result.has_episode_info()


def test_result_without_episode_info(parser):
    """Test parsing without episode information."""
    filename = "Movie Name.mkv"
    result = parser.parse(filename)

    # Might not have episode info if no pattern matches
    assert isinstance(result, ParsingResult)


def test_complex_title_extraction(parser):
    """Test extraction of complex anime titles."""
    filename = "[Group] Anime Title: The Adventure Continues - 03 [720p].mkv"
    result = parser.parse(filename)

    assert result.episode == 3
    assert len(result.title) > 0
    assert "Anime Title" in result.title or "Adventure" in result.title
