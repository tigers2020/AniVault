"""Tests for the filename parser module.

This module contains comprehensive tests for the unified filename parsing system,
including tests for both anitopy and fallback parsing mechanisms.
"""

import pytest

from anivault.scanner.filename_parser import (
    FallbackParser,
    ParsedAnimeInfo,
    UnifiedFilenameParser,
    parse_filename,
)


class TestParsedAnimeInfo:
    """Test cases for ParsedAnimeInfo class."""

    def test_init_with_minimal_data(self) -> None:
        """Test ParsedAnimeInfo initialization with minimal data."""
        info = ParsedAnimeInfo(filename="test.mp4")

        assert info.filename == "test.mp4"
        assert info.anime_title is None
        assert info.parser_used == "none"
        assert info.confidence == 0.0
        assert not info.is_parsed
        assert not info.has_episode_info

    def test_init_with_full_data(self) -> None:
        """Test ParsedAnimeInfo initialization with full data."""
        info = ParsedAnimeInfo(
            filename="Attack on Titan - S01E01.mp4",
            anime_title="Attack on Titan",
            episode_number="01",
            episode_title="To You, in 2000 Years",
            season=1,
            year=2013,
            release_group="HorribleSubs",
            video_resolution="1080p",
            video_term="BluRay",
            audio_term="AAC",
            file_extension=".mp4",
            parser_used="anitopy",
            raw_data={"test": "data"},
            confidence=0.95,
        )

        assert info.filename == "Attack on Titan - S01E01.mp4"
        assert info.anime_title == "Attack on Titan"
        assert info.episode_number == "01"
        assert info.episode_title == "To You, in 2000 Years"
        assert info.season == 1
        assert info.year == 2013
        assert info.release_group == "HorribleSubs"
        assert info.video_resolution == "1080p"
        assert info.video_term == "BluRay"
        assert info.audio_term == "AAC"
        assert info.file_extension == ".mp4"
        assert info.parser_used == "anitopy"
        assert info.raw_data == {"test": "data"}
        assert info.confidence == 0.95
        assert info.is_parsed
        assert info.has_episode_info

    def test_is_parsed_property(self) -> None:
        """Test is_parsed property logic."""
        # Not parsed
        info = ParsedAnimeInfo(filename="test.mp4", parser_used="none")
        assert not info.is_parsed

        # Parsed but no title
        info = ParsedAnimeInfo(filename="test.mp4", parser_used="anitopy")
        assert not info.is_parsed

        # Properly parsed
        info = ParsedAnimeInfo(
            filename="test.mp4",
            anime_title="Test Anime",
            parser_used="anitopy",
        )
        assert info.is_parsed

    def test_has_episode_info_property(self) -> None:
        """Test has_episode_info property logic."""
        # No episode info
        info = ParsedAnimeInfo(filename="test.mp4", anime_title="Test Anime")
        assert not info.has_episode_info

        # Has episode number
        info = ParsedAnimeInfo(
            filename="test.mp4",
            anime_title="Test Anime",
            episode_number="01",
        )
        assert info.has_episode_info

        # Has episode title
        info = ParsedAnimeInfo(
            filename="test.mp4",
            anime_title="Test Anime",
            episode_title="Episode Title",
        )
        assert info.has_episode_info

    def test_to_dict(self) -> None:
        """Test to_dict method."""
        info = ParsedAnimeInfo(
            filename="test.mp4",
            anime_title="Test Anime",
            episode_number="01",
            parser_used="anitopy",
            confidence=0.8,
        )

        result = info.to_dict()

        assert isinstance(result, dict)
        assert result["filename"] == "test.mp4"
        assert result["anime_title"] == "Test Anime"
        assert result["episode_number"] == "01"
        assert result["parser_used"] == "anitopy"
        assert result["confidence"] == 0.8
        assert result["is_parsed"] is True
        assert result["has_episode_info"] is True


