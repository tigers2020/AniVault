"""Tests for the thread-safe configuration management system.

This module tests the ThreadSafeConfigManager class to ensure proper
thread safety, observer pattern functionality, and concurrent access patterns.
"""

import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from src.core.thread_safe_config import (
    ConfigurationChangeEvent,
    ConfigurationObserver,
    ThreadSafeConfigManager,
)


class TestConfigurationChangeEvent:
    """Test cases for ConfigurationChangeEvent class."""

    def test_initialization(self) -> None:
        """Test ConfigurationChangeEvent initialization."""
        event = ConfigurationChangeEvent("test.key", "old_value", "new_value", 1234567890.0)

        assert event.key_path == "test.key"
        assert event.old_value == "old_value"
        assert event.new_value == "new_value"
        assert event.timestamp == 1234567890.0

    def test_string_representation(self) -> None:
        """Test string representation of ConfigurationChangeEvent."""
        event = ConfigurationChangeEvent("test.key", "old", "new", 1234567890.0)
        repr_str = repr(event)

        assert "ConfigChange" in repr_str
        assert "test.key" in repr_str
        assert "old" in repr_str
        assert "new" in repr_str


class TestConfigurationObserver:
    """Test cases for ConfigurationObserver class."""

    def test_initialization(self) -> None:
        """Test ConfigurationObserver initialization."""

        def callback(x: Any) -> None:
            return None

        observer = ConfigurationObserver(callback, ["test.*"])

        assert observer.callback == callback
        assert observer.key_patterns == ["test.*"]
        assert observer.observer_id is not None

    def test_should_notify_all_keys(self) -> None:
        """Test notification for all keys when no patterns specified."""

        def callback(x: Any) -> None:
            return None

        observer = ConfigurationObserver(callback)

        assert observer.should_notify("any.key") is True
        assert observer.should_notify("another.key") is True

    def test_should_notify_pattern_matching(self) -> None:
        """Test notification based on key patterns."""

        def callback(x: Any) -> None:
            return None

        observer = ConfigurationObserver(callback, ["test.*", "user.*"])

        assert observer.should_notify("test.key") is True
        assert observer.should_notify("user.preferences") is True
        assert observer.should_notify("other.key") is False
        assert observer.should_notify("test") is False

    def test_notify_callback(self) -> None:
        """Test observer notification."""
        events = []

        def callback(event: Any) -> None:
            events.append(event)

        observer = ConfigurationObserver(callback)
        event = ConfigurationChangeEvent("test.key", "old", "new", 1234567890.0)

        observer.notify(event)
        assert len(events) == 1
        assert events[0] == event

    def test_notify_callback_error(self) -> None:
        """Test observer notification with callback error."""

        def callback(event):
            raise ValueError("Test error")

        observer = ConfigurationObserver(callback)
        event = ConfigurationChangeEvent("test.key", "old", "new", 1234567890.0)

        # Should not raise exception
        observer.notify(event)


