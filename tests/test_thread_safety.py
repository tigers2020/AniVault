"""
Tests for thread safety mechanisms in AniVault application.

This module tests the thread safety utilities and ensures proper
synchronization across different components.
"""

import threading

import pytest

from src.core.services.file_pipeline_worker import FilePipelineWorker, WorkerTask
from src.core.services.thread_safety import (
    ThreadSafeCounter,
    ThreadSafeDict,
    ThreadSafeList,
    ThreadSafeProperty,
    ThreadSafetyValidator,
    python_thread_safe_method,
    thread_safe_method,
)
from src.viewmodels.base_viewmodel import BaseViewModel


class TestThreadSafeProperty:
    """Test ThreadSafeProperty functionality."""

    def test_thread_safe_property_get_set(self) -> None:
        """Test basic property get/set operations."""

        class TestClass:
            def __init__(self):
                self._value = 0

            def _get_value(self):
                return self._value

            def _set_value(self, value):
                self._value = value

            value = ThreadSafeProperty(_get_value, _set_value)

        obj = TestClass()
        assert obj.value == 0

        obj.value = 42
        assert obj.value == 42

    def test_thread_safe_property_read_only(self) -> None:
        """Test read-only property behavior."""

        class TestClass:
            def __init__(self):
                self._value = 42

            def _get_value(self):
                return self._value

            value = ThreadSafeProperty(_get_value)

        obj = TestClass()
        assert obj.value == 42

        with pytest.raises(AttributeError):
            obj.value = 100


class TestThreadSafeCounter:
    """Test ThreadSafeCounter functionality."""

    def test_counter_initialization(self) -> None:
        """Test counter initialization."""
        counter = ThreadSafeCounter(10)
        assert counter.get_value() == 10

    def test_counter_increment(self) -> None:
        """Test counter increment operations."""
        counter = ThreadSafeCounter(0)
        assert counter.increment() == 1
        assert counter.increment(5) == 6
        assert counter.get_value() == 6

    def test_counter_decrement(self) -> None:
        """Test counter decrement operations."""
        counter = ThreadSafeCounter(10)
        assert counter.decrement() == 9
        assert counter.decrement(3) == 6
        assert counter.get_value() == 6

    def test_counter_set_value(self) -> None:
        """Test counter value setting."""
        counter = ThreadSafeCounter(0)
        counter.set_value(100)
        assert counter.get_value() == 100

    def test_counter_reset(self) -> None:
        """Test counter reset."""
        counter = ThreadSafeCounter(50)
        counter.reset()
        assert counter.get_value() == 0


class TestThreadSafeList:
    """Test ThreadSafeList functionality."""

    def test_list_initialization(self) -> None:
        """Test list initialization."""
        items = [1, 2, 3]
        safe_list = ThreadSafeList(items)
        assert safe_list.get_all_items() == items
        assert len(safe_list) == 3

    def test_list_append(self) -> None:
        """Test list append operations."""
        safe_list = ThreadSafeList()
        safe_list.append(1)
        safe_list.append(2)
        assert safe_list.get_all_items() == [1, 2]
        assert len(safe_list) == 2

    def test_list_extend(self) -> None:
        """Test list extend operations."""
        safe_list = ThreadSafeList([1, 2])
        safe_list.extend([3, 4, 5])
        assert safe_list.get_all_items() == [1, 2, 3, 4, 5]

    def test_list_remove(self) -> None:
        """Test list remove operations."""
        safe_list = ThreadSafeList([1, 2, 3, 2])
        assert safe_list.remove(2) == True
        assert safe_list.get_all_items() == [1, 3, 2]
        assert safe_list.remove(99) == False

    def test_list_pop(self) -> None:
        """Test list pop operations."""
        safe_list = ThreadSafeList([1, 2, 3])
        assert safe_list.pop() == 3
        assert safe_list.pop(0) == 1
        assert safe_list.get_all_items() == [2]

    def test_list_clear(self) -> None:
        """Test list clear operations."""
        safe_list = ThreadSafeList([1, 2, 3])
        safe_list.clear()
        assert safe_list.get_all_items() == []
        assert len(safe_list) == 0


class TestThreadSafeDict:
    """Test ThreadSafeDict functionality."""

    def test_dict_initialization(self) -> None:
        """Test dictionary initialization."""
        items = {"a": 1, "b": 2}
        safe_dict = ThreadSafeDict(items)
        assert safe_dict.get_all_items() == items
        assert len(safe_dict) == 2

    def test_dict_get_set(self) -> None:
        """Test dictionary get/set operations."""
        safe_dict = ThreadSafeDict()
        safe_dict.set("key1", "value1")
        assert safe_dict.get("key1") == "value1"
        assert safe_dict.get("nonexistent", "default") == "default"

    def test_dict_delete(self) -> None:
        """Test dictionary delete operations."""
        safe_dict = ThreadSafeDict({"a": 1, "b": 2})
        assert safe_dict.delete("a") == True
        assert safe_dict.get_all_items() == {"b": 2}
        assert safe_dict.delete("c") == False

    def test_dict_clear(self) -> None:
        """Test dictionary clear operations."""
        safe_dict = ThreadSafeDict({"a": 1, "b": 2})
        safe_dict.clear()
        assert safe_dict.get_all_items() == {}
        assert len(safe_dict) == 0


