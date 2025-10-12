"""Tests for MetadataTransformer module.

This module tests the MetadataTransformer class which converts EnrichedMetadata
to FileMetadata for presentation layer consumption.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from anivault.core.parser.models import ParsingResult
from anivault.services.metadata_enricher.transformer import MetadataTransformer
from anivault.services.tmdb_models import TMDBGenre, TMDBMediaDetails
from anivault.shared.constants import TMDBResponseKeys


@pytest.fixture
def transformer() -> MetadataTransformer:
    """Create a MetadataTransformer instance."""
    return MetadataTransformer()


@pytest.fixture
def mock_parsing_result() -> ParsingResult:
    """Create a mock ParsingResult."""
    return ParsingResult(
        title="Attack on Titan",
        season=1,
        episode=1,
        year=2013,
    )


@pytest.fixture
def mock_file_path() -> Path:
    """Create a mock file path."""
    return Path("/anime/attack_on_titan_s01e01.mkv")


class TestMetadataTransformerBasic:
    """Tests for basic MetadataTransformer functionality."""

    def test_transform_with_none_tmdb_data(
        self,
        transformer: MetadataTransformer,
        mock_parsing_result: ParsingResult,
        mock_file_path: Path,
    ) -> None:
        """Test transformation with no TMDB data uses ParsingResult only."""
        # When: Transform with None TMDB data
        result = transformer.transform(
            file_info=mock_parsing_result,
            tmdb_data=None,
            file_path=mock_file_path,
        )

        # Then: Uses ParsingResult fields
        assert result.title == "Attack on Titan"
        assert result.season == 1
        assert result.episode == 1
        assert result.file_path == mock_file_path
        assert result.file_type == "mkv"
        assert result.genres == []
        assert result.tmdb_id is None
        assert result.media_type is None


class TestMetadataTransformerPydantic:
    """Tests for TMDBMediaDetails (Pydantic) transformation."""

    def test_transform_with_pydantic_model_tv(
        self,
        transformer: MetadataTransformer,
        mock_parsing_result: ParsingResult,
        mock_file_path: Path,
    ) -> None:
        """Test transformation with TMDBMediaDetails (TV show)."""
        # Given: Mock TMDBMediaDetails for TV show
        mock_details = Mock(spec=TMDBMediaDetails)
        mock_details.display_title = "進撃の巨人"
        mock_details.id = 1429
        mock_details.overview = "Epic anime series"
        mock_details.poster_path = "/poster.jpg"
        mock_details.vote_average = 8.7
        mock_details.number_of_seasons = 4
        mock_details.display_date = "2013-04-07"

        mock_genre1 = Mock(spec=TMDBGenre)
        mock_genre1.name = "Action"
        mock_genre2 = Mock(spec=TMDBGenre)
        mock_genre2.name = "Animation"
        mock_details.genres = [mock_genre1, mock_genre2]

        # When: Transform with Pydantic model
        result = transformer.transform(
            file_info=mock_parsing_result,
            tmdb_data=mock_details,
            file_path=mock_file_path,
        )

        # Then: Uses TMDB data (overrides ParsingResult)
        assert result.title == "進撃の巨人"
        assert result.tmdb_id == 1429
        assert result.media_type == "tv"
        assert result.year == 2013
        assert result.genres == ["Action", "Animation"]
        assert result.overview == "Epic anime series"
        assert result.poster_path == "/poster.jpg"
        assert result.vote_average == 8.7
        # ParsingResult fields preserved
        assert result.season == 1
        assert result.episode == 1

    def test_transform_with_pydantic_model_movie(
        self,
        transformer: MetadataTransformer,
        mock_parsing_result: ParsingResult,
        mock_file_path: Path,
    ) -> None:
        """Test transformation with TMDBMediaDetails (Movie)."""
        # Given: Mock TMDBMediaDetails for movie (no number_of_seasons)
        mock_details = Mock(spec=TMDBMediaDetails)
        mock_details.display_title = "Your Name"
        mock_details.id = 372058
        mock_details.overview = "Beautiful anime movie"
        mock_details.poster_path = "/your_name.jpg"
        mock_details.vote_average = 8.5
        mock_details.number_of_seasons = None  # Movie
        mock_details.display_date = "2016-08-26"
        mock_details.genres = []

        # When: Transform
        result = transformer.transform(
            file_info=mock_parsing_result,
            tmdb_data=mock_details,
            file_path=mock_file_path,
        )

        # Then: Identifies as movie
        assert result.media_type == "movie"
        assert result.year == 2016

    def test_transform_with_pydantic_invalid_date(
        self,
        transformer: MetadataTransformer,
        mock_parsing_result: ParsingResult,
        mock_file_path: Path,
    ) -> None:
        """Test transformation with invalid date format."""
        # Given: Invalid date format
        mock_details = Mock(spec=TMDBMediaDetails)
        mock_details.display_title = "Test"
        mock_details.id = 123
        mock_details.overview = None
        mock_details.poster_path = None
        mock_details.vote_average = None
        mock_details.number_of_seasons = None
        mock_details.display_date = "invalid-date"
        mock_details.genres = []

        # When: Transform
        result = transformer.transform(
            file_info=mock_parsing_result,
            tmdb_data=mock_details,
            file_path=mock_file_path,
        )

        # Then: Year is None (graceful failure)
        assert result.year is None

    def test_transform_with_pydantic_none_date(
        self,
        transformer: MetadataTransformer,
        mock_parsing_result: ParsingResult,
        mock_file_path: Path,
    ) -> None:
        """Test transformation with None date."""
        # Given: None date
        mock_details = Mock(spec=TMDBMediaDetails)
        mock_details.display_title = "Test"
        mock_details.id = 123
        mock_details.overview = None
        mock_details.poster_path = None
        mock_details.vote_average = None
        mock_details.number_of_seasons = None
        mock_details.display_date = None
        mock_details.genres = []

        # When: Transform
        result = transformer.transform(
            file_info=mock_parsing_result,
            tmdb_data=mock_details,
            file_path=mock_file_path,
        )

        # Then: Year is None
        assert result.year is None


class TestMetadataTransformerDict:
    """Tests for dictionary (fallback) transformation."""

    def test_transform_with_dict_complete(
        self,
        transformer: MetadataTransformer,
        mock_parsing_result: ParsingResult,
        mock_file_path: Path,
    ) -> None:
        """Test transformation with complete dict data."""
        # Given: Complete dict data
        tmdb_dict = {
            TMDBResponseKeys.TITLE: "Attack on Titan",
            TMDBResponseKeys.ID: 1429,
            TMDBResponseKeys.MEDIA_TYPE: "tv",
            TMDBResponseKeys.OVERVIEW: "Epic series",
            TMDBResponseKeys.POSTER_PATH: "/poster.jpg",
            TMDBResponseKeys.VOTE_AVERAGE: 8.7,
            TMDBResponseKeys.FIRST_AIR_DATE: "2013-04-07",
            TMDBResponseKeys.GENRES: [
                {TMDBResponseKeys.NAME: "Action"},
                {TMDBResponseKeys.NAME: "Animation"},
            ],
        }

        # When: Transform
        result = transformer.transform(
            file_info=mock_parsing_result,
            tmdb_data=tmdb_dict,
            file_path=mock_file_path,
        )

        # Then: Uses dict data
        assert result.title == "Attack on Titan"
        assert result.tmdb_id == 1429
        assert result.media_type == "tv"
        assert result.year == 2013
        assert result.genres == ["Action", "Animation"]
        assert result.overview == "Epic series"

    def test_transform_with_dict_name_fallback(
        self,
        transformer: MetadataTransformer,
        mock_parsing_result: ParsingResult,
        mock_file_path: Path,
    ) -> None:
        """Test transformation with dict using 'name' instead of 'title'."""
        # Given: Dict with 'name' key (TV show format)
        tmdb_dict = {
            TMDBResponseKeys.NAME: "Attack on Titan",
            TMDBResponseKeys.ID: 1429,
            TMDBResponseKeys.MEDIA_TYPE: "tv",
        }

        # When: Transform
        result = transformer.transform(
            file_info=mock_parsing_result,
            tmdb_data=tmdb_dict,
            file_path=mock_file_path,
        )

        # Then: Uses 'name' as title
        assert result.title == "Attack on Titan"

    def test_transform_with_dict_missing_title(
        self,
        transformer: MetadataTransformer,
        mock_parsing_result: ParsingResult,
        mock_file_path: Path,
    ) -> None:
        """Test transformation with dict missing title (uses fallback)."""
        # Given: Dict without title/name
        tmdb_dict = {
            TMDBResponseKeys.ID: 1429,
            TMDBResponseKeys.MEDIA_TYPE: "tv",
        }

        # When: Transform
        result = transformer.transform(
            file_info=mock_parsing_result,
            tmdb_data=tmdb_dict,
            file_path=mock_file_path,
        )

        # Then: Falls back to ParsingResult title
        assert result.title == "Attack on Titan"

    def test_transform_with_dict_release_date_fallback(
        self,
        transformer: MetadataTransformer,
        mock_parsing_result: ParsingResult,
        mock_file_path: Path,
    ) -> None:
        """Test transformation with dict using release_date (movie format)."""
        # Given: Dict with release_date instead of first_air_date
        tmdb_dict = {
            TMDBResponseKeys.TITLE: "Your Name",
            TMDBResponseKeys.ID: 372058,
            TMDBResponseKeys.MEDIA_TYPE: "movie",
            TMDBResponseKeys.RELEASE_DATE: "2016-08-26",
        }

        # When: Transform
        result = transformer.transform(
            file_info=mock_parsing_result,
            tmdb_data=tmdb_dict,
            file_path=mock_file_path,
        )

        # Then: Extracts year from release_date
        assert result.year == 2016

    def test_transform_with_dict_invalid_genres(
        self,
        transformer: MetadataTransformer,
        mock_parsing_result: ParsingResult,
        mock_file_path: Path,
    ) -> None:
        """Test transformation with dict containing invalid genres format."""
        # Given: Invalid genres format (not list of dicts)
        tmdb_dict = {
            TMDBResponseKeys.TITLE: "Test",
            TMDBResponseKeys.ID: 123,
            TMDBResponseKeys.GENRES: ["Action", "Animation"],  # Invalid format
        }

        # When: Transform
        result = transformer.transform(
            file_info=mock_parsing_result,
            tmdb_data=tmdb_dict,
            file_path=mock_file_path,
        )

        # Then: Genres is empty (graceful failure)
        assert result.genres == []


class TestMetadataTransformerHelpers:
    """Tests for helper methods."""

    def test_extract_year_valid_date(self, transformer: MetadataTransformer) -> None:
        """Test year extraction from valid date string."""
        assert transformer._extract_year("2013-04-07") == 2013

    def test_extract_year_none(self, transformer: MetadataTransformer) -> None:
        """Test year extraction from None."""
        assert transformer._extract_year(None) is None

    def test_extract_year_invalid_format(
        self, transformer: MetadataTransformer
    ) -> None:
        """Test year extraction from invalid format."""
        assert transformer._extract_year("invalid") is None

    def test_extract_year_non_string(self, transformer: MetadataTransformer) -> None:
        """Test year extraction from non-string."""
        assert transformer._extract_year(12345) is None  # type: ignore[arg-type]
