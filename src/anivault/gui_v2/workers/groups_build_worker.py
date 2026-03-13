"""Groups build worker for GUI v2.

Runs FileGrouper and series regrouping off the main thread to prevent UI freeze.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path
from typing import Callable

from anivault.core.file_grouper import FileGrouper
from anivault.core.file_grouper.grouper import TitleExtractor
from anivault.core.models import ScannedFile
from anivault.core.parser.models import ParsingAdditionalInfo, ParsingResult
from anivault.gui_v2.models import OperationError
from anivault.gui_v2.workers.base_worker import BaseWorker
from anivault.shared.models.metadata import FileMetadata

logger = logging.getLogger(__name__)

RESOLUTION_PATTERNS = ("1080p", "720p", "480p", "2160p", "4k", "1440p")
LANG_PATTERNS_KO = ("korean", "kor", "ko")
LANG_PATTERNS_JA = ("japanese", "jap", "ja")
LANG_PATTERNS_EN = ("english", "eng", "en")


def _path_resolved(p: Path) -> Path:
    """Resolve path; return original on OSError."""
    try:
        return p.resolve()
    except OSError:
        return p


def _scanned_file_from_metadata(
    fm: FileMetadata,
    title_extractor: TitleExtractor,
) -> ScannedFile:
    """Build a ScannedFile from FileMetadata for FileGrouper."""
    series_title = title_extractor.extract_title_with_parser(fm.file_path.name)
    if not series_title or series_title == "unknown":
        series_title = title_extractor.extract_base_title(fm.file_path.name)
    if not series_title or series_title == "unknown":
        series_title = fm.title
    parsing_result = ParsingResult(
        title=series_title,
        episode=fm.episode,
        season=fm.season,
        year=fm.year,
        quality=None,
        release_group=None,
        additional_info=ParsingAdditionalInfo(),
    )
    path_exists = fm.file_path.exists()
    return ScannedFile(
        file_path=fm.file_path,
        metadata=parsing_result,
        file_size=fm.file_path.stat().st_size if path_exists else 0,
        last_modified=fm.file_path.stat().st_mtime if path_exists else 0.0,
    )


def _normalize_series_name(group_title: str) -> str:
    """Strip episode/season suffix from group title for series key."""
    name = re.sub(r"\s*-\s*\d+.*$", "", group_title)
    name = re.sub(r"\s*E\d+.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*Episode\s*\d+.*$", "", name, flags=re.IGNORECASE)
    name = name.strip()
    return name if name and len(name) >= 2 else group_title


def _display_title_for_files(
    all_files: list[FileMetadata],
    fallback: str,
) -> str:
    """Best display title from matched files by confidence; else fallback."""
    matched_with_title = [fm for fm in all_files if fm.tmdb_id is not None and fm.title and fm.title != fm.file_path.name]
    if not matched_with_title:
        return fallback
    best = max(
        matched_with_title,
        key=lambda fm: getattr(fm, "match_confidence", 0.0) or 0.0,
    )
    return best.title


def _confidence_for_files(all_files: list[FileMetadata], matched: bool) -> int:
    """Max match confidence (0-100) for group; 100 if matched and no values."""
    values = [
        int(getattr(fm, "match_confidence", 0.0) * 100)
        for fm in all_files
        if fm.tmdb_id is not None and getattr(fm, "match_confidence", None) is not None
    ]
    if values:
        return max(values)
    return 100 if matched else 0


def _resolution_for_files(all_files: list[FileMetadata]) -> str:
    """Infer resolution from filenames/quality; default 'unknown'."""
    resolutions: set[str] = set()
    for item in all_files:
        name_lower = item.file_path.name.lower()
        for res in RESOLUTION_PATTERNS:
            if res in name_lower:
                resolutions.add(res.upper().replace("P", "p"))
                break
        if hasattr(item, "quality") and item.quality:
            resolutions.add(item.quality)
    return next(iter(resolutions), "unknown") if resolutions else "unknown"


def _language_for_files(all_files: list[FileMetadata]) -> str:
    """Infer language from filenames; default 'unknown'."""
    for item in all_files:
        name_lower = item.file_path.name.lower()
        if any(lang in name_lower for lang in LANG_PATTERNS_KO):
            return "ko"
        if any(lang in name_lower for lang in LANG_PATTERNS_JA):
            return "ja"
        if any(lang in name_lower for lang in LANG_PATTERNS_EN):
            return "en"
    return "unknown"


def _build_group_dict(
    index: int,
    series_name: str,
    all_files: list[FileMetadata],
) -> dict:
    """Build one group display dict from series name and file list."""
    seasons = {item.season for item in all_files if item.season is not None}
    episodes = {item.episode for item in all_files if item.episode is not None}
    matched = any(item.tmdb_id is not None for item in all_files)
    display_title = _display_title_for_files(all_files, series_name)
    confidence = _confidence_for_files(all_files, matched)
    resolution = _resolution_for_files(all_files)
    language = _language_for_files(all_files)
    return {
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


def _collect_tmdb_buckets(
    series_groups: dict[str, list[FileMetadata]],
) -> tuple[
    dict[int, list[tuple[str, list[FileMetadata]]]],
    dict[str, list[FileMetadata]],
]:
    """Split groups into tmdb_id buckets and unmerged (no tmdb_id)."""
    tmdb_to_items: dict[int, list[tuple[str, list[FileMetadata]]]] = {}
    unmerged: dict[str, list[FileMetadata]] = {}

    for series_name, file_list in series_groups.items():
        tmdb_ids: list[int] = [tid for fm in file_list if (tid := getattr(fm, "tmdb_id", None)) is not None]
        if not tmdb_ids:
            unmerged[series_name] = file_list
            continue
        canonical_id: int = Counter(tmdb_ids).most_common(1)[0][0]
        if canonical_id not in tmdb_to_items:
            tmdb_to_items[canonical_id] = []
        tmdb_to_items[canonical_id].append((series_name, file_list))

    return tmdb_to_items, unmerged


def _best_title_for_merge(
    items: list[tuple[str, list[FileMetadata]]],
    tmdb_id: int,
) -> str:
    """Pick best display title from items by match_confidence (for merged group key)."""
    best_title = ""
    best_confidence = -1.0
    for _, file_list in items:
        for fm in file_list:
            if fm.tmdb_id != tmdb_id or not fm.title or fm.title == fm.file_path.name:
                continue
            conf = getattr(fm, "match_confidence", 0.0) or 0.0
            if conf > best_confidence:
                best_confidence = conf
                best_title = fm.title or ""
    return best_title if best_title else items[0][0]


def _apply_merged_group(
    series_groups: dict[str, list[FileMetadata]],
    tmdb_id: int,
    items: list[tuple[str, list[FileMetadata]]],
) -> None:
    """Merge multiple items into one group and write into series_groups."""
    all_files: list[FileMetadata] = []
    for _, file_list in items:
        all_files.extend(file_list)
    merge_key = _best_title_for_merge(items, tmdb_id)
    series_groups[merge_key] = all_files
    logger.info(
        "Merged %d groups by tmdb_id=%d into '%s' (%d files)",
        len(items),
        tmdb_id,
        merge_key,
        len(all_files),
    )


def _merge_groups_by_tmdb_id(
    series_groups: dict[str, list[FileMetadata]],
) -> None:
    """Merge groups that share the same tmdb_id (post-TMDB matching consolidation).

    Modifies series_groups in place. Groups without tmdb_id are left unchanged.
    When multiple groups share a tmdb_id, they are merged into one; the merged
    group uses the TMDB title as key (from highest-confidence matched file).
    """
    tmdb_to_items, unmerged = _collect_tmdb_buckets(series_groups)
    series_groups.clear()
    series_groups.update(unmerged)

    for tmdb_id, items in tmdb_to_items.items():
        if len(items) == 1:
            key, file_list = items[0]
            series_groups[key] = file_list
        else:
            _apply_merged_group(series_groups, tmdb_id, items)


def _file_groups_to_series_groups(
    file_groups: list,
    files_by_path: dict[Path, FileMetadata],
) -> dict[str, list[FileMetadata]]:
    """Map FileGrouper groups to series name -> list[FileMetadata]."""
    series_groups: dict[str, list[FileMetadata]] = {}
    for group in file_groups:
        group_files_metadata = [files_by_path[resolved] for sf in group.files if (resolved := _path_resolved(sf.file_path)) in files_by_path]
        if not group_files_metadata:
            continue
        series_name = _normalize_series_name(group.title)
        if series_name not in series_groups:
            series_groups[series_name] = []
        series_groups[series_name].extend(group_files_metadata)
    return series_groups


def _build_groups_from_metadata(files: list[FileMetadata]) -> list[dict]:
    """Build group display data from FileMetadata (CPU-heavy, run off main thread)."""
    title_extractor = TitleExtractor()
    file_grouper = FileGrouper()

    scanned_files = [_scanned_file_from_metadata(fm, title_extractor) for fm in files]
    file_groups = file_grouper.group_files(scanned_files)

    files_by_path = {_path_resolved(fm.file_path): fm for fm in files}
    series_groups = _file_groups_to_series_groups(file_groups, files_by_path)

    _merge_groups_by_tmdb_id(series_groups)

    grouped_resolved = {_path_resolved(fm.file_path) for files_list in series_groups.values() for fm in files_list}
    ungrouped = [fm for fm in files if _path_resolved(fm.file_path) not in grouped_resolved]
    if ungrouped:
        logger.info("Adding %d ungrouped file(s) to '미분류' group", len(ungrouped))
        series_groups["미분류"] = series_groups.get("미분류", []) + ungrouped

    return [_build_group_dict(index, series_name, all_files) for index, (series_name, all_files) in enumerate(series_groups.items(), start=1)]


def _tmdb_id_for_file_in_map(
    fm: FileMetadata,
    files_by_path: dict[Path, FileMetadata],
    path_resolved: Callable[[Path], Path],
) -> int | None:
    """Return tmdb_id for this file if it exists in files_by_path and has tmdb_id."""
    resolved = path_resolved(fm.file_path)
    new_fm = files_by_path.get(resolved)
    if new_fm is None:
        return None
    tid = getattr(new_fm, "tmdb_id", None)
    return tid if isinstance(tid, int) else None


def _needs_merge_by_tmdb_id(
    existing_groups: list[dict],
    files_by_path: dict[Path, FileMetadata],
    path_resolved: Callable[[Path], Path],
) -> bool:
    """Return True if multiple groups would share the same tmdb_id after update (merge required)."""
    tmdb_id_to_group_indices: dict[int, set[int]] = {}
    for idx, g in enumerate(existing_groups):
        for fm in g.get("file_metadata_list", []):
            tid = _tmdb_id_for_file_in_map(fm, files_by_path, path_resolved)
            if tid is not None:
                tmdb_id_to_group_indices.setdefault(tid, set()).add(idx)
    return any(len(indices) > 1 for indices in tmdb_id_to_group_indices.values())


def apply_metadata_update_to_groups(
    existing_groups: list[dict],
    files: list[FileMetadata],
) -> list[dict] | None:
    """Fast path: update group metadata when only tmdb_id/title changed (no re-grouping).

    Returns updated groups if path set matches, else None (caller should do full rebuild).
    Forces full rebuild when multiple groups share the same tmdb_id (merge required).
    """
    if not existing_groups or not files:
        return None

    files_by_path = {_path_resolved(fm.file_path): fm for fm in files}
    new_paths = set(files_by_path)

    existing_paths = set()
    for g in existing_groups:
        for fm in g.get("file_metadata_list", []):
            existing_paths.add(_path_resolved(fm.file_path))

    if new_paths != existing_paths or len(new_paths) != len(files):
        return None

    if _needs_merge_by_tmdb_id(existing_groups, files_by_path, _path_resolved):
        return None

    updated: list[dict] = []
    for idx, group in enumerate(existing_groups, start=1):
        old_list = group.get("file_metadata_list", [])
        new_list = [files_by_path[_path_resolved(fm.file_path)] for fm in old_list if _path_resolved(fm.file_path) in files_by_path]
        if not new_list:
            continue
        series_name = group.get("title", "")
        updated.append(_build_group_dict(idx, series_name, new_list))
    return updated