class TestThreadSafeDecorators:
    """Test thread safety decorators."""

    def test_thread_safe_method_decorator(self) -> None:
        """Test thread_safe_method decorator."""

        class TestClass:
            def __init__(self):
                self._value = 0
                self._mutex = QMutex()

            @thread_safe_method()
            def increment(self):
                self._value += 1
                return self._value

        obj = TestClass()
        assert obj.increment() == 1
        assert obj.increment() == 2

    def test_python_thread_safe_method_decorator(self) -> None:
        """Test python_thread_safe_method decorator."""

        class TestClass:
            def __init__(self):
                self._value = 0
                self._python_lock = threading.Lock()

            @python_thread_safe_method()
            def increment(self):
                self._value += 1
                return self._value

        obj = TestClass()
        assert obj.increment() == 1
        assert obj.increment() == 2


class TestThreadSafetyValidator:
    """Test ThreadSafetyValidator functionality."""

    def test_validate_mutex_usage(self) -> None:
        """Test mutex usage validation."""

        class TestClass:
            def __init__(self):
                self._mutex = QMutex()

        obj = TestClass()
        assert ThreadSafetyValidator.validate_mutex_usage(obj) == True

        obj._mutex = None
        assert ThreadSafetyValidator.validate_mutex_usage(obj) == False

    def test_validate_lock_usage(self) -> None:
        """Test lock usage validation."""

        class TestClass:
            def __init__(self):
                self._python_lock = threading.Lock()

        obj = TestClass()
        assert ThreadSafetyValidator.validate_lock_usage(obj) == True

        obj._python_lock = None
        assert ThreadSafetyValidator.validate_lock_usage(obj) == False


class TestConcurrentAccess:
    """Test concurrent access scenarios."""

    def test_concurrent_counter_access(self) -> None:
        """Test concurrent access to ThreadSafeCounter."""
        counter = ThreadSafeCounter(0)
        results = []

        def increment_worker():
            for _ in range(100):
                counter.increment()
                results.append(counter.get_value())

        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=increment_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify final value
        assert counter.get_value() == 500
        assert len(results) == 500

    def test_concurrent_list_access(self) -> None:
        """Test concurrent access to ThreadSafeList."""
        safe_list = ThreadSafeList()
        results = []

        def list_worker(worker_id):
            for i in range(10):
                safe_list.append(f"worker_{worker_id}_item_{i}")
                results.append(len(safe_list))

        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=list_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify final state
        assert len(safe_list) == 30
        assert len(results) == 30


class TestBaseViewModelThreadSafety:
    """Test thread safety in BaseViewModel."""

    def test_viewmodel_property_thread_safety(self) -> None:
        """Test that ViewModel properties are thread-safe."""

        class TestViewModel(BaseViewModel):
            def _setup_commands(self):
                pass

            def _setup_properties(self):
                self.set_property("test_value", 0)

        viewmodel = TestViewModel()
        viewmodel.initialize()

        # Test property access from multiple threads
        results = []

        def property_worker():
            for i in range(10):
                viewmodel.set_property("test_value", i)
                results.append(viewmodel.get_property("test_value"))

        threads = []
        for _ in range(3):
            thread = threading.Thread(target=property_worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify no race conditions occurred
        assert len(results) == 30

    def test_viewmodel_command_thread_safety(self) -> None:
        """Test that ViewModel commands are thread-safe."""

        class TestViewModel(BaseViewModel):
            def _setup_commands(self):
                self.add_command("test_command", self._test_command)

            def _setup_properties(self):
                self.set_property("command_count", 0)

            def _test_command(self):
                current = self.get_property("command_count")
                self.set_property("command_count", current + 1)
                return current + 1

        viewmodel = TestViewModel()
        viewmodel.initialize()

        # Test command execution from multiple threads
        results = []

        def command_worker():
            for _ in range(5):
                try:
                    result = viewmodel.execute_command("test_command")
                    results.append(result)
                except Exception as e:
                    results.append(f"Error: {e}")

        threads = []
        for _ in range(3):
            thread = threading.Thread(target=command_worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify command execution was thread-safe
        assert len(results) == 15
        # All results should be numbers (no errors)
        assert all(isinstance(r, int) for r in results)


class TestFilePipelineWorkerThreadSafety:
    """Test thread safety in FilePipelineWorker."""

    def test_worker_task_queue_thread_safety(self) -> None:
        """Test that worker task queue is thread-safe."""
        worker = FilePipelineWorker()

        class TestTask(WorkerTask):
            def __init__(self, task_id):
                self.task_id = task_id

            def execute(self):
                return f"Task {self.task_id}"

            def get_name(self):
                return f"TestTask_{self.task_id}"

        # Add tasks from multiple threads
        results = []

        def add_tasks_worker(worker_id):
            for i in range(5):
                task = TestTask(f"{worker_id}_{i}")
                worker.add_task(task)
                results.append(worker.get_queue_size())

        threads = []
        for i in range(3):
            thread = threading.Thread(target=add_tasks_worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify queue size is correct
        assert worker.get_queue_size() == 15
        assert len(results) == 15


if __name__ == "__main__":
    pytest.main([__file__])
