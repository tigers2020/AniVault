"""Match controller for GUI v2."""

from __future__ import annotations

import logging

from anivault.gui_v2.app_context import AppContext
from anivault.gui_v2.controllers.base_controller import BaseController
from anivault.gui_v2.models import OperationError
from anivault.gui_v2.workers.match_worker import MatchWorker
from anivault.shared.metadata_models import FileMetadata

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

        matching_engine = self.app_context.container.matching_engine()
        worker = MatchWorker(files, matching_engine)
        self._start_worker(worker)
