"""Match use case (Phase 5).

Orchestrates file matching pipeline: find files → parse → match → return FileMetadata list.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path

from anivault.app.models.match_services import MatchServices
from anivault.core.matching.pipeline import (
    MatchResultBundle,
    match_result_to_file_metadata,
    process_file_for_matching,
)
from anivault.core.parser.models import ParsingAdditionalInfo, ParsingResult
from anivault.shared.constants import FileSystem
from anivault.shared.models.metadata import FileMetadata


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
        exts = extensions or FileSystem.CLI_VIDEO_EXTENSIONS
        anime_files = self._find_anime_files(directory, exts)

        if not anime_files:
            return []

        return await self._process_files(anime_files, concurrency)

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
                    return bundle
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
