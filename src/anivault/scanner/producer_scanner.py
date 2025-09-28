"""Producer Scanner module for AniVault.

This module provides a dedicated Scanner class that acts as a producer,
scanning directories and putting file paths into a bounded queue for
processing by consumer threads.
"""

import queue
from pathlib import Path
from typing import Callable, Optional, Any

from anivault.core.logging import get_logger
from anivault.scanner.file_scanner import scan_directory_paths

logger = get_logger(__name__)


class Scanner:
    """Producer scanner that puts file paths into a bounded queue.
    
    This class acts as a producer in the producer-consumer pattern,
    scanning directories and putting file paths into a bounded queue
    for processing by consumer threads.
    
    Attributes:
        extension_filter: Function to filter files by extension.
        stats: Dictionary tracking scanner statistics.
    """
    
    def __init__(
        self,
        extension_filter: Optional[Callable[[str], bool]] = None
    ) -> None:
        """Initialize the Scanner.
        
        Args:
            extension_filter: Optional function to filter files by extension.
                If None, all files are included.
        """
        self.extension_filter = extension_filter
        
        # Statistics tracking
        self.stats = {
            "directories_scanned": 0,
            "files_found": 0,
            "files_filtered": 0,
            "files_queued": 0,
            "queue_put_blocks": 0,
            "queue_put_errors": 0
        }
        
        logger.info(f"Initialized Scanner with extension_filter={extension_filter is not None}")
    
    def scan(
        self,
        directory_path: str | Path,
        file_queue: queue.Queue,
        num_consumers: int = 1
    ) -> None:
        """Scan a directory and put file paths into the bounded queue.
        
        Args:
            directory_path: Path to the directory to scan.
            file_queue: Bounded queue to put file paths into.
            num_consumers: Number of consumer threads (for end-of-queue signaling).
            
        Raises:
            Exception: If scanning fails.
        """
        try:
            logger.info(f"Starting scan of directory: {directory_path}")
            self.stats["directories_scanned"] += 1
            
            files_processed = 0
            
            for file_path in scan_directory_paths(directory_path):
                self.stats["files_found"] += 1
                
                # Apply extension filter if provided
                if self.extension_filter is not None:
                    if not self.extension_filter(file_path):
                        self.stats["files_filtered"] += 1
                        continue
                
                # Put file into bounded queue (this will block if queue is full)
                try:
                    file_queue.put(file_path, timeout=1)
                    self.stats["files_queued"] += 1
                    files_processed += 1
                    logger.debug(f"Queued file: {file_path}")
                    
                except queue.Full:
                    # Queue is full, backpressure in effect
                    self.stats["queue_put_blocks"] += 1
                    logger.warning(f"Queue full, blocking on file: {file_path}")
                    
                    # Block until space is available
                    try:
                        file_queue.put(file_path)
                        self.stats["files_queued"] += 1
                        files_processed += 1
                        logger.debug(f"Queued file (after block): {file_path}")
                    except Exception as e:
                        self.stats["queue_put_errors"] += 1
                        logger.error(f"Error putting file {file_path} into queue: {e}")
                        continue
                        
                except Exception as e:
                    self.stats["queue_put_errors"] += 1
                    logger.error(f"Error putting file {file_path} into queue: {e}")
                    continue
            
            # Signal end of queue by putting None for each consumer
            for _ in range(num_consumers):
                try:
                    file_queue.put(None, timeout=1)
                    logger.debug("Sent end-of-queue signal")
                except queue.Full:
                    # If queue is full, block until we can put the signal
                    file_queue.put(None)
                    logger.debug("Sent end-of-queue signal (after block)")
                except Exception as e:
                    logger.error(f"Error sending end-of-queue signal: {e}")
            
            logger.info(
                f"Scan completed for {directory_path}: "
                f"{files_processed} files processed, "
                f"{self.stats['files_filtered']} files filtered"
            )
            
        except Exception as e:
            logger.error(f"Error scanning directory {directory_path}: {e}")
            # Still try to signal end of queue to prevent consumers from hanging
            try:
                for _ in range(num_consumers):
                    file_queue.put(None, timeout=1)
            except Exception:
                pass
            raise
    
    def get_stats(self) -> dict[str, Any]:
        """Get scanner statistics.
        
        Returns:
            Dictionary containing scanner statistics.
        """
        return self.stats.copy()
    
    def reset_stats(self) -> None:
        """Reset scanner statistics."""
        self.stats = {
            "directories_scanned": 0,
            "files_found": 0,
            "files_filtered": 0,
            "files_queued": 0,
            "queue_put_blocks": 0,
            "queue_put_errors": 0
        }
        logger.debug("Scanner statistics reset")
