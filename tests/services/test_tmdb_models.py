"""Tests for TMDB API Response Models.

This module contains unit tests for the Pydantic models defined in
src/anivault/services/tmdb_models.py.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from anivault.services.tmdb_models import (
    TMDBEpisode,
    TMDBGenre,
    TMDBMediaDetails,
    TMDBSearchResponse,
    TMDBSearchResult,
)


class TestTMDBGenre:
    """Test cases for TMDBGenre model."""

    def test_tmdb_genre_valid_data(self) -> None:
        """Test TMDBGenre with valid data."""
        # Given
        genre_data = {"id": 16, "name": "Animation"}

        # When
        genre = TMDBGenre(**genre_data)

        # Then
        assert genre.id == 16
        assert genre.name == "Animation"

    def test_tmdb_genre_extra_fields_ignored(self) -> None:
        """Test TMDBGenre ignores extra fields from API response."""
        # Given
        genre_data = {
            "id": 16,
            "name": "Animation",
            "unknown_field_1": "should be ignored",
            "unknown_field_2": 123,
        }

        # When
        genre = TMDBGenre(**genre_data)

        # Then
        assert genre.id == 16
        assert genre.name == "Animation"
        assert not hasattr(genre, "unknown_field_1")
        assert not hasattr(genre, "unknown_field_2")

    def test_tmdb_genre_missing_required_field(self) -> None:
        """Test TMDBGenre raises ValidationError for missing required field."""
        # Given
        genre_data_missing_id = {"name": "Animation"}
        genre_data_missing_name = {"id": 16}

        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            TMDBGenre(**genre_data_missing_id)
        assert "id" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            TMDBGenre(**genre_data_missing_name)
        assert "name" in str(exc_info.value)

    def test_tmdb_genre_invalid_field_type(self) -> None:
        """Test TMDBGenre raises ValidationError for invalid field type."""
        # Given
        genre_data_invalid_id = {"id": "not_an_int", "name": "Animation"}
        genre_data_invalid_name = {"id": 16, "name": 123}

        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            TMDBGenre(**genre_data_invalid_id)
        assert "id" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            TMDBGenre(**genre_data_invalid_name)
        assert "name" in str(exc_info.value)


class TestTMDBSearchResult:
    """Test cases for TMDBSearchResult model."""

    def test_tmdb_search_result_valid_tv_show(self) -> None:
        """Test TMDBSearchResult with valid TV show data."""
        # Given
        tv_data = {
            "id": 1429,
            "media_type": "tv",
            "name": "진격의 거인",
            "original_name": "進撃の巨人",
            "first_air_date": "2013-04-07",
            "popularity": 21.4371,
            "vote_average": 8.7,
            "vote_count": 6998,
            "overview": "100여 년 전 갑자기 나타난 거인들...",
            "poster_path": "/quLA9tkgHFte762gqQaayBslB2T.jpg",
            "backdrop_path": "/rqbCbjB19amtOtFQbb3K2lgm2zv.jpg",
            "genre_ids": [16, 10759],
            "original_language": "ja",
        }

        # When
        result = TMDBSearchResult(**tv_data)

        # Then
        assert result.id == 1429
        assert result.media_type == "tv"
        assert result.name == "진격의 거인"
        assert result.first_air_date == "2013-04-07"
        assert result.title is None  # TV show has no title
        assert result.release_date is None  # TV show has no release_date
        assert result.genre_ids == [16, 10759]
        assert result.original_language == "ja"

    def test_tmdb_search_result_valid_movie(self) -> None:
        """Test TMDBSearchResult with valid movie data."""
        # Given
        movie_data = {
            "id": 100,
            "media_type": "movie",
            "title": "Your Name",
            "original_title": "君の名は。",
            "release_date": "2016-08-26",
            "popularity": 150.5,
            "vote_average": 8.5,
            "vote_count": 10000,
            "overview": "Two strangers find themselves linked...",
            "poster_path": "/poster.jpg",
            "genre_ids": [16, 18],
            "original_language": "ja",
        }

        # When
        result = TMDBSearchResult(**movie_data)

        # Then
        assert result.id == 100
        assert result.media_type == "movie"
        assert result.title == "Your Name"
        assert result.release_date == "2016-08-26"
        assert result.name is None  # Movie has no name
        assert result.first_air_date is None  # Movie has no first_air_date
        assert result.genre_ids == [16, 18]

    def test_tmdb_search_result_default_values(self) -> None:
        """Test TMDBSearchResult uses correct default values."""
        # Given
        minimal_data = {"id": 1, "media_type": "tv"}

        # When
        result = TMDBSearchResult(**minimal_data)

        # Then
        assert result.popularity == 0.0
        assert result.vote_average == 0.0
        assert result.vote_count == 0
        assert result.overview == ""
        assert result.original_language == ""
        assert result.genre_ids == []
        assert result.poster_path is None
        assert result.backdrop_path is None

    def test_tmdb_search_result_extra_fields_ignored(self) -> None:
        """Test TMDBSearchResult ignores extra fields from API response."""
        # Given
        data_with_extras = {
            "id": 1,
            "media_type": "tv",
            "unknown_field_1": "should be ignored",
            "new_api_field": 999,
        }

        # When
        result = TMDBSearchResult(**data_with_extras)

        # Then
        assert result.id == 1
        assert not hasattr(result, "unknown_field_1")
        assert not hasattr(result, "new_api_field")

    def test_tmdb_search_result_missing_required_field(self) -> None:
        """Test TMDBSearchResult raises ValidationError for missing required fields."""
        # Given
        data_missing_id = {"media_type": "tv"}
        data_missing_media_type = {"id": 1}

        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            TMDBSearchResult(**data_missing_id)
        assert "id" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            TMDBSearchResult(**data_missing_media_type)
        assert "media_type" in str(exc_info.value)

    def test_tmdb_search_result_invalid_media_type(self) -> None:
        """Test TMDBSearchResult raises ValidationError for invalid media_type."""
        # Given
        data_invalid_media_type = {"id": 1, "media_type": "invalid"}

        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            TMDBSearchResult(**data_invalid_media_type)
        assert "media_type" in str(exc_info.value)

    def test_tmdb_search_result_display_title_tv(self) -> None:
        """Test display_title property returns TV show name."""
        # Given
        tv_data = {"id": 1, "media_type": "tv", "name": "Test Show"}

        # When
        result = TMDBSearchResult(**tv_data)

        # Then
        assert result.display_title == "Test Show"

    def test_tmdb_search_result_display_title_movie(self) -> None:
        """Test display_title property returns movie title."""
        # Given
        movie_data = {"id": 1, "media_type": "movie", "title": "Test Movie"}

        # When
        result = TMDBSearchResult(**movie_data)

        # Then
        assert result.display_title == "Test Movie"

    def test_tmdb_search_result_display_title_unknown(self) -> None:
        """Test display_title property returns Unknown when both are None."""
        # Given
        minimal_data = {"id": 1, "media_type": "tv"}

        # When
        result = TMDBSearchResult(**minimal_data)

        # Then
        assert result.display_title == "Unknown"

    def test_tmdb_search_result_display_date_tv(self) -> None:
        """Test display_date property returns TV first_air_date."""
        # Given
        tv_data = {"id": 1, "media_type": "tv", "first_air_date": "2013-04-07"}

        # When
        result = TMDBSearchResult(**tv_data)

        # Then
        assert result.display_date == "2013-04-07"

    def test_tmdb_search_result_display_date_movie(self) -> None:
        """Test display_date property returns movie release_date."""
        # Given
        movie_data = {"id": 1, "media_type": "movie", "release_date": "2016-08-26"}

        # When
        result = TMDBSearchResult(**movie_data)

        # Then
        assert result.display_date == "2016-08-26"

    def test_tmdb_search_result_display_date_none(self) -> None:
        """Test display_date property returns None when both are None."""
        # Given
        minimal_data = {"id": 1, "media_type": "tv"}

        # When
        result = TMDBSearchResult(**minimal_data)

        # Then
        assert result.display_date is None


class TestTMDBSearchResponse:
    """Test cases for TMDBSearchResponse model."""

    def test_tmdb_search_response_valid_data(self) -> None:
        """Test TMDBSearchResponse with valid data."""
        # Given
        response_data = {
            "page": 1,
            "total_pages": 5,
            "total_results": 100,
            "results": [
                {
                    "id": 1429,
                    "media_type": "tv",
                    "name": "진격의 거인",
                    "first_air_date": "2013-04-07",
                    "genre_ids": [16, 10759],
                },
                {
                    "id": 100,
                    "media_type": "movie",
                    "title": "Your Name",
                    "release_date": "2016-08-26",
                    "genre_ids": [16, 18],
                },
            ],
        }

        # When
        response = TMDBSearchResponse(**response_data)

        # Then
        assert response.page == 1
        assert response.total_pages == 5
        assert response.total_results == 100
        assert len(response.results) == 2
        assert response.results[0].id == 1429
        assert response.results[0].media_type == "tv"
        assert response.results[1].id == 100
        assert response.results[1].media_type == "movie"

    def test_tmdb_search_response_empty_results(self) -> None:
        """Test TMDBSearchResponse with empty results list."""
        # Given
        response_data = {
            "page": 1,
            "total_pages": 0,
            "total_results": 0,
            "results": [],
        }

        # When
        response = TMDBSearchResponse(**response_data)

        # Then
        assert response.page == 1
        assert response.total_pages == 0
        assert response.total_results == 0
        assert len(response.results) == 0

    def test_tmdb_search_response_default_values(self) -> None:
        """Test TMDBSearchResponse uses correct default values."""
        # Given
        minimal_data: dict[str, object] = {}

        # When
        response = TMDBSearchResponse(**minimal_data)

        # Then
        assert response.page == 1
        assert response.total_pages == 1
        assert response.total_results == 0
        assert response.results == []

    def test_tmdb_search_response_nested_validation(self) -> None:
        """Test TMDBSearchResponse validates nested TMDBSearchResult."""
        # Given - invalid nested result (missing required field)
        response_data = {
            "page": 1,
            "results": [
                {
                    "media_type": "tv",
                    # missing "id" field
                },
            ],
        }

        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            TMDBSearchResponse(**response_data)
        assert "id" in str(exc_info.value)

    def test_tmdb_search_response_extra_fields_ignored(self) -> None:
        """Test TMDBSearchResponse ignores extra fields from API response."""
        # Given
        response_data = {
            "page": 1,
            "total_pages": 1,
            "total_results": 0,
            "results": [],
            "unknown_field": "should be ignored",
            "new_api_field": 999,
        }

        # When
        response = TMDBSearchResponse(**response_data)

        # Then
        assert response.page == 1
        assert not hasattr(response, "unknown_field")
        assert not hasattr(response, "new_api_field")


class TestTMDBEpisode:
    """Test cases for TMDBEpisode model."""

    def test_tmdb_episode_valid_data(self) -> None:
        """Test TMDBEpisode with valid data."""
        # Given
        episode_data = {
            "id": 3508327,
            "name": "인류의 새벽",
            "overview": "배에 탄 미카사...",
            "episode_number": 28,
            "season_number": 4,
            "air_date": "2022-04-04",
            "vote_average": 8.818,
            "vote_count": 33,
            "runtime": 23,
            "still_path": "/9IT29LxBTDd610r2XzzGZXeca0b.jpg",
        }

        # When
        episode = TMDBEpisode(**episode_data)

        # Then
        assert episode.id == 3508327
        assert episode.name == "인류의 새벽"
        assert episode.episode_number == 28
        assert episode.season_number == 4
        assert episode.air_date == "2022-04-04"
        assert episode.runtime == 23

    def test_tmdb_episode_minimal_data(self) -> None:
        """Test TMDBEpisode with minimal required fields."""
        # Given
        minimal_episode = {
            "id": 1,
            "name": "Pilot",
            "episode_number": 1,
            "season_number": 1,
        }

        # When
        episode = TMDBEpisode(**minimal_episode)

        # Then
        assert episode.id == 1
        assert episode.name == "Pilot"
        assert episode.episode_number == 1
        assert episode.season_number == 1
        assert episode.air_date is None
        assert episode.overview == ""
        assert episode.vote_average == 0.0


class TestTMDBMediaDetails:
    """Test cases for TMDBMediaDetails model."""

    def test_tmdb_media_details_tv_show(self) -> None:
        """Test TMDBMediaDetails with TV show data."""
        # Given
        tv_data = {
            "id": 1429,
            "name": "진격의 거인",
            "original_name": "進撃の巨人",
            "first_air_date": "2013-04-07",
            "popularity": 21.4371,
            "vote_average": 8.7,
            "vote_count": 6998,
            "overview": "100여 년 전 갑자기 나타난 거인들...",
            "poster_path": "/quLA9tkgHFte762gqQaayBslB2T.jpg",
            "number_of_episodes": 87,
            "number_of_seasons": 4,
            "genres": [
                {"id": 16, "name": "Animation"},
                {"id": 10759, "name": "Action & Adventure"},
            ],
            "last_episode_to_air": {
                "id": 3508327,
                "name": "인류의 새벽",
                "episode_number": 28,
                "season_number": 4,
                "air_date": "2022-04-04",
            },
        }

        # When
        details = TMDBMediaDetails(**tv_data)

        # Then
        assert details.id == 1429
        assert details.name == "진격의 거인"
        assert details.first_air_date == "2013-04-07"
        assert details.number_of_episodes == 87
        assert details.number_of_seasons == 4
        assert len(details.genres) == 2
        assert details.genres[0].id == 16
        assert details.genres[0].name == "Animation"
        assert details.last_episode_to_air is not None
        assert details.last_episode_to_air.episode_number == 28

    def test_tmdb_media_details_movie(self) -> None:
        """Test TMDBMediaDetails with movie data."""
        # Given
        movie_data = {
            "id": 100,
            "title": "Your Name",
            "original_title": "君の名は。",
            "release_date": "2016-08-26",
            "popularity": 150.5,
            "vote_average": 8.5,
            "vote_count": 10000,
            "overview": "Two strangers find themselves linked...",
            "poster_path": "/poster.jpg",
            "genres": [{"id": 16, "name": "Animation"}, {"id": 18, "name": "Drama"}],
        }

        # When
        details = TMDBMediaDetails(**movie_data)

        # Then
        assert details.id == 100
        assert details.title == "Your Name"
        assert details.release_date == "2016-08-26"
        assert details.number_of_episodes is None
        assert details.number_of_seasons is None
        assert details.last_episode_to_air is None
        assert len(details.genres) == 2

    def test_tmdb_media_details_minimal_data(self) -> None:
        """Test TMDBMediaDetails with minimal required fields."""
        # Given
        minimal_data = {"id": 1}

        # When
        details = TMDBMediaDetails(**minimal_data)

        # Then
        assert details.id == 1
        assert details.genres == []
        assert details.popularity == 0.0
        assert details.overview == ""

    def test_tmdb_media_details_nested_validation(self) -> None:
        """Test TMDBMediaDetails validates nested models."""
        # Given - invalid genre (missing required field)
        invalid_data = {"id": 1, "genres": [{"name": "Animation"}]}  # missing "id"

        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            TMDBMediaDetails(**invalid_data)
        assert "id" in str(exc_info.value)

    def test_tmdb_media_details_display_title_tv(self) -> None:
        """Test display_title property returns TV show name."""
        # Given
        tv_data = {"id": 1, "name": "Test Show"}

        # When
        details = TMDBMediaDetails(**tv_data)

        # Then
        assert details.display_title == "Test Show"

    def test_tmdb_media_details_display_title_movie(self) -> None:
        """Test display_title property returns movie title."""
        # Given
        movie_data = {"id": 1, "title": "Test Movie"}

        # When
        details = TMDBMediaDetails(**movie_data)

        # Then
        assert details.display_title == "Test Movie"

    def test_tmdb_media_details_display_date_tv(self) -> None:
        """Test display_date property returns TV first_air_date."""
        # Given
        tv_data = {"id": 1, "first_air_date": "2013-04-07"}

        # When
        details = TMDBMediaDetails(**tv_data)

        # Then
        assert details.display_date == "2013-04-07"

    def test_tmdb_media_details_display_date_movie(self) -> None:
        """Test display_date property returns movie release_date."""
        # Given
        movie_data = {"id": 1, "release_date": "2016-08-26"}

        # When
        details = TMDBMediaDetails(**movie_data)

        # Then
        assert details.display_date == "2016-08-26"
