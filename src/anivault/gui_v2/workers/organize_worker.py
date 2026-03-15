"""Organize worker for GUI v2."""

from __future__ import annotations

import logging

from anivault.app.use_cases.organize_use_case import OrganizeUseCase
from anivault.config import Settings
from anivault.gui_v2.models import OperationError, OperationProgress
from anivault.gui_v2.workers.base_worker import BaseWorker
from anivault.shared.models.metadata import FileMetadata

logger = logging.getLogger(__name__)


class OrganizeWorker(BaseWorker):
    """Worker that runs file organization (preview-only in R2: emits plan, no execute)."""

    def __init__(
        self,
        files: list[FileMetadata],
        organize_use_case: OrganizeUseCase,
        dry_run: bool = True,
        settings: Settings | None = None,
    ) -> None:
        super().__init__()
        self._files = files
        self._organize_use_case = organize_use_case
        self._dry_run = dry_run
        self._settings = settings

    def run(self) -> None:
        """Run the organize workflow (coarse progress: start then complete)."""
        if self.is_cancelled():
            self.finished.emit([])
            return

        n = len(self._files)
        try:
            self.progress.emit(
                OperationProgress(
                    current=0,
                    total=n,
                    stage="organizing",
                    message="정리 계획 생성 중...",
                )
            )
            plan = self._organize_use_case.generate_plan_from_metadata(
                self._files, settings=self._settings
            )
            self.progress.emit(
                OperationProgress(
                    current=n,
                    total=n,
                    stage="organizing",
                    message="정리 완료",
                )
            )
            self.finished.emit(plan)
        except Exception as exc:
            logger.exception("Organize workflow failed")
            self._emit_error(
                OperationError(
                    code="ORGANIZE_FAILED",
                    message="파일 정리 중 오류가 발생했습니다.",
                    detail=str(exc),
                )
            )
