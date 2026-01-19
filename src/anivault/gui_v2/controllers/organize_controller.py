"""Organize controller for GUI v2."""

from __future__ import annotations

import logging

from anivault.core.log_manager import OperationLogManager
from anivault.core.organizer.main import FileOrganizer
from anivault.gui_v2.app_context import AppContext
from anivault.gui_v2.controllers.base_controller import BaseController
from anivault.gui_v2.models import OperationError
from anivault.gui_v2.workers.organize_worker import OrganizeWorker
from anivault.shared.models.metadata import FileMetadata
from anivault.utils.resource_path import get_project_root

logger = logging.getLogger(__name__)


class OrganizeController(BaseController):
    """Controller for file organization."""

    def __init__(self, app_context: AppContext) -> None:
        super().__init__(app_context)

    def organize_files(self, files: list[FileMetadata], dry_run: bool = True) -> None:
        """Start organizing files."""
        if not files:
            self.operation_error.emit(
                OperationError(
                    code="NO_FILES",
                    message="정리할 파일이 없습니다.",
                )
            )
            return

        log_manager = OperationLogManager(get_project_root())
        organizer = FileOrganizer(log_manager=log_manager, settings=self.app_context.settings)
        worker = OrganizeWorker(files, organizer, dry_run=dry_run)
        self._start_worker(worker)
