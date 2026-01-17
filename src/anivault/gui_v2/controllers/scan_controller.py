"""Scan controller for GUI v2."""

from __future__ import annotations

import logging
from pathlib import Path

from anivault.gui_v2.app_context import AppContext
from anivault.gui_v2.controllers.base_controller import BaseController
from anivault.gui_v2.models import OperationError
from anivault.gui_v2.workers.scan_worker import ScanWorker
from anivault.shared.constants.file_formats import SubtitleFormats, VideoFormats

logger = logging.getLogger(__name__)


class ScanController(BaseController):
    """Controller for running directory scans."""

    def __init__(self, app_context: AppContext) -> None:
        super().__init__(app_context)

    def scan_directory(self, directory: Path) -> None:
        """Start scanning a directory."""
        if not directory.exists() or not directory.is_dir():
            self.operation_error.emit(
                OperationError(
                    code="INVALID_PATH",
                    message="유효하지 않은 디렉터리입니다.",
                    detail=str(directory),
                )
            )
            return

        extensions = list(VideoFormats.ALL_EXTENSIONS)
        worker = ScanWorker(directory, extensions)
        self._start_worker(worker)

    def scan_subtitle_directory(self, directory: Path) -> None:
        """Start scanning a directory for subtitle files only."""
        if not directory.exists() or not directory.is_dir():
            self.operation_error.emit(
                OperationError(
                    code="INVALID_PATH",
                    message="유효하지 않은 디렉터리입니다.",
                    detail=str(directory),
                )
            )
            return

        extensions = list(SubtitleFormats.EXTENSIONS)
        worker = ScanWorker(directory, extensions)
        self._start_worker(worker)
