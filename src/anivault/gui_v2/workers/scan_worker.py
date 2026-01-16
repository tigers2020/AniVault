"""Scan worker for GUI v2."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from anivault.core.pipeline import run_pipeline
from anivault.gui_v2.models import OperationError, OperationProgress
from anivault.gui_v2.workers.base_worker import BaseWorker
from anivault.shared.metadata_models import FileMetadata

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
            metadata_list = self._convert_results(results)
            logger.info("Converted to %d FileMetadata objects", len(metadata_list))
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
        except Exception as exc:  # noqa: BLE001
            logger.exception("Scan pipeline failed")
            self._emit_error(
                OperationError(
                    code="SCAN_FAILED",
                    message="스캔 중 오류가 발생했습니다.",
                    detail=str(exc),
                )
            )

    def _convert_results(self, results: list[dict[str, Any]]) -> list[FileMetadata]:
        """Convert pipeline results to FileMetadata."""
        logger.info("Converting %d pipeline results to FileMetadata", len(results))
        metadata_list: list[FileMetadata] = []
        skipped_count = 0
        for i, result in enumerate(results):
            try:
                file_path = Path(result["file_path"])
                title = result.get("title") or result.get("file_name") or file_path.stem
                file_type = result.get("file_type") or result.get("file_extension", "").lstrip(".") or file_path.suffix.lstrip(".")
                
                if not title:
                    logger.warning("Result %d: Empty title, using file path stem: %s", i, file_path.stem)
                    title = file_path.stem
                
                if not file_type:
                    logger.warning("Result %d: Empty file_type, using file extension: %s", i, file_path.suffix)
                    file_type = file_path.suffix.lstrip(".") or "unknown"
                
                metadata_list.append(
                    FileMetadata(
                        title=title,
                        file_path=file_path,
                        file_type=file_type,
                        year=result.get("year"),
                        season=result.get("season"),
                        episode=result.get("episode"),
                        genres=result.get("genres", []),
                        overview=result.get("overview"),
                        poster_path=result.get("poster_path"),
                        vote_average=result.get("vote_average"),
                        tmdb_id=result.get("tmdb_id"),
                        media_type=result.get("media_type"),
                    )
                )
            except (KeyError, ValueError, TypeError) as exc:
                skipped_count += 1
                logger.warning("Skipping invalid scan result %d: %s (result keys: %s)", i, exc, list(result.keys()) if isinstance(result, dict) else "not a dict")
        
        logger.info("Converted %d results to FileMetadata (%d skipped)", len(metadata_list), skipped_count)
        if skipped_count > 0:
            logger.warning("Skipped %d invalid results out of %d total", skipped_count, len(results))
        return metadata_list
