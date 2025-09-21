"""Integration tests for the complete configuration management system.

This module tests the integration between all configuration components
including SecureConfigManager, ThreadSafeConfigManager, validation,
and secure storage.
"""

import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

from src.core.config import SecureConfigManager
from src.core.config_schema import get_schema_validator
from src.core.secure_storage import get_secure_storage
from src.core.thread_safe_config import ThreadSafeConfigManager
from src.utils.validators import get_validator


class TestConfigurationIntegration:
    """Integration tests for the complete configuration system."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "integration_test_config.json"
        self.secure_manager = SecureConfigManager(self.config_path)
        self.thread_safe_manager = ThreadSafeConfigManager(self.config_path)
        self.validator = get_validator()
        self.schema_validator = get_schema_validator()
        self.secure_storage = get_secure_storage()

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_secure_config_manager_integration(self) -> None:
        """Test SecureConfigManager integration with all components."""
        # Test API key management with encryption
        api_key = "a1b2c3d4e5f6789012345678901234ab"
        result = self.secure_manager.set_tmdb_api_key(api_key)
        assert result is True

        retrieved_key = self.secure_manager.get_tmdb_api_key()
        assert retrieved_key == api_key

        # Test destination root with validation
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.secure_manager.set_destination_root(temp_dir)
            assert result is True

            retrieved_path = self.secure_manager.get_destination_root()
            assert retrieved_path == temp_dir

        # Test theme and language validation
        result = self.secure_manager.set_theme("dark")
        assert result is True
        assert self.secure_manager.get_theme() == "dark"

        result = self.secure_manager.set_language("ko")
        assert result is True
        assert self.secure_manager.get_language() == "ko"

        # Test configuration validation
        is_valid = self.secure_manager.validate_config()
        assert is_valid is True

        # Test security status
        security_status = self.secure_manager.get_security_status()
        assert isinstance(security_status, dict)
        assert "encryption_enabled" in security_status
        assert "secure_storage_available" in security_status

    def test_thread_safe_config_manager_integration(self) -> None:
        """Test ThreadSafeConfigManager integration with all components."""
        # Test observer pattern
        events = []

        def observer_callback(event):
            events.append(event)

        _observer_id = self.thread_safe_manager.add_observer(observer_callback)

        # Test basic operations
        self.thread_safe_manager.set("test.key", "test_value")
        assert self.thread_safe_manager.get("test.key") == "test_value"

        # Verify observer was notified
        assert len(events) == 1
        assert events[0].key_path == "test.key"
        assert events[0].old_value is None
        assert events[0].new_value == "test_value"

        # Test batch update
        batch_updates = {"key1": "value1", "key2": "value2", "key3": "value3"}
        self.thread_safe_manager.batch_update(batch_updates)

        # Verify all values were set
        for key, value in batch_updates.items():
            assert self.thread_safe_manager.get(key) == value

        # Test atomic update
        def increment(value):
            return (value or 0) + 1

        new_value = self.thread_safe_manager.atomic_update("counter", increment)
        assert new_value == 1
        assert self.thread_safe_manager.get("counter") == 1

        # Test validation
        is_valid = self.thread_safe_manager.validate_config()
        assert is_valid is True

        # Test statistics
        stats = self.thread_safe_manager.get_statistics()
        assert isinstance(stats, dict)
        assert "read_count" in stats
        assert "write_count" in stats
        assert "observer_count" in stats

    def test_validation_integration(self) -> None:
        """Test validation system integration."""
        # Test with valid configuration
        valid_config = {
            "version": "1.0.0",
            "security": {
                "encryption_enabled": True,
                "encrypted_keys": ["services.tmdb_api.api_key"],
            },
            "services": {
                "tmdb_api": {
                    "api_key": "a1b2c3d4e5f6789012345678901234ab",
                    "language": "ko-KR",
                    "timeout": 30,
                    "retry_attempts": 3,
                }
            },
            "application": {
                "file_organization": {
                    "destination_root": "/test/path",
                    "organize_mode": "복사",
                    "naming_scheme": "standard",
                    "safe_mode": True,
                    "backup_before_organize": False,
                    "prefer_anitopy": False,
                    "fallback_parser": "FileParser",
                    "realtime_monitoring": False,
                    "auto_refresh_interval": 30,
                    "show_advanced_options": False,
                },
                "backup_settings": {"backup_location": "/backup/path", "max_backup_count": 10},
                "logging_config": {"log_level": "INFO", "log_to_file": False},
                "performance_settings": {"max_workers": 4, "cache_size": 100},
            },
            "user_preferences": {
                "gui_state": {
                    "window_geometry": None,
                    "last_source_directory": "/source/path",
                    "last_destination_directory": "/dest/path",
                    "remember_last_session": True,
                },
                "accessibility": {
                    "high_contrast_mode": False,
                    "keyboard_navigation": True,
                    "screen_reader_support": True,
                },
                "theme_preferences": {"theme": "dark", "language": "ko"},
                "language_settings": {"date_format": "YYYY-MM-DD", "time_format": "HH:mm:ss"},
            },
            "metadata": {"migrated_at": "", "migration_version": "1.0.0", "source_files": []},
        }

        # Test schema validation
        is_valid, errors = self.schema_validator.validate_config(valid_config)
        assert is_valid is True
        assert len(errors) == 0

        # Test individual validators
        assert self.validator.validate_api_key("a1b2c3d4e5f6789012345678901234ab", "tmdb")
        assert self.validator.validate_theme("dark")
        assert self.validator.validate_language("ko")
        assert self.validator.validate_organize_mode("복사")
        assert self.validator.validate_naming_scheme("standard")
        assert self.validator.validate_log_level("INFO")

    def test_secure_storage_integration(self) -> None:
        """Test secure storage integration."""
        # Test encryption/decryption
        test_data = "This is sensitive configuration data"
        encrypted = self.secure_storage.encrypt_data(test_data)
        decrypted = self.secure_storage.decrypt_data(encrypted)
        assert decrypted == test_data

        # Test data integrity
        hash_value = self.secure_storage.hash_data(test_data)
        assert self.secure_storage.verify_data_integrity(test_data, hash_value)

        # Test secure store/retrieve
        stored_data = self.secure_storage.secure_store("test_key", test_data)
        retrieved_data = self.secure_storage.secure_retrieve(stored_data)
        assert retrieved_data == test_data

        # Test key rotation
        success = self.secure_storage.rotate_encryption_key()
        assert success is True

    def test_end_to_end_configuration_flow(self) -> None:
        """Test complete end-to-end configuration flow."""
        # 1. Initialize configuration with default values
        default_config = self.schema_validator.get_default_config()
        assert isinstance(default_config, dict)

        # 2. Set up thread-safe manager with observer
        events = []

        def config_observer(event):
            events.append(event)

        _observer_id = self.thread_safe_manager.add_observer(config_observer)

        # 3. Configure application settings
        with tempfile.TemporaryDirectory() as temp_dir:
            config_updates = {
                "services.tmdb_api.api_key": "a1b2c3d4e5f6789012345678901234ab",
                "services.tmdb_api.language": "ko-KR",
                "application.file_organization.destination_root": temp_dir,
                "application.file_organization.organize_mode": "복사",
                "application.file_organization.safe_mode": True,
                "user_preferences.theme_preferences.theme": "dark",
                "user_preferences.theme_preferences.language": "ko",
            }

            # 4. Apply configuration changes atomically
            self.thread_safe_manager.batch_update(config_updates)

            # 5. Verify all changes were applied
            for key, expected_value in config_updates.items():
                actual_value = self.thread_safe_manager.get(key)
                assert actual_value == expected_value

            # 6. Verify observer was notified
            assert len(events) == len(config_updates)

            # 7. Validate configuration
            is_valid = self.thread_safe_manager.validate_config()
            assert is_valid is True

            # 8. Get validation errors (should be empty)
            errors = self.thread_safe_manager.get_validation_errors()
            assert len(errors) == 0

            # 9. Save configuration
            save_result = self.thread_safe_manager.save_config()
            assert save_result is True

            # 10. Create new manager and verify persistence
            new_manager = ThreadSafeConfigManager(self.config_path)
            for key, expected_value in config_updates.items():
                actual_value = new_manager.get(key)
                assert actual_value == expected_value

            # 11. Test security operations
            security_status = new_manager.get_security_status()
            assert isinstance(security_status, dict)
            assert security_status["encryption_enabled"] is True

            # 12. Test statistics
            stats = new_manager.get_statistics()
            assert isinstance(stats, dict)
            # Note: new_manager has fresh statistics, so write_count will be 0
            # We should check the original manager's statistics instead
            original_stats = self.thread_safe_manager.get_statistics()
            assert original_stats["write_count"] > 0

    def test_concurrent_configuration_operations(self) -> None:
        """Test concurrent configuration operations across all components."""
        results = []
        errors = []

        def worker(worker_id):
            try:
                for i in range(10):
                    # Test secure manager operations
                    key = f"secure_key_{worker_id}_{i}"
                    value = f"secure_value_{worker_id}_{i}"
                    self.secure_manager.set(key, value, encrypt=True)
                    retrieved = self.secure_manager.get(key)
                    results.append(("secure", worker_id, key, retrieved))

                    # Test thread-safe manager operations
                    t_key = f"thread_key_{worker_id}_{i}"
                    t_value = f"thread_value_{worker_id}_{i}"
                    self.thread_safe_manager.set(t_key, t_value)
                    t_retrieved = self.thread_safe_manager.get(t_key)
                    results.append(("thread_safe", worker_id, t_key, t_retrieved))

                    # Test validation
                    is_valid = self.thread_safe_manager.validate_config()
                    results.append(("validation", worker_id, i, is_valid))

                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        # Start multiple worker threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check for errors
        assert len(errors) == 0, f"Concurrent operation errors: {errors}"

        # Verify all operations completed successfully
        assert len(results) == 90  # 3 workers * 10 iterations * 3 operations each

        # Verify data consistency
        for operation_type, worker_id, key, value in results:
            if operation_type in ["secure", "thread_safe"]:
                expected_value = (
                    f"{operation_type.split('_')[0]}_value_{worker_id}_{key.split('_')[-1]}"
                )
                assert (
                    value == expected_value
                ), f"Data inconsistency: {key} = {value}, expected {expected_value}"
            elif operation_type == "validation":
                assert value is True, f"Validation failed for worker {worker_id}, iteration {key}"

    def test_error_handling_integration(self) -> None:
        """Test error handling across all components."""
        # Test invalid API key
        result = self.secure_manager.set_tmdb_api_key("invalid_key")
        assert result is False

        # Test invalid theme
        result = self.secure_manager.set_theme("invalid_theme")
        assert result is False

        # Test invalid language
        result = self.secure_manager.set_language("invalid_lang")
        assert result is False

        # Test invalid path
        result = self.secure_manager.set_destination_root("/nonexistent/path")
        assert result is False

        # Test validation with invalid configuration
        invalid_config = {
            "version": "invalid_version",
            "security": {"encryption_enabled": "not_boolean"},
        }

        is_valid, errors = self.schema_validator.validate_config(invalid_config)
        assert is_valid is False
        assert len(errors) > 0

        # Test secure storage with invalid data
        with patch.object(self.secure_storage, "_cipher_suite", None):
            # Should fallback to base64
            encrypted = self.secure_storage.encrypt_data("test_data")
            decrypted = self.secure_storage.decrypt_data(encrypted)
            assert decrypted == "test_data"

    def test_performance_integration(self) -> None:
        """Test performance characteristics of the integrated system."""
        import time

        # Test read performance
        start_time = time.time()
        for _ in range(1000):
            self.thread_safe_manager.get("test.key")
        read_time = time.time() - start_time

        # Test write performance
        start_time = time.time()
        for i in range(100):
            self.thread_safe_manager.set(f"perf_key_{i}", f"perf_value_{i}")
        write_time = time.time() - start_time

        # Test batch update performance
        start_time = time.time()
        batch_updates = {f"batch_key_{i}": f"batch_value_{i}" for i in range(100)}
        self.thread_safe_manager.batch_update(batch_updates)
        batch_time = time.time() - start_time

        # Performance should be reasonable (these are rough benchmarks)
        assert read_time < 1.0, f"Read performance too slow: {read_time}s"
        assert write_time < 1.0, f"Write performance too slow: {write_time}s"
        assert batch_time < 0.5, f"Batch update performance too slow: {batch_time}s"

        # Test statistics
        stats = self.thread_safe_manager.get_statistics()
        assert stats["read_count"] >= 1000
        assert stats["write_count"] >= 100  # At least 100 individual writes

    def test_memory_usage_integration(self) -> None:
        """Test memory usage characteristics of the integrated system."""
        import gc

        # Get initial memory usage (rough estimate)
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Create and use many configuration managers
        managers = []
        for i in range(10):
            manager = ThreadSafeConfigManager(self.config_path)
            managers.append(manager)

            # Use the manager
            for j in range(100):
                manager.set(f"key_{i}_{j}", f"value_{i}_{j}")
                manager.get(f"key_{i}_{j}")

        # Check memory usage
        gc.collect()
        final_objects = len(gc.get_objects())

        # Memory usage should be reasonable
        object_increase = final_objects - initial_objects
        assert object_increase < 10000, f"Memory usage too high: {object_increase} objects"

        # Clean up
        del managers
        gc.collect()

    def test_configuration_migration_integration(self) -> None:
        """Test configuration migration and backward compatibility."""
        # Create a configuration with old format
        old_config = {
            "version": "1.0.0",
            "tmdb_api_key": "old_format_key",  # Old format
            "destination_path": "/old/path",  # Old format
            "theme": "light",  # Old format
        }

        # Save old configuration
        import json

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(old_config, f, indent=2)

        # Load with new system
        new_manager = ThreadSafeConfigManager(self.config_path)

        # The system should handle the old format gracefully
        # (This would require migration logic in a real implementation)
        assert new_manager.get("version") == "1.0.0"

        # Test that new format works
        new_manager.set("services.tmdb_api.api_key", "new_format_key")
        assert new_manager.get("services.tmdb_api.api_key") == "new_format_key"

    def test_backup_and_restore_integration(self) -> None:
        """Test backup and restore functionality integration."""
        # Set up some configuration
        test_config = {
            "test.key1": "value1",
            "test.key2": "value2",
            "services.tmdb_api.api_key": "test_api_key",
        }

        for key, value in test_config.items():
            self.thread_safe_manager.set(key, value)

        # Create backup
        backup_path = Path(self.temp_dir) / "backup_config.json"
        backup_result = self.thread_safe_manager.backup_config(backup_path)
        assert backup_result is True
        assert backup_path.exists()

        # Modify configuration
        self.thread_safe_manager.set("test.key1", "modified_value")
        assert self.thread_safe_manager.get("test.key1") == "modified_value"

        # Restore from backup (simulate by creating new manager)
        restored_manager = ThreadSafeConfigManager(backup_path)

        # Verify original values are restored
        for key, expected_value in test_config.items():
            actual_value = restored_manager.get(key)
            assert (
                actual_value == expected_value
            ), f"Backup restore failed for {key}: {actual_value} != {expected_value}"
