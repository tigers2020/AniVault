"""Scan worker for GUI v2."""

from __future__ import annotations

import logging
from pathlib import Path

from anivault.core.pipeline import run_pipeline
from anivault.gui_v2.models import OperationError, OperationProgress
from anivault.gui_v2.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class ScanWorker(BaseWorker):
    """Worker that runs the scan pipeline."""

    def __init__(self, root_path: Path, extensions: list[str]) -> None:
        super().__init__()
        self._root_path = root_path
        self._extensions = extensions

    def run(self) -> None:
        """Run the scan pipeline."""
        if self.is_cancelled():
            self.finished.emit([])
            return

        self.progress.emit(
            OperationProgress(
                current=0,
                total=0,
                stage="scanning",
                message="스캔 시작",
            )
        )

        try:
            logger.info("Starting pipeline scan: root_path=%s, extensions=%s", self._root_path, self._extensions)
            results = run_pipeline(str(self._root_path), self._extensions)
            logger.info("Pipeline returned %d results", len(results))
            metadata_list = results
            self.progress.emit(
                OperationProgress(
                    current=len(metadata_list),
                    total=len(metadata_list),
                    stage="scanning",
                    message="스캔 완료",
                )
            )
            self.finished.emit(metadata_list)
            logger.info("Emitted finished signal with %d FileMetadata objects", len(metadata_list))
        except Exception as exc:
            logger.exception("Scan pipeline failed")
            self._emit_error(
                OperationError(
                    code="SCAN_FAILED",
                    message="스캔 중 오류가 발생했습니다.",
                    detail=str(exc),
                )
            )
