"""
Tests for incremental synchronization functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch

from src.core.incremental_sync import (
    IncrementalSyncManager,
    SyncStateManager,
    SyncEntityType,
    SyncState,
    IncrementalSyncResult
)
from src.core.sync_monitoring import SyncOperationStatus
from src.core.database import AnimeMetadata, ParsedFile


class TestSyncStateManager:
    """Test cases for SyncStateManager."""

    def test_initial_state(self):
        """Test initial state of sync state manager."""
        manager = SyncStateManager()

        assert manager.get_last_sync_timestamp(SyncEntityType.TMDB_METADATA) is None
        assert manager.get_last_sync_version(SyncEntityType.TMDB_METADATA) == 0
        assert not manager.is_entity_locked(SyncEntityType.TMDB_METADATA)

    def test_update_sync_state(self):
        """Test updating sync state."""
        manager = SyncStateManager()
        timestamp = datetime.now(timezone.utc)

        manager.update_sync_state(
            entity_type=SyncEntityType.TMDB_METADATA,
            timestamp=timestamp,
            version=5,
            records_synced=100,
            duration_ms=1500.0,
            status=SyncOperationStatus.SUCCESS
        )

        state = manager.get_sync_state(SyncEntityType.TMDB_METADATA)
        assert state is not None
        assert state.entity_type == SyncEntityType.TMDB_METADATA
        assert state.last_sync_timestamp == timestamp
        assert state.last_sync_version == 5
        assert state.records_synced == 100
        assert state.sync_duration_ms == 1500.0
        assert state.status == SyncOperationStatus.SUCCESS

    def test_entity_locking(self):
        """Test entity locking mechanism."""
        manager = SyncStateManager()
        entity_type = SyncEntityType.TMDB_METADATA

        # Initially not locked
        assert not manager.is_entity_locked(entity_type)

        # Lock entity
        assert manager.lock_entity(entity_type)
        assert manager.is_entity_locked(entity_type)

        # Cannot lock again
        assert not manager.lock_entity(entity_type)

        # Unlock entity
        manager.unlock_entity(entity_type)
        assert not manager.is_entity_locked(entity_type)


class TestIncrementalSyncManager:
    """Test cases for IncrementalSyncManager."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        db_manager = Mock()
        return db_manager

    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager."""
        cache_manager = Mock()
        return cache_manager

    @pytest.fixture
    def sync_manager(self, mock_db_manager, mock_cache_manager):
        """Create IncrementalSyncManager instance."""
        return IncrementalSyncManager(mock_db_manager, mock_cache_manager)

    def test_initialization(self, mock_db_manager, mock_cache_manager):
        """Test IncrementalSyncManager initialization."""
        manager = IncrementalSyncManager(mock_db_manager, mock_cache_manager)

        assert manager.db_manager == mock_db_manager
        assert manager.cache_manager == mock_cache_manager
        assert isinstance(manager.state_manager, SyncStateManager)

    def test_get_sync_status(self, sync_manager):
        """Test getting sync status."""
        status = sync_manager.get_sync_status()

        assert SyncEntityType.TMDB_METADATA in status
        assert SyncEntityType.PARSED_FILES in status
        assert status[SyncEntityType.TMDB_METADATA] is None
        assert status[SyncEntityType.PARSED_FILES] is None


class TestIncrementalSyncIntegration:
    """Integration tests for incremental sync functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = Mock()
        return session

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        db_manager = Mock()
        return db_manager

    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager."""
        cache_manager = Mock()
        cache_manager.get.return_value = None  # Cache miss by default
        return cache_manager

    @pytest.fixture
    def sync_manager(self, mock_db_manager, mock_cache_manager):
        """Create IncrementalSyncManager instance."""
        return IncrementalSyncManager(mock_db_manager, mock_cache_manager)

    @patch('src.core.incremental_sync.sync_monitor')
    def test_sync_tmdb_metadata_incremental_no_records(self, mock_sync_monitor, sync_manager, mock_session):
        """Test incremental TMDB sync with no records."""
        # Mock empty query result
        mock_query = Mock()
        mock_query.all.return_value = []
        mock_session.query.return_value.order_by.return_value = mock_query

        # Mock sync monitor context manager
        mock_metrics = Mock()
        mock_sync_monitor.monitor_operation.return_value.__enter__.return_value = mock_metrics

        result = sync_manager.sync_tmdb_metadata_incremental(mock_session, force_full_sync=False)

        assert isinstance(result, IncrementalSyncResult)
        assert result.entity_type == SyncEntityType.TMDB_METADATA
        assert result.records_found == 0
        assert result.records_processed == 0
        assert result.status == SyncOperationStatus.SUCCESS

    @patch('src.core.incremental_sync.sync_monitor')
    def test_sync_tmdb_metadata_incremental_with_records(self, mock_sync_monitor, sync_manager, mock_session):
        """Test incremental TMDB sync with records."""
        # Create mock metadata records
        mock_metadata = Mock(spec=AnimeMetadata)
        mock_metadata.tmdb_id = 123
        mock_metadata.version = 1
        mock_metadata.to_tmdb_anime.return_value = Mock()

        # Mock query result
        mock_query = Mock()
        mock_query.all.return_value = [mock_metadata]
        mock_session.query.return_value.filter.return_value.order_by.return_value = mock_query

        # Mock sync monitor context manager
        mock_metrics = Mock()
        mock_sync_monitor.monitor_operation.return_value.__enter__.return_value = mock_metrics

        result = sync_manager.sync_tmdb_metadata_incremental(mock_session, force_full_sync=False)

        assert isinstance(result, IncrementalSyncResult)
        assert result.entity_type == SyncEntityType.TMDB_METADATA
        assert result.records_found == 1
        assert result.records_processed == 1
        assert result.status == SyncOperationStatus.SUCCESS

        # Verify cache manager was called
        sync_manager.cache_manager.put.assert_called_once()

    def test_entity_locking_prevents_concurrent_sync(self, sync_manager, mock_session):
        """Test that entity locking prevents concurrent sync operations."""
        # Lock the entity first
        assert sync_manager.state_manager.lock_entity(SyncEntityType.TMDB_METADATA)

        # Try to sync the same entity type
        result = sync_manager.sync_tmdb_metadata_incremental(mock_session)

        assert result.records_found == 0
        assert result.status == SyncOperationStatus.FAILED
        assert "already in progress" in result.error_message

        # Unlock and try again
        sync_manager.state_manager.unlock_entity(SyncEntityType.TMDB_METADATA)

    @patch('src.core.incremental_sync.sync_monitor')
    def test_sync_all_entities(self, mock_sync_monitor, sync_manager, mock_session):
        """Test syncing all entities."""
        # Mock empty query results for both entity types
        mock_query = Mock()
        mock_query.all.return_value = []
        mock_session.query.return_value.order_by.return_value = mock_query

        # Mock sync monitor context manager
        mock_metrics = Mock()
        mock_sync_monitor.monitor_operation.return_value.__enter__.return_value = mock_metrics

        results = sync_manager.sync_all_entities_incremental(mock_session, force_full_sync=True)

        assert SyncEntityType.TMDB_METADATA in results
        assert SyncEntityType.PARSED_FILES in results

        for result in results.values():
            assert isinstance(result, IncrementalSyncResult)
            assert result.status == SyncOperationStatus.SUCCESS


if __name__ == "__main__":
    pytest.main([__file__])
