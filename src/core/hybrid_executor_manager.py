"""Hybrid Executor Manager for CPU and I/O bound tasks.

This module provides a unified interface for managing both ThreadPoolExecutor
and ProcessPoolExecutor instances, optimized for different types of operations:
- I/O-bound tasks: ThreadPoolExecutor (file scanning, network calls)
- CPU-bound tasks: ProcessPoolExecutor (parsing, similarity calculations)
"""

import os
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Union, Optional

logger = logging.getLogger(__name__)


class HybridExecutorManager:
    """Manages both ThreadPoolExecutor and ProcessPoolExecutor instances.

    Provides optimized executor configurations for different types of operations:
    - I/O-bound tasks (ThreadPoolExecutor): File scanning, network operations
    - CPU-bound tasks (ProcessPoolExecutor): Parsing, similarity calculations
    """

    def __init__(self) -> None:
        """Initialize the HybridExecutorManager with default configurations."""
        self._io_executors: dict[str, ThreadPoolExecutor] = {}
        self._cpu_executors: dict[str, ProcessPoolExecutor] = {}
        
        # Configuration for different operation types
        self._io_configs = {
            "tmdb": self._calculate_tmdb_workers(),
            "file_scan": self._calculate_file_scan_workers(),
            "general_io": self._calculate_general_io_workers(),
        }
        
        self._cpu_configs = {
            "parsing": self._calculate_parsing_workers(),
            "grouping": self._calculate_grouping_workers(),
            "general_cpu": self._calculate_general_cpu_workers(),
        }

        logger.info(
            f"HybridExecutorManager initialized with I/O workers: {self._io_configs}, "
            f"CPU workers: {self._cpu_configs}"
        )

    def _calculate_tmdb_workers(self) -> int:
        """Calculate optimal worker count for TMDB API calls.

        TMDB API calls are I/O-bound network operations.
        
        Returns:
            int: Recommended number of workers for TMDB operations
        """
        cpu_count = os.cpu_count() or 4
        
        # For I/O-bound tasks like API calls, we can use many more workers than CPU cores
        # Start conservative to avoid hitting TMDB rate limits
        base_workers = 32
        
        # Adjust based on CPU count, but cap at reasonable limits
        if cpu_count >= 8:
            workers = min(64, base_workers + (cpu_count - 4) * 4)
        else:
            workers = min(32, base_workers)
        
        # Allow environment variable override
        return max(8, int(os.getenv("TMDB_WORKERS", workers)))

    def _calculate_file_scan_workers(self) -> int:
        """Calculate optimal worker count for file scanning operations.

        File scanning is I/O-bound disk operations.
        
        Returns:
            int: Recommended number of workers for file scanning
        """
        cpu_count = os.cpu_count() or 4
        
        # For disk I/O, use 1.5x to 2x CPU count as starting point
        workers = int(cpu_count * 1.5)
        
        # Allow environment variable override
        return min(32, max(4, int(os.getenv("FILE_SCAN_WORKERS", workers))))

    def _calculate_general_io_workers(self) -> int:
        """Calculate optimal worker count for general I/O operations.
        
        Returns:
            int: Recommended number of workers for general I/O operations
        """
        cpu_count = os.cpu_count() or 4
        workers = int(cpu_count * 1.2)
        return max(4, min(24, int(os.getenv("GENERAL_IO_WORKERS", workers))))

    def _calculate_parsing_workers(self) -> int:
        """Calculate optimal worker count for parsing operations.

        Parsing is CPU-bound and benefits from ProcessPoolExecutor.
        
        Returns:
            int: Recommended number of workers for parsing operations
        """
        cpu_count = os.cpu_count() or 4
        
        # For CPU-bound tasks, use all available cores
        workers = cpu_count
        
        # Allow environment variable override
        return int(os.getenv("PARSING_WORKERS", workers))

    def _calculate_grouping_workers(self) -> int:
        """Calculate optimal worker count for grouping operations.

        Grouping involves similarity calculations which are CPU-bound.
        
        Returns:
            int: Recommended number of workers for grouping operations
        """
        cpu_count = os.cpu_count() or 4
        
        # For CPU-bound tasks, use all available cores
        workers = cpu_count
        
        # Allow environment variable override
        return int(os.getenv("GROUPING_WORKERS", workers))

    def _calculate_general_cpu_workers(self) -> int:
        """Calculate optimal worker count for general CPU operations.
        
        Returns:
            int: Recommended number of workers for general CPU operations
        """
        cpu_count = os.cpu_count() or 4
        
        # For CPU-bound tasks, use all available cores
        workers = cpu_count
        
        # Allow environment variable override
        return int(os.getenv("GENERAL_CPU_WORKERS", workers))

    def get_io_executor(self, operation_type: str = "general_io") -> ThreadPoolExecutor:
        """Get or create a ThreadPoolExecutor for I/O-bound operations.

        Args:
            operation_type: Type of I/O operation ('tmdb', 'file_scan', 'general_io')

        Returns:
            ThreadPoolExecutor: Executor configured for I/O operations
            
        Raises:
            ValueError: If operation_type is not recognized
        """
        if operation_type not in self._io_configs:
            raise ValueError(
                f"Unknown I/O operation type: {operation_type}. "
                f"Supported types: {list(self._io_configs.keys())}"
            )

        if operation_type not in self._io_executors:
            max_workers = self._io_configs[operation_type]
            self._io_executors[operation_type] = ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix=f"{operation_type.title()}Worker"
            )
            logger.info(f"Created {operation_type} ThreadPoolExecutor with {max_workers} workers")

        executor = self._io_executors[operation_type]
        if executor._shutdown:
            # Recreate if shutdown
            max_workers = self._io_configs[operation_type]
            self._io_executors[operation_type] = ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix=f"{operation_type.title()}Worker"
            )
            logger.info(f"Recreated {operation_type} ThreadPoolExecutor with {max_workers} workers")

        return self._io_executors[operation_type]

    def get_cpu_executor(self, operation_type: str = "general_cpu") -> ProcessPoolExecutor:
        """Get or create a ProcessPoolExecutor for CPU-bound operations.

        Args:
            operation_type: Type of CPU operation ('parsing', 'grouping', 'general_cpu')

        Returns:
            ProcessPoolExecutor: Executor configured for CPU operations
            
        Raises:
            ValueError: If operation_type is not recognized
        """
        if operation_type not in self._cpu_configs:
            raise ValueError(
                f"Unknown CPU operation type: {operation_type}. "
                f"Supported types: {list(self._cpu_configs.keys())}"
            )

        if operation_type not in self._cpu_executors:
            max_workers = self._cpu_configs[operation_type]
            self._cpu_executors[operation_type] = ProcessPoolExecutor(
                max_workers=max_workers
            )
            logger.info(f"Created {operation_type} ProcessPoolExecutor with {max_workers} workers")

        executor = self._cpu_executors[operation_type]
        if executor._shutdown:
            # Recreate if shutdown
            max_workers = self._cpu_configs[operation_type]
            self._cpu_executors[operation_type] = ProcessPoolExecutor(
                max_workers=max_workers
            )
            logger.info(f"Recreated {operation_type} ProcessPoolExecutor with {max_workers} workers")

        return self._cpu_executors[operation_type]

    def get_executor_for_operation(self, operation_type: str) -> Union[ThreadPoolExecutor, ProcessPoolExecutor]:
        """Get the appropriate executor for a specific operation type.

        Args:
            operation_type: Type of operation (I/O or CPU bound)

        Returns:
            Union[ThreadPoolExecutor, ProcessPoolExecutor]: Appropriate executor
            
        Raises:
            ValueError: If operation_type is not recognized
        """
        # Try I/O operations first
        if operation_type in self._io_configs:
            return self.get_io_executor(operation_type)
        
        # Try CPU operations
        if operation_type in self._cpu_configs:
            return self.get_cpu_executor(operation_type)
        
        raise ValueError(
            f"Unknown operation type: {operation_type}. "
            f"Supported I/O types: {list(self._io_configs.keys())}, "
            f"Supported CPU types: {list(self._cpu_configs.keys())}"
        )

    def shutdown_all(self, wait: bool = True) -> None:
        """Shutdown all executor instances.

        Args:
            wait: If True, wait for all pending tasks to complete before shutdown
        """
        logger.info("Shutting down all executors")

        # Shutdown I/O executors
        for operation_type, executor in self._io_executors.items():
            if not executor._shutdown:
                executor.shutdown(wait=wait)
                logger.debug(f"{operation_type} I/O executor shutdown")

        # Shutdown CPU executors
        for operation_type, executor in self._cpu_executors.items():
            if not executor._shutdown:
                executor.shutdown(wait=wait)
                logger.debug(f"{operation_type} CPU executor shutdown")

        # Clear executor dictionaries
        self._io_executors.clear()
        self._cpu_executors.clear()

    def get_configuration_info(self) -> dict:
        """Get current configuration information.

        Returns:
            dict: Configuration details including worker counts and system info
        """
        return {
            "system_cpu_count": os.cpu_count(),
            "io_configs": self._io_configs.copy(),
            "cpu_configs": self._cpu_configs.copy(),
            "active_io_executors": [
                op_type for op_type, executor in self._io_executors.items()
                if not executor._shutdown
            ],
            "active_cpu_executors": [
                op_type for op_type, executor in self._cpu_executors.items()
                if not executor._shutdown
            ],
        }


# Global instance for easy access
_hybrid_executor_manager: Optional[HybridExecutorManager] = None


def get_hybrid_executor_manager() -> HybridExecutorManager:
    """Get the global HybridExecutorManager instance.

    Returns:
        HybridExecutorManager: Global instance of the hybrid executor manager
    """
    global _hybrid_executor_manager
    if _hybrid_executor_manager is None:
        _hybrid_executor_manager = HybridExecutorManager()
    return _hybrid_executor_manager


def shutdown_hybrid_executor_manager(wait: bool = True) -> None:
    """Shutdown the global HybridExecutorManager instance.

    Args:
        wait: If True, wait for all pending tasks to complete before shutdown
    """
    global _hybrid_executor_manager
    if _hybrid_executor_manager is not None:
        _hybrid_executor_manager.shutdown_all(wait=wait)
        _hybrid_executor_manager = None
