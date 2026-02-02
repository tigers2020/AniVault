"""Groups build worker for GUI v2.

Runs FileGrouper and series regrouping off the main thread to prevent UI freeze.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from anivault.core.file_grouper import FileGrouper
from anivault.core.file_grouper.grouper import TitleExtractor
from anivault.core.models import ScannedFile
from anivault.core.parser.models import ParsingAdditionalInfo, ParsingResult
from anivault.gui_v2.models import OperationError
from anivault.gui_v2.workers.base_worker import BaseWorker
from anivault.shared.models.metadata import FileMetadata

logger = logging.getLogger(__name__)


class GroupsBuildWorker(BaseWorker):
    """Worker that builds group display data from FileMetadata (off main thread)."""

    def __init__(self, files: list[FileMetadata]) -> None:
        super().__init__()
        self._files = files

    def run(self) -> None:
        """Build groups from FileMetadata and emit finished(groups)."""
        if self.is_cancelled():
            self.finished.emit([])
            return

        if not self._files:
            logger.warning("GroupsBuildWorker: empty file list")
            self.finished.emit([])
            return

        try:
            groups = _build_groups_from_metadata(self._files)
            logger.info("GroupsBuildWorker: built %d groups from %d files", len(groups), len(self._files))
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


def _build_groups_from_metadata(files: list[FileMetadata]) -> list[dict]:
    """Build group display data from FileMetadata (CPU-heavy, run off main thread)."""
    title_extractor = TitleExtractor()
    file_grouper = FileGrouper()

    # Convert FileMetadata to ScannedFile for FileGrouper
    scanned_files: list[ScannedFile] = []
    for file_metadata in files:
        series_title = title_extractor.extract_title_with_parser(file_metadata.file_path.name)
        if not series_title or series_title == "unknown":
            series_title = title_extractor.extract_base_title(file_metadata.file_path.name)
        if not series_title or series_title == "unknown":
            series_title = file_metadata.title
        parsing_result = ParsingResult(
            title=series_title,
            episode=file_metadata.episode,
            season=file_metadata.season,
            year=file_metadata.year,
            quality=None,
            release_group=None,
            additional_info=ParsingAdditionalInfo(),
        )
        scanned_file = ScannedFile(
            file_path=file_metadata.file_path,
            metadata=parsing_result,
            file_size=file_metadata.file_path.stat().st_size if file_metadata.file_path.exists() else 0,
            last_modified=file_metadata.file_path.stat().st_mtime if file_metadata.file_path.exists() else 0.0,
        )
        scanned_files.append(scanned_file)

    file_groups = file_grouper.group_files(scanned_files)

    def _path_resolved(p: Path) -> Path:
        try:
            return p.resolve()
        except OSError:
            return p

    # O(n) index: path -> FileMetadata (avoids O(n²) nested loop)
    files_by_path: dict[Path, FileMetadata] = {_path_resolved(fm.file_path): fm for fm in files}

    series_groups: dict[str, list[FileMetadata]] = {}
    for group in file_groups:
        group_files_metadata: list[FileMetadata] = []
        for scanned_file in group.files:
            resolved = _path_resolved(scanned_file.file_path)
            if resolved in files_by_path:
                group_files_metadata.append(files_by_path[resolved])

        if not group_files_metadata:
            continue

        group_title = group.title
        series_name = re.sub(r"\s*-\s*\d+.*$", "", group_title)
        series_name = re.sub(r"\s*E\d+.*$", "", series_name, flags=re.IGNORECASE)
        series_name = re.sub(r"\s*Episode\s*\d+.*$", "", series_name, flags=re.IGNORECASE)
        series_name = series_name.strip()

        if not series_name or len(series_name) < 2:
            series_name = group_title

        if series_name not in series_groups:
            series_groups[series_name] = []
        series_groups[series_name].extend(group_files_metadata)

    grouped_resolved: set[Path] = {_path_resolved(fm.file_path) for files_list in series_groups.values() for fm in files_list}
    ungrouped = [fm for fm in files if _path_resolved(fm.file_path) not in grouped_resolved]
    if ungrouped:
        logger.info("Adding %d ungrouped file(s) to '미분류' group", len(ungrouped))
        series_groups["미분류"] = series_groups.get("미분류", []) + ungrouped

    groups: list[dict] = []
    for index, (series_name, all_files) in enumerate(series_groups.items(), start=1):
        seasons = {item.season for item in all_files if item.season is not None}
        episodes = {item.episode for item in all_files if item.episode is not None}
        matched = any(item.tmdb_id is not None for item in all_files)

        display_title = series_name
        if matched:
            matched_with_title = [fm for fm in all_files if fm.tmdb_id is not None and fm.title and fm.title != fm.file_path.name]
            if matched_with_title:
                best = max(
                    matched_with_title,
                    key=lambda fm: getattr(fm, "match_confidence", 0.0) or 0.0,
                )
                display_title = best.title

        confidence_values = [
            int(getattr(fm, "match_confidence", 0.0) * 100)
            for fm in all_files
            if fm.tmdb_id is not None and getattr(fm, "match_confidence", None) is not None
        ]
        confidence = max(confidence_values) if confidence_values else (100 if matched else 0)

        resolutions = set()
        for item in all_files:
            file_name_lower = item.file_path.name.lower()
            for res in ["1080p", "720p", "480p", "2160p", "4k", "1440p"]:
                if res in file_name_lower:
                    resolutions.add(res.upper().replace("P", "p"))
                    break
            if hasattr(item, "quality") and item.quality:
                resolutions.add(item.quality)
        if not resolutions:
            resolutions.add("unknown")
        resolution = next(iter(resolutions), "unknown")

        language = "unknown"
        for item in all_files:
            file_name_lower = item.file_path.name.lower()
            if any(lang in file_name_lower for lang in ["korean", "kor", "ko"]):
                language = "ko"
                break
            if any(lang in file_name_lower for lang in ["japanese", "jap", "ja"]):
                language = "ja"
                break
            if any(lang in file_name_lower for lang in ["english", "eng", "en"]):
                language = "en"
                break

        groups.append(
            {
                "id": index,
                "title": display_title,
                "season": min(seasons) if seasons else 1,
                "episodes": len(episodes) if episodes else len(all_files),
                "files": len(all_files),
                "matched": matched,
                "confidence": confidence,
                "resolution": resolution,
                "language": language,
                "file_metadata_list": all_files,
            }
        )

    return groups


def apply_metadata_update_to_groups(
    existing_groups: list[dict],
    files: list[FileMetadata],
) -> list[dict] | None:
    """Fast path: update group metadata when only tmdb_id/title changed (no re-grouping).

    Returns updated groups if path set matches, else None (caller should do full rebuild).
    """
    if not existing_groups or not files:
        return None

    def _path_resolved(p: Path) -> Path:
        try:
            return p.resolve()
        except OSError:
            return p

    files_by_path: dict[Path, FileMetadata] = {_path_resolved(fm.file_path): fm for fm in files}
    new_paths = set(files_by_path)

    # Collect paths from existing groups
    existing_paths: set[Path] = set()
    for g in existing_groups:
        for fm in g.get("file_metadata_list", []):
            existing_paths.add(_path_resolved(fm.file_path))

    if new_paths != existing_paths or len(new_paths) != len(files):
        return None

    # Same path set - do metadata-only update
    updated: list[dict] = []
    for idx, group in enumerate(existing_groups, start=1):
        old_list = group.get("file_metadata_list", [])
        new_list = [files_by_path[_path_resolved(fm.file_path)] for fm in old_list if _path_resolved(fm.file_path) in files_by_path]
        if not new_list:
            continue

        all_files = new_list
        seasons = {item.season for item in all_files if item.season is not None}
        episodes = {item.episode for item in all_files if item.episode is not None}
        matched = any(item.tmdb_id is not None for item in all_files)
        series_name = group.get("title", "")

        display_title = series_name
        if matched:
            matched_with_title = [fm for fm in all_files if fm.tmdb_id is not None and fm.title and fm.title != fm.file_path.name]
            if matched_with_title:
                best = max(
                    matched_with_title,
                    key=lambda fm: getattr(fm, "match_confidence", 0.0) or 0.0,
                )
                display_title = best.title

        confidence_values = [
            int(getattr(fm, "match_confidence", 0.0) * 100)
            for fm in all_files
            if fm.tmdb_id is not None and getattr(fm, "match_confidence", None) is not None
        ]
        confidence = max(confidence_values) if confidence_values else (100 if matched else 0)

        resolutions = set()
        for item in all_files:
            fn = item.file_path.name.lower()
            for res in ["1080p", "720p", "480p", "2160p", "4k", "1440p"]:
                if res in fn:
                    resolutions.add(res.upper().replace("P", "p"))
                    break
            if hasattr(item, "quality") and item.quality:
                resolutions.add(item.quality)
        resolution = next(iter(resolutions), "unknown") if resolutions else "unknown"

        language = "unknown"
        for item in all_files:
            fn = item.file_path.name.lower()
            if any(lang in fn for lang in ["korean", "kor", "ko"]):
                language = "ko"
                break
            if any(lang in fn for lang in ["japanese", "jap", "ja"]):
                language = "ja"
                break
            if any(lang in fn for lang in ["english", "eng", "en"]):
                language = "en"
                break

        updated.append(
            {
                "id": idx,
                "title": display_title,
                "season": min(seasons) if seasons else 1,
                "episodes": len(episodes) if episodes else len(all_files),
                "files": len(all_files),
                "matched": matched,
                "confidence": confidence,
                "resolution": resolution,
                "language": language,
                "file_metadata_list": all_files,
            }
        )
    return updated
