#!/usr/bin/env python3
"""Tests for database schema validation functionality."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.core.database import DatabaseManager, Base
from src.core.models import TMDBAnime, ParsedAnimeInfo


class TestSchemaValidation:
    """Test cases for schema validation functionality."""

    @pytest.fixture
    def db_manager(self):
        """Create a test database manager."""
        manager = DatabaseManager("sqlite:///:memory:")
        manager.initialize()
        return manager

    @pytest.fixture
    def temp_db_manager(self):
        """Create a temporary database manager for integration tests."""
        manager = DatabaseManager("sqlite:///:memory:")
        manager.initialize()
        return manager

    def test_validate_schema_success(self, db_manager):
        """Test successful schema validation."""
        # Mock the inspector to return expected tables
        with patch('sqlalchemy.inspect') as mock_inspect:
            mock_inspector = Mock()
            mock_inspector.get_table_names.return_value = ['anime_metadata', 'parsed_files']
            
            # Mock columns for anime_metadata table
            anime_columns = [
                {'name': 'tmdb_id', 'type': 'INTEGER'},
                {'name': 'title', 'type': 'TEXT'},
                {'name': 'original_title', 'type': 'TEXT'},
                {'name': 'korean_title', 'type': 'TEXT'},
                {'name': 'overview', 'type': 'TEXT'},
                {'name': 'poster_path', 'type': 'TEXT'},
                {'name': 'backdrop_path', 'type': 'TEXT'},
                {'name': 'first_air_date', 'type': 'DATE'},
                {'name': 'last_air_date', 'type': 'DATE'},
                {'name': 'status', 'type': 'TEXT'},
                {'name': 'vote_average', 'type': 'REAL'},
                {'name': 'vote_count', 'type': 'INTEGER'},
                {'name': 'popularity', 'type': 'REAL'},
                {'name': 'number_of_seasons', 'type': 'INTEGER'},
                {'name': 'number_of_episodes', 'type': 'INTEGER'},
                {'name': 'genres', 'type': 'TEXT'},
                {'name': 'networks', 'type': 'TEXT'},
                {'name': 'raw_data', 'type': 'TEXT'},
                {'name': 'created_at', 'type': 'DATETIME'},
                {'name': 'updated_at', 'type': 'DATETIME'},
            ]
            
            # Mock columns for parsed_files table
            parsed_columns = [
                {'name': 'id', 'type': 'INTEGER'},
                {'name': 'file_path', 'type': 'TEXT'},
                {'name': 'filename', 'type': 'TEXT'},
                {'name': 'file_size', 'type': 'INTEGER'},
                {'name': 'file_extension', 'type': 'TEXT'},
                {'name': 'file_hash', 'type': 'TEXT'},
                {'name': 'created_at', 'type': 'DATETIME'},
                {'name': 'modified_at', 'type': 'DATETIME'},
                {'name': 'parsed_title', 'type': 'TEXT'},
                {'name': 'season', 'type': 'INTEGER'},
                {'name': 'episode', 'type': 'INTEGER'},
                {'name': 'episode_title', 'type': 'TEXT'},
                {'name': 'resolution', 'type': 'TEXT'},
                {'name': 'resolution_width', 'type': 'INTEGER'},
                {'name': 'resolution_height', 'type': 'INTEGER'},
                {'name': 'video_codec', 'type': 'TEXT'},
                {'name': 'audio_codec', 'type': 'TEXT'},
                {'name': 'release_group', 'type': 'TEXT'},
                {'name': 'source', 'type': 'TEXT'},
                {'name': 'year', 'type': 'INTEGER'},
                {'name': 'is_processed', 'type': 'BOOLEAN'},
                {'name': 'processing_errors', 'type': 'TEXT'},
                {'name': 'metadata_id', 'type': 'INTEGER'},
                {'name': 'db_created_at', 'type': 'DATETIME'},
                {'name': 'db_updated_at', 'type': 'DATETIME'},
            ]
            
            def mock_get_columns(table_name):
                if table_name == 'anime_metadata':
                    return anime_columns
                elif table_name == 'parsed_files':
                    return parsed_columns
                return []
            
            mock_inspector.get_columns.side_effect = mock_get_columns
            mock_inspect.return_value = mock_inspector
            
            result = db_manager.validate_schema()
            assert result is True

    def test_validate_schema_missing_tables(self, db_manager):
        """Test schema validation with missing tables."""
        with patch('sqlalchemy.inspect') as mock_inspect:
            mock_inspector = Mock()
            mock_inspector.get_table_names.return_value = ['anime_metadata']  # Missing parsed_files
            mock_inspect.return_value = mock_inspector
            
            result = db_manager.validate_schema()
            assert result is False

    def test_validate_schema_missing_columns(self, db_manager):
        """Test schema validation with missing columns."""
        with patch('sqlalchemy.inspect') as mock_inspect:
            mock_inspector = Mock()
            mock_inspector.get_table_names.return_value = ['anime_metadata', 'parsed_files']
            mock_inspector.get_columns.return_value = [
                {'name': 'tmdb_id', 'type': 'INTEGER'},
                # Missing required columns like 'title', 'overview'
            ]
            mock_inspect.return_value = mock_inspector
            
            result = db_manager.validate_schema()
            assert result is False

    def test_validate_table_structure_success(self, db_manager):
        """Test successful table structure validation."""
        with patch('sqlalchemy.inspect') as mock_inspect:
            mock_inspector = Mock()
            # Mock all required columns for anime_metadata table
            mock_inspector.get_columns.return_value = [
                {'name': 'tmdb_id', 'type': 'INTEGER'},
                {'name': 'title', 'type': 'TEXT'},
                {'name': 'original_title', 'type': 'TEXT'},
                {'name': 'korean_title', 'type': 'TEXT'},
                {'name': 'overview', 'type': 'TEXT'},
                {'name': 'poster_path', 'type': 'TEXT'},
                {'name': 'backdrop_path', 'type': 'TEXT'},
                {'name': 'first_air_date', 'type': 'DATE'},
                {'name': 'last_air_date', 'type': 'DATE'},
                {'name': 'status', 'type': 'TEXT'},
                {'name': 'vote_average', 'type': 'REAL'},
                {'name': 'vote_count', 'type': 'INTEGER'},
                {'name': 'popularity', 'type': 'REAL'},
                {'name': 'number_of_seasons', 'type': 'INTEGER'},
                {'name': 'number_of_episodes', 'type': 'INTEGER'},
                {'name': 'genres', 'type': 'TEXT'},
                {'name': 'networks', 'type': 'TEXT'},
                {'name': 'raw_data', 'type': 'TEXT'},
                {'name': 'created_at', 'type': 'DATETIME'},
                {'name': 'updated_at', 'type': 'DATETIME'},
            ]
            mock_inspect.return_value = mock_inspector
            
            result = db_manager._validate_table_structure('anime_metadata', mock_inspector)
            assert result is True

    def test_validate_table_structure_missing_columns(self, db_manager):
        """Test table structure validation with missing columns."""
        with patch('sqlalchemy.inspect') as mock_inspect:
            mock_inspector = Mock()
            mock_inspector.get_columns.return_value = [
                {'name': 'tmdb_id', 'type': 'INTEGER'},
                # Missing 'title' column
            ]
            mock_inspector.return_value = mock_inspector
            
            result = db_manager._validate_table_structure('anime_metadata', mock_inspector)
            assert result is False

    def test_is_type_compatible(self, db_manager):
        """Test type compatibility checking."""
        # Test compatible types
        assert db_manager._is_type_compatible('INTEGER', 'INTEGER') is True
        assert db_manager._is_type_compatible('TEXT', 'VARCHAR') is True
        assert db_manager._is_type_compatible('REAL', 'FLOAT') is True
        
        # Test incompatible types
        assert db_manager._is_type_compatible('INTEGER', 'TEXT') is False
        assert db_manager._is_type_compatible('TEXT', 'INTEGER') is False

    def test_get_schema_version_success(self, db_manager):
        """Test successful schema version retrieval."""
        with patch.object(db_manager, 'transaction') as mock_transaction:
            mock_session = Mock()
            # Mock the result tuple directly
            mock_session.execute.return_value.fetchone.return_value = ('3ff80129897d',)
            mock_transaction.return_value.__enter__.return_value = mock_session
            
            version = db_manager.get_schema_version()
            assert version == '3ff80129897d'

    def test_get_schema_version_no_version(self, db_manager):
        """Test schema version retrieval when no version exists."""
        with patch.object(db_manager, 'transaction') as mock_transaction:
            mock_session = Mock()
            mock_session.execute.return_value.fetchone.return_value = None
            mock_transaction.return_value.__enter__.return_value = mock_session
            
            version = db_manager.get_schema_version()
            assert version is None

    def test_get_schema_version_exception(self, db_manager):
        """Test schema version retrieval with exception."""
        with patch.object(db_manager, 'transaction') as mock_transaction:
            mock_transaction.side_effect = Exception("Database error")
            
            version = db_manager.get_schema_version()
            assert version is None

    def test_is_schema_up_to_date_success(self, db_manager):
        """Test successful schema up-to-date check."""
        with patch.object(db_manager, 'get_schema_version') as mock_get_version:
            mock_get_version.return_value = '3ff80129897d'
            
            with patch('alembic.config.Config') as mock_config:
                mock_alembic_cfg = Mock()
                mock_alembic_cfg.get_main_option.return_value = 'alembic'
                mock_config.return_value = mock_alembic_cfg
                
                result = db_manager.is_schema_up_to_date()
                assert result is True

    def test_is_schema_up_to_date_no_version(self, db_manager):
        """Test schema up-to-date check with no version."""
        with patch.object(db_manager, 'get_schema_version') as mock_get_version:
            mock_get_version.return_value = None
            
            result = db_manager.is_schema_up_to_date()
            assert result is False

    def test_is_schema_up_to_date_exception(self, db_manager):
        """Test schema up-to-date check with exception."""
        with patch.object(db_manager, 'get_schema_version') as mock_get_version:
            mock_get_version.side_effect = Exception("Database error")
            
            result = db_manager.is_schema_up_to_date()
            assert result is False


class TestSchemaValidationIntegration:
    """Integration tests for schema validation."""

    @pytest.fixture
    def temp_db_manager(self):
        """Create a temporary database manager for integration tests."""
        manager = DatabaseManager("sqlite:///:memory:")
        manager.initialize()
        return manager

    def test_validate_schema_with_real_database(self, temp_db_manager):
        """Test schema validation with a real database."""
        # This test uses a real database manager with in-memory SQLite
        result = temp_db_manager.validate_schema()
        assert result is True

    def test_get_schema_version_with_real_database(self, temp_db_manager):
        """Test schema version retrieval with a real database."""
        from sqlalchemy import text
        
        # Create alembic_version table
        with temp_db_manager.transaction() as session:
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """))
            session.execute(text(
                "INSERT INTO alembic_version (version_num) VALUES (:version)"
            ), {'version': 'test_version_123'})
        
        version = temp_db_manager.get_schema_version()
        assert version == 'test_version_123'
