"""TMDB API 추가 탐색 - 미수집 엔드포인트 확인.

Collections, Companies, Networks, Keywords, Reviews, Configuration,
TV Episodes, Watch Providers 등 추가 엔드포인트를 수집하여
스키마 호환성을 재검증합니다.
"""

import json
import logging
from pathlib import Path
from typing import Any

from tmdbv3api import (
    Collection,
    Company,
    Configuration,
    Episode,
    Genre,
    Keyword,
    Network,
    Review,
    TMDb,
)

from anivault.config.settings import get_config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 결과 저장 디렉토리
OUTPUT_DIR = Path("scripts/tmdb_api_responses_additional")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class TMDBAPIAdditionalExplorer:
    """TMDB API 추가 탐색기."""

    def __init__(self):
        """TMDB 클라이언트 초기화."""
        config = get_config()

        self.tmdb = TMDb()
        self.tmdb.api_key = config.tmdb.api_key
        self.tmdb.language = "ko-KR"

        logger.info("TMDB API 클라이언트 초기화 완료")

    def save_response(self, name: str, data: Any) -> None:
        """API 응답을 JSON 파일로 저장."""
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

    def explore_collections(self) -> None:
        """Collections API 탐색."""
        logger.info("\n=== Collections API 탐색 시작 ===")
        collection = Collection()

        try:
            # Star Wars Collection
            collection_id = 10
            logger.info(f"Collection Details (ID: {collection_id})")
            details = collection.details(collection_id)
            self.save_response("collection_details", details)

        except Exception as e:
            logger.error(f"Collections API 탐색 중 에러: {e}", exc_info=True)

    def explore_companies(self) -> None:
        """Companies API 탐색."""
        logger.info("\n=== Companies API 탐색 시작 ===")
        company = Company()

        try:
            # Lucasfilm
            company_id = 1
            logger.info(f"Company Details (ID: {company_id})")
            details = company.details(company_id)
            self.save_response("company_details", details)

        except Exception as e:
            logger.error(f"Companies API 탐색 중 에러: {e}", exc_info=True)

    def explore_networks(self) -> None:
        """Networks API 탐색."""
        logger.info("\n=== Networks API 탐색 시작 ===")
        network = Network()

        try:
            # Netflix
            network_id = 213
            logger.info(f"Network Details (ID: {network_id})")
            details = network.details(network_id)
            self.save_response("network_details", details)

        except Exception as e:
            logger.error(f"Networks API 탐색 중 에러: {e}", exc_info=True)

    def explore_keywords(self) -> None:
        """Keywords API 탐색."""
        logger.info("\n=== Keywords API 탐색 시작 ===")
        keyword = Keyword()

        try:
            # Anime keyword
            keyword_id = 210024
            logger.info(f"Keyword Details (ID: {keyword_id})")
            details = keyword.details(keyword_id)
            self.save_response("keyword_details", details)

        except Exception as e:
            logger.error(f"Keywords API 탐색 중 에러: {e}", exc_info=True)

    def explore_reviews(self) -> None:
        """Reviews API 탐색."""
        logger.info("\n=== Reviews API 탐색 시작 ===")
        review = Review()

        try:
            review_id = "5488c29bc3a3686f4a00004a"
            logger.info(f"Review Details (ID: {review_id})")
            details = review.details(review_id)
            self.save_response("review_details", details)

        except Exception as e:
            logger.error(f"Reviews API 탐색 중 에러: {e}", exc_info=True)

    def explore_configuration(self) -> None:
        """Configuration API 탐색."""
        logger.info("\n=== Configuration API 탐색 시작 ===")
        config = Configuration()

        try:
            logger.info("Configuration Info")
            info = config.info()
            self.save_response("configuration_info", info)

            logger.info("Configuration Countries")
            countries = config.countries()
            self.save_response("configuration_countries", countries)

            logger.info("Configuration Languages")
            languages = config.languages()
            self.save_response("configuration_languages", languages)

        except Exception as e:
            logger.error(f"Configuration API 탐색 중 에러: {e}", exc_info=True)

    def explore_tv_episodes(self) -> None:
        """TV Episodes API 탐색."""
        logger.info("\n=== TV Episodes API 탐색 시작 ===")
        episode = Episode()

        try:
            # Attack on Titan S01E01
            tv_id = 1429
            season_number = 1
            episode_number = 1

            logger.info(f"TV Episode Details (TV ID: {tv_id}, S{season_number}E{episode_number})")
            details = episode.details(tv_id, season_number, episode_number)
            self.save_response("tv_episode_details", details)

        except Exception as e:
            logger.error(f"TV Episodes API 탐색 중 에러: {e}", exc_info=True)

    def explore_genres(self) -> None:
        """Genres API 탐색."""
        logger.info("\n=== Genres API 탐색 시작 ===")
        genre = Genre()

        try:
            logger.info("Movie Genres List")
            movie_genres = genre.movie_list()
            self.save_response("genre_movie_list", movie_genres)

            logger.info("TV Genres List")
            tv_genres = genre.tv_list()
            self.save_response("genre_tv_list", tv_genres)

        except Exception as e:
            logger.error(f"Genres API 탐색 중 에러: {e}", exc_info=True)

    def run_exploration(self) -> None:
        """모든 추가 API 탐색 실행."""
        logger.info("🚀 TMDB API 추가 탐색 시작!\n")

        try:
            self.explore_collections()
            self.explore_companies()
            self.explore_networks()
            self.explore_keywords()
            self.explore_reviews()
            self.explore_configuration()
            self.explore_tv_episodes()
            self.explore_genres()

            logger.info("\n✅ 모든 추가 API 탐색 완료!")
            logger.info(f"📁 결과 저장 위치: {OUTPUT_DIR}")

        except Exception as e:
            logger.error(f"API 탐색 중 예상치 못한 에러: {e}", exc_info=True)


def main():
    """메인 함수."""
    explorer = TMDBAPIAdditionalExplorer()
    explorer.run_exploration()


if __name__ == "__main__":
    main()