class TestThreadSafeConfigManager:
    """Test cases for ThreadSafeConfigManager class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.json"
        self.manager = ThreadSafeConfigManager(self.config_path)

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self) -> None:
        """Test ThreadSafeConfigManager initialization."""
        assert self.manager._base_manager is not None
        assert self.manager._lock is not None
        assert self.manager._read_lock is not None
        assert self.manager._write_lock is not None
        assert len(self.manager._observers) == 0
        assert len(self.manager._change_history) == 0
        assert self.manager._batch_mode is False

    def test_add_remove_observer(self) -> None:
        """Test adding and removing observers."""
        events = []

        def callback(event: Any) -> None:
            events.append(event)

        # Add observer
        observer_id = self.manager.add_observer(callback)
        assert observer_id in self.manager._observers
        assert len(self.manager._observers) == 1

        # Remove observer
        result = self.manager.remove_observer(observer_id)
        assert result is True
        assert observer_id not in self.manager._observers
        assert len(self.manager._observers) == 0

        # Remove non-existent observer
        result = self.manager.remove_observer(999)
        assert result is False

    def test_observer_with_patterns(self) -> None:
        """Test observer with key patterns."""
        events = []

        def callback(event: Any) -> None:
            events.append(event)

        # Add observer with pattern
        _observer_id = self.manager.add_observer(callback, ["test.*"])

        # Set values
        self.manager.set("test.key1", "value1")
        self.manager.set("other.key", "value2")
        self.manager.set("test.key2", "value3")

        # Should only receive notifications for test.* keys
        assert len(events) == 2
        assert events[0].key_path == "test.key1"
        assert events[1].key_path == "test.key2"

    def test_basic_get_set(self) -> None:
        """Test basic get and set operations."""
        # Set a value
        self.manager.set("test.key", "test_value")

        # Get the value
        value = self.manager.get("test.key")
        assert value == "test_value"

        # Get non-existent key
        default_value = self.manager.get("non.existent", "default")
        assert default_value == "default"

    def test_change_history(self) -> None:
        """Test configuration change history."""
        # Set some values
        self.manager.set("key1", "value1")
        self.manager.set("key2", "value2")
        self.manager.set("key1", "value1_updated")

        # Get change history
        history = self.manager.get_change_history()
        assert len(history) == 3

        # Check first change
        assert history[0].key_path == "key1"
        assert history[0].old_value is None  # First set
        assert history[0].new_value == "value1"

        # Check second change
        assert history[1].key_path == "key2"
        assert history[1].old_value is None
        assert history[1].new_value == "value2"

        # Check third change
        assert history[2].key_path == "key1"
        assert history[2].old_value == "value1"
        assert history[2].new_value == "value1_updated"

    def test_change_history_filtering(self) -> None:
        """Test change history filtering by key pattern."""
        # Set some values
        self.manager.set("test.key1", "value1")
        self.manager.set("other.key", "value2")
        self.manager.set("test.key2", "value3")

        # Get filtered history
        test_history = self.manager.get_change_history("test.")
        assert len(test_history) == 2
        assert all("test." in change.key_path for change in test_history)

        # Get limited history
        limited_history = self.manager.get_change_history(limit=2)
        assert len(limited_history) == 2
        assert limited_history == self.manager._change_history[-2:]

    def test_batch_update(self) -> None:
        """Test atomic batch update."""
        events = []

        def callback(event: Any) -> None:
            events.append(event)

        self.manager.add_observer(callback)

        # Perform batch update
        updates = {"key1": "value1", "key2": "value2", "key3": "value3"}

        self.manager.batch_update(updates)

        # Check that all values were set
        assert self.manager.get("key1") == "value1"
        assert self.manager.get("key2") == "value2"
        assert self.manager.get("key3") == "value3"

        # Check that all changes were recorded
        assert len(events) == 3
        assert all(change.key_path in updates for change in events)

    def test_atomic_update(self) -> None:
        """Test atomic update with function."""
        # Set initial value
        self.manager.set("counter", 5)

        # Atomic increment
        def increment(value: Any) -> int:
            return (value or 0) + 1

        new_value = self.manager.atomic_update("counter", increment)
        assert new_value == 6
        assert self.manager.get("counter") == 6

        # Atomic append to list
        self.manager.set("list", [1, 2, 3])

        def append_item(value: Any) -> list[Any]:
            if isinstance(value, list):
                return [*value, 4]
            return [4]

        new_list = self.manager.atomic_update("list", append_item)
        assert new_list == [1, 2, 3, 4]
        assert self.manager.get("list") == [1, 2, 3, 4]

    def test_statistics(self) -> None:
        """Test configuration manager statistics."""
        # Perform some operations
        self.manager.get("test.key")
        self.manager.set("test.key", "value")
        self.manager.get("test.key")

        stats = self.manager.get_statistics()

        assert stats["read_count"] >= 2
        assert stats["write_count"] >= 1
        assert stats["observer_count"] == 0
        assert stats["history_size"] >= 1
        assert stats["batch_mode"] is False
        assert "last_access_time" in stats

    def test_wait_for_change(self) -> None:
        """Test waiting for configuration changes."""
        # Set initial value
        self.manager.set("test.key", "initial")

        # Start a thread that will change the value after a delay
        def change_value() -> None:
            time.sleep(0.1)
            self.manager.set("test.key", "changed")

        change_thread = threading.Thread(target=change_value)
        change_thread.start()

        # Wait for the change
        result = self.manager.wait_for_change("test.key", timeout=1.0)
        assert result is True
        assert self.manager.get("test.key") == "changed"

        change_thread.join()

    def test_wait_for_change_timeout(self) -> None:
        """Test waiting for configuration changes with timeout."""
        # Set initial value
        self.manager.set("test.key", "initial")

        # Wait for change that won't happen
        result = self.manager.wait_for_change("test.key", timeout=0.1)
        assert result is False
        assert self.manager.get("test.key") == "initial"

    def test_thread_safety_concurrent_reads(self) -> None:
        """Test thread safety with concurrent read operations."""
        # Set some test data
        test_data = {f"key{i}": f"value{i}" for i in range(10)}
        for key, value in test_data.items():
            self.manager.set(key, value)

        results = []
        errors = []

        def reader(thread_id: int) -> None:
            try:
                for i in range(100):
                    key = f"key{i % 10}"
                    value = self.manager.get(key)
                    results.append((thread_id, key, value))
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        # Start multiple reader threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=reader, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check for errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"

        # Verify all reads were successful
        assert len(results) == 500  # 5 threads * 100 reads each

        # Verify data consistency
        for _thread_id, key, value in results:
            expected_value = test_data[key]
            assert (
                value == expected_value
            ), f"Data inconsistency: {key} = {value}, expected {expected_value}"

    def test_thread_safety_concurrent_writes(self) -> None:
        """Test thread safety with concurrent write operations."""
        results = []
        errors = []

        def writer(thread_id: int) -> None:
            try:
                for i in range(50):
                    key = f"thread_{thread_id}_key_{i}"
                    value = f"thread_{thread_id}_value_{i}"
                    self.manager.set(key, value)
                    results.append((thread_id, key, value))
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        # Start multiple writer threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=writer, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check for errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"

        # Verify all writes were successful
        assert len(results) == 150  # 3 threads * 50 writes each

        # Verify data consistency
        for _thread_id, key, value in results:
            stored_value = self.manager.get(key)
            assert (
                stored_value == value
            ), f"Data inconsistency: {key} = {stored_value}, expected {value}"

    def test_thread_safety_mixed_operations(self) -> None:
        """Test thread safety with mixed read/write operations."""
        results = []
        errors = []

        def mixed_worker(thread_id: int) -> None:
            try:
                for i in range(50):
                    # Read operation
                    key = f"shared_key_{i % 10}"
                    value = self.manager.get(key, "default")
                    results.append(("read", thread_id, key, value))

                    # Write operation
                    write_key = f"thread_{thread_id}_key_{i}"
                    write_value = f"thread_{thread_id}_value_{i}"
                    self.manager.set(write_key, write_value)
                    results.append(("write", thread_id, write_key, write_value))

                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        # Start multiple worker threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=mixed_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check for errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"

        # Verify operations completed
        assert len(results) == 300  # 3 threads * 50 iterations * 2 operations each

    def test_deadlock_prevention(self) -> None:
        """Test that the implementation prevents deadlocks."""
        # This test is more of a stress test to ensure no deadlocks occur
        # during complex operations

        def complex_operation(thread_id: int) -> None:
            try:
                for i in range(20):
                    # Multiple operations that could potentially cause deadlocks
                    self.manager.set(f"key_{thread_id}_{i}", f"value_{i}")
                    self.manager.get(f"key_{thread_id}_{i}")

                    # Batch update
                    batch_updates = {
                        f"batch_{thread_id}_{i}_1": "batch_value_1",
                        f"batch_{thread_id}_{i}_2": "batch_value_2",
                    }
                    self.manager.batch_update(batch_updates)

                    # Atomic update
                    self.manager.atomic_update(f"atomic_{thread_id}_{i}", lambda x: (x or 0) + 1)

                    time.sleep(0.001)
            except Exception as e:
                # If we get here, it might be a deadlock or other issue
                raise e

        # Start multiple threads with complex operations
        threads = []
        for i in range(3):
            thread = threading.Thread(target=complex_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete with timeout
        for thread in threads:
            thread.join(timeout=5.0)  # 5 second timeout
            assert thread.is_alive() is False, "Thread did not complete, possible deadlock"

    def test_observer_notification_thread_safety(self) -> None:
        """Test that observer notifications are thread-safe."""
        events = []
        event_lock = threading.Lock()

        def callback(event: Any) -> None:
            with event_lock:
                events.append(event)

        # Add observer
        self.manager.add_observer(callback)

        def writer(thread_id: int) -> None:
            for i in range(10):
                key = f"thread_{thread_id}_key_{i}"
                value = f"thread_{thread_id}_value_{i}"
                self.manager.set(key, value)
                time.sleep(0.001)

        # Start multiple writer threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=writer, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all events were recorded
        assert len(events) == 30  # 3 threads * 10 writes each

        # Verify no duplicate events
        event_keys = [(event.key_path, event.new_value) for event in events]
        assert len(set(event_keys)) == len(event_keys), "Duplicate events detected"

    def test_configuration_persistence(self) -> None:
        """Test that configuration changes are persisted."""
        # Set some values
        self.manager.set("persistent_key", "persistent_value")
        self.manager.set("another_key", "another_value")

        # Save configuration
        result = self.manager.save_config()
        assert result is True

        # Create new manager instance
        new_manager = ThreadSafeConfigManager(self.config_path)

        # Verify values are loaded
        assert new_manager.get("persistent_key") == "persistent_value"
        assert new_manager.get("another_key") == "another_value"

    def test_validation_thread_safety(self) -> None:
        """Test that validation operations are thread-safe."""
        # Set some test data
        self.manager.set("test.key", "test_value")

        def validator(thread_id: int) -> None:
            for _i in range(10):
                # Validate configuration
                is_valid = self.manager.validate_config()
                assert is_valid is True

                # Get validation errors
                errors = self.manager.get_validation_errors()
                assert isinstance(errors, list)

                time.sleep(0.001)

        # Start multiple validator threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=validator, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

    def test_security_operations_thread_safety(self) -> None:
        """Test that security operations are thread-safe."""

        # Test encryption key rotation
        def security_worker(thread_id):
            for _i in range(5):
                # Get security status
                status = self.manager.get_security_status()
                assert isinstance(status, dict)

                # Test API key operations
                if thread_id == 0:  # Only one thread sets the key
                    self.manager.set_tmdb_api_key("test_api_key_12345")

                # Get API key
                _api_key = self.manager.get_tmdb_api_key()

                time.sleep(0.001)

        # Start multiple security worker threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=security_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()
