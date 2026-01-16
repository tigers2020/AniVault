"""Match worker for GUI v2."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from anivault.core.matching.engine import MatchingEngine
from anivault.core.matching.models import MatchResult
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.core.parser.models import ParsingAdditionalInfo, ParsingResult
from anivault.gui_v2.models import OperationError, OperationProgress
from anivault.gui_v2.workers.base_worker import BaseWorker
from anivault.shared.metadata_models import FileMetadata

logger = logging.getLogger(__name__)


class MatchWorker(BaseWorker):
    """Worker that runs TMDB matching."""

    def __init__(
        self,
        files: list[FileMetadata],
        matching_engine: MatchingEngine,
    ) -> None:
        super().__init__()
        self._files = files
        self._matching_engine = matching_engine
        self._parser = AnitopyParser()

    def run(self) -> None:
        """Run the match workflow."""
        try:
            results = asyncio.run(self._match_files())
            self.finished.emit(results)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Match workflow failed")
            self._emit_error(
                OperationError(
                    code="MATCH_FAILED",
                    message="TMDB 매칭 중 오류가 발생했습니다.",
                    detail=str(exc),
                )
            )

    async def _match_files(self) -> list[FileMetadata]:
        """Match files asynchronously."""
        total = len(self._files)
        results: list[FileMetadata] = []

        for index, file_item in enumerate(self._files, start=1):
            if self.is_cancelled():
                break

            self.progress.emit(
                OperationProgress(
                    current=index - 1,
                    total=total,
                    stage="matching",
                    message=f"매칭 중... {index - 1}/{total}",
                )
            )

            metadata = await self._match_single_file(file_item)
            if metadata:
                results.append(metadata)

        self.progress.emit(
            OperationProgress(
                current=len(results),
                total=total,
                stage="matching",
                message="매칭 완료",
            )
        )
        return results

    async def _match_single_file(self, file_item: FileMetadata) -> FileMetadata | None:
        """Match a single file."""
        parsing_result = self._parser.parse(str(file_item.file_path))
        if not parsing_result:
            return None

        parsing_result = self._normalize_parsing_result(parsing_result, file_item)
        parsing_dict = self._parsing_result_to_dict(parsing_result)
        match_result = await self._matching_engine.find_match(parsing_dict)

        return self._match_result_to_file_metadata(file_item, parsing_result, match_result)

    def _normalize_parsing_result(
        self,
        parsing_result: ParsingResult | dict[str, Any] | Any,
        file_item: FileMetadata,
    ) -> ParsingResult:
        """Ensure ParsingResult type."""
        if isinstance(parsing_result, ParsingResult):
            return parsing_result

        if isinstance(parsing_result, dict):
            return ParsingResult(
                title=parsing_result.get("anime_title", file_item.title),
                episode=parsing_result.get("episode_number"),
                season=parsing_result.get("season"),
                year=parsing_result.get("anime_year"),
                quality=parsing_result.get("video_resolution"),
                release_group=parsing_result.get("release_group"),
                additional_info=ParsingAdditionalInfo(),
            )

        return ParsingResult(
            title=getattr(parsing_result, "title", file_item.title),
            episode=getattr(parsing_result, "episode", file_item.episode),
            season=getattr(parsing_result, "season", file_item.season),
            year=getattr(parsing_result, "year", file_item.year),
            quality=getattr(parsing_result, "quality", None),
            release_group=getattr(parsing_result, "release_group", None),
            additional_info=ParsingAdditionalInfo(),
        )

    def _parsing_result_to_dict(self, parsing_result: ParsingResult) -> dict[str, Any]:
        """Convert ParsingResult to dict for matching engine."""
        return {
            "anime_title": parsing_result.title,
            "episode_number": parsing_result.episode,
            "release_group": parsing_result.release_group,
            "video_resolution": parsing_result.quality,
            "anime_year": parsing_result.year,
        }

    def _match_result_to_file_metadata(
        self,
        file_item: FileMetadata,
        parsing_result: ParsingResult,
        match_result: MatchResult | None,
    ) -> FileMetadata:
        """Convert match result to FileMetadata."""
        title = parsing_result.title
        year = parsing_result.year
        season = parsing_result.season
        episode = parsing_result.episode

        overview = None
        poster_path = None
        vote_average = None
        tmdb_id = None
        media_type = None

        if match_result is not None:
            title = match_result.title
            year = match_result.year or year
            tmdb_id = match_result.tmdb_id
            media_type = match_result.media_type
            poster_path = match_result.poster_path
            overview = match_result.overview
            vote_average = match_result.vote_average

        return FileMetadata(
            title=title,
            file_path=file_item.file_path,
            file_type=file_item.file_type,
            year=year,
            season=season,
            episode=episode,
            genres=file_item.genres,
            overview=overview,
            poster_path=poster_path,
            vote_average=vote_average,
            tmdb_id=tmdb_id,
            media_type=media_type,
        )
