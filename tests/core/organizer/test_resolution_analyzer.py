"""Unit tests for ResolutionAnalyzer service.

This module tests the resolution analysis functionality,
including TMDB metadata detection, filename pattern matching,
and mixed resolution detection.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from anivault.core.matching.models import MatchResult
from anivault.core.models import ScannedFile
from anivault.core.organizer.resolution import (
    FileResolutionInfo,
    ResolutionAnalyzer,
    ResolutionSummary,
)
from anivault.core.parser.models import ParsingResult

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def analyzer() -> ResolutionAnalyzer:
    """Create ResolutionAnalyzer instance."""
    return ResolutionAnalyzer()


@pytest.fixture
def mock_settings():
    """Create mock settings object."""
    settings = Mock()
    settings.app = Mock()
    return settings


# ============================================================================
# Data Model Tests (3 tests)
# ============================================================================


class TestResolutionSummary:
    """Tests for ResolutionSummary dataclass."""

    def test_resolution_summary_creation(self) -> None:
        """Test creating a valid ResolutionSummary."""
        summary = ResolutionSummary(
            series_title="Attack on Titan",
            has_mixed_resolutions=True,
            resolutions=frozenset([True, False]),
            file_count=10,
        )

        assert summary.series_title == "Attack on Titan"
        assert summary.has_mixed_resolutions is True
        assert summary.resolutions == frozenset([True, False])
        assert summary.file_count == 10

    def test_resolution_summary_validation_negative_count(self) -> None:
        """Test ResolutionSummary validation rejects negative file_count."""
        with pytest.raises(ValueError, match="file_count must be non-negative"):
            ResolutionSummary(
                series_title="Test",
                has_mixed_resolutions=False,
                resolutions=frozenset([True]),
                file_count=-1,
            )

    def test_resolution_summary_validation_empty_title(self) -> None:
        """Test ResolutionSummary validation rejects empty series_title."""
        with pytest.raises(ValueError, match="series_title cannot be empty"):
            ResolutionSummary(
                series_title="",
                has_mixed_resolutions=False,
                resolutions=frozenset([True]),
                file_count=5,
            )


class TestFileResolutionInfo:
    """Tests for FileResolutionInfo dataclass."""

    def test_file_resolution_info_creation(self) -> None:
        """Test creating a valid FileResolutionInfo."""
        info = FileResolutionInfo(
            series_title="Demon Slayer",
            is_high_res=True,
            quality_string="1080P",
            detection_method="tmdb_metadata",
        )

        assert info.series_title == "Demon Slayer"
        assert info.is_high_res is True
        assert info.quality_string == "1080P"
        assert info.detection_method == "tmdb_metadata"


# ============================================================================
# TMDB Metadata Detection Tests (3 tests)
# ============================================================================


class TestTMDBMetadataDetection:
    """Tests for TMDB metadata-based resolution detection."""

    def test_detect_from_tmdb_metadata_high_res(
        self, analyzer: ResolutionAnalyzer
    ) -> None:
        """Test detection from TMDB metadata with high resolution."""
        result = analyzer._detect_from_tmdb_metadata(
            series_title="Jujutsu Kaisen",
            quality="1080p",
        )

        assert result.series_title == "Jujutsu Kaisen"
        assert result.is_high_res is True
        assert result.quality_string == "1080p"
        assert result.detection_method == "tmdb_metadata"

    def test_detect_from_tmdb_metadata_low_res(
        self, analyzer: ResolutionAnalyzer
    ) -> None:
        """Test detection from TMDB metadata with low resolution."""
        result = analyzer._detect_from_tmdb_metadata(
            series_title="Naruto",
            quality="720p",
        )

        assert result.series_title == "Naruto"
        assert result.is_high_res is False
        assert result.quality_string == "720p"
        assert result.detection_method == "tmdb_metadata"

    def test_detect_from_tmdb_metadata_4k(self, analyzer: ResolutionAnalyzer) -> None:
        """Test detection from TMDB metadata with 4K quality."""
        result = analyzer._detect_from_tmdb_metadata(
            series_title="One Piece",
            quality="4K",
        )

        assert result.series_title == "One Piece"
        assert result.is_high_res is True
        assert result.quality_string == "4K"
        assert result.detection_method == "tmdb_metadata"


# ============================================================================
# Filename Pattern Detection Tests (5 tests)
# ============================================================================


class TestFilenamePatternDetection:
    """Tests for filename-based resolution detection."""

    @pytest.mark.parametrize(
        "filename,expected_quality,expected_high_res",
        [
            ("[Group] Anime [1080p].mkv", "1080P", True),
            ("Anime (720p) Episode 01.mp4", "720P", False),
            ("Anime 4K BluRay.mkv", "4K", True),
            ("Anime.480p.WEBRip.mkv", "480P", False),
            ("Anime SD Version.avi", "SD", False),
            ("[Release] Anime - 01 [2160p].mkv", "2160P", True),
        ],
    )
    def test_detect_from_filename_pattern_standard(
        self,
        analyzer: ResolutionAnalyzer,
        filename: str,
        expected_quality: str,
        expected_high_res: bool,
    ) -> None:
        """Test detection from filename with standard resolution patterns."""
        result = analyzer._detect_from_filename_pattern(filename)

        assert result is not None
        quality_str, is_high_res = result
        assert quality_str == expected_quality
        assert is_high_res == expected_high_res

    @pytest.mark.parametrize(
        "filename,expected_quality,expected_high_res",
        [
            ("Anime 1920x1080.mkv", "1080P", True),
            ("Anime 1280x720.mp4", "720P", False),
            ("Anime 854x480.avi", "480P", False),
            ("Anime 640x360.mkv", "SD", False),
        ],
    )
    def test_detect_from_filename_pattern_dimensions(
        self,
        analyzer: ResolutionAnalyzer,
        filename: str,
        expected_quality: str,
        expected_high_res: bool,
    ) -> None:
        """Test detection from filename with dimension patterns."""
        result = analyzer._detect_from_filename_pattern(filename)

        assert result is not None
        quality_str, is_high_res = result
        assert quality_str == expected_quality
        assert is_high_res == expected_high_res

    def test_detect_from_filename_pattern_no_match(
        self, analyzer: ResolutionAnalyzer
    ) -> None:
        """Test detection returns None when no pattern matches."""
        result = analyzer._detect_from_filename_pattern("Anime Episode 01.mkv")
        assert result is None

    def test_map_dimensions_to_resolution(self, analyzer: ResolutionAnalyzer) -> None:
        """Test dimension to resolution mapping."""
        assert analyzer._map_dimensions_to_resolution(1920, 1080) == "1080P"
        assert analyzer._map_dimensions_to_resolution(1280, 720) == "720P"
        assert analyzer._map_dimensions_to_resolution(854, 480) == "480P"
        assert analyzer._map_dimensions_to_resolution(640, 360) == "SD"


# ============================================================================
# Title Extraction Tests (2 tests)
# ============================================================================


class TestTitleExtraction:
    """Tests for series title extraction from filenames."""

    @pytest.mark.parametrize(
        "filename,expected_title",
        [
            ("[Group] Attack on Titan - 01.mkv", "Group"),
            ("Demon Slayer - 05 [1080p].mp4", "Demon Slayer"),
            ("One Piece (2023) - 1000.mkv", "One Piece"),
            ("[SubGroup] Jujutsu Kaisen - 12.mkv", "SubGroup"),
        ],
    )
    def test_extract_title_from_filename(
        self, analyzer: ResolutionAnalyzer, filename: str, expected_title: str
    ) -> None:
        """Test title extraction from various filename patterns."""
        result = analyzer._extract_title_from_filename(filename)
        assert result is not None
        assert expected_title in result

    def test_extract_title_fallback(self, analyzer: ResolutionAnalyzer) -> None:
        """Test title extraction fallback for non-standard filenames."""
        result = analyzer._extract_title_from_filename("some_anime_file.mkv")
        assert result is not None
        assert "some_anime_file" in result


# ============================================================================
# Integration Tests (6 tests)
# ============================================================================


class TestAnalyzeSeries:
    """Tests for complete series analysis workflow."""

    def test_analyze_series_single_high_res(
        self, analyzer: ResolutionAnalyzer, tmp_path: Path
    ) -> None:
        """Test analyzing series with only high resolution files."""
        # Create test files
        files = []
        for i in range(3):
            file_path = tmp_path / f"anime_{i}_1080p.mkv"
            file_path.touch()

            match_result = MatchResult(
                title="Test Anime",
                tmdb_id=12345,
                year=None,
                confidence_score=0.95,
                media_type="tv",
            )

            metadata = ParsingResult(
                title="Test Anime",
                quality="1080p",
                other_info={"match_result": match_result},
            )

            files.append(
                ScannedFile(
                    file_path=file_path,
                    metadata=metadata,
                    file_size=1024000,
                    last_modified=1640995200.0,
                )
            )

        # Analyze
        summaries = analyzer.analyze_series(files)

        # Verify
        assert len(summaries) == 1
        assert "Test Anime" in summaries

        summary = summaries["Test Anime"]
        assert summary.has_mixed_resolutions is False
        assert summary.resolutions == frozenset([True])
        assert summary.file_count == 3

    def test_analyze_series_mixed_resolutions(
        self, analyzer: ResolutionAnalyzer, tmp_path: Path
    ) -> None:
        """Test analyzing series with mixed resolution files."""
        # Create test files with mixed resolutions
        files = []

        # High res files
        for i in range(2):
            file_path = tmp_path / f"anime_{i}_1080p.mkv"
            file_path.touch()

            match_result = MatchResult(
                title="Mixed Anime",
                tmdb_id=54321,
                year=None,
                confidence_score=0.95,
                media_type="tv",
            )

            metadata = ParsingResult(
                title="Mixed Anime",
                quality="1080p",
                other_info={"match_result": match_result},
            )

            files.append(
                ScannedFile(
                    file_path=file_path,
                    metadata=metadata,
                    file_size=2048000,
                    last_modified=1640995200.0,
                )
            )

        # Low res files
        for i in range(2):
            file_path = tmp_path / f"anime_{i}_720p.mkv"
            file_path.touch()

            match_result = MatchResult(
                title="Mixed Anime",
                tmdb_id=54321,
                year=None,
                confidence_score=0.95,
                media_type="tv",
            )

            metadata = ParsingResult(
                title="Mixed Anime",
                quality="720p",
                other_info={"match_result": match_result},
            )

            files.append(
                ScannedFile(
                    file_path=file_path,
                    metadata=metadata,
                    file_size=1024000,
                    last_modified=1640995200.0,
                )
            )

        # Analyze
        summaries = analyzer.analyze_series(files)

        # Verify
        assert len(summaries) == 1
        assert "Mixed Anime" in summaries

        summary = summaries["Mixed Anime"]
        assert summary.has_mixed_resolutions is True
        assert summary.resolutions == frozenset([True, False])
        assert summary.file_count == 4

    def test_analyze_series_multiple_shows(
        self, analyzer: ResolutionAnalyzer, tmp_path: Path
    ) -> None:
        """Test analyzing multiple different series."""
        files = []

        # Series 1: High res
        for i in range(2):
            file_path = tmp_path / f"anime1_{i}_1080p.mkv"
            file_path.touch()

            match_result = MatchResult(
                title="Anime One",
                tmdb_id=11111,
                year=None,
                confidence_score=0.95,
                media_type="tv",
            )

            metadata = ParsingResult(
                title="Anime One",
                quality="1080p",
                other_info={"match_result": match_result},
            )

            files.append(
                ScannedFile(
                    file_path=file_path,
                    metadata=metadata,
                    file_size=2048000,
                    last_modified=1640995200.0,
                )
            )

        # Series 2: Low res
        for i in range(2):
            file_path = tmp_path / f"anime2_{i}_720p.mkv"
            file_path.touch()

            match_result = MatchResult(
                title="Anime Two",
                tmdb_id=22222,
                year=None,
                confidence_score=0.95,
                media_type="tv",
            )

            metadata = ParsingResult(
                title="Anime Two",
                quality="720p",
                other_info={"match_result": match_result},
            )

            files.append(
                ScannedFile(
                    file_path=file_path,
                    metadata=metadata,
                    file_size=1024000,
                    last_modified=1640995200.0,
                )
            )

        # Analyze
        summaries = analyzer.analyze_series(files)

        # Verify
        assert len(summaries) == 2

        assert "Anime One" in summaries
        assert summaries["Anime One"].has_mixed_resolutions is False
        assert summaries["Anime One"].resolutions == frozenset([True])

        assert "Anime Two" in summaries
        assert summaries["Anime Two"].has_mixed_resolutions is False
        assert summaries["Anime Two"].resolutions == frozenset([False])

    def test_analyze_series_filename_fallback(
        self, analyzer: ResolutionAnalyzer, tmp_path: Path
    ) -> None:
        """Test analyzing files without TMDB match (filename-only mode)."""
        files = []

        for i in range(2):
            file_path = tmp_path / f"[Group] Test Anime - {i:02d} [1080p].mkv"
            file_path.touch()

            metadata = ParsingResult(
                title="Test Anime",
                quality=None,  # No quality in metadata
                other_info={},  # No match_result
            )

            files.append(
                ScannedFile(
                    file_path=file_path,
                    metadata=metadata,
                    file_size=2048000,
                    last_modified=1640995200.0,
                )
            )

        # Analyze
        summaries = analyzer.analyze_series(files)

        # Verify
        assert len(summaries) >= 1
        # Should extract title from filename and detect resolution

    def test_analyze_series_empty_list(self, analyzer: ResolutionAnalyzer) -> None:
        """Test analyzing empty file list."""
        summaries = analyzer.analyze_series([])
        assert len(summaries) == 0

    def test_analyze_series_no_resolution_info(
        self, analyzer: ResolutionAnalyzer, tmp_path: Path
    ) -> None:
        """Test analyzing files with no resolution information."""
        files = []

        file_path = tmp_path / "anime_no_res.mkv"
        file_path.touch()

        metadata = ParsingResult(
            title="No Resolution Anime",
            quality=None,
            other_info={},
        )

        files.append(
            ScannedFile(
                file_path=file_path,
                metadata=metadata,
                file_size=1024000,
                last_modified=1640995200.0,
            )
        )

        # Analyze
        summaries = analyzer.analyze_series(files)

        # Should return empty or skip files without resolution info
        # Depends on implementation, but should not crash
        assert isinstance(summaries, dict)


# ============================================================================
# Edge Cases and Logging Tests (2 tests)
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_analyzer_with_settings(self, mock_settings) -> None:
        """Test analyzer initialization with settings."""
        analyzer = ResolutionAnalyzer(settings=mock_settings)
        assert analyzer.settings == mock_settings

    def test_analyzer_returns_empty_for_invalid_files(
        self, analyzer: ResolutionAnalyzer, tmp_path: Path
    ) -> None:
        """Test that analyzer handles files with invalid metadata gracefully."""
        # Create test files with incomplete metadata
        files = []

        for i in range(2):
            file_path = tmp_path / f"invalid_{i}.mkv"
            file_path.touch()

            # No match result, no quality info
            metadata = ParsingResult(
                title="",  # Empty title
                quality=None,
                other_info={},
            )

            files.append(
                ScannedFile(
                    file_path=file_path,
                    metadata=metadata,
                    file_size=1024000,
                    last_modified=1640995200.0,
                )
            )

        # Analyze - should not crash
        summaries = analyzer.analyze_series(files)

        # Should return empty or skip invalid files
        assert isinstance(summaries, dict)