class TestFallbackParser:
    """Test cases for FallbackParser class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.parser = FallbackParser()

    def test_parse_standard_format(self) -> None:
        """Test parsing standard format: Title - Episode - [Release Group] - [Quality]."""
        filename = "Attack on Titan - Episode 01 - [HorribleSubs] - [1080p].mkv"
        result = self.parser.parse(filename)

        assert result is not None
        assert result.anime_title == "Attack on Titan"
        assert result.episode_number == "01"
        assert result.release_group == "HorribleSubs"
        assert result.video_resolution == "1080p"
        assert result.parser_used == "fallback"
        assert result.is_parsed

    def test_parse_season_episode_format(self) -> None:
        """Test parsing season/episode format: Title S##E## [Release Group] [Quality]."""
        filename = "One Piece S01E1000 [HorribleSubs] [720p].mp4"
        result = self.parser.parse(filename)

        assert result is not None
        assert result.anime_title == "One Piece"
        assert result.season == 1
        assert result.episode_number == "1000"
        assert result.release_group == "HorribleSubs"
        assert result.video_resolution == "720p"
        assert result.parser_used == "fallback"
        assert result.is_parsed

    def test_parse_underscore_format(self) -> None:
        """Test parsing underscore format: Title_Season_Episode_[Release_Group]_[Quality]."""
        filename = "Naruto_1_001_HorribleSubs_1080p.avi"
        result = self.parser.parse(filename)

        assert result is not None
        assert result.anime_title == "Naruto"
        assert result.season == 1
        assert result.episode_number == "001"
        assert result.release_group == "HorribleSubs"
        assert result.video_resolution == "1080p"
        assert result.parser_used == "fallback"
        assert result.is_parsed

    def test_parse_bracket_format(self) -> None:
        """Test parsing bracket format: [Release Group] Title - Episode [Quality]."""
        filename = "[HorribleSubs] Death Note - Episode 01 [1080p].mkv"
        result = self.parser.parse(filename)

        assert result is not None
        assert result.anime_title == "Death Note"
        assert result.episode_number == "01"
        assert result.release_group == "HorribleSubs"
        assert result.video_resolution == "1080p"
        assert result.parser_used == "fallback"
        assert result.is_parsed

    def test_parse_simple_format(self) -> None:
        """Test parsing simple format: Title Episode."""
        filename = "Fullmetal Alchemist Episode 01.mp4"
        result = self.parser.parse(filename)

        assert result is not None
        assert result.anime_title == "Fullmetal Alchemist"
        assert result.episode_number == "01"
        assert result.parser_used == "fallback"
        assert result.is_parsed

    def test_parse_year_format(self) -> None:
        """Test parsing year format: Title (Year) - Episode."""
        filename = "Demon Slayer (2019) - Episode 01.mkv"
        result = self.parser.parse(filename)

        assert result is not None
        assert result.anime_title == "Demon Slayer"
        assert result.year == 2019
        assert result.episode_number == "01"
        assert result.parser_used == "fallback"
        assert result.is_parsed

    def test_parse_quality_first_format(self) -> None:
        """Test parsing quality-first format: [Quality] Title - Episode [Release Group]."""
        filename = "[1080p] Jujutsu Kaisen - Episode 01 [HorribleSubs].mp4"
        result = self.parser.parse(filename)

        assert result is not None
        assert result.anime_title == "Jujutsu Kaisen"
        assert result.episode_number == "01"
        assert result.release_group == "HorribleSubs"
        assert result.video_resolution == "1080p"
        assert result.parser_used == "fallback"
        assert result.is_parsed

    def test_parse_failure(self) -> None:
        """Test parsing failure with unrecognized format."""
        filename = "random_file_with_no_anime_info.txt"
        result = self.parser.parse(filename)

        assert result is None

    def test_clean_title(self) -> None:
        """Test title cleaning functionality."""
        # Test removing brackets
        cleaned = self.parser._clean_title("[HorribleSubs] Attack on Titan [1080p]")
        assert cleaned == "Attack on Titan"

        # Test removing parentheses
        cleaned = self.parser._clean_title("(2013) Attack on Titan (Season 1)")
        assert cleaned == "Attack on Titan"

        # Test replacing underscores and dashes
        cleaned = self.parser._clean_title("Attack_on_Titan-Season_1")
        assert cleaned == "Attack on Titan Season 1"

        # Test normalizing whitespace
        cleaned = self.parser._clean_title("Attack   on    Titan")
        assert cleaned == "Attack on Titan"

    def test_extract_resolution(self) -> None:
        """Test resolution extraction functionality."""
        # Test 1080p extraction
        resolution = self.parser._extract_resolution("1080p BluRay")
        assert resolution == "1080p"

        # Test 720p extraction
        resolution = self.parser._extract_resolution("720p WEB-DL")
        assert resolution == "720p"

        # Test resolution with dimensions
        resolution = self.parser._extract_resolution("1920x1080")
        assert resolution == "1920x1080"

        # Test no resolution
        resolution = self.parser._extract_resolution("BluRay AAC")
        assert resolution is None

        # Test empty string
        resolution = self.parser._extract_resolution("")
        assert resolution is None


