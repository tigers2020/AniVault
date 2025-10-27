"""
TMDB API 모든 엔드포인트 호출 및 응답 저장 스크립트

이 스크립트는 TMDB API의 모든 엔드포인트를 체계적으로 호출하고
응답을 JSON 파일로 저장합니다.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from tmdbv3api import (
    TV,
    Collection,
    Company,
    Discover,
    Episode,
    Find,
    Genre,
    Keyword,
    Movie,
    Network,
    Person,
    Review,
    Search,
    Season,
    TMDb,
    Trending,
)

from anivault.config.settings import get_config

logger = logging.getLogger(__name__)


class TMDBEndpointFetcher:
    """TMDB API 엔드포인트 호출 및 저장 클래스."""

    def __init__(self, output_dir: Path):
        """초기화.

        Args:
            output_dir: 응답 저장 디렉터리
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # TMDB 클라이언트 초기화
        config = get_config()
        self.tmdb = TMDb()
        self.tmdb.api_key = config.tmdb.api_key
        self.tmdb.language = "ko-KR"

        # API 객체 초기화
        self.movie = Movie()
        self.tv = TV()
        self.person = Person()
        self.search = Search()
        self.discover = Discover()
        self.collection = Collection()
        self.company = Company()
        self.genre = Genre()
        self.keyword = Keyword()
        self.network = Network()
        self.review = Review()
        self.trending = Trending()
        self.find = Find()
        self.season = Season()
        self.episode = Episode()

        # 카운터
        self.success_count = 0
        self.failure_count = 0
        self.errors: List[Dict[str, str]] = []

    def _convert_to_dict(self, obj: Any) -> Any:
        """객체를 딕셔너리로 변환 (재귀적으로 처리).

        Args:
            obj: 변환할 객체

        Returns:
            변환된 딕셔너리 또는 기본 타입
        """
        # None, 기본 타입은 그대로 반환
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj

        # 딕셔너리
        if isinstance(obj, dict):
            return {key: self._convert_to_dict(value) for key, value in obj.items()}

        # 리스트/튜플
        if isinstance(obj, (list, tuple)):
            return [self._convert_to_dict(item) for item in obj]

        # AsObj 또는 __dict__ 속성이 있는 객체
        if hasattr(obj, "__dict__"):
            result = {}
            for key, value in obj.__dict__.items():
                if not key.startswith("_"):  # private 속성 제외
                    result[key] = self._convert_to_dict(value)
            return result

        # 기타: 문자열로 변환
        return str(obj)

    def save_response(
        self,
        category: str,
        endpoint_name: str,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """응답을 JSON 파일로 저장.

        Args:
            category: 카테고리 (예: account, movies, tv)
            endpoint_name: 엔드포인트 이름
            data: 저장할 데이터
            metadata: 추가 메타데이터
        """
        category_dir = self.output_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)

        # 파일명 생성 (타임스탬프 포함)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{endpoint_name}_{timestamp}.json"
        filepath = category_dir / filename

        # 데이터를 딕셔너리로 변환 (재귀적으로)
        try:
            data_dict = self._convert_to_dict(data)
        except Exception as e:
            logger.error(f"데이터 변환 실패: {e}")
            data_dict = str(data)

        # 메타데이터 추가
        response_data = {
            "metadata": {
                "category": category,
                "endpoint": endpoint_name,
                "timestamp": timestamp,
                "language": self.tmdb.language,
                **(metadata or {}),
            },
            "data": data_dict,
        }

        # 파일 저장
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(response_data, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ {category}/{endpoint_name} 저장 완료: {filepath}")
            self.success_count += 1
        except Exception as e:
            logger.error(f"파일 저장 실패: {filepath}, 에러: {e}")
            self.failure_count += 1

    def handle_error(self, category: str, endpoint_name: str, error: Exception) -> None:
        """에러 처리.

        Args:
            category: 카테고리
            endpoint_name: 엔드포인트 이름
            error: 발생한 에러
        """
        error_msg = f"❌ {category}/{endpoint_name} 실패: {error}"
        logger.error(error_msg)
        self.failure_count += 1
        self.errors.append(
            {
                "category": category,
                "endpoint": endpoint_name,
                "error": str(error),
                "timestamp": datetime.now().isoformat(),
            },
        )

    # =========================================================================
    # Configuration Endpoints
    # =========================================================================

    def fetch_configuration(self) -> None:
        """Configuration 엔드포인트 호출."""
        category = "configuration"

        try:
            # Configuration Details
            config_data = self.tmdb.configuration()
            self.save_response(category, "details", config_data)
        except Exception as e:
            self.handle_error(category, "details", e)

        try:
            # Countries
            countries = self.tmdb.countries()
            self.save_response(category, "countries", countries)
        except Exception as e:
            self.handle_error(category, "countries", e)

        try:
            # Languages
            languages = self.tmdb.languages()
            self.save_response(category, "languages", languages)
        except Exception as e:
            self.handle_error(category, "languages", e)

        try:
            # Primary Translations
            translations = self.tmdb.primary_translations()
            self.save_response(category, "primary_translations", translations)
        except Exception as e:
            self.handle_error(category, "primary_translations", e)

        try:
            # Timezones
            timezones = self.tmdb.timezones()
            self.save_response(category, "timezones", timezones)
        except Exception as e:
            self.handle_error(category, "timezones", e)

    # =========================================================================
    # Genres Endpoints
    # =========================================================================

    def fetch_genres(self) -> None:
        """Genres 엔드포인트 호출."""
        category = "genres"

        try:
            # Movie Genres
            movie_genres = self.genre.movie_list()
            self.save_response(category, "movie_list", movie_genres)
        except Exception as e:
            self.handle_error(category, "movie_list", e)

        try:
            # TV Genres
            tv_genres = self.genre.tv_list()
            self.save_response(category, "tv_list", tv_genres)
        except Exception as e:
            self.handle_error(category, "tv_list", e)

    # =========================================================================
    # Movie Lists Endpoints
    # =========================================================================

    def fetch_movie_lists(self) -> None:
        """Movie Lists 엔드포인트 호출."""
        category = "movie_lists"

        try:
            # Now Playing
            now_playing = self.movie.now_playing()
            self.save_response(category, "now_playing", now_playing)
        except Exception as e:
            self.handle_error(category, "now_playing", e)

        try:
            # Popular
            popular = self.movie.popular()
            self.save_response(category, "popular", popular)
        except Exception as e:
            self.handle_error(category, "popular", e)

        try:
            # Top Rated
            top_rated = self.movie.top_rated()
            self.save_response(category, "top_rated", top_rated)
        except Exception as e:
            self.handle_error(category, "top_rated", e)

        try:
            # Upcoming
            upcoming = self.movie.upcoming()
            self.save_response(category, "upcoming", upcoming)
        except Exception as e:
            self.handle_error(category, "upcoming", e)

    # =========================================================================
    # Movie Details Endpoints
    # =========================================================================

    def fetch_movie_details(self, movie_id: int = 550) -> None:
        """Movie Details 엔드포인트 호출.

        Args:
            movie_id: 영화 ID (기본값: 550 - Fight Club)
        """
        category = f"movies/movie_{movie_id}"

        try:
            # Details
            details = self.movie.details(movie_id)
            self.save_response(category, "details", details)
        except Exception as e:
            self.handle_error(category, "details", e)

        try:
            # Alternative Titles
            alt_titles = self.movie.alternative_titles(movie_id)
            self.save_response(category, "alternative_titles", alt_titles)
        except Exception as e:
            self.handle_error(category, "alternative_titles", e)

        try:
            # Credits
            credits = self.movie.credits(movie_id)
            self.save_response(category, "credits", credits)
        except Exception as e:
            self.handle_error(category, "credits", e)

        try:
            # External IDs
            external_ids = self.movie.external_ids(movie_id)
            self.save_response(category, "external_ids", external_ids)
        except Exception as e:
            self.handle_error(category, "external_ids", e)

        try:
            # Images
            images = self.movie.images(movie_id)
            self.save_response(category, "images", images)
        except Exception as e:
            self.handle_error(category, "images", e)

        try:
            # Keywords
            keywords = self.movie.keywords(movie_id)
            self.save_response(category, "keywords", keywords)
        except Exception as e:
            self.handle_error(category, "keywords", e)

        try:
            # Recommendations
            recommendations = self.movie.recommendations(movie_id)
            self.save_response(category, "recommendations", recommendations)
        except Exception as e:
            self.handle_error(category, "recommendations", e)

        try:
            # Release Dates
            release_dates = self.movie.release_dates(movie_id)
            self.save_response(category, "release_dates", release_dates)
        except Exception as e:
            self.handle_error(category, "release_dates", e)

        try:
            # Reviews
            reviews = self.movie.reviews(movie_id)
            self.save_response(category, "reviews", reviews)
        except Exception as e:
            self.handle_error(category, "reviews", e)

        try:
            # Similar
            similar = self.movie.similar(movie_id)
            self.save_response(category, "similar", similar)
        except Exception as e:
            self.handle_error(category, "similar", e)

        try:
            # Translations
            translations = self.movie.translations(movie_id)
            self.save_response(category, "translations", translations)
        except Exception as e:
            self.handle_error(category, "translations", e)

        try:
            # Videos
            videos = self.movie.videos(movie_id)
            self.save_response(category, "videos", videos)
        except Exception as e:
            self.handle_error(category, "videos", e)

        try:
            # Watch Providers
            watch_providers = self.movie.watch_providers(movie_id)
            self.save_response(category, "watch_providers", watch_providers)
        except Exception as e:
            self.handle_error(category, "watch_providers", e)

    # =========================================================================
    # TV Series Lists Endpoints
    # =========================================================================

    def fetch_tv_lists(self) -> None:
        """TV Series Lists 엔드포인트 호출."""
        category = "tv_lists"

        try:
            # Airing Today
            airing_today = self.tv.airing_today()
            self.save_response(category, "airing_today", airing_today)
        except Exception as e:
            self.handle_error(category, "airing_today", e)

        try:
            # On The Air
            on_the_air = self.tv.on_the_air()
            self.save_response(category, "on_the_air", on_the_air)
        except Exception as e:
            self.handle_error(category, "on_the_air", e)

        try:
            # Popular
            popular = self.tv.popular()
            self.save_response(category, "popular", popular)
        except Exception as e:
            self.handle_error(category, "popular", e)

        try:
            # Top Rated
            top_rated = self.tv.top_rated()
            self.save_response(category, "top_rated", top_rated)
        except Exception as e:
            self.handle_error(category, "top_rated", e)

    # =========================================================================
    # TV Series Details Endpoints
    # =========================================================================

    def fetch_tv_details(self, tv_id: int = 1396) -> None:
        """TV Series Details 엔드포인트 호출.

        Args:
            tv_id: TV 시리즈 ID (기본값: 1396 - Breaking Bad)
        """
        category = f"tv/tv_{tv_id}"

        try:
            # Details
            details = self.tv.details(tv_id)
            self.save_response(category, "details", details)
        except Exception as e:
            self.handle_error(category, "details", e)

        try:
            # Aggregate Credits
            aggregate_credits = self.tv.aggregate_credits(tv_id)
            self.save_response(category, "aggregate_credits", aggregate_credits)
        except Exception as e:
            self.handle_error(category, "aggregate_credits", e)

        try:
            # Alternative Titles
            alt_titles = self.tv.alternative_titles(tv_id)
            self.save_response(category, "alternative_titles", alt_titles)
        except Exception as e:
            self.handle_error(category, "alternative_titles", e)

        try:
            # Content Ratings
            content_ratings = self.tv.content_ratings(tv_id)
            self.save_response(category, "content_ratings", content_ratings)
        except Exception as e:
            self.handle_error(category, "content_ratings", e)

        try:
            # Credits
            credits = self.tv.credits(tv_id)
            self.save_response(category, "credits", credits)
        except Exception as e:
            self.handle_error(category, "credits", e)

        try:
            # External IDs
            external_ids = self.tv.external_ids(tv_id)
            self.save_response(category, "external_ids", external_ids)
        except Exception as e:
            self.handle_error(category, "external_ids", e)

        try:
            # Images
            images = self.tv.images(tv_id)
            self.save_response(category, "images", images)
        except Exception as e:
            self.handle_error(category, "images", e)

        try:
            # Keywords
            keywords = self.tv.keywords(tv_id)
            self.save_response(category, "keywords", keywords)
        except Exception as e:
            self.handle_error(category, "keywords", e)

        try:
            # Recommendations
            recommendations = self.tv.recommendations(tv_id)
            self.save_response(category, "recommendations", recommendations)
        except Exception as e:
            self.handle_error(category, "recommendations", e)

        try:
            # Reviews
            reviews = self.tv.reviews(tv_id)
            self.save_response(category, "reviews", reviews)
        except Exception as e:
            self.handle_error(category, "reviews", e)

        try:
            # Screened Theatrically
            screened_theatrically = self.tv.screened_theatrically(tv_id)
            self.save_response(category, "screened_theatrically", screened_theatrically)
        except Exception as e:
            self.handle_error(category, "screened_theatrically", e)

        try:
            # Similar
            similar = self.tv.similar(tv_id)
            self.save_response(category, "similar", similar)
        except Exception as e:
            self.handle_error(category, "similar", e)

        try:
            # Translations
            translations = self.tv.translations(tv_id)
            self.save_response(category, "translations", translations)
        except Exception as e:
            self.handle_error(category, "translations", e)

        try:
            # Videos
            videos = self.tv.videos(tv_id)
            self.save_response(category, "videos", videos)
        except Exception as e:
            self.handle_error(category, "videos", e)

        try:
            # Watch Providers
            watch_providers = self.tv.watch_providers(tv_id)
            self.save_response(category, "watch_providers", watch_providers)
        except Exception as e:
            self.handle_error(category, "watch_providers", e)

    # =========================================================================
    # TV Season Endpoints
    # =========================================================================

    def fetch_tv_season(self, tv_id: int = 1396, season_number: int = 1) -> None:
        """TV Season 엔드포인트 호출.

        Args:
            tv_id: TV 시리즈 ID
            season_number: 시즌 번호
        """
        category = f"tv/tv_{tv_id}/season_{season_number}"

        try:
            # Details
            details = self.season.details(tv_id, season_number)
            self.save_response(category, "details", details)
        except Exception as e:
            self.handle_error(category, "details", e)

        try:
            # Aggregate Credits
            aggregate_credits = self.season.aggregate_credits(tv_id, season_number)
            self.save_response(category, "aggregate_credits", aggregate_credits)
        except Exception as e:
            self.handle_error(category, "aggregate_credits", e)

        try:
            # Credits
            credits = self.season.credits(tv_id, season_number)
            self.save_response(category, "credits", credits)
        except Exception as e:
            self.handle_error(category, "credits", e)

        try:
            # External IDs
            external_ids = self.season.external_ids(tv_id, season_number)
            self.save_response(category, "external_ids", external_ids)
        except Exception as e:
            self.handle_error(category, "external_ids", e)

        try:
            # Images
            images = self.season.images(tv_id, season_number)
            self.save_response(category, "images", images)
        except Exception as e:
            self.handle_error(category, "images", e)

        try:
            # Translations
            translations = self.season.translations(tv_id, season_number)
            self.save_response(category, "translations", translations)
        except Exception as e:
            self.handle_error(category, "translations", e)

        try:
            # Videos
            videos = self.season.videos(tv_id, season_number)
            self.save_response(category, "videos", videos)
        except Exception as e:
            self.handle_error(category, "videos", e)

    # =========================================================================
    # TV Episode Endpoints
    # =========================================================================

    def fetch_tv_episode(
        self,
        tv_id: int = 1396,
        season_number: int = 1,
        episode_number: int = 1,
    ) -> None:
        """TV Episode 엔드포인트 호출.

        Args:
            tv_id: TV 시리즈 ID
            season_number: 시즌 번호
            episode_number: 에피소드 번호
        """
        category = f"tv/tv_{tv_id}/season_{season_number}/episode_{episode_number}"

        try:
            # Details
            details = self.episode.details(tv_id, season_number, episode_number)
            self.save_response(category, "details", details)
        except Exception as e:
            self.handle_error(category, "details", e)

        try:
            # Credits
            credits = self.episode.credits(tv_id, season_number, episode_number)
            self.save_response(category, "credits", credits)
        except Exception as e:
            self.handle_error(category, "credits", e)

        try:
            # External IDs
            external_ids = self.episode.external_ids(
                tv_id,
                season_number,
                episode_number,
            )
            self.save_response(category, "external_ids", external_ids)
        except Exception as e:
            self.handle_error(category, "external_ids", e)

        try:
            # Images
            images = self.episode.images(tv_id, season_number, episode_number)
            self.save_response(category, "images", images)
        except Exception as e:
            self.handle_error(category, "images", e)

        try:
            # Translations
            translations = self.episode.translations(
                tv_id,
                season_number,
                episode_number,
            )
            self.save_response(category, "translations", translations)
        except Exception as e:
            self.handle_error(category, "translations", e)

        try:
            # Videos
            videos = self.episode.videos(tv_id, season_number, episode_number)
            self.save_response(category, "videos", videos)
        except Exception as e:
            self.handle_error(category, "videos", e)

    # =========================================================================
    # People Endpoints
    # =========================================================================

    def fetch_people_list(self) -> None:
        """People Lists 엔드포인트 호출."""
        category = "people_lists"

        try:
            # Popular
            popular = self.person.popular()
            self.save_response(category, "popular", popular)
        except Exception as e:
            self.handle_error(category, "popular", e)

    def fetch_person_details(self, person_id: int = 287) -> None:
        """Person Details 엔드포인트 호출.

        Args:
            person_id: 인물 ID (기본값: 287 - Brad Pitt)
        """
        category = f"people/person_{person_id}"

        try:
            # Details
            details = self.person.details(person_id)
            self.save_response(category, "details", details)
        except Exception as e:
            self.handle_error(category, "details", e)

        try:
            # Combined Credits
            combined_credits = self.person.combined_credits(person_id)
            self.save_response(category, "combined_credits", combined_credits)
        except Exception as e:
            self.handle_error(category, "combined_credits", e)

        try:
            # External IDs
            external_ids = self.person.external_ids(person_id)
            self.save_response(category, "external_ids", external_ids)
        except Exception as e:
            self.handle_error(category, "external_ids", e)

        try:
            # Images
            images = self.person.images(person_id)
            self.save_response(category, "images", images)
        except Exception as e:
            self.handle_error(category, "images", e)

        try:
            # Movie Credits
            movie_credits = self.person.movie_credits(person_id)
            self.save_response(category, "movie_credits", movie_credits)
        except Exception as e:
            self.handle_error(category, "movie_credits", e)

        try:
            # TV Credits
            tv_credits = self.person.tv_credits(person_id)
            self.save_response(category, "tv_credits", tv_credits)
        except Exception as e:
            self.handle_error(category, "tv_credits", e)

        try:
            # Tagged Images
            tagged_images = self.person.tagged_images(person_id)
            self.save_response(category, "tagged_images", tagged_images)
        except Exception as e:
            self.handle_error(category, "tagged_images", e)

        try:
            # Translations
            translations = self.person.translations(person_id)
            self.save_response(category, "translations", translations)
        except Exception as e:
            self.handle_error(category, "translations", e)

    # =========================================================================
    # Search Endpoints
    # =========================================================================

    def fetch_search_results(self) -> None:
        """Search 엔드포인트 호출."""
        category = "search"

        search_query = "Fight Club"

        try:
            # Search Movie
            movie_results = self.search.movies(search_query)
            self.save_response(
                category,
                "movie",
                movie_results,
                {"query": search_query},
            )
        except Exception as e:
            self.handle_error(category, "movie", e)

        try:
            # Search TV
            tv_results = self.search.tv_shows(search_query)
            self.save_response(category, "tv", tv_results, {"query": search_query})
        except Exception as e:
            self.handle_error(category, "tv", e)

        try:
            # Search Person
            person_results = self.search.people("Brad Pitt")
            self.save_response(
                category,
                "person",
                person_results,
                {"query": "Brad Pitt"},
            )
        except Exception as e:
            self.handle_error(category, "person", e)

        try:
            # Search Company
            company_results = self.search.companies("Marvel")
            self.save_response(
                category,
                "company",
                company_results,
                {"query": "Marvel"},
            )
        except Exception as e:
            self.handle_error(category, "company", e)

        try:
            # Search Collection
            collection_results = self.search.collections("Avengers")
            self.save_response(
                category,
                "collection",
                collection_results,
                {"query": "Avengers"},
            )
        except Exception as e:
            self.handle_error(category, "collection", e)

        try:
            # Search Keyword
            keyword_results = self.search.keywords("superhero")
            self.save_response(
                category,
                "keyword",
                keyword_results,
                {"query": "superhero"},
            )
        except Exception as e:
            self.handle_error(category, "keyword", e)

    # =========================================================================
    # Discover Endpoints
    # =========================================================================

    def fetch_discover(self) -> None:
        """Discover 엔드포인트 호출."""
        category = "discover"

        try:
            # Discover Movie
            movie_results = self.discover.discover_movies(
                {"sort_by": "popularity.desc", "page": 1},
            )
            self.save_response(category, "movie", movie_results)
        except Exception as e:
            self.handle_error(category, "movie", e)

        try:
            # Discover TV
            tv_results = self.discover.discover_tv_shows(
                {"sort_by": "popularity.desc", "page": 1},
            )
            self.save_response(category, "tv", tv_results)
        except Exception as e:
            self.handle_error(category, "tv", e)

    # =========================================================================
    # Trending Endpoints
    # =========================================================================

    def fetch_trending(self) -> None:
        """Trending 엔드포인트 호출."""
        category = "trending"

        try:
            # Trending All (Day)
            all_day = self.trending.all_day()
            self.save_response(category, "all_day", all_day)
        except Exception as e:
            self.handle_error(category, "all_day", e)

        try:
            # Trending All (Week)
            all_week = self.trending.all_week()
            self.save_response(category, "all_week", all_week)
        except Exception as e:
            self.handle_error(category, "all_week", e)

        try:
            # Trending Movies (Day)
            movies_day = self.trending.movie_day()
            self.save_response(category, "movies_day", movies_day)
        except Exception as e:
            self.handle_error(category, "movies_day", e)

        try:
            # Trending Movies (Week)
            movies_week = self.trending.movie_week()
            self.save_response(category, "movies_week", movies_week)
        except Exception as e:
            self.handle_error(category, "movies_week", e)

        try:
            # Trending TV (Day)
            tv_day = self.trending.tv_day()
            self.save_response(category, "tv_day", tv_day)
        except Exception as e:
            self.handle_error(category, "tv_day", e)

        try:
            # Trending TV (Week)
            tv_week = self.trending.tv_week()
            self.save_response(category, "tv_week", tv_week)
        except Exception as e:
            self.handle_error(category, "tv_week", e)

        try:
            # Trending People (Day)
            people_day = self.trending.people_day()
            self.save_response(category, "people_day", people_day)
        except Exception as e:
            self.handle_error(category, "people_day", e)

        try:
            # Trending People (Week)
            people_week = self.trending.people_week()
            self.save_response(category, "people_week", people_week)
        except Exception as e:
            self.handle_error(category, "people_week", e)

    # =========================================================================
    # Collection Endpoints
    # =========================================================================

    def fetch_collection(self, collection_id: int = 10) -> None:
        """Collection 엔드포인트 호출.

        Args:
            collection_id: 컬렉션 ID (기본값: 10 - Star Wars Collection)
        """
        category = f"collections/collection_{collection_id}"

        try:
            # Details
            details = self.collection.details(collection_id)
            self.save_response(category, "details", details)
        except Exception as e:
            self.handle_error(category, "details", e)

        try:
            # Images
            images = self.collection.images(collection_id)
            self.save_response(category, "images", images)
        except Exception as e:
            self.handle_error(category, "images", e)

        try:
            # Translations
            translations = self.collection.translations(collection_id)
            self.save_response(category, "translations", translations)
        except Exception as e:
            self.handle_error(category, "translations", e)

    # =========================================================================
    # Company Endpoints
    # =========================================================================

    def fetch_company(self, company_id: int = 1) -> None:
        """Company 엔드포인트 호출.

        Args:
            company_id: 회사 ID (기본값: 1 - Lucasfilm)
        """
        category = f"companies/company_{company_id}"

        try:
            # Details
            details = self.company.details(company_id)
            self.save_response(category, "details", details)
        except Exception as e:
            self.handle_error(category, "details", e)

        try:
            # Alternative Names
            alt_names = self.company.alternative_names(company_id)
            self.save_response(category, "alternative_names", alt_names)
        except Exception as e:
            self.handle_error(category, "alternative_names", e)

        try:
            # Images
            images = self.company.images(company_id)
            self.save_response(category, "images", images)
        except Exception as e:
            self.handle_error(category, "images", e)

    # =========================================================================
    # Keyword Endpoints
    # =========================================================================

    def fetch_keyword(self, keyword_id: int = 9715) -> None:
        """Keyword 엔드포인트 호출.

        Args:
            keyword_id: 키워드 ID (기본값: 9715 - superhero)
        """
        category = f"keywords/keyword_{keyword_id}"

        try:
            # Details
            details = self.keyword.info(keyword_id)
            self.save_response(category, "details", details)
        except Exception as e:
            self.handle_error(category, "details", e)

        try:
            # Movies
            movies = self.keyword.movies(keyword_id)
            self.save_response(category, "movies", movies)
        except Exception as e:
            self.handle_error(category, "movies", e)

    # =========================================================================
    # Network Endpoints
    # =========================================================================

    def fetch_network(self, network_id: int = 213) -> None:
        """Network 엔드포인트 호출.

        Args:
            network_id: 네트워크 ID (기본값: 213 - Netflix)
        """
        category = f"networks/network_{network_id}"

        try:
            # Details
            details = self.network.details(network_id)
            self.save_response(category, "details", details)
        except Exception as e:
            self.handle_error(category, "details", e)

        try:
            # Alternative Names
            alt_names = self.network.alternative_names(network_id)
            self.save_response(category, "alternative_names", alt_names)
        except Exception as e:
            self.handle_error(category, "alternative_names", e)

        try:
            # Images
            images = self.network.images(network_id)
            self.save_response(category, "images", images)
        except Exception as e:
            self.handle_error(category, "images", e)

    # =========================================================================
    # Review Endpoints
    # =========================================================================

    def fetch_review(self, review_id: str = "5488c29bc3a3686f4a00004a") -> None:
        """Review 엔드포인트 호출.

        Args:
            review_id: 리뷰 ID
        """
        category = f"reviews/review_{review_id}"

        try:
            # Details
            details = self.review.details(review_id)
            self.save_response(category, "details", details)
        except Exception as e:
            self.handle_error(category, "details", e)

    # =========================================================================
    # Find Endpoints
    # =========================================================================

    def fetch_find(self) -> None:
        """Find 엔드포인트 호출."""
        category = "find"

        try:
            # Find by IMDB ID
            find_results = self.find.find_by_imdb_id("tt0137523")  # Fight Club
            self.save_response(
                category,
                "by_imdb_id",
                find_results,
                {"external_id": "tt0137523", "source": "imdb_id"},
            )
        except Exception as e:
            self.handle_error(category, "by_imdb_id", e)

    # =========================================================================
    # Main Runner
    # =========================================================================

    def run_all(self) -> None:
        """모든 엔드포인트 호출."""
        logger.info("=" * 80)
        logger.info("TMDB API 모든 엔드포인트 호출 시작")
        logger.info("=" * 80)

        start_time = datetime.now()

        # Configuration
        logger.info("\n📝 Configuration 엔드포인트 호출...")
        self.fetch_configuration()

        # Genres
        logger.info("\n🎬 Genres 엔드포인트 호출...")
        self.fetch_genres()

        # Movie Lists
        logger.info("\n🎥 Movie Lists 엔드포인트 호출...")
        self.fetch_movie_lists()

        # Movie Details (여러 영화)
        logger.info("\n📽️ Movie Details 엔드포인트 호출...")
        movie_ids = [550, 278, 238]  # Fight Club, Shawshank, Godfather
        for movie_id in movie_ids:
            logger.info(f"  - Movie ID: {movie_id}")
            self.fetch_movie_details(movie_id)

        # TV Lists
        logger.info("\n📺 TV Lists 엔드포인트 호출...")
        self.fetch_tv_lists()

        # TV Details (여러 TV 시리즈)
        logger.info("\n📡 TV Details 엔드포인트 호출...")
        tv_ids = [1396, 1399, 60735]  # Breaking Bad, Game of Thrones, Flash
        for tv_id in tv_ids:
            logger.info(f"  - TV ID: {tv_id}")
            self.fetch_tv_details(tv_id)

        # TV Season
        logger.info("\n📚 TV Season 엔드포인트 호출...")
        self.fetch_tv_season(1396, 1)

        # TV Episode
        logger.info("\n📄 TV Episode 엔드포인트 호출...")
        self.fetch_tv_episode(1396, 1, 1)

        # People
        logger.info("\n👤 People 엔드포인트 호출...")
        self.fetch_people_list()
        person_ids = [287, 500, 6193]  # Brad Pitt, Tom Cruise, Leo DiCaprio
        for person_id in person_ids:
            logger.info(f"  - Person ID: {person_id}")
            self.fetch_person_details(person_id)

        # Search
        logger.info("\n🔍 Search 엔드포인트 호출...")
        self.fetch_search_results()

        # Discover
        logger.info("\n🌟 Discover 엔드포인트 호출...")
        self.fetch_discover()

        # Trending
        logger.info("\n🔥 Trending 엔드포인트 호출...")
        self.fetch_trending()

        # Collection
        logger.info("\n📦 Collection 엔드포인트 호출...")
        collection_ids = [10, 1241, 2344]  # Star Wars, Harry Potter, Avengers
        for collection_id in collection_ids:
            logger.info(f"  - Collection ID: {collection_id}")
            self.fetch_collection(collection_id)

        # Company
        logger.info("\n🏢 Company 엔드포인트 호출...")
        company_ids = [1, 33, 420]  # Lucasfilm, Pixar, Marvel
        for company_id in company_ids:
            logger.info(f"  - Company ID: {company_id}")
            self.fetch_company(company_id)

        # Keyword
        logger.info("\n🔑 Keyword 엔드포인트 호출...")
        keyword_ids = [9715, 10364, 1453]  # superhero, sword fight, dystopia
        for keyword_id in keyword_ids:
            logger.info(f"  - Keyword ID: {keyword_id}")
            self.fetch_keyword(keyword_id)

        # Network
        logger.info("\n📡 Network 엔드포인트 호출...")
        network_ids = [213, 49, 16]  # Netflix, HBO, CBS
        for network_id in network_ids:
            logger.info(f"  - Network ID: {network_id}")
            self.fetch_network(network_id)

        # Review
        logger.info("\n💬 Review 엔드포인트 호출...")
        self.fetch_review("5488c29bc3a3686f4a00004a")

        # Find
        logger.info("\n🔎 Find 엔드포인트 호출...")
        self.fetch_find()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 결과 요약
        logger.info("\n" + "=" * 80)
        logger.info("TMDB API 엔드포인트 호출 완료")
        logger.info("=" * 80)
        logger.info(f"✅ 성공: {self.success_count}개")
        logger.info(f"❌ 실패: {self.failure_count}개")
        logger.info(f"⏱️ 소요 시간: {duration:.2f}초")
        logger.info(f"📁 저장 위치: {self.output_dir}")

        # 에러 로그 저장
        if self.errors:
            error_file = self.output_dir / "errors.json"
            with open(error_file, "w", encoding="utf-8") as f:
                json.dump(self.errors, f, ensure_ascii=False, indent=2)
            logger.info(f"⚠️ 에러 로그: {error_file}")


def setup_logging() -> None:
    """로깅 설정."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/fetch_tmdb_endpoints.log", encoding="utf-8"),
        ],
    )


def main() -> None:
    """메인 함수."""
    # 로깅 설정
    setup_logging()

    # 출력 디렉터리 설정
    output_dir = Path("data/tmdb_responses")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetcher 실행
    fetcher = TMDBEndpointFetcher(output_dir)
    fetcher.run_all()


if __name__ == "__main__":
    main()
