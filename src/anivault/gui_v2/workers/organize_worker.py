"""Organize worker for GUI v2."""

from __future__ import annotations

import logging
from pathlib import Path

from anivault.core.models import ScannedFile
from anivault.core.organizer.main import FileOrganizer
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.gui_v2.models import OperationError, OperationProgress
from anivault.gui_v2.workers.base_worker import BaseWorker
from anivault.shared.models.metadata import FileMetadata

logger = logging.getLogger(__name__)


class OrganizeWorker(BaseWorker):
    """Worker that runs file organization."""

    def __init__(
        self,
        files: list[FileMetadata],
        organizer: FileOrganizer,
        dry_run: bool = True,
    ) -> None:
        super().__init__()
        self._files = files
        self._organizer = organizer
        self._dry_run = dry_run
        self._parser = AnitopyParser()

    def run(self) -> None:
        """Run the organize workflow."""
        if self.is_cancelled():
            self.finished.emit([])
            return

        try:
            scanned_files = self._build_scanned_files()
            self.progress.emit(
                OperationProgress(
                    current=0,
                    total=len(scanned_files),
                    stage="organizing",
                    message="정리 계획 생성 중...",
                )
            )
            result = self._organizer.organize(scanned_files, dry_run=self._dry_run)
            self.progress.emit(
                OperationProgress(
                    current=len(scanned_files),
                    total=len(scanned_files),
                    stage="organizing",
                    message="정리 완료",
                )
            )
            self.finished.emit(result)
        except Exception as exc:
            logger.exception("Organize workflow failed")
            self._emit_error(
                OperationError(
                    code="ORGANIZE_FAILED",
                    message="파일 정리 중 오류가 발생했습니다.",
                    detail=str(exc),
                )
            )

    def _build_scanned_files(self) -> list[ScannedFile]:
        """Convert FileMetadata to ScannedFile for organizer."""
        scanned_files: list[ScannedFile] = []
        for index, file_item in enumerate(self._files, start=1):
            if self.is_cancelled():
                break

            parsing_result = self._parser.parse(str(file_item.file_path))

            scanned_files.append(
                ScannedFile(
                    file_path=Path(file_item.file_path),
                    metadata=parsing_result,
                    file_size=0,
                    last_modified=0.0,
                )
            )
            self.progress.emit(
                OperationProgress(
                    current=index,
                    total=len(self._files),
                    stage="organizing",
                    message=f"정리 준비 중... {index}/{len(self._files)}",
                )
            )

        return scanned_files
