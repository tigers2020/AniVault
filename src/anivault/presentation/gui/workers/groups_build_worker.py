"""Groups build worker for GUI v2.

Runs group build off the main thread via BuildGroupsUseCase.
Worker only relays progress/finished/error; all grouping logic lives in the use case.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anivault.application.use_cases.build_groups_use_case import BuildGroupsUseCase

from anivault.presentation.gui.models import OperationError, OperationProgress
from anivault.presentation.gui.workers.base_worker import BaseWorker
from anivault.shared.models.metadata import FileMetadata

logger = logging.getLogger(__name__)


class GroupsBuildWorker(BaseWorker):
    """Worker that builds group display data from FileMetadata (off main thread)."""

    def __init__(
        self,
        files: list[FileMetadata],
        build_groups_use_case: BuildGroupsUseCase,
    ) -> None:
        super().__init__()
        self._files = files
        self._build_groups_use_case = build_groups_use_case

    def run(self) -> None:
        """Build groups from FileMetadata and emit finished(groups)."""
        if self.is_cancelled():
            self.finished.emit([])
            return

        if not self._files:
            logger.warning("GroupsBuildWorker: empty file list")
            self.finished.emit([])
            return

        total = len(self._files)

        def on_progress(current: int, tot: int) -> None:
            self.progress.emit(
                OperationProgress(
                    current=current,
                    total=tot,
                    stage="groups_build",
                    message=f"그룹 빌드 중... {current}/{tot}",
                )
            )

        self.progress.emit(
            OperationProgress(
                current=0,
                total=total,
                stage="groups_build",
                message="그룹 빌드 시작",
            )
        )

        try:
            groups = self._build_groups_use_case.execute(
                self._files,
                progress_callback=on_progress,
            )
            logger.info(
                "GroupsBuildWorker: built %d groups from %d files",
                len(groups),
                len(self._files),
            )
            self.finished.emit(groups)
        except Exception as exc:
            logger.exception("GroupsBuildWorker failed")
            self._emit_error(
                OperationError(
                    code="GROUPS_BUILD_FAILED",
                    message="그룹 빌드 중 오류가 발생했습니다.",
                    detail=str(exc),
                )
            )
