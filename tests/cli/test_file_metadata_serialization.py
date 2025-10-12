"""Unit tests for FileMetadata serialization in CLI."""

from pathlib import Path

import pytest

from anivault.cli.helpers.scan import _file_metadata_to_dict
from anivault.shared.metadata_models import FileMetadata


class TestFileMetadataSerialization:
    """Test FileMetadata to dict conversion for CLI JSON output."""

    def test_file_metadata_to_dict_full_data(self) -> None:
        """Test conversion with all fields populated."""
        metadata = FileMetadata(
            title="Attack on Titan",
            file_path=Path("/anime/aot_s01e01.mkv"),
            file_type="mkv",
            year=2013,
            season=1,
            episode=1,
            genres=["Action", "Fantasy", "Drama"],
            overview="Humans fight against Titans.",
            poster_path="/abc123.jpg",
            vote_average=8.5,
            tmdb_id=1429,
            media_type="tv",
        )

        result = _file_metadata_to_dict(metadata)

        assert isinstance(result, dict)
        assert result["title"] == "Attack on Titan"
        assert "aot_s01e01.mkv" in result["file_path"]  # Platform-independent check
        assert result["file_name"] == "aot_s01e01.mkv"
        assert result["file_type"] == "mkv"
        assert result["year"] == 2013
        assert result["season"] == 1
        assert result["episode"] == 1
        assert result["genres"] == ["Action", "Fantasy", "Drama"]
        assert result["overview"] == "Humans fight against Titans."
        assert result["poster_path"] == "/abc123.jpg"
        assert result["vote_average"] == 8.5
        assert result["tmdb_id"] == 1429
        assert result["media_type"] == "tv"

    def test_file_metadata_to_dict_minimal_data(self) -> None:
        """Test conversion with only required fields."""
        metadata = FileMetadata(
            title="Cowboy Bebop",
            file_path=Path("/anime/bebop.mkv"),
            file_type="mkv",
        )

        result = _file_metadata_to_dict(metadata)

        assert isinstance(result, dict)
        assert result["title"] == "Cowboy Bebop"
        assert "bebop.mkv" in result["file_path"]  # Platform-independent check
        assert result["file_name"] == "bebop.mkv"
        assert result["file_type"] == "mkv"
        assert result["year"] is None
        assert result["season"] is None
        assert result["episode"] is None
        assert result["genres"] == []
        assert result["overview"] is None
        assert result["poster_path"] is None
        assert result["vote_average"] is None
        assert result["tmdb_id"] is None
        assert result["media_type"] is None

    def test_file_metadata_to_dict_json_serializable(self) -> None:
        """Test that result is JSON serializable."""
        import json

        metadata = FileMetadata(
            title="Death Note",
            file_path=Path("/anime/death_note.mkv"),
            file_type="mkv",
            year=2006,
            genres=["Thriller", "Mystery"],
        )

        result = _file_metadata_to_dict(metadata)

        # Should not raise exception
        json_str = json.dumps(result)
        assert isinstance(json_str, str)

        # Verify round-trip
        parsed = json.loads(json_str)
        assert parsed["title"] == "Death Note"
        assert parsed["year"] == 2006
        assert parsed["genres"] == ["Thriller", "Mystery"]

    def test_file_metadata_to_dict_with_windows_path(self) -> None:
        """Test conversion with Windows-style path."""
        metadata = FileMetadata(
            title="Test Anime",
            file_path=Path("C:/Users/Test/anime/test.mkv"),
            file_type="mkv",
        )

        result = _file_metadata_to_dict(metadata)

        # Path should be converted to string
        assert isinstance(result["file_path"], str)
        assert "test.mkv" in result["file_path"]
        assert result["file_name"] == "test.mkv"
