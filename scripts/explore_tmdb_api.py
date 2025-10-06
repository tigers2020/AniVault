"""TMDB API 탐색 스크립트 - 모든 API 응답 구조 분석.

이 스크립트는 tmdbv3api의 주요 클래스와 메서드를 실행하여
실제 API 응답 구조를 수집하고 분석합니다.

김지유의 '영수증 드리븐 개발' 원칙에 따라:
1. 실제 API 응답 수집
2. 응답 구조 분석
3. 최적의 스키마 설계
"""

import json
import logging
from pathlib import Path
from typing import Any

from tmdbv3api import TV, Discover, Movie, Person, Season, TMDb, Trending

from anivault.config.settings import get_config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 결과 저장 디렉토리
OUTPUT_DIR = Path("scripts/tmdb_api_responses")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class TMDBAPIExplorer:
    """TMDB API 탐색기."""

    def __init__(self):
        """TMDB 클라이언트 초기화."""
        config = get_config()

        self.tmdb = TMDb()
        self.tmdb.api_key = config.tmdb.api_key
        self.tmdb.language = "ko-KR"

        logger.info("TMDB API 클라이언트 초기화 완료")

    def save_response(self, name: str, data: Any) -> None:
        """API 응답을 JSON 파일로 저장.

        Args:
            name: 파일명 (확장자 제외)
            data: 저장할 데이터
        """
        output_file = OUTPUT_DIR / f"{name}.json"

        # AsObj를 dict로 변환
        if hasattr(data, "__dict__"):
            data = self._convert_to_dict(data)
        elif isinstance(data, list):
            data = [self._convert_to_dict(item) for item in data]

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 저장: {output_file}")

    def _convert_to_dict(self, obj: Any) -> Any:
        """재귀적으로 AsObj를 dict로 변환."""
        if isinstance(obj, dict):
            return {k: self._convert_to_dict(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._convert_to_dict(item) for item in obj]
        if hasattr(obj, "__dict__"):
            return {
                k: self._convert_to_dict(v)
                for k, v in obj.__dict__.items()
                if not k.startswith("_")
            }
        return obj

    def explore_movie_api(self) -> None:
        """Movie API 탐색."""
        logger.info("\n=== Movie API 탐색 시작 ===")
        movie = Movie()

        try:
            # 1. 인기 영화 목록
            logger.info("1. Popular Movies")
            popular = movie.popular()
            self.save_response("movie_popular", popular)

            # 2. 영화 검색
            logger.info("2. Search Movies")
            search_results = movie.search("Attack on Titan")
            self.save_response("movie_search", search_results)

            # 3. 영화 상세 정보 (Attack on Titan ID 사용)
            if search_results:
                movie_id = search_results[0].id
                logger.info(f"3. Movie Details (ID: {movie_id})")
                details = movie.details(movie_id)
                self.save_response("movie_details", details)

                # 4. 영화 추천
                logger.info(f"4. Movie Recommendations (ID: {movie_id})")
                recommendations = movie.recommendations(movie_id)
                self.save_response("movie_recommendations", recommendations)

                # 5. 유사 영화
                logger.info(f"5. Similar Movies (ID: {movie_id})")
                similar = movie.similar(movie_id)
                self.save_response("movie_similar", similar)

            # 6. 현재 상영작
            logger.info("6. Now Playing Movies")
            now_playing = movie.now_playing()
            self.save_response("movie_now_playing", now_playing)

            # 7. 개봉 예정작
            logger.info("7. Upcoming Movies")
            upcoming = movie.upcoming()
            self.save_response("movie_upcoming", upcoming)

            # 8. 최고 평점 영화
            logger.info("8. Top Rated Movies")
            top_rated = movie.top_rated()
            self.save_response("movie_top_rated", top_rated)

        except Exception as e:
            logger.error(f"Movie API 탐색 중 에러: {e}", exc_info=True)

    def explore_tv_api(self) -> None:
        """TV API 탐색."""
        logger.info("\n=== TV API 탐색 시작 ===")
        tv = TV()

        try:
            # 1. 인기 TV 쇼
            logger.info("1. Popular TV Shows")
            popular = tv.popular()
            self.save_response("tv_popular", popular)

            # 2. TV 검색
            logger.info("2. Search TV Shows")
            search_results = tv.search("Attack on Titan")
            self.save_response("tv_search", search_results)

            # 3. TV 상세 정보
            if search_results:
                tv_id = search_results[0].id
                logger.info(f"3. TV Details (ID: {tv_id})")
                details = tv.details(tv_id)
                self.save_response("tv_details", details)

                # 4. TV 추천
                logger.info(f"4. TV Recommendations (ID: {tv_id})")
                recommendations = tv.recommendations(tv_id)
                self.save_response("tv_recommendations", recommendations)

                # 5. 유사 TV 쇼
                logger.info(f"5. Similar TV Shows (ID: {tv_id})")
                similar = tv.similar(tv_id)
                self.save_response("tv_similar", similar)

            # 6. 현재 방영 중
            logger.info("6. On The Air TV Shows")
            on_the_air = tv.on_the_air()
            self.save_response("tv_on_the_air", on_the_air)

            # 7. 오늘 방영
            logger.info("7. Airing Today TV Shows")
            airing_today = tv.airing_today()
            self.save_response("tv_airing_today", airing_today)

            # 8. 최고 평점 TV 쇼
            logger.info("8. Top Rated TV Shows")
            top_rated = tv.top_rated()
            self.save_response("tv_top_rated", top_rated)

        except Exception as e:
            logger.error(f"TV API 탐색 중 에러: {e}", exc_info=True)

    def explore_season_api(self) -> None:
        """Season API 탐색."""
        logger.info("\n=== Season API 탐색 시작 ===")
        season = Season()

        try:
            # Attack on Titan TV ID (예: 1429)
            tv_id = 1429
            season_number = 1

            logger.info(f"Season Details (TV ID: {tv_id}, Season: {season_number})")
            details = season.details(tv_id, season_number)
            self.save_response("season_details", details)

        except Exception as e:
            logger.error(f"Season API 탐색 중 에러: {e}", exc_info=True)

    def explore_person_api(self) -> None:
        """Person API 탐색."""
        logger.info("\n=== Person API 탐색 시작 ===")
        person = Person()

        try:
            # 1. 인기 인물
            logger.info("1. Popular People")
            popular = person.popular()
            self.save_response("person_popular", popular)

            # 2. 인물 상세 정보 (예: Tom Hanks ID: 31)
            person_id = 31
            logger.info(f"2. Person Details (ID: {person_id})")
            details = person.details(person_id)
            self.save_response("person_details", details)

            # 3. 인물 검색
            logger.info("3. Search People")
            search_results = person.search("Tom Hanks")
            self.save_response("person_search", search_results)

        except Exception as e:
            logger.error(f"Person API 탐색 중 에러: {e}", exc_info=True)

    def explore_discover_api(self) -> None:
        """Discover API 탐색."""
        logger.info("\n=== Discover API 탐색 시작 ===")
        discover = Discover()

        try:
            # 1. 인기 영화 발견
            logger.info("1. Discover Popular Movies")
            movies = discover.discover_movies({
                "sort_by": "popularity.desc",
                "page": 1,
            })
            self.save_response("discover_movies_popular", movies)

            # 2. 애니메이션 장르 영화
            logger.info("2. Discover Animation Movies")
            animation_movies = discover.discover_movies({
                "with_genres": 16,  # Animation genre ID
                "sort_by": "vote_average.desc",
                "vote_count.gte": 100,
            })
            self.save_response("discover_movies_animation", animation_movies)

            # 3. TV 쇼 발견
            logger.info("3. Discover Popular TV Shows")
            tv_shows = discover.discover_tv_shows({
                "sort_by": "popularity.desc",
                "page": 1,
            })
            self.save_response("discover_tv_popular", tv_shows)

            # 4. 애니메이션 TV 쇼
            logger.info("4. Discover Animation TV Shows")
            animation_tv = discover.discover_tv_shows({
                "with_genres": 16,  # Animation genre ID
                "sort_by": "vote_average.desc",
                "vote_count.gte": 50,
            })
            self.save_response("discover_tv_animation", animation_tv)

        except Exception as e:
            logger.error(f"Discover API 탐색 중 에러: {e}", exc_info=True)

    def explore_trending_api(self) -> None:
        """Trending API 탐색."""
        logger.info("\n=== Trending API 탐색 시작 ===")
        trending = Trending()

        try:
            # 1. 오늘의 트렌드 영화
            logger.info("1. Trending Movies (Day)")
            movies_day = trending.movie_day()
            self.save_response("trending_movies_day", movies_day)

            # 2. 이번 주 트렌드 영화
            logger.info("2. Trending Movies (Week)")
            movies_week = trending.movie_week()
            self.save_response("trending_movies_week", movies_week)

            # 3. 오늘의 트렌드 TV 쇼
            logger.info("3. Trending TV Shows (Day)")
            tv_day = trending.tv_day()
            self.save_response("trending_tv_day", tv_day)

            # 4. 이번 주 트렌드 TV 쇼
            logger.info("4. Trending TV Shows (Week)")
            tv_week = trending.tv_week()
            self.save_response("trending_tv_week", tv_week)

            # 5. 오늘의 트렌드 인물
            logger.info("5. Trending People (Day)")
            people_day = trending.people_day()
            self.save_response("trending_people_day", people_day)

            # 6. 이번 주 트렌드 인물
            logger.info("6. Trending People (Week)")
            people_week = trending.people_week()
            self.save_response("trending_people_week", people_week)

        except Exception as e:
            logger.error(f"Trending API 탐색 중 에러: {e}", exc_info=True)

    def run_exploration(self) -> None:
        """모든 API 탐색 실행."""
        logger.info("🚀 TMDB API 전체 탐색 시작!\n")

        try:
            self.explore_movie_api()
            self.explore_tv_api()
            self.explore_season_api()
            self.explore_person_api()
            self.explore_discover_api()
            self.explore_trending_api()

            logger.info("\n✅ 모든 API 탐색 완료!")
            logger.info(f"📁 결과 저장 위치: {OUTPUT_DIR}")

            # 요약 정보 생성
            self.generate_summary()

        except Exception as e:
            logger.error(f"API 탐색 중 예상치 못한 에러: {e}", exc_info=True)

    def generate_summary(self) -> None:
        """API 응답 요약 정보 생성."""
        logger.info("\n=== API 응답 요약 생성 ===")

        summary = {
            "total_files": 0,
            "endpoints": {},
            "common_fields": set(),
            "unique_fields": {},
        }

        for json_file in OUTPUT_DIR.glob("*.json"):
            summary["total_files"] += 1

            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)

            endpoint_name = json_file.stem

            # 응답 구조 분석
            if isinstance(data, list) and data:
                sample = data[0]
            elif isinstance(data, dict):
                sample = data
            else:
                continue

            fields = set(sample.keys()) if isinstance(sample, dict) else set()
            summary["endpoints"][endpoint_name] = {
                "fields": list(fields),
                "field_count": len(fields),
            }

            # 공통 필드 추출
            if not summary["common_fields"]:
                summary["common_fields"] = fields
            else:
                summary["common_fields"] &= fields

        # set을 list로 변환
        summary["common_fields"] = list(summary["common_fields"])

        # 요약 저장
        summary_file = OUTPUT_DIR / "_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 요약 정보 저장: {summary_file}")
        logger.info(f"📊 총 {summary['total_files']}개 응답 파일 생성")
        logger.info(f"🔍 공통 필드: {', '.join(summary['common_fields'][:10])}...")


def main():
    """메인 함수."""
    explorer = TMDBAPIExplorer()
    explorer.run_exploration()


if __name__ == "__main__":
    main()

