"""Convert pipeline result dicts to domain models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from anivault.domain.entities.metadata import FileMetadata


def dict_to_file_metadata(result: dict[str, Any]) -> FileMetadata:
    """Convert parser result dictionary to FileMetadata.

    This function converts the dictionary structure returned by the parser
    worker into a type-safe FileMetadata dataclass instance.

    Args:
        result: Dictionary containing parsed file information with keys:
            - file_path: str (required)
            - file_name: str (used as title, required)
            - file_extension: str (converted to file_type, required)
            - file_size: int (optional, not stored in FileMetadata)
            - status: str (optional, not stored in FileMetadata)
            - worker_id: str (optional, not stored in FileMetadata)

    Returns:
        FileMetadata instance with converted data

    Raises:
        ValueError: If required fields are missing or invalid
    """
    file_path_str = result.get("file_path")
    if not file_path_str:
        msg = "file_path is required in result dictionary"
        raise ValueError(msg)

    file_path = Path(file_path_str)

    title = result.get("file_name") or file_path.name
    if not title:
        msg = "file_name or valid file_path.name is required"
        raise ValueError(msg)

    file_extension = result.get("file_extension", "")
    file_type = file_extension.lstrip(".").lower() if file_extension else file_path.suffix.lstrip(".").lower() or "unknown"

    episode = result.get("episode_number")
    season = result.get("anime_season")
    year = result.get("anime_year")

    return FileMetadata(
        title=title,
        file_path=file_path,
        file_type=file_type,
        year=year,
        season=season,
        episode=episode,
    )
