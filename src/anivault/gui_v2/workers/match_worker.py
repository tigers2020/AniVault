"""Match worker for GUI v2."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace

from anivault.core.matching.engine import MatchingEngine
from anivault.core.matching.pipeline import MatchOptions, process_file_for_matching
from anivault.core.parser.anitopy_parser import AnitopyParser
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
        bundle = await process_file_for_matching(
            file_item.file_path,
            engine=self._matching_engine,
            parser=self._parser,
            options=MatchOptions(),
        )
        if not bundle.metadata:
            return None

        return replace(
            bundle.metadata,
            file_path=file_item.file_path,
            file_type=file_item.file_type,
            genres=file_item.genres,
        )
