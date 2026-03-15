"""Match worker for GUI v2."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anivault.app.use_cases.match_use_case import MatchUseCase

from anivault.gui_v2.models import OperationError, OperationProgress
from anivault.gui_v2.workers.base_worker import BaseWorker
from anivault.shared.models.metadata import FileMetadata

logger = logging.getLogger(__name__)


class MatchWorker(BaseWorker):
    """Worker that runs TMDB matching via MatchUseCase."""

    def __init__(
        self,
        files: list[FileMetadata],
        match_use_case: MatchUseCase,
    ) -> None:
        super().__init__()
        self._files = files
        self._match_use_case = match_use_case

    def run(self) -> None:
        """Run the match workflow."""
        try:
            def progress_callback(
                current: int, total: int, stage_key: str | None
            ) -> None:
                _ = stage_key
                self.progress.emit(
                    OperationProgress(
                        current=current,
                        total=total,
                        stage="matching",
                        message="매칭 중...",
                    )
                )

            results = asyncio.run(
                self._match_use_case.execute_from_files(
                    self._files,
                    progress_callback=progress_callback,
                    cancel_check=self.is_cancelled,
                )
            )

            total = len(self._files)
            self.progress.emit(
                OperationProgress(
                    current=total,
                    total=total,
                    stage="matching",
                    message="매칭 완료",
                )
            )
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
