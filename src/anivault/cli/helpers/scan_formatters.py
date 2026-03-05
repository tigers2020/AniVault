"""Scan command formatting helpers.

Extracted from scan.py for better code organization.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from anivault.shared.constants import CLIDefaults
from anivault.shared.constants.scan_fields import ScanColors
from anivault.shared.models.metadata import FileMetadata

from .format_utils import format_size


def display_scan_results(
    results: list[FileMetadata],
    console: Console,
    *,
    show_tmdb: bool = True,
) -> None:
    """Display scan results in a formatted table.

    Args:
        results: List of FileMetadata instances
        console: Rich console for output
        show_tmdb: Whether to show TMDB metadata
    """
    if not results:
        console.print(f"[{ScanColors.YELLOW}]No files found.[/{ScanColors.YELLOW}]")
        return

    table = Table(title="Anime File Scan Results")
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Title", style="green")
    table.add_column("Episode", style=ScanColors.BLUE)
    table.add_column("Year", style="magenta")

    if show_tmdb:
        table.add_column("TMDB Match", style=ScanColors.YELLOW)
        table.add_column("TMDB Rating", style="red")
        table.add_column("Status", style="green")

    for metadata in results:
        file_path = str(metadata.file_path)
        title = metadata.title or "Unknown"
        episode = str(metadata.episode) if metadata.episode else "-"
        year = str(metadata.year) if metadata.year else "-"

        if show_tmdb and metadata.tmdb_id:
            tmdb_title = metadata.title or "Unknown"
            rating = f"{metadata.vote_average:.1f}" if metadata.vote_average else "N/A"
            status = "Matched" if metadata.tmdb_id else "No match"

            table.add_row(
                Path(file_path).name,
                title,
                episode,
                year,
                tmdb_title,
                str(rating),
                status,
            )
        else:
            table.add_row(Path(file_path).name, title, episode, year)

    console.print(table)


def collect_scan_data(
    results: list[FileMetadata],
    directory: Path,
    *,
    show_tmdb: bool = True,
) -> dict[str, object]:
    """Collect scan data for JSON output.

    Args:
        results: List of FileMetadata instances
        directory: Scanned directory path
        show_tmdb: Whether TMDB metadata was enriched

    Returns:
        Dictionary containing scan statistics and file data
    """
    total_files = len(results)
    total_size = CLIDefaults.DEFAULT_FILE_SIZE
    file_counts_by_extension: dict[str, int] = {}
    scanned_paths: list[str] = []
    file_data: list[dict[str, object]] = []

    for metadata in results:
        file_path = str(metadata.file_path)
        scanned_paths.append(file_path)

        try:
            file_size = metadata.file_path.stat().st_size
            total_size += file_size
        except (OSError, TypeError):
            file_size = CLIDefaults.DEFAULT_FILE_SIZE

        file_ext = metadata.file_path.suffix.lower()
        file_counts_by_extension[file_ext] = file_counts_by_extension.get(file_ext, 0) + 1

        file_info: dict[str, object] = {
            "file_path": file_path,
            "file_name": metadata.file_name,
            "file_size": file_size,
            "file_extension": file_ext,
            "title": metadata.title,
            "year": metadata.year,
            "season": metadata.season,
            "episode": metadata.episode,
        }

        if show_tmdb and metadata.tmdb_id:
            file_info["tmdb_id"] = metadata.tmdb_id
            file_info["tmdb_title"] = metadata.title
            file_info["tmdb_rating"] = metadata.vote_average
            file_info["tmdb_genres"] = metadata.genres
            file_info["tmdb_overview"] = metadata.overview
            file_info["tmdb_poster_path"] = metadata.poster_path
            file_info["tmdb_media_type"] = metadata.media_type

        file_data.append(file_info)

    return {
        "scan_summary": {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_formatted": format_size(total_size),
            "scanned_directory": str(directory),
            "metadata_enriched": show_tmdb,
        },
        "file_statistics": {
            "counts_by_extension": file_counts_by_extension,
            "scanned_paths": scanned_paths,
        },
        "files": file_data,
    }
