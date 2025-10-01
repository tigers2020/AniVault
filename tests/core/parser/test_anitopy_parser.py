"""Tests for AnitopyParser."""

from __future__ import annotations

import pytest

from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.core.parser.models import ParsingResult

# Check if anitopy is available
try:
    import anitopy

    ANITOPY_AVAILABLE = True
except ImportError:
    ANITOPY_AVAILABLE = False

# Skip all tests if anitopy is not installed
pytestmark = pytest.mark.skipif(not ANITOPY_AVAILABLE, reason="anitopy not installed")


@pytest.fixture
def parser():
    """Create an AnitopyParser instance for testing."""
    return AnitopyParser()


def test_parser_initialization():
    """Test that AnitopyParser can be initialized."""
    parser = AnitopyParser()
    assert parser is not None


def test_parse_basic_filename(parser):
    """Test parsing a basic anime filename."""
    filename = "[SubsPlease] My Anime - 01 (1080p) [12345678].mkv"
    result = parser.parse(filename)

    assert isinstance(result, ParsingResult)
    assert result.title == "My Anime"
    assert result.episode == 1
    assert result.quality == "1080p"
    assert result.release_group == "SubsPlease"
    assert result.parser_used == "anitopy"
    assert result.confidence > 0.8


def test_parse_with_season_and_episode(parser):
    """Test parsing filename with season and episode."""
    filename = "[HorribleSubs] Attack on Titan S02E05 [720p].mkv"
    result = parser.parse(filename)

    assert result.title == "Attack on Titan"
    assert result.season == 2
    assert result.episode == 5
    assert result.quality == "720p"
    assert result.release_group == "HorribleSubs"


def test_parse_with_leading_zeros(parser):
    """Test that leading zeros in episode numbers are handled."""
    filename = "One Piece - 0001 [1080p].mkv"
    result = parser.parse(filename)

    assert result.episode == 1
    assert result.title == "One Piece"


def test_parse_with_codec_info(parser):
    """Test parsing filename with codec information."""
    filename = "[Erai-raws] My Anime - 12 [1080p][HEVC 10bit x265 AAC].mkv"
    result = parser.parse(filename)

    assert result.title == "My Anime"
    assert result.episode == 12
    # Codec info might be in various fields depending on anitopy parsing
    assert result.parser_used == "anitopy"


def test_parse_with_source(parser):
    """Test parsing filename with source information."""
    filename = "[SubsPlease] Anime Name - 01 (1080p) [BluRay].mkv"
    result = parser.parse(filename)

    assert result.title
    assert result.episode == 1


def test_parse_minimal_filename(parser):
    """Test parsing a minimal filename with just title."""
    filename = "My Anime.mkv"
    result = parser.parse(filename)

    assert result.title == "My Anime"
    assert result.episode is None
    assert result.season is None
    assert result.confidence < 0.8  # Lower confidence for minimal info


def test_parse_complex_title(parser):
    """Test parsing filename with complex anime title."""
    filename = "[Group] Anime Title: The Adventure Continues - 03 [720p].mkv"
    result = parser.parse(filename)

    assert result.episode == 3
    assert result.quality == "720p"
    assert len(result.title) > 0


def test_parse_multi_episode(parser):
    """Test parsing filename with multiple episodes."""
    filename = "[Group] Anime - 01-02 [1080p].mkv"
    result = parser.parse(filename)

    # Should take the first episode number
    assert result.episode in [1, 2]
    assert result.title == "Anime"


def test_parse_other_info_collection(parser):
    """Test that unmapped fields are collected in other_info."""
    filename = "[SubsPlease] Anime - 01 (1080p) [Web].mkv"
    result = parser.parse(filename)

    assert isinstance(result.other_info, dict)
    # other_info should contain any fields not mapped to main attributes


def test_parse_confidence_scoring_high(parser):
    """Test confidence scoring for well-formed filename."""
    filename = "[SubsPlease] Attack on Titan S02E05 (1080p) [BluRay].mkv"
    result = parser.parse(filename)

    # Should have high confidence (title + episode + season + quality)
    assert result.confidence >= 0.8


def test_parse_confidence_scoring_medium(parser):
    """Test confidence scoring for filename with only title."""
    filename = "My Anime.mkv"
    result = parser.parse(filename)

    # Should have medium confidence (title only)
    assert 0.4 <= result.confidence <= 0.7


def test_parse_is_valid_result(parser):
    """Test that result is valid when title is extracted."""
    filename = "[Group] Valid Anime - 01.mkv"
    result = parser.parse(filename)

    assert result.is_valid()


def test_parse_has_episode_info(parser):
    """Test has_episode_info helper method."""
    filename = "[Group] Anime - 05.mkv"
    result = parser.parse(filename)

    assert result.has_episode_info()


def test_parse_without_episode_info(parser):
    """Test parsing filename without episode information."""
    filename = "Movie Name [1080p].mkv"
    result = parser.parse(filename)

    assert not result.has_episode_info()
    assert result.episode is None


def test_parse_error_handling(parser):
    """Test that parser handles errors gracefully."""
    # Pass a problematic filename that might cause issues
    filename = ""
    result = parser.parse(filename)

    # Should return a result, not crash
    assert isinstance(result, ParsingResult)
    # Confidence should be low for empty filename
    assert result.confidence < 0.5


def test_extract_episode_number_from_list(parser):
    """Test episode number extraction when anitopy returns a list."""
    # This tests the internal method indirectly
    parsed_dict = {"episode_number": ["01", "02"]}
    episode = parser._extract_episode_number(parsed_dict)

    assert episode == 1


def test_extract_season_number_conversion(parser):
    """Test season number string to int conversion."""
    parsed_dict = {"anime_season": "02"}
    season = parser._extract_season_number(parsed_dict)

    assert season == 2


def test_calculate_confidence_with_all_fields(parser):
    """Test confidence calculation with complete metadata."""
    parsed = {
        "anime_title": "Test Anime",
        "episode_number": "1",
        "anime_season": "1",
        "release_group": "Group",
        "video_resolution": "1080p",
        "source": "BluRay",
        "video_term": "H.264",
        "audio_term": "AAC",
    }

    confidence = parser._calculate_confidence(
        title="Test Anime", episode=1, season=1, parsed=parsed
    )

    # Should be very high confidence
    assert confidence >= 0.9


def test_collect_other_info_unmapped_fields(parser):
    """Test that unmapped fields are collected correctly."""
    parsed = {
        "anime_title": "Test",
        "episode_number": "1",
        "file_checksum": "ABC123",  # Unmapped field
        "file_extension": "mkv",  # Unmapped field
    }

    other_info = parser._collect_other_info(parsed)

    assert "file_checksum" in other_info
    assert "file_extension" in other_info
    assert "anime_title" not in other_info  # Mapped field should not be here
    assert "episode_number" not in other_info