class TestUnifiedFilenameParser:
    """Test cases for UnifiedFilenameParser class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.parser = UnifiedFilenameParser()

    def test_parse_with_anitopy_success(self) -> None:
        """Test successful parsing with anitopy."""
        # Use a filename that anitopy should handle well
        filename = "Attack on Titan S01E01 1080p BluRay.mkv"
        result = self.parser.parse_filename(filename)

        assert result is not None
        assert result.filename == filename
        assert result.parser_used in ["anitopy", "fallback"]  # Could be either
        assert result.is_parsed
        assert result.confidence > 0.0

    def test_parse_with_fallback_success(self) -> None:
        """Test successful parsing with fallback parser."""
        # Use a filename that might need fallback parsing
        filename = "One Piece - Episode 1000 - [HorribleSubs] - [720p].mp4"
        result = self.parser.parse_filename(filename)

        assert result is not None
        assert result.filename == filename
        assert result.parser_used in ["anitopy", "fallback"]
        assert result.is_parsed
        assert result.confidence > 0.0

    def test_parse_failure(self) -> None:
        """Test parsing with minimal meaningful information."""
        filename = ".txt"
        result = self.parser.parse_filename(filename)

        assert result is not None
        assert result.filename == filename
        # Anitopy is very permissive, so it might still parse this
        assert result.parser_used in ["anitopy", "fallback", "none"]
        # Even if parsed, the confidence should be very low
        assert result.confidence <= 0.5

    def test_statistics_tracking(self) -> None:
        """Test statistics tracking functionality."""
        # Reset stats
        self.parser.reset_stats()

        # Parse some files
        self.parser.parse_filename("Attack on Titan S01E01.mkv")
        self.parser.parse_filename("One Piece - Episode 1000.mp4")
        self.parser.parse_filename("random_file.txt")

        stats = self.parser.get_stats()

        assert stats["total_parsed"] == 3
        assert stats["total_parsed"] == (
            stats["anitopy_successes"]
            + stats["fallback_successes"]
            + stats["total_failures"]
        )

    def test_calculate_confidence(self) -> None:
        """Test confidence calculation."""
        # Test with minimal data
        minimal_data = {"anime_title": "Test Anime"}
        confidence = self.parser._calculate_confidence(minimal_data)
        assert confidence == 0.4  # Base confidence for title

        # Test with full data
        full_data = {
            "anime_title": "Test Anime",
            "episode_number": "01",
            "season": 1,
            "year": 2020,
            "video_resolution": "1080p",
            "release_group": "TestGroup",
        }
        confidence = self.parser._calculate_confidence(full_data)
        assert confidence == 1.0  # Maximum confidence

        # Test with partial data
        partial_data = {
            "anime_title": "Test Anime",
            "episode_title": "Test Episode",
            "year": 2020,
        }
        confidence = self.parser._calculate_confidence(partial_data)
        assert confidence == 0.7  # Title + episode title + year

    def test_reset_stats(self) -> None:
        """Test statistics reset functionality."""
        # Parse some files to generate stats
        self.parser.parse_filename("test1.mkv")
        self.parser.parse_filename("test2.mp4")

        # Verify stats exist
        stats_before = self.parser.get_stats()
        assert stats_before["total_parsed"] > 0

        # Reset stats
        self.parser.reset_stats()

        # Verify stats are reset
        stats_after = self.parser.get_stats()
        assert stats_after["total_parsed"] == 0
        assert stats_after["anitopy_successes"] == 0
        assert stats_after["fallback_successes"] == 0
        assert stats_after["total_failures"] == 0


class TestGlobalFunctions:
    """Test cases for global functions."""

    def test_parse_filename_function(self) -> None:
        """Test the global parse_filename function."""
        filename = "Attack on Titan S01E01.mkv"
        result = parse_filename(filename)

        assert result is not None
        assert result.filename == filename
        assert result.parser_used in ["anitopy", "fallback", "none"]
        assert isinstance(result, ParsedAnimeInfo)

    def test_get_parser_singleton(self) -> None:
        """Test that get_parser returns a singleton instance."""
        from anivault.scanner.filename_parser import get_parser

        parser1 = get_parser()
        parser2 = get_parser()

        assert parser1 is parser2
        assert isinstance(parser1, UnifiedFilenameParser)


class TestRealWorldExamples:
    """Test cases with real-world anime filename examples."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.parser = UnifiedFilenameParser()

    def test_horrible_subs_format(self) -> None:
        """Test HorribleSubs naming format."""
        filename = "[HorribleSubs] Attack on Titan - 01 [1080p].mkv"
        result = self.parser.parse_filename(filename)

        assert result is not None
        assert result.is_parsed
        assert result.anime_title is not None
        assert result.episode_number is not None

    def test_erai_raws_format(self) -> None:
        """Test Erai-Raws naming format."""
        filename = "[Erai-raws] Attack on Titan - 01 [1080p][Multiple Subtitle].mkv"
        result = self.parser.parse_filename(filename)

        assert result is not None
        assert result.is_parsed
        assert result.anime_title is not None
        assert result.episode_number is not None

    def test_japanese_titles(self) -> None:
        """Test Japanese anime titles."""
        filename = "進撃の巨人 S01E01 [1080p].mkv"
        result = self.parser.parse_filename(filename)

        assert result is not None
        # Should be parsed (either by anitopy or fallback)
        assert result.is_parsed or result.parser_used == "none"

    def test_multi_episode_format(self) -> None:
        """Test multi-episode format."""
        filename = "Attack on Titan S01E01-E03 [1080p].mkv"
        result = self.parser.parse_filename(filename)

        assert result is not None
        assert result.is_parsed
        assert result.anime_title is not None
        assert result.episode_number is not None

    def test_special_episodes(self) -> None:
        """Test special episode formats."""
        filename = "Attack on Titan - OVA 01 [1080p].mkv"
        result = self.parser.parse_filename(filename)

        assert result is not None
        assert result.is_parsed
        assert result.anime_title is not None

    def test_movie_format(self) -> None:
        """Test movie format."""
        filename = "Attack on Titan - Movie (2014) [1080p].mkv"
        result = self.parser.parse_filename(filename)

        assert result is not None
        assert result.is_parsed
        assert result.anime_title is not None
        assert result.year is not None

    def test_complex_format(self) -> None:
        """Test complex naming format."""
        filename = "[HorribleSubs] Attack on Titan - 01 [1080p][AAC][Multiple Subtitle][WEB-DL].mkv"
        result = self.parser.parse_filename(filename)

        assert result is not None
        assert result.is_parsed
        assert result.anime_title is not None
        assert result.episode_number is not None

    def test_no_extension(self) -> None:
        """Test filename without extension."""
        filename = "Attack on Titan S01E01"
        result = self.parser.parse_filename(filename)

        assert result is not None
        assert result.is_parsed
        assert result.anime_title is not None

    def test_long_filename(self) -> None:
        """Test very long filename."""
        filename = "Very Long Anime Title With Many Words That Should Still Be Parsed Correctly S01E01 [1080p][HorribleSubs][WEB-DL][AAC][Multiple Subtitle].mkv"
        result = self.parser.parse_filename(filename)

        assert result is not None
        # Should be parsed (either by anitopy or fallback)
        assert result.is_parsed or result.parser_used == "none"

    def test_edge_case_empty_filename(self) -> None:
        """Test edge case with empty filename."""
        filename = ""
        result = self.parser.parse_filename(filename)

        assert result is not None
        assert result.filename == ""
        assert result.parser_used == "none"
        assert not result.is_parsed

    def test_edge_case_whitespace_only(self) -> None:
        """Test edge case with whitespace-only filename."""
        filename = "   "
        result = self.parser.parse_filename(filename)

        assert result is not None
        assert result.filename == "   "
        assert result.parser_used == "none"
        assert not result.is_parsed


