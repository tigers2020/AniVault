"""Integrated Executor Manager for unified executor access.

This module provides a unified interface that combines the existing ThreadExecutorManager
with the new HybridExecutorManager, allowing for seamless migration and backward compatibility
while providing access to both ThreadPoolExecutor and ProcessPoolExecutor instances.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Union, Optional

from .thread_executor_manager import ThreadExecutorManager
from .hybrid_executor_manager import HybridExecutorManager

logger = logging.getLogger(__name__)


class IntegratedExecutorManager:
    """Unified manager for both thread and process executors.

    Provides a single interface for accessing both ThreadPoolExecutor and ProcessPoolExecutor
    instances, with automatic selection based on operation type and backward compatibility
    with existing ThreadExecutorManager usage patterns.
    """

    def __init__(self) -> None:
        """Initialize the IntegratedExecutorManager."""
        self._thread_manager = ThreadExecutorManager()
        self._hybrid_manager = HybridExecutorManager()
        
        logger.info("IntegratedExecutorManager initialized with both thread and hybrid managers")

    def get_tmdb_executor(self) -> ThreadPoolExecutor:
        """Get TMDB executor for API operations.
        
        Returns:
            ThreadPoolExecutor: Executor optimized for TMDB API calls
        """
        return self._thread_manager.get_tmdb_executor()

    def get_file_scan_executor(self) -> ThreadPoolExecutor:
        """Get file scan executor for file system operations.
        
        Returns:
            ThreadPoolExecutor: Executor optimized for file scanning
        """
        return self._thread_manager.get_file_scan_executor()

    def get_general_executor(self) -> ThreadPoolExecutor:
        """Get general executor for mixed operations.
        
        Returns:
            ThreadPoolExecutor: Executor for general file processing
        """
        return self._thread_manager.get_general_executor()

    def get_io_executor(self, operation_type: str = "general_io") -> ThreadPoolExecutor:
        """Get I/O executor for I/O-bound operations.
        
        Args:
            operation_type: Type of I/O operation ('tmdb', 'file_scan', 'general_io')
            
        Returns:
            ThreadPoolExecutor: Executor configured for I/O operations
        """
        return self._hybrid_manager.get_io_executor(operation_type)

    def get_cpu_executor(self, operation_type: str = "general_cpu") -> ProcessPoolExecutor:
        """Get CPU executor for CPU-bound operations.
        
        Args:
            operation_type: Type of CPU operation ('parsing', 'grouping', 'general_cpu')
            
        Returns:
            ProcessPoolExecutor: Executor configured for CPU operations
        """
        return self._hybrid_manager.get_cpu_executor(operation_type)

    def get_executor_for_operation(self, operation_type: str) -> Union[ThreadPoolExecutor, ProcessPoolExecutor]:
        """Get the appropriate executor for a specific operation type.
        
        Args:
            operation_type: Type of operation (I/O or CPU bound)
            
        Returns:
            Union[ThreadPoolExecutor, ProcessPoolExecutor]: Appropriate executor
        """
        return self._hybrid_manager.get_executor_for_operation(operation_type)

    def get_executor_for_task(self, task_type: str) -> Union[ThreadPoolExecutor, ProcessPoolExecutor]:
        """Get the appropriate executor based on task type.
        
        Maps common task types to appropriate executors:
        - File scanning: ThreadPoolExecutor (I/O-bound)
        - Anime parsing: ProcessPoolExecutor (CPU-bound)
        - File grouping: ProcessPoolExecutor (CPU-bound)
        - TMDB operations: ThreadPoolExecutor (I/O-bound)
        
        Args:
            task_type: Type of task ('file_scan', 'anime_parse', 'file_group', 'tmdb_call')
            
        Returns:
            Union[ThreadPoolExecutor, ProcessPoolExecutor]: Appropriate executor
        """
        task_mapping = {
            "file_scan": "file_scan",
            "anime_parse": "parsing", 
            "file_group": "grouping",
            "tmdb_call": "tmdb",
            "general_io": "general_io",
            "general_cpu": "general_cpu"
        }
        
        if task_type in task_mapping:
            operation_type = task_mapping[task_type]
            return self.get_executor_for_operation(operation_type)
        
        # Default to general I/O executor for unknown task types
        logger.warning(f"Unknown task type '{task_type}', using general I/O executor")
        return self.get_io_executor("general_io")

    def shutdown_all(self, wait: bool = True) -> None:
        """Shutdown all executor instances.
        
        Args:
            wait: If True, wait for all pending tasks to complete before shutdown
        """
        logger.info("Shutting down all executors")
        
        # Shutdown thread manager
        self._thread_manager.shutdown_all(wait=wait)
        
        # Shutdown hybrid manager
        self._hybrid_manager.shutdown_all(wait=wait)

    def get_configuration_info(self) -> dict:
        """Get current configuration information.
        
        Returns:
            dict: Configuration details from both managers
        """
        thread_config = self._thread_manager.get_configuration_info()
        hybrid_config = self._hybrid_manager.get_configuration_info()
        
        return {
            "thread_manager": thread_config,
            "hybrid_manager": hybrid_config,
            "integration_status": "active"
        }


# Global instance for easy access
_integrated_executor_manager: Optional[IntegratedExecutorManager] = None


def get_integrated_executor_manager() -> IntegratedExecutorManager:
    """Get the global IntegratedExecutorManager instance.
    
    Returns:
        IntegratedExecutorManager: Global instance of the integrated executor manager
    """
    global _integrated_executor_manager
    if _integrated_executor_manager is None:
        _integrated_executor_manager = IntegratedExecutorManager()
    return _integrated_executor_manager


def shutdown_integrated_executor_manager(wait: bool = True) -> None:
    """Shutdown the global IntegratedExecutorManager instance.
    
    Args:
        wait: If True, wait for all pending tasks to complete before shutdown
    """
    global _integrated_executor_manager
    if _integrated_executor_manager is not None:
        _integrated_executor_manager.shutdown_all(wait=wait)
        _integrated_executor_manager = None
