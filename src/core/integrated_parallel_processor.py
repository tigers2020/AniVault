"""Integrated parallel file processor for the existing file processing pipeline.

This module provides a high-level interface that integrates the new parallel
processing capabilities with the existing file processing infrastructure.
"""

import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

from .file_processing_queue import FileProcessingQueue, QueueConfig, QueueStatus
from .hybrid_executor_manager import HybridExecutorManager
from .integrated_executor_manager import IntegratedExecutorManager
from .parallel_file_processor import (
    ParallelFileProcessor,
    process_single_file_path,
    create_anime_file_only,
    parse_anime_file_only,
    get_processing_statistics
)
from .models import AnimeFile, ParsedAnimeInfo, ProcessingResult

logger = logging.getLogger(__name__)


class IntegratedParallelProcessor:
    """High-level processor that integrates parallel processing with existing infrastructure.
    
    This class provides a unified interface for parallel file processing while
    maintaining compatibility with existing file processing workflows.
    """
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        executor_type: str = "hybrid",
        operation_type: str = "file_processing"
    ) -> None:
        """Initialize the integrated parallel processor.
        
        Args:
            max_workers: Maximum number of workers (auto-detected if None)
            executor_type: Type of executor ('thread', 'process', 'hybrid', 'integrated')
            operation_type: Type of operation for executor selection
        """
        self.max_workers = max_workers
        self.executor_type = executor_type
        self.operation_type = operation_type
        
        # Initialize the appropriate executor manager
        if executor_type == "hybrid":
            self.executor_manager = HybridExecutorManager()
        elif executor_type == "integrated":
            self.executor_manager = IntegratedExecutorManager()
        else:
            self.executor_manager = None
        
        # Initialize file processing queue
        queue_config = QueueConfig(
            max_queue_size=1000,
            batch_size=10
        )
        self.processing_queue = FileProcessingQueue(
            config=queue_config,
            executor_type=executor_type,
            max_workers=max_workers,
            operation_type=operation_type
        )
        
        logger.info(
            f"IntegratedParallelProcessor initialized: "
            f"type={executor_type}, operation={operation_type}"
        )
    
    def process_files_parallel(
        self,
        file_paths: List[Union[str, Path]],
        include_metadata: bool = True,
        use_queue: bool = True
    ) -> List[ProcessingResult]:
        """Process files in parallel using the configured executor.
        
        Args:
            file_paths: List of file paths to process
            include_metadata: Whether to include metadata parsing
            use_queue: Whether to use the file processing queue
            
        Returns:
            List of ProcessingResult objects
        """
        if not file_paths:
            return []
        
        logger.info(f"Processing {len(file_paths)} files in parallel")
        start_time = time.time()
        
        if use_queue:
            return self._process_with_queue(file_paths, include_metadata)
        else:
            return self._process_direct(file_paths, include_metadata)
    
    def _process_with_queue(
        self,
        file_paths: List[Union[str, Path]],
        include_metadata: bool
    ) -> List[ProcessingResult]:
        """Process files using the file processing queue."""
        # Add files to queue
        added_count = self.processing_queue.add_items(file_paths)
        logger.info(f"Added {added_count} files to processing queue")
        
        results = []
        
        def worker_function(file_path):
            """Worker function for processing individual files."""
            return process_single_file_path(file_path, include_metadata)
        
        # Start processing
        self.processing_queue.start_processing(worker_function)
        
        # Wait for completion and collect results
        while self.processing_queue.get_status() == QueueStatus.RUNNING:
            time.sleep(0.1)
        
        # Get final statistics
        stats = self.processing_queue.get_stats()
        logger.info(f"Processing completed: {stats.processed_items} processed, {stats.failed_items} failed")
        
        return results
    
    def _process_direct(
        self,
        file_paths: List[Union[str, Path]],
        include_metadata: bool
    ) -> List[ProcessingResult]:
        """Process files directly using the executor manager."""
        if self.executor_manager is None:
            # Fallback to simple ThreadPoolExecutor
            return self._process_with_simple_executor(file_paths, include_metadata)
        
        # Use the configured executor manager
        if hasattr(self.executor_manager, 'execute_parallel'):
            return self.executor_manager.execute_parallel(
                file_paths,
                process_single_file_path,
                include_metadata
            )
        else:
            # Fallback for executors that don't support this method
            return self._process_with_simple_executor(file_paths, include_metadata)
    
    def _process_with_simple_executor(
        self,
        file_paths: List[Union[str, Path]],
        include_metadata: bool
    ) -> List[ProcessingResult]:
        """Process files using a simple ThreadPoolExecutor as fallback."""
        import os
        
        max_workers = self.max_workers or min(32, (os.cpu_count() or 4) + 4)
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(process_single_file_path, path, include_metadata): path
                for path in file_paths
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_path):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    file_path = future_to_path[future]
                    logger.error(f"Error processing {file_path}: {e}")
                    results.append(ProcessingResult(
                        success=False,
                        error=f"Processing failed: {e}",
                        processing_time=0.0
                    ))
        
        return results
    
    def process_files_in_batches(
        self,
        file_paths: List[Union[str, Path]],
        batch_size: int = 10,
        include_metadata: bool = True
    ) -> List[ProcessingResult]:
        """Process files in batches for better resource management.
        
        Args:
            file_paths: List of file paths to process
            batch_size: Number of files to process in each batch
            include_metadata: Whether to include metadata parsing
            
        Returns:
            List of ProcessingResult objects
        """
        all_results = []
        total_batches = (len(file_paths) + batch_size - 1) // batch_size
        
        logger.info(f"Processing {len(file_paths)} files in {total_batches} batches of {batch_size}")
        
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} files)")
            
            batch_results = self.process_files_parallel(batch, include_metadata, use_queue=False)
            all_results.extend(batch_results)
            
            # Small delay between batches to prevent resource exhaustion
            time.sleep(0.1)
        
        return all_results
    
    def process_files_with_progress(
        self,
        file_paths: List[Union[str, Path]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        include_metadata: bool = True
    ) -> List[ProcessingResult]:
        """Process files with progress reporting.
        
        Args:
            file_paths: List of file paths to process
            progress_callback: Callback function for progress updates (processed, total, message)
            include_metadata: Whether to include metadata parsing
            
        Returns:
            List of ProcessingResult objects
        """
        results = []
        total_files = len(file_paths)
        
        if progress_callback:
            progress_callback(0, total_files, "Starting file processing...")
        
        # Process files in smaller batches for better progress reporting
        batch_size = min(50, max(10, total_files // 10))
        
        for i in range(0, total_files, batch_size):
            batch = file_paths[i:i + batch_size]
            
            if progress_callback:
                progress_callback(i, total_files, f"Processing batch {i//batch_size + 1}...")
            
            batch_results = self.process_files_parallel(batch, include_metadata, use_queue=False)
            results.extend(batch_results)
            
            if progress_callback:
                progress_callback(i + len(batch), total_files, f"Processed {len(results)} files")
        
        if progress_callback:
            progress_callback(total_files, total_files, "File processing completed")
        
        return results
    
    def get_processing_stats(self, results: List[ProcessingResult]) -> Dict[str, Any]:
        """Get processing statistics from results.
        
        Args:
            results: List of ProcessingResult objects
            
        Returns:
            Dictionary containing processing statistics
        """
        return get_processing_statistics(results)
    
    def shutdown(self) -> None:
        """Shutdown the processor and clean up resources."""
        if self.processing_queue:
            self.processing_queue.stop_processing(wait=True)
        
        if self.executor_manager and hasattr(self.executor_manager, 'shutdown'):
            self.executor_manager.shutdown()
        
        logger.info("IntegratedParallelProcessor shutdown completed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()


# Convenience functions for common operations
def process_files_parallel(
    file_paths: List[Union[str, Path]],
    max_workers: Optional[int] = None,
    include_metadata: bool = True,
    executor_type: str = "hybrid"
) -> List[ProcessingResult]:
    """Process files in parallel using the integrated processor.
    
    Args:
        file_paths: List of file paths to process
        max_workers: Maximum number of workers
        include_metadata: Whether to include metadata parsing
        executor_type: Type of executor to use
        
    Returns:
        List of ProcessingResult objects
    """
    with IntegratedParallelProcessor(
        max_workers=max_workers,
        executor_type=executor_type
    ) as processor:
        return processor.process_files_parallel(file_paths, include_metadata)


def process_files_with_progress(
    file_paths: List[Union[str, Path]],
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    max_workers: Optional[int] = None,
    include_metadata: bool = True
) -> List[ProcessingResult]:
    """Process files in parallel with progress reporting.
    
    Args:
        file_paths: List of file paths to process
        progress_callback: Progress callback function
        max_workers: Maximum number of workers
        include_metadata: Whether to include metadata parsing
        
    Returns:
        List of ProcessingResult objects
    """
    with IntegratedParallelProcessor(max_workers=max_workers) as processor:
        return processor.process_files_with_progress(
            file_paths, progress_callback, include_metadata
        )
