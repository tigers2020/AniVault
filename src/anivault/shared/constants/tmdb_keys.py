"""TMDB API Response Keys Constants.

This module contains all TMDB API response field keys to ensure
type safety and prevent typos when accessing API responses.
"""


class TMDBResponseKeys:
    """TMDB API response field keys."""

    # Media identification
    ID = "id"
    TMDB_ID = "id"

    # Title fields
    NAME = "name"
    TITLE = "title"
    ORIGINAL_NAME = "original_name"
    ORIGINAL_TITLE = "original_title"
    ORIGINAL_LANGUAGE = "original_language"

    # Media type
    MEDIA_TYPE = "media_type"

    # Dates
    FIRST_AIR_DATE = "first_air_date"
    RELEASE_DATE = "release_date"

    # Ratings and popularity
    VOTE_AVERAGE = "vote_average"
    VOTE_COUNT = "vote_count"
    POPULARITY = "popularity"

    # Content
    OVERVIEW = "overview"
    POSTER_PATH = "poster_path"
    BACKDROP_PATH = "backdrop_path"

    # TV specific
    NUMBER_OF_EPISODES = "number_of_episodes"
    NUMBER_OF_SEASONS = "number_of_seasons"
    EPISODE_RUN_TIME = "episode_run_time"

    # Movie specific
    RUNTIME = "runtime"

    # Genre and classification
    GENRE_IDS = "genre_ids"
    GENRES = "genres"

    # Additional metadata
    ADULT = "adult"
    VIDEO = "video"

    # Search results
    RESULTS = "results"
    PAGE = "page"
    TOTAL_PAGES = "total_pages"
    TOTAL_RESULTS = "total_results"


class TMDBSearchKeys:
    """TMDB search-specific keys."""

    QUERY = "query"
    LANGUAGE = "language"
    PAGE = "page"
    INCLUDE_ADULT = "include_adult"
    YEAR = "year"
    FIRST_AIR_DATE_YEAR = "first_air_date_year"


class TMDBMediaTypes:
    """TMDB media type values."""

    TV = "tv"
    MOVIE = "movie"
    PERSON = "person"
    ALL = "all"
