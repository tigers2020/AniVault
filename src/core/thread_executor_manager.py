"""ThreadPoolExecutor management for file processing operations.

This module provides a centralized way to configure and manage ThreadPoolExecutor
instances for different types of file processing operations, with optimized
worker counts for I/O-bound tasks like TMDB API calls and file scanning.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class ThreadExecutorManager:
    """Manages ThreadPoolExecutor instances with optimized configurations.

    Provides different executor configurations for different types of operations:
    - TMDB API calls (I/O-bound, network operations)
    - File scanning (I/O-bound, disk operations)
    - General file processing (mixed I/O and CPU operations)
    """

    def __init__(self) -> None:
        """Initialize the ThreadExecutorManager with default configurations."""
        self._tmdb_executor: ThreadPoolExecutor | None = None
        self._file_scan_executor: ThreadPoolExecutor | None = None
        self._general_executor: ThreadPoolExecutor | None = None

        # Configuration for different operation types
        self._tmdb_max_workers = self._calculate_tmdb_workers()
        self._file_scan_max_workers = self._calculate_file_scan_workers()
        self._general_max_workers = self._calculate_general_workers()

        logger.info(
            f"ThreadExecutorManager initialized with workers: "
            f"TMDB={self._tmdb_max_workers}, "
            f"FileScan={self._file_scan_max_workers}, "
            f"General={self._general_max_workers}"
        )

    def _calculate_tmdb_workers(self) -> int:
        """Calculate optimal worker count for TMDB API calls.

        TMDB API calls are I/O-bound network operations. Based on research:
        - Start with 32-64 workers for synchronous I/O-bound tasks
        - Consider TMDB rate limits (40 requests per 10 seconds)
        - Allow for network latency and connection pooling

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

        # Ensure minimum of 8 workers for reasonable parallelism
        return max(8, workers)

    def _calculate_file_scan_workers(self) -> int:
        """Calculate optimal worker count for file scanning operations.

        File scanning is I/O-bound disk operations. Based on research:
        - Can benefit from multiple threads, especially with SSDs
        - Start with os.cpu_count() to 2 * os.cpu_count()

        Returns:
            int: Recommended number of workers for file scanning
        """
        cpu_count = os.cpu_count() or 4

        # For disk I/O, use 1.5x to 2x CPU count as starting point
        workers = int(cpu_count * 1.5)

        # Cap at reasonable limits
        return min(32, max(4, workers))

    def _calculate_general_workers(self) -> int:
        """Calculate optimal worker count for general file processing.

        General processing may include mixed I/O and CPU operations.
        Use a moderate number that balances parallelism with resource usage.

        Returns:
            int: Recommended number of workers for general operations
        """
        cpu_count = os.cpu_count() or 4

        # For mixed workloads, use 1.2x to 1.5x CPU count
        workers = int(cpu_count * 1.2)

        return max(4, min(24, workers))

    def get_tmdb_executor(self) -> ThreadPoolExecutor:
        """Get or create a ThreadPoolExecutor optimized for TMDB API calls.

        Returns:
            ThreadPoolExecutor: Executor configured for network I/O operations
        """
        if self._tmdb_executor is None or self._tmdb_executor._shutdown:
            self._tmdb_executor = ThreadPoolExecutor(
                max_workers=self._tmdb_max_workers, thread_name_prefix="TMDBWorker"
            )
            logger.info(f"Created TMDB ThreadPoolExecutor with {self._tmdb_max_workers} workers")

        return self._tmdb_executor

    def get_file_scan_executor(self) -> ThreadPoolExecutor:
        """Get or create a ThreadPoolExecutor optimized for file scanning.

        Returns:
            ThreadPoolExecutor: Executor configured for disk I/O operations
        """
        if self._file_scan_executor is None or self._file_scan_executor._shutdown:
            self._file_scan_executor = ThreadPoolExecutor(
                max_workers=self._file_scan_max_workers, thread_name_prefix="FileScanWorker"
            )
            logger.info(
                f"Created FileScan ThreadPoolExecutor with {self._file_scan_max_workers} workers"
            )

        return self._file_scan_executor

    def get_general_executor(self) -> ThreadPoolExecutor:
        """Get or create a ThreadPoolExecutor for general file processing.

        Returns:
            ThreadPoolExecutor: Executor configured for mixed I/O and CPU operations
        """
        if self._general_executor is None or self._general_executor._shutdown:
            self._general_executor = ThreadPoolExecutor(
                max_workers=self._general_max_workers, thread_name_prefix="GeneralWorker"
            )
            logger.info(
                f"Created General ThreadPoolExecutor with {self._general_max_workers} workers"
            )

        return self._general_executor

    def get_executor_for_operation(self, operation_type: str) -> ThreadPoolExecutor:
        """Get the appropriate executor for a specific operation type.

        Args:
            operation_type: Type of operation ('tmdb', 'file_scan', 'general')

        Returns:
            ThreadPoolExecutor: Appropriate executor for the operation type

        Raises:
            ValueError: If operation_type is not recognized
        """
        if operation_type == "tmdb":
            return self.get_tmdb_executor()
        elif operation_type == "file_scan":
            return self.get_file_scan_executor()
        elif operation_type == "general":
            return self.get_general_executor()
        else:
            raise ValueError(
                f"Unknown operation type: {operation_type}. "
                f"Supported types: 'tmdb', 'file_scan', 'general'"
            )

    def shutdown_all(self, wait: bool = True) -> None:
        """Shutdown all executor instances.

        Args:
            wait: If True, wait for all pending tasks to complete before shutdown
        """
        logger.info("Shutting down all ThreadPoolExecutors")

        if self._tmdb_executor and not self._tmdb_executor._shutdown:
            self._tmdb_executor.shutdown(wait=wait)
            logger.debug("TMDB executor shutdown")

        if self._file_scan_executor and not self._file_scan_executor._shutdown:
            self._file_scan_executor.shutdown(wait=wait)
            logger.debug("File scan executor shutdown")

        if self._general_executor and not self._general_executor._shutdown:
            self._general_executor.shutdown(wait=wait)
            logger.debug("General executor shutdown")

    def get_configuration_info(self) -> dict:
        """Get current configuration information.

        Returns:
            dict: Configuration details including worker counts and system info
        """
        return {
            "system_cpu_count": os.cpu_count(),
            "tmdb_max_workers": self._tmdb_max_workers,
            "file_scan_max_workers": self._file_scan_max_workers,
            "general_max_workers": self._general_max_workers,
            "tmdb_executor_active": (
                self._tmdb_executor is not None and not self._tmdb_executor._shutdown
            ),
            "file_scan_executor_active": (
                self._file_scan_executor is not None and not self._file_scan_executor._shutdown
            ),
            "general_executor_active": (
                self._general_executor is not None and not self._general_executor._shutdown
            ),
        }


# Global instance for easy access throughout the application
_thread_executor_manager: ThreadExecutorManager | None = None


def get_thread_executor_manager() -> ThreadExecutorManager:
    """Get the global ThreadExecutorManager instance.

    Returns:
        ThreadExecutorManager: Global instance
    """
    global _thread_executor_manager

    if _thread_executor_manager is None:
        _thread_executor_manager = ThreadExecutorManager()
        logger.info("Created global ThreadExecutorManager instance")

    return _thread_executor_manager


def cleanup_thread_executors() -> None:
    """Cleanup all thread executors. Call this when the application shuts down."""
    global _thread_executor_manager

    if _thread_executor_manager is not None:
        _thread_executor_manager.shutdown_all(wait=True)
        _thread_executor_manager = None
        logger.info("Cleaned up all thread executors")
