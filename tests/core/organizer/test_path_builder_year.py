"""Tests for PathBuilder year-based folder organization."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from anivault.core.matching.models import MatchResult
from anivault.core.models import ScannedFile
from anivault.core.organizer.path_builder import PathBuilder, PathContext
from anivault.core.parser.models import ParsingResult


class TestPathBuilderYearExtraction:
    """Test cases for year extraction from TMDB data."""

    def test_extract_year_from_tmdb_with_year(self) -> None:
        """Test extracting year from TMDB match result with year."""
        # Given
        builder = PathBuilder()
        match_result = MatchResult(
            tmdb_id=1429,
            title="Attack on Titan",
            year=2013,
            confidence_score=0.95,
            media_type="tv",
        )
        scanned_file = ScannedFile(
            file_path=Path("test.mkv"),
            metadata=ParsingResult(
                title="Attack on Titan",
                other_info={"match_result": match_result},
            ),
        )

        # When
        year = builder._extract_year_from_tmdb(scanned_file)

        # Then
        assert year == 2013

    def test_extract_year_from_tmdb_without_year(self) -> None:
        """Test extracting year from TMDB match result without year."""
        # Given
        builder = PathBuilder()
        match_result = MatchResult(
            tmdb_id=1429,
            title="Attack on Titan",
            year=None,
            confidence_score=0.95,
            media_type="tv",
        )
        scanned_file = ScannedFile(
            file_path=Path("test.mkv"),
            metadata=ParsingResult(
                title="Attack on Titan",
                other_info={"match_result": match_result},
            ),
        )

        # When
        year = builder._extract_year_from_tmdb(scanned_file)

        # Then
        assert year is None

    def test_extract_year_from_tmdb_no_match_result(self) -> None:
        """Test extracting year when no match result available."""
        # Given
        builder = PathBuilder()
        scanned_file = ScannedFile(
            file_path=Path("test.mkv"),
            metadata=ParsingResult(
                title="Unknown Series",
                other_info={},
            ),
        )

        # When
        year = builder._extract_year_from_tmdb(scanned_file)

        # Then
        assert year is None

    def test_extract_year_from_tmdb_invalid_year_range(self) -> None:
        """Test extracting year with invalid year range."""
        # Given
        builder = PathBuilder()
        match_result = MatchResult(
            tmdb_id=1429,
            title="Attack on Titan",
            year=1800,  # Too old
            confidence_score=0.95,
            media_type="tv",
        )
        scanned_file = ScannedFile(
            file_path=Path("test.mkv"),
            metadata=ParsingResult(
                title="Attack on Titan",
                other_info={"match_result": match_result},
            ),
        )

        # When
        year = builder._extract_year_from_tmdb(scanned_file)

        # Then
        assert year is None


class TestPathBuilderYearFolderStructure:
    """Test cases for year-based folder structure."""

    def test_build_path_with_year_organization(self) -> None:
        """Test building path with year organization enabled."""
        # Given
        builder = PathBuilder()
        match_result = MatchResult(
            tmdb_id=1429,
            title="Attack on Titan",
            year=2013,
            confidence_score=0.95,
            media_type="tv",
        )
        scanned_file = ScannedFile(
            file_path=Path("Attack on Titan S01E01.mkv"),
            metadata=ParsingResult(
                title="Attack on Titan",
                season=1,
                other_info={"match_result": match_result},
            ),
        )
        context = PathContext(
            scanned_file=scanned_file,
            series_has_mixed_resolutions=False,
            target_folder=Path("/media"),
            media_type="anime",
            organize_by_resolution=False,
            organize_by_year=True,
        )

        # When
        path = builder.build_path(context)

        # Then
        expected_path = Path(
            "/media/anime/2013/Attack on Titan/Season 01/Attack on Titan S01E01.mkv"
        )
        assert path == expected_path

    def test_build_path_without_year_organization(self) -> None:
        """Test building path without year organization (default behavior)."""
        # Given
        builder = PathBuilder()
        match_result = MatchResult(
            tmdb_id=1429,
            title="Attack on Titan",
            year=2013,
            confidence_score=0.95,
            media_type="tv",
        )
        scanned_file = ScannedFile(
            file_path=Path("Attack on Titan S01E01.mkv"),
            metadata=ParsingResult(
                title="Attack on Titan",
                season=1,
                other_info={"match_result": match_result},
            ),
        )
        context = PathContext(
            scanned_file=scanned_file,
            series_has_mixed_resolutions=False,
            target_folder=Path("/media"),
            media_type="anime",
            organize_by_resolution=False,
            organize_by_year=False,
        )

        # When
        path = builder.build_path(context)

        # Then
        expected_path = Path(
            "/media/anime/Attack on Titan/Season 01/Attack on Titan S01E01.mkv"
        )
        assert path == expected_path

    def test_build_path_with_year_but_no_year_data(self) -> None:
        """Test building path with year organization enabled but no year data."""
        # Given
        builder = PathBuilder()
        scanned_file = ScannedFile(
            file_path=Path("Unknown Series S01E01.mkv"),
            metadata=ParsingResult(
                title="Unknown Series",
                season=1,
                other_info={},
            ),
        )
        context = PathContext(
            scanned_file=scanned_file,
            series_has_mixed_resolutions=False,
            target_folder=Path("/media"),
            media_type="anime",
            organize_by_resolution=False,
            organize_by_year=True,
        )

        # When
        path = builder.build_path(context)

        # Then
        # Should fall back to normal structure when no year data
        expected_path = Path(
            "/media/anime/Unknown Series/Season 01/Unknown Series S01E01.mkv"
        )
        assert path == expected_path

    def test_build_path_with_year_and_resolution_organization_high_res(self) -> None:
        """Test building path with both year and resolution organization (high resolution)."""
        # Given
        builder = PathBuilder()
        match_result = MatchResult(
            tmdb_id=1429,
            title="Attack on Titan",
            year=2013,
            confidence_score=0.95,
            media_type="tv",
        )
        scanned_file = ScannedFile(
            file_path=Path("Attack on Titan S01E01 [1080p].mkv"),
            metadata=ParsingResult(
                title="Attack on Titan",
                season=1,
                quality="1080p",
                other_info={"match_result": match_result},
            ),
        )
        context = PathContext(
            scanned_file=scanned_file,
            series_has_mixed_resolutions=True,
            target_folder=Path("/media"),
            media_type="anime",
            organize_by_resolution=True,
            organize_by_year=True,
        )

        # When
        path = builder.build_path(context)

        # Then
        # High resolution: normal structure with year folder
        expected_path = Path(
            "/media/anime/2013/Attack on Titan/Season 01/Attack on Titan S01E01 [1080p].mkv"
        )
        assert path == expected_path

    def test_build_path_with_year_and_resolution_organization_low_res(self) -> None:
        """Test building path with both year and resolution organization (low resolution)."""
        # Given
        builder = PathBuilder()
        match_result = MatchResult(
            tmdb_id=1429,
            title="Attack on Titan",
            year=2013,
            confidence_score=0.95,
            media_type="tv",
        )
        scanned_file = ScannedFile(
            file_path=Path("Attack on Titan S01E01 [720p].mkv"),
            metadata=ParsingResult(
                title="Attack on Titan",
                season=1,
                quality="720p",
                other_info={"match_result": match_result},
            ),
        )
        context = PathContext(
            scanned_file=scanned_file,
            series_has_mixed_resolutions=True,
            target_folder=Path("/media"),
            media_type="anime",
            organize_by_resolution=True,
            organize_by_year=True,
        )

        # When
        path = builder.build_path(context)

        # Then
        # Low resolution: low_res/year/series/season structure
        expected_path = Path(
            "/media/anime/low_res/2013/Attack on Titan/Season 01/Attack on Titan S01E01 [720p].mkv"
        )
        assert path == expected_path
