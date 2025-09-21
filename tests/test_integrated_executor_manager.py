"""Tests for IntegratedExecutorManager."""

import pytest
import os
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from src.core.integrated_executor_manager import IntegratedExecutorManager


class TestIntegratedExecutorManager:
    """Test cases for IntegratedExecutorManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = IntegratedExecutorManager()

    def teardown_method(self):
        """Clean up after tests."""
        self.manager.shutdown_all(wait=True)

    def test_manager_initialization(self):
        """Test that manager initializes correctly."""
        assert self.manager is not None
        assert self.manager._thread_manager is not None
        assert self.manager._hybrid_manager is not None

    def test_tmdb_executor(self):
        """Test TMDB executor retrieval."""
        executor = self.manager.get_tmdb_executor()
        assert isinstance(executor, ThreadPoolExecutor)
        assert not executor._shutdown

    def test_file_scan_executor(self):
        """Test file scan executor retrieval."""
        executor = self.manager.get_file_scan_executor()
        assert isinstance(executor, ThreadPoolExecutor)
        assert not executor._shutdown

    def test_general_executor(self):
        """Test general executor retrieval."""
        executor = self.manager.get_general_executor()
        assert isinstance(executor, ThreadPoolExecutor)
        assert not executor._shutdown

    def test_io_executor_retrieval(self):
        """Test I/O executor retrieval for different operation types."""
        # Test general I/O executor
        executor = self.manager.get_io_executor("general_io")
        assert isinstance(executor, ThreadPoolExecutor)
        assert not executor._shutdown

        # Test file scan executor via hybrid manager
        executor = self.manager.get_io_executor("file_scan")
        assert isinstance(executor, ThreadPoolExecutor)
        assert not executor._shutdown

        # Test TMDB executor via hybrid manager
        executor = self.manager.get_io_executor("tmdb")
        assert isinstance(executor, ThreadPoolExecutor)
        assert not executor._shutdown

    def test_cpu_executor_retrieval(self):
        """Test CPU executor retrieval for different operation types."""
        # Skip on Windows due to multiprocessing issues in tests
        if os.name == 'nt':
            pytest.skip("Skipping ProcessPoolExecutor tests on Windows")

        # Test general CPU executor
        executor = self.manager.get_cpu_executor("general_cpu")
        assert isinstance(executor, ProcessPoolExecutor)
        assert not executor._shutdown

        # Test parsing executor
        executor = self.manager.get_cpu_executor("parsing")
        assert isinstance(executor, ProcessPoolExecutor)
        assert not executor._shutdown

        # Test grouping executor
        executor = self.manager.get_cpu_executor("grouping")
        assert isinstance(executor, ProcessPoolExecutor)
        assert not executor._shutdown

    def test_executor_for_operation(self):
        """Test getting executor for specific operation types."""
        # Test I/O operations
        executor = self.manager.get_executor_for_operation("tmdb")
        assert isinstance(executor, ThreadPoolExecutor)

        executor = self.manager.get_executor_for_operation("file_scan")
        assert isinstance(executor, ThreadPoolExecutor)

        # Test CPU operations (skip on Windows)
        if os.name != 'nt':
            executor = self.manager.get_executor_for_operation("parsing")
            assert isinstance(executor, ProcessPoolExecutor)

            executor = self.manager.get_executor_for_operation("grouping")
            assert isinstance(executor, ProcessPoolExecutor)

    def test_executor_for_task(self):
        """Test getting executor based on task type."""
        # Test file scanning task
        executor = self.manager.get_executor_for_task("file_scan")
        assert isinstance(executor, ThreadPoolExecutor)

        # Test TMDB call task
        executor = self.manager.get_executor_for_task("tmdb_call")
        assert isinstance(executor, ThreadPoolExecutor)

        # Test CPU-bound tasks (skip on Windows)
        if os.name != 'nt':
            executor = self.manager.get_executor_for_task("anime_parse")
            assert isinstance(executor, ProcessPoolExecutor)

            executor = self.manager.get_executor_for_task("file_group")
            assert isinstance(executor, ProcessPoolExecutor)

        # Test unknown task type (should default to general I/O)
        executor = self.manager.get_executor_for_task("unknown_task")
        assert isinstance(executor, ThreadPoolExecutor)

    def test_executor_reuse(self):
        """Test that executors are reused when requested multiple times."""
        executor1 = self.manager.get_tmdb_executor()
        executor2 = self.manager.get_tmdb_executor()
        assert executor1 is executor2

        executor1 = self.manager.get_io_executor("general_io")
        executor2 = self.manager.get_io_executor("general_io")
        assert executor1 is executor2

    def test_simple_task_execution(self):
        """Test that executors can execute simple tasks."""
        def simple_task(x):
            return x * 2

        # Test with ThreadPoolExecutor
        executor = self.manager.get_general_executor()
        future = executor.submit(simple_task, 5)
        result = future.result(timeout=5)
        assert result == 10

        # Test with I/O executor
        executor = self.manager.get_io_executor("general_io")
        future = executor.submit(simple_task, 3)
        result = future.result(timeout=5)
        assert result == 6

    def test_configuration_info(self):
        """Test that configuration info is returned correctly."""
        config = self.manager.get_configuration_info()
        
        assert "thread_manager" in config
        assert "hybrid_manager" in config
        assert "integration_status" in config
        assert config["integration_status"] == "active"

        # Check thread manager config
        thread_config = config["thread_manager"]
        assert "tmdb_max_workers" in thread_config
        assert "file_scan_max_workers" in thread_config
        assert "general_max_workers" in thread_config

        # Check hybrid manager config
        hybrid_config = config["hybrid_manager"]
        assert "system_cpu_count" in hybrid_config
        assert "io_configs" in hybrid_config
        assert "cpu_configs" in hybrid_config

    def test_shutdown_all(self):
        """Test that all executors are properly shutdown."""
        # Get some executors
        tmdb_executor = self.manager.get_tmdb_executor()
        file_scan_executor = self.manager.get_file_scan_executor()
        
        # Verify they are active
        assert not tmdb_executor._shutdown
        assert not file_scan_executor._shutdown

        # Shutdown all
        self.manager.shutdown_all(wait=True)

        # Verify they are shutdown
        assert tmdb_executor._shutdown
        assert file_scan_executor._shutdown

    def test_executor_after_shutdown(self):
        """Test that new executors are created after shutdown."""
        # Get executor and shutdown
        executor1 = self.manager.get_tmdb_executor()
        self.manager.shutdown_all(wait=True)
        assert executor1._shutdown

        # Get new executor
        executor2 = self.manager.get_tmdb_executor()
        assert not executor2._shutdown
        assert executor1 is not executor2


class TestGlobalIntegratedExecutorManager:
    """Test cases for global IntegratedExecutorManager instance."""

    def teardown_method(self):
        """Clean up after tests."""
        from src.core.integrated_executor_manager import shutdown_integrated_executor_manager
        shutdown_integrated_executor_manager(wait=True)

    def test_global_instance_creation(self):
        """Test global instance creation and access."""
        from src.core.integrated_executor_manager import get_integrated_executor_manager
        
        manager1 = get_integrated_executor_manager()
        manager2 = get_integrated_executor_manager()
        
        assert manager1 is manager2
        assert manager1 is not None

    def test_global_instance_shutdown(self):
        """Test global instance shutdown."""
        from src.core.integrated_executor_manager import (
            get_integrated_executor_manager,
            shutdown_integrated_executor_manager
        )
        
        manager1 = get_integrated_executor_manager()
        assert manager1 is not None
        
        shutdown_integrated_executor_manager(wait=True)
        
        manager2 = get_integrated_executor_manager()
        assert manager2 is not None
        assert manager1 is not manager2  # New instance should be created
