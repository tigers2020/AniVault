"""Unit tests for reconciliation strategies and conflict resolution."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.core.reconciliation_strategies import (
    ReconciliationEngine,
    ReconciliationStrategy,
    ReconciliationResult
)
from src.core.consistency_validator import DataConflict, ConflictType, ConflictSeverity


class TestReconciliationEngine:
    """Test reconciliation engine functionality."""

    @pytest.fixture
    def mock_metadata_cache(self):
        """Create a mock metadata cache."""
        cache = Mock()
        cache.set.return_value = None
        return cache

    @pytest.fixture
    def engine(self, mock_metadata_cache):
        """Create a reconciliation engine with mock cache."""
        return ReconciliationEngine(metadata_cache=mock_metadata_cache)

    def test_reconciliation_result_creation(self):
        """Test ReconciliationResult object creation."""
        result = ReconciliationResult(
            success=True,
            strategy_used=ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH,
            conflicts_resolved=5,
            conflicts_failed=0,
            details=["Resolved conflict 1", "Resolved conflict 2"],
            errors=[]
        )

        assert result.success is True
        assert result.strategy_used == ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH
        assert result.conflicts_resolved == 5
        assert result.conflicts_failed == 0
        assert len(result.details) == 2
        assert len(result.errors) == 0
        assert isinstance(result.timestamp, datetime)

    def test_database_wins_strategy_missing_in_cache(self, engine, mock_metadata_cache):
        """Test database-wins strategy for missing cache data."""
        conflict = DataConflict(
            conflict_type=ConflictType.MISSING_IN_CACHE,
            entity_type="anime_metadata",
            entity_id=12345,
            db_data={"tmdb_id": 12345, "title": "Test Anime", "version": 2},
            severity=ConflictSeverity.MEDIUM
        )

        result = engine.reconcile_conflicts([conflict], ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH)

        assert result.success is True
        assert result.conflicts_resolved == 1
        assert result.conflicts_failed == 0
        assert result.strategy_used == ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH
        mock_metadata_cache.set.assert_called_once_with("anime_metadata:12345", conflict.db_data)

    def test_database_wins_strategy_version_mismatch(self, engine, mock_metadata_cache):
        """Test database-wins strategy for version mismatch."""
        conflict = DataConflict(
            conflict_type=ConflictType.VERSION_MISMATCH,
            entity_type="anime_metadata",
            entity_id=12345,
            db_data={"tmdb_id": 12345, "title": "Test Anime", "version": 3},
            cache_data={"tmdb_id": 12345, "title": "Test Anime", "version": 1},
            severity=ConflictSeverity.HIGH
        )

        result = engine.reconcile_conflicts([conflict], ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH)

        assert result.success is True
        assert result.conflicts_resolved == 1
        assert result.conflicts_failed == 0
        mock_metadata_cache.set.assert_called_once_with("anime_metadata:12345", conflict.db_data)

    def test_cache_wins_strategy_missing_in_database(self, engine):
        """Test cache-wins strategy for missing database data."""
        conflict = DataConflict(
            conflict_type=ConflictType.MISSING_IN_DATABASE,
            entity_type="anime_metadata",
            entity_id=12345,
            cache_data={"tmdb_id": 12345, "title": "Test Anime", "version": 2},
            severity=ConflictSeverity.HIGH
        )

        with patch.object(engine.db_manager, 'transaction') as mock_transaction:
            mock_session = Mock()
            mock_transaction.return_value.__enter__.return_value = mock_session
            mock_transaction.return_value.__exit__.return_value = None

            # Mock database query to return None (not found)
            mock_session.query.return_value.filter.return_value.first.return_value = None

            result = engine.reconcile_conflicts([conflict], ReconciliationStrategy.CACHE_IS_SOURCE_OF_TRUTH)

        assert result.success is True
        assert result.conflicts_resolved == 1
        assert result.conflicts_failed == 0
        assert result.strategy_used == ReconciliationStrategy.CACHE_IS_SOURCE_OF_TRUTH

    def test_last_modified_wins_strategy_timestamp_comparison(self, engine, mock_metadata_cache):
        """Test last-modified-wins strategy with timestamp comparison."""
        # Create timestamps with cache being newer
        cache_time = datetime(2023, 6, 1, tzinfo=timezone.utc)
        db_time = datetime(2023, 5, 1, tzinfo=timezone.utc)

        conflict = DataConflict(
            conflict_type=ConflictType.DATA_MISMATCH,
            entity_type="anime_metadata",
            entity_id=12345,
            db_data={"tmdb_id": 12345, "title": "DB Title", "updated_at": db_time.isoformat()},
            cache_data={"tmdb_id": 12345, "title": "Cache Title", "updated_at": cache_time.isoformat()},
            severity=ConflictSeverity.MEDIUM
        )

        with patch.object(engine.db_manager, 'transaction') as mock_transaction:
            mock_session = Mock()
            mock_transaction.return_value.__enter__.return_value = mock_session
            mock_transaction.return_value.__exit__.return_value = None

            # Mock database query to return existing record
            mock_anime = Mock()
            mock_anime.tmdb_id = 12345
            mock_anime.version = 1
            mock_session.query.return_value.filter.return_value.first.return_value = mock_anime

            result = engine.reconcile_conflicts([conflict], ReconciliationStrategy.LAST_MODIFIED_WINS)

        assert result.success is True
        assert result.conflicts_resolved == 1
        assert result.conflicts_failed == 0
        # Should update database with cache data since cache is newer

    def test_manual_review_strategy(self, engine):
        """Test manual review strategy (no automatic resolution)."""
        conflict = DataConflict(
            conflict_type=ConflictType.DATA_MISMATCH,
            entity_type="anime_metadata",
            entity_id=12345,
            db_data={"tmdb_id": 12345, "title": "DB Title"},
            cache_data={"tmdb_id": 12345, "title": "Cache Title"},
            severity=ConflictSeverity.HIGH
        )

        result = engine.reconcile_conflicts([conflict], ReconciliationStrategy.MANUAL_REVIEW)

        assert result.success is True
        assert result.conflicts_resolved == 1  # Marked for review counts as resolved
        assert result.conflicts_failed == 0
        assert result.strategy_used == ReconciliationStrategy.MANUAL_REVIEW

    def test_reconcile_multiple_conflicts(self, engine, mock_metadata_cache):
        """Test reconciling multiple conflicts."""
        conflicts = [
            DataConflict(
                conflict_type=ConflictType.MISSING_IN_CACHE,
                entity_type="anime_metadata",
                entity_id=12345,
                db_data={"tmdb_id": 12345, "title": "Anime 1"},
                severity=ConflictSeverity.MEDIUM
            ),
            DataConflict(
                conflict_type=ConflictType.MISSING_IN_CACHE,
                entity_type="anime_metadata",
                entity_id=67890,
                db_data={"tmdb_id": 67890, "title": "Anime 2"},
                severity=ConflictSeverity.MEDIUM
            )
        ]

        result = engine.reconcile_conflicts(conflicts, ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH)

        assert result.success is True
        assert result.conflicts_resolved == 2
        assert result.conflicts_failed == 0
        assert mock_metadata_cache.set.call_count == 2

    def test_reconcile_with_errors(self, engine):
        """Test reconciliation with errors."""
        # Create a conflict that will cause an error
        conflict = DataConflict(
            conflict_type=ConflictType.MISSING_IN_DATABASE,
            entity_type="unknown_entity",  # Unknown entity type
            entity_id=12345,
            cache_data={"id": 12345, "data": "test"},
            severity=ConflictSeverity.HIGH
        )

        result = engine.reconcile_conflicts([conflict], ReconciliationStrategy.CACHE_IS_SOURCE_OF_TRUTH)

        assert result.success is False
        assert result.conflicts_resolved == 0
        assert result.conflicts_failed == 1
        assert len(result.errors) == 1

    def test_get_recommended_strategy_missing_in_cache(self, engine):
        """Test strategy recommendation when most conflicts are missing in cache."""
        conflicts = [
            DataConflict(ConflictType.MISSING_IN_CACHE, "anime_metadata", 1),
            DataConflict(ConflictType.MISSING_IN_CACHE, "anime_metadata", 2),
            DataConflict(ConflictType.MISSING_IN_DATABASE, "anime_metadata", 3),
        ]

        strategy = engine.get_recommended_strategy(conflicts)
        assert strategy == ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH

    def test_get_recommended_strategy_missing_in_database(self, engine):
        """Test strategy recommendation when most conflicts are missing in database."""
        conflicts = [
            DataConflict(ConflictType.MISSING_IN_DATABASE, "anime_metadata", 1),
            DataConflict(ConflictType.MISSING_IN_DATABASE, "anime_metadata", 2),
            DataConflict(ConflictType.MISSING_IN_CACHE, "anime_metadata", 3),
        ]

        strategy = engine.get_recommended_strategy(conflicts)
        assert strategy == ReconciliationStrategy.CACHE_IS_SOURCE_OF_TRUTH

    def test_get_recommended_strategy_version_mismatches(self, engine):
        """Test strategy recommendation when most conflicts are version mismatches."""
        conflicts = [
            DataConflict(ConflictType.VERSION_MISMATCH, "anime_metadata", 1),
            DataConflict(ConflictType.DATA_MISMATCH, "anime_metadata", 2),
            DataConflict(ConflictType.MISSING_IN_CACHE, "anime_metadata", 3),
        ]

        strategy = engine.get_recommended_strategy(conflicts)
        assert strategy == ReconciliationStrategy.LAST_MODIFIED_WINS

    def test_get_recommended_strategy_empty_list(self, engine):
        """Test strategy recommendation with empty conflict list."""
        strategy = engine.get_recommended_strategy([])
        assert strategy == ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH

    def test_parse_datetime_valid_string(self, engine):
        """Test parsing valid datetime string."""
        dt_str = "2023-06-01T12:00:00+00:00"
        result = engine._parse_datetime(dt_str)
        assert isinstance(result, datetime)
        assert result.year == 2023
        assert result.month == 6
        assert result.day == 1

    def test_parse_datetime_with_z_suffix(self, engine):
        """Test parsing datetime string with Z suffix."""
        dt_str = "2023-06-01T12:00:00Z"
        result = engine._parse_datetime(dt_str)
        assert isinstance(result, datetime)
        assert result.year == 2023

    def test_parse_datetime_invalid_string(self, engine):
        """Test parsing invalid datetime string."""
        result = engine._parse_datetime("invalid datetime")
        assert result is None

    def test_parse_datetime_none(self, engine):
        """Test parsing None datetime."""
        result = engine._parse_datetime(None)
        assert result is None

    def test_parse_datetime_datetime_object(self, engine):
        """Test parsing datetime object (should return as-is)."""
        dt = datetime.now(timezone.utc)
        result = engine._parse_datetime(dt)
        assert result == dt

    def test_update_anime_metadata_from_cache_existing_record(self, engine):
        """Test updating existing anime metadata record from cache."""
        conflict = DataConflict(
            conflict_type=ConflictType.MISSING_IN_DATABASE,
            entity_type="anime_metadata",
            entity_id=12345,
            cache_data={
                "tmdb_id": 12345,
                "title": "Updated Title",
                "overview": "Updated overview",
                "version": 2
            },
            severity=ConflictSeverity.HIGH
        )

        with patch.object(engine.db_manager, 'transaction') as mock_transaction:
            mock_session = Mock()
            mock_transaction.return_value.__enter__.return_value = mock_session
            mock_transaction.return_value.__exit__.return_value = None

            # Mock existing record
            mock_anime = Mock()
            mock_anime.tmdb_id = 12345
            mock_anime.version = 1
            mock_anime.title = "Old Title"
            mock_anime.overview = "Old overview"
            mock_session.query.return_value.filter.return_value.first.return_value = mock_anime

            result = engine._update_anime_metadata_from_cache(mock_session, conflict)

            assert result is True
            assert mock_anime.title == "Updated Title"
            assert mock_anime.overview == "Updated overview"
            assert mock_anime.version == 3  # Incremented from 1 to 3
            mock_session.commit.assert_called_once()

    def test_update_anime_metadata_from_cache_new_record(self, engine):
        """Test creating new anime metadata record from cache."""
        conflict = DataConflict(
            conflict_type=ConflictType.MISSING_IN_DATABASE,
            entity_type="anime_metadata",
            entity_id=12345,
            cache_data={
                "tmdb_id": 12345,
                "title": "New Title",
                "overview": "New overview",
                "version": 1
            },
            severity=ConflictSeverity.HIGH
        )

        with patch.object(engine.db_manager, 'transaction') as mock_transaction:
            mock_session = Mock()
            mock_transaction.return_value.__enter__.return_value = mock_session
            mock_transaction.return_value.__exit__.return_value = None

            # Mock no existing record
            mock_session.query.return_value.filter.return_value.first.return_value = None

            result = engine._update_anime_metadata_from_cache(mock_session, conflict)

            assert result is True
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_update_parsed_file_from_cache_existing_record(self, engine):
        """Test updating existing parsed file record from cache."""
        conflict = DataConflict(
            conflict_type=ConflictType.MISSING_IN_DATABASE,
            entity_type="parsed_file",
            entity_id=1,
            cache_data={
                "id": 1,
                "parsed_title": "Updated Title",
                "season": 2,
                "episode": 3,
                "version": 2
            },
            severity=ConflictSeverity.HIGH
        )

        with patch.object(engine.db_manager, 'transaction') as mock_transaction:
            mock_session = Mock()
            mock_transaction.return_value.__enter__.return_value = mock_session
            mock_transaction.return_value.__exit__.return_value = None

            # Mock existing record
            mock_file = Mock()
            mock_file.id = 1
            mock_file.version = 1
            mock_file.parsed_title = "Old Title"
            mock_file.season = 1
            mock_file.episode = 1
            mock_session.query.return_value.filter.return_value.first.return_value = mock_file

            result = engine._update_parsed_file_from_cache(mock_session, conflict)

            assert result is True
            assert mock_file.parsed_title == "Updated Title"
            assert mock_file.season == 2
            assert mock_file.episode == 3
            assert mock_file.version == 3  # Incremented from 1 to 3
            mock_session.commit.assert_called_once()