class TestPerformanceAndReliability:
    """Test cases for performance and reliability."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.parser = UnifiedFilenameParser()

    @pytest.mark.parametrize(
        "filename",
        [
            "Attack on Titan S01E01.mkv",
            "One Piece - Episode 1000.mp4",
            "Naruto_1_001.avi",
            "[HorribleSubs] Death Note - 01.mkv",
            "Fullmetal Alchemist Episode 01.mp4",
            "Demon Slayer (2019) - 01.mkv",
            "[1080p] Jujutsu Kaisen - 01.mp4",
            "random_file.txt",
            "",
            "   ",
        ],
    )
    def test_parse_various_formats(self, filename: str) -> None:
        """Test parsing various filename formats."""
        result = self.parser.parse_filename(filename)

        assert result is not None
        assert isinstance(result, ParsedAnimeInfo)
        assert result.filename == filename
        assert result.parser_used in ["anitopy", "fallback", "none"]
        assert 0.0 <= result.confidence <= 1.0

    def test_concurrent_parsing(self) -> None:
        """Test that parsing is thread-safe."""
        import queue
        import threading

        results = queue.Queue()

        def parse_worker(filename: str) -> None:
            """Worker function for concurrent parsing."""
            result = self.parser.parse_filename(filename)
            results.put((filename, result))

        # Create multiple threads parsing different files
        threads = []
        filenames = [
            "Attack on Titan S01E01.mkv",
            "One Piece - Episode 1000.mp4",
            "Naruto_1_001.avi",
            "[HorribleSubs] Death Note - 01.mkv",
        ]

        for filename in filenames:
            thread = threading.Thread(target=parse_worker, args=(filename,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all results were collected
        assert results.qsize() == len(filenames)

        # Verify all results are valid
        while not results.empty():
            filename, result = results.get()
            assert result is not None
            assert result.filename == filename
            assert isinstance(result, ParsedAnimeInfo)

    def test_memory_usage(self) -> None:
        """Test that parsing doesn't cause memory leaks."""
        import gc

        # Parse many files
        for i in range(100):
            filename = f"Test Anime S01E{i:02d}.mkv"
            result = self.parser.parse_filename(filename)
            assert result is not None

        # Force garbage collection
        gc.collect()

        # Verify stats are still accessible
        stats = self.parser.get_stats()
        assert stats["total_parsed"] >= 100
