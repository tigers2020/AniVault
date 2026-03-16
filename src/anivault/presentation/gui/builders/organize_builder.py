"""Builder for organize-related data structures."""

from __future__ import annotations

from pathlib import Path

from anivault.shared.constants.file_formats import SubtitleFormats, VideoFormats
from anivault.shared.types.cli import CLIDirectoryPath, OrganizeOptions


class OrganizeBuilder:
    """Build organize-related data structures from GUI context."""

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
