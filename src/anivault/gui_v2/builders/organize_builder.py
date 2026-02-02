"""Builder for organize-related data structures."""

from __future__ import annotations

import logging
from pathlib import Path

from anivault.core.models import ScannedFile
from anivault.shared.constants.file_formats import SubtitleFormats, VideoFormats
from anivault.shared.models.metadata import FileMetadata
from anivault.shared.types.cli import CLIDirectoryPath, OrganizeOptions
from anivault.shared.utils.metadata_converter import MetadataConverter

logger = logging.getLogger(__name__)


class OrganizeBuilder:
    """Build organize-related data structures from GUI context."""

    @staticmethod
    def build_scanned_files(files: list[FileMetadata]) -> list[ScannedFile]:
        """Convert FileMetadata to ScannedFile for organize service.

        Preserves TMDB match result in additional_info.match_result for year extraction.

        Args:
            files: List of FileMetadata from scan/match results.

        Returns:
            List of ScannedFile for organize pipeline.
        """
        scanned_files: list[ScannedFile] = []
        files_without_year = 0

        for file_metadata in files:
            if not hasattr(file_metadata, "file_path"):
                continue

            if not getattr(file_metadata, "year", None):
                files_without_year += 1

            parsing_result = MetadataConverter.file_metadata_to_parsing_result(file_metadata)
            file_path = file_metadata.file_path
            scanned_files.append(
                ScannedFile(
                    file_path=file_path,
                    metadata=parsing_result,
                    file_size=file_path.stat().st_size if file_path.exists() else 0,
                    last_modified=file_path.stat().st_mtime if file_path.exists() else 0.0,
                )
            )

        if files_without_year > 0:
            logger.debug(
                "build_scanned_files: total=%d, without_year=%d",
                len(scanned_files),
                files_without_year,
            )
        return scanned_files

    @staticmethod
    def build_organize_options(
        directory: Path,
        destination: str = "Anime",
        *,
        dry_run: bool = True,
        use_subtitles: bool = False,
    ) -> OrganizeOptions:
        """Build OrganizeOptions from resolved directory and settings.

        Args:
            directory: Resolved source directory path.
            destination: Target folder for organized files.
            dry_run: Whether this is a dry-run preview.
            use_subtitles: Use subtitle extensions instead of video.

        Returns:
            OrganizeOptions for organize service.
        """
        extensions_source = SubtitleFormats.EXTENSIONS if use_subtitles else VideoFormats.ORGANIZE_EXTENSIONS
        extensions = ",".join(ext.lstrip(".") for ext in extensions_source)

        return OrganizeOptions(
            directory=CLIDirectoryPath(path=directory),
            dry_run=dry_run,
            yes=True,
            enhanced=False,
            destination=destination or "Anime",
            extensions=extensions,
            json_output=False,
            verbose=False,
        )
