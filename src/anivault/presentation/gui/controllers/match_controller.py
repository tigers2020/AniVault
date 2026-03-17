"""Match controller for GUI v2."""

from __future__ import annotations

import logging

from anivault.presentation.gui.app_context import AppContext
from anivault.presentation.gui.controllers.base_controller import BaseController
from anivault.presentation.gui.models import OperationError
from anivault.presentation.gui.workers.match_worker import MatchWorker
from anivault.domain.entities.metadata import FileMetadata

logger = logging.getLogger(__name__)


class MatchController(BaseController):
    """Controller for TMDB matching."""

    def __init__(self, app_context: AppContext) -> None:
        super().__init__(app_context)

    def match_files(self, files: list[FileMetadata]) -> None:
        """Start matching files."""
        if not files:
            self.operation_error.emit(
                OperationError(
                    code="NO_FILES",
                    message="매칭할 파일이 없습니다.",
                )
            )
            return

        match_use_case = self.app_context.container.match_use_case()
        worker = MatchWorker(files, match_use_case)
        self._start_worker(worker)
