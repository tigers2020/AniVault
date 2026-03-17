"""Match use case (Phase 5).

Orchestrates file matching pipeline: find files → parse → match → return FileMetadata list.
GUI path: execute_from_files (grouped by series, one TMDB search per series).
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path

from anivault.application.models.match_services import MatchServices
from anivault.core import normalize_series_title
from anivault.core.matching.pipeline import (
    MatchOptions,
    MatchResultBundle,
    match_result_to_file_metadata,
    process_file_for_matching,
)
from anivault.domain.entities.parser import ParsingAdditionalInfo, ParsingResult
from anivault.shared.constants import FileSystem
from anivault.domain.entities.metadata import FileMetadata

logger = logging.getLogger(__name__)


def _series_key(fm: FileMetadata) -> tuple[str, int | None]:
    """Key for deduplicating TMDB searches: (series_title, year)."""
    raw = (fm.title or "").strip() or (fm.file_path.stem if fm.file_path else "")
    return (normalize_series_title(raw), fm.year)


class MatchUseCase:
    """Use case for matching anime files against TMDB."""

    def __init__(self, services: MatchServices) -> None:
        """Initialize with injected services."""
        self._services = services

    async def execute(
        self,
        directory: Path,
        extensions: tuple[str, ...] | None = None,
        concurrency: int = 4,
    ) -> list[FileMetadata]:
        """Match anime files in directory.

        Args:
            directory: Root directory to scan
            extensions: File extensions to include (default: CLI_VIDEO_EXTENSIONS)
            concurrency: Max concurrent file processing

        Returns:
            List of FileMetadata (includes error-placeholder entries for failed files)
        """
        exts = extensions or tuple(FileSystem.CLI_VIDEO_EXTENSIONS)
        anime_files = self._find_anime_files(directory, exts)

        if not anime_files:
            return []

        return await self._process_files(anime_files, concurrency)

    async def execute_from_files(
        self,
        files: Sequence[FileMetadata],
        progress_callback: Callable[[int, int, str | None], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> list[FileMetadata]:
        """Match files from GUI scan result (grouped by series, one TMDB search per series).

        Preserves input order and length. On cancel, returns results for processed
        series and original FileMetadata for unprocessed files.
        """
        if not files:
            return []
        return await self._process_grouped_files(
            list(files),
            progress_callback=progress_callback,
            cancel_check=cancel_check,
        )

    async def _process_grouped_files(
        self,
        files: list[FileMetadata],
        progress_callback: Callable[[int, int, str | None], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> list[FileMetadata]:
        """Group by (series_title, year), one TMDB search per group, remap to original order."""
        groups: dict[tuple[str, int | None], list[FileMetadata]] = defaultdict(list)
        for fm in files:
            groups[_series_key(fm)].append(fm)

        unique_count = len(groups)
        total = len(files)
        logger.info(
            "MatchUseCase: %d unique series from %d files (%.0f%% API reduction)",
            unique_count,
            total,
            100 * (1 - unique_count / total) if total else 0,
        )

        parser = self._services.parser
        engine = self._services.matching_engine
        options = MatchOptions()

        key_to_bundle: dict[tuple[str, int | None], MatchResultBundle] = {}
        for idx, (key, group_files) in enumerate(groups.items(), start=1):
            if cancel_check and cancel_check():
                break
            if progress_callback is not None:
                progress_callback(idx - 1, unique_count, "matching")

            series_title, _ = key
            representative = group_files[0]
            bundle = await process_file_for_matching(
                representative.file_path,
                engine=engine,
                parser=parser,
                options=options,
                search_title=series_title,
            )
            if bundle is not None:
                key_to_bundle[key] = bundle

        # Build results in original file order; re-inject original FileMetadata fields.
        results: list[FileMetadata] = []
        for fm in files:
            key = _series_key(fm)
            result_bundle = key_to_bundle.get(key)
            if result_bundle and result_bundle.metadata:
                meta = replace(
                    result_bundle.metadata,
                    file_path=fm.file_path,
                    file_type=fm.file_type,
                    episode=fm.episode,
                    season=fm.season,
                    year=fm.year or result_bundle.metadata.year,
                    genres=fm.genres,
                )
                results.append(meta)
            else:
                results.append(fm)

        return results

    def _find_anime_files(self, directory: Path, extensions: tuple[str, ...]) -> list[Path]:
        """Find anime files in directory."""
        anime_files: list[Path] = []
        for ext in extensions:
            anime_files.extend(directory.rglob(f"*{ext}"))
        return anime_files

    async def _process_files(
        self,
        anime_files: list[Path],
        concurrency: int,
    ) -> list[FileMetadata]:
        """Process files concurrently and return FileMetadata list."""
        parser = self._services.parser
        engine = self._services.matching_engine
        semaphore = asyncio.Semaphore(concurrency)

        async def process_one(file_path: Path) -> FileMetadata | MatchResultBundle | None:
            async with semaphore:
                try:
                    bundle = await process_file_for_matching(
                        file_path,
                        engine=engine,
                        parser=parser,
                    )
                    if isinstance(bundle, MatchResultBundle):
                        return bundle.metadata
                    return bundle  # type: ignore[unreachable]
                except (OSError, ValueError, TypeError):
                    return None

        results = await asyncio.gather(
            *[process_one(fp) for fp in anime_files],
            return_exceptions=True,
        )

        return self._convert_results(results, anime_files)

    def _convert_results(
        self,
        results: Sequence[object],
        anime_files: list[Path],
    ) -> list[FileMetadata]:
        """Convert processing results to FileMetadata list."""
        processed: list[FileMetadata] = []
        for i, result in enumerate(results):
            file_path = anime_files[i]

            if isinstance(result, FileMetadata):
                processed.append(result)
            elif isinstance(result, BaseException):
                processed.append(
                    self._error_metadata(file_path, str(result)),
                )
            elif result is None:
                processed.append(self._error_metadata(file_path, "Parsing failed"))
            else:
                processed.append(
                    self._error_metadata(file_path, "Unexpected result type"),
                )

        return processed

    def _error_metadata(self, file_path: Path, error_msg: str) -> FileMetadata:
        """Create FileMetadata placeholder for error case."""
        parsing_result = ParsingResult(
            title=str(file_path.name),
            additional_info=ParsingAdditionalInfo(error=error_msg),
        )
        return match_result_to_file_metadata(file_path, parsing_result, None)
