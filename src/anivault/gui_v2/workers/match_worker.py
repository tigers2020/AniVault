"""Match worker for GUI v2."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import replace

from anivault.core.matching.engine import MatchingEngine
from anivault.core.matching.pipeline import MatchOptions, process_file_for_matching
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.gui_v2.models import OperationError, OperationProgress
from anivault.gui_v2.workers.base_worker import BaseWorker
from anivault.shared.models.metadata import FileMetadata

logger = logging.getLogger(__name__)


def _title_year_key(fm: FileMetadata) -> tuple[str, int | None]:
    """Key for deduplicating TMDB searches: (title, year)."""
    title = (fm.title or "").strip() or fm.file_path.stem
    return (title, fm.year)


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
        except Exception as exc:
            logger.exception("Match workflow failed")
            self._emit_error(
                OperationError(
                    code="MATCH_FAILED",
                    message="TMDB 매칭 중 오류가 발생했습니다.",
                    detail=str(exc),
                )
            )

    async def _match_files(self) -> list[FileMetadata]:
        """Match files asynchronously. Groups by (title, year) to reduce TMDB API calls."""
        # Group files by (title, year) - same series = one TMDB search
        groups: dict[tuple[str, int | None], list[FileMetadata]] = defaultdict(list)
        for fm in self._files:
            groups[_title_year_key(fm)].append(fm)

        unique_count = len(groups)
        total = len(self._files)
        logger.info(
            "MatchWorker: %d unique titles from %d files (%.0f%% API reduction)",
            unique_count,
            total,
            100 * (1 - unique_count / total) if total else 0,
        )

        # Match each unique (title, year) once
        key_to_bundle: dict = {}
        for idx, (key, group_files) in enumerate(groups.items(), start=1):
            if self.is_cancelled():
                break

            self.progress.emit(
                OperationProgress(
                    current=idx - 1,
                    total=unique_count,
                    stage="matching",
                    message=f"매칭 중... {idx}/{unique_count} (고유 제목)",
                )
            )

            representative = group_files[0]
            bundle = await process_file_for_matching(
                representative.file_path,
                engine=self._matching_engine,
                parser=self._parser,
                options=MatchOptions(),
            )
            key_to_bundle[key] = bundle

        # Build results in original file order
        results: list[FileMetadata] = []
        for fm in self._files:
            key = _title_year_key(fm)
            bundle = key_to_bundle.get(key)
            if bundle and bundle.metadata:
                meta = replace(
                    bundle.metadata,
                    file_path=fm.file_path,
                    file_type=fm.file_type,
                    episode=fm.episode,
                    season=fm.season,
                    year=fm.year or bundle.metadata.year,
                    genres=fm.genres,
                )
                results.append(meta)
            else:
                results.append(fm)

        self.progress.emit(
            OperationProgress(
                current=len(results),
                total=total,
                stage="matching",
                message="매칭 완료",
            )
        )
        return results
