"""Unit tests for presentation layer metadata models."""

from __future__ import annotations

from pathlib import Path

import pytest

from anivault.shared.metadata_models import FileMetadata


class TestFileMetadata:
    """Test suite for FileMetadata dataclass."""

    def test_create_with_all_fields(self) -> None:
        """Test creating FileMetadata with all fields provided."""
        metadata = FileMetadata(
            title="Attack on Titan",
            year=2013,
            season=1,
            episode=1,
            file_path=Path("/anime/aot_s01e01.mkv"),
            file_type="mkv",
            genres=["Action", "Fantasy", "Drama"],
            overview="Humans fight against Titans to survive.",
            poster_path="/abc123.jpg",
            vote_average=8.5,
            tmdb_id=1429,
            media_type="tv",
        )

        assert metadata.title == "Attack on Titan"
        assert metadata.year == 2013
        assert metadata.season == 1
        assert metadata.episode == 1
        assert metadata.file_path == Path("/anime/aot_s01e01.mkv")
        assert metadata.file_type == "mkv"
        assert metadata.genres == ["Action", "Fantasy", "Drama"]
        assert metadata.overview == "Humans fight against Titans to survive."
        assert metadata.poster_path == "/abc123.jpg"
        assert metadata.vote_average == 8.5
        assert metadata.tmdb_id == 1429
        assert metadata.media_type == "tv"

    def test_create_with_minimal_fields(self) -> None:
        """Test creating FileMetadata with only required fields."""
        metadata = FileMetadata(
            title="Cowboy Bebop",
            file_path=Path("/anime/cowboy_bebop.mkv"),
            file_type="mkv",
        )

        assert metadata.title == "Cowboy Bebop"
        assert metadata.file_path == Path("/anime/cowboy_bebop.mkv")
        assert metadata.file_type == "mkv"
        assert metadata.year is None
        assert metadata.season is None
        assert metadata.episode is None
        assert metadata.genres == []  # Empty list by default
        assert metadata.overview is None
        assert metadata.poster_path is None
        assert metadata.vote_average is None
        assert metadata.tmdb_id is None
        assert metadata.media_type is None

    def test_genres_defaults_to_empty_list(self) -> None:
        """Test that genres field defaults to an empty list."""
        metadata = FileMetadata(
            title="Death Note",
            file_path=Path("/anime/death_note.mkv"),
            file_type="mkv",
        )

        assert metadata.genres == []
        assert isinstance(metadata.genres, list)

    def test_genres_not_shared_between_instances(self) -> None:
        """Test that default genres list is not shared between instances."""
        metadata1 = FileMetadata(
            title="Anime 1",
            file_path=Path("/anime1.mkv"),
            file_type="mkv",
        )
        metadata2 = FileMetadata(
            title="Anime 2",
            file_path=Path("/anime2.mkv"),
            file_type="mkv",
        )

        metadata1.genres.append("Action")

        assert metadata1.genres == ["Action"]
        assert metadata2.genres == []  # Should still be empty

    def test_empty_title_raises_error(self) -> None:
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            FileMetadata(
                title="",
                file_path=Path("/anime/test.mkv"),
                file_type="mkv",
            )

    def test_invalid_file_path_type_raises_error(self) -> None:
        """Test that non-Path file_path raises TypeError."""
        with pytest.raises(TypeError, match="file_path must be a Path object"):
            FileMetadata(
                title="Test Anime",
                file_path="/anime/test.mkv",  # type: ignore[arg-type]
                file_type="mkv",
            )

    def test_empty_file_type_raises_error(self) -> None:
        """Test that empty file_type raises ValueError."""
        with pytest.raises(ValueError, match="file_type cannot be empty"):
            FileMetadata(
                title="Test Anime",
                file_path=Path("/anime/test.mkv"),
                file_type="",
            )

    def test_year_too_old_raises_error(self) -> None:
        """Test that year before 1900 raises ValueError."""
        with pytest.raises(ValueError, match=r"year must be between 1900 and \d+"):
            FileMetadata(
                title="Ancient Anime",
                year=1899,
                file_path=Path("/anime/ancient.mkv"),
                file_type="mkv",
            )

    def test_year_too_far_future_raises_error(self) -> None:
        """Test that year too far in future raises ValueError."""
        with pytest.raises(ValueError, match=r"year must be between 1900 and \d+"):
            FileMetadata(
                title="Future Anime",
                year=2050,
                file_path=Path("/anime/future.mkv"),
                file_type="mkv",
            )

    def test_negative_season_raises_error(self) -> None:
        """Test that negative season raises ValueError."""
        with pytest.raises(ValueError, match="season must be non-negative"):
            FileMetadata(
                title="Test Anime",
                season=-1,
                file_path=Path("/anime/test.mkv"),
                file_type="mkv",
            )

    def test_negative_episode_raises_error(self) -> None:
        """Test that negative episode raises ValueError."""
        with pytest.raises(ValueError, match="episode must be non-negative"):
            FileMetadata(
                title="Test Anime",
                episode=-1,
                file_path=Path("/anime/test.mkv"),
                file_type="mkv",
            )

    def test_vote_average_below_range_raises_error(self) -> None:
        """Test that vote_average below 0.0 raises ValueError."""
        with pytest.raises(
            ValueError, match=r"vote_average must be between 0\.0 and 10\.0"
        ):
            FileMetadata(
                title="Test Anime",
                vote_average=-0.1,
                file_path=Path("/anime/test.mkv"),
                file_type="mkv",
            )

    def test_vote_average_above_range_raises_error(self) -> None:
        """Test that vote_average above 10.0 raises ValueError."""
        with pytest.raises(
            ValueError, match=r"vote_average must be between 0\.0 and 10\.0"
        ):
            FileMetadata(
                title="Test Anime",
                vote_average=10.1,
                file_path=Path("/anime/test.mkv"),
                file_type="mkv",
            )

    def test_display_name_with_season_and_episode(self) -> None:
        """Test display_name property with season and episode."""
        metadata = FileMetadata(
            title="Attack on Titan",
            season=1,
            episode=1,
            file_path=Path("/anime/aot.mkv"),
            file_type="mkv",
        )

        assert metadata.display_name == "Attack on Titan S01E01"

    def test_display_name_with_episode_only(self) -> None:
        """Test display_name property with episode but no season."""
        metadata = FileMetadata(
            title="Cowboy Bebop",
            episode=5,
            file_path=Path("/anime/bebop.mkv"),
            file_type="mkv",
        )

        assert metadata.display_name == "Cowboy Bebop E05"

    def test_display_name_with_year_only(self) -> None:
        """Test display_name property with year but no episode info."""
        metadata = FileMetadata(
            title="Your Name",
            year=2016,
            file_path=Path("/anime/your_name.mkv"),
            file_type="mkv",
        )

        assert metadata.display_name == "Your Name (2016)"

    def test_display_name_title_only(self) -> None:
        """Test display_name property with title only."""
        metadata = FileMetadata(
            title="Spirited Away",
            file_path=Path("/anime/spirited_away.mkv"),
            file_type="mkv",
        )

        assert metadata.display_name == "Spirited Away"

    def test_file_name_property(self) -> None:
        """Test file_name property returns filename without path."""
        metadata = FileMetadata(
            title="Attack on Titan",
            file_path=Path("/anime/subdir/aot_s01e01.mkv"),
            file_type="mkv",
        )

        assert metadata.file_name == "aot_s01e01.mkv"

    def test_season_zero_allowed(self) -> None:
        """Test that season 0 (specials) is allowed."""
        metadata = FileMetadata(
            title="Test Anime",
            season=0,
            episode=1,
            file_path=Path("/anime/test_s00e01.mkv"),
            file_type="mkv",
        )

        assert metadata.season == 0
        assert metadata.display_name == "Test Anime S00E01"

    def test_episode_zero_allowed(self) -> None:
        """Test that episode 0 is allowed."""
        metadata = FileMetadata(
            title="Test Anime",
            season=1,
            episode=0,
            file_path=Path("/anime/test_s01e00.mkv"),
            file_type="mkv",
        )

        assert metadata.episode == 0
        assert metadata.display_name == "Test Anime S01E00"
