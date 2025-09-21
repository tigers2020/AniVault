"""Parallel file processing functions for asynchronous execution.

This module provides thread-safe and process-safe functions that can be used
with concurrent.futures for parallel file processing operations.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .anime_parser import AnimeParser
from .file_classifier import FileClassifier
from .file_scanner import FileScanner
from .models import AnimeFile, ParsedAnimeInfo, ProcessingResult

logger = logging.getLogger(__name__)


class ParallelFileProcessor:
    """Thread-safe file processor for parallel execution.
    
    This class provides stateless methods that can be safely executed
    in parallel by multiple threads or processes.
    """
    
    def __init__(self) -> None:
        """Initialize the parallel file processor."""
        self.anime_parser = AnimeParser()
        self.file_classifier = FileClassifier()
        self.file_scanner = FileScanner(max_workers=1)  # Single worker for individual operations
        
    def process_single_file_path(
        self, 
        file_path: Union[str, Path], 
        include_metadata: bool = True
    ) -> ProcessingResult:
        """Process a single file path and return complete processing result.
        
        This function is designed to be thread-safe and stateless,
        making it suitable for parallel execution.
        
        Args:
            file_path: Path to the file to process
            include_metadata: Whether to include metadata parsing
            
        Returns:
            ProcessingResult containing the processed file information
        """
        start_time = time.time()
        file_path = Path(file_path)
        
        try:
            # Step 1: Create AnimeFile object
            anime_file = self._create_anime_file_safe(file_path)
            if not anime_file:
                return ProcessingResult(
                    success=False,
                    error=f"Failed to create AnimeFile for {file_path}",
                    processing_time=time.time() - start_time
                )
            
            # Step 2: Classify file type
            try:
                file_type = self.file_classifier.classify_file(anime_file)
                anime_file.file_type = file_type
            except (AttributeError, TypeError) as e:
                # Skip classification if not supported or if file_type attribute doesn't exist
                logger.debug(f"File classification skipped: {e}")
                pass
            
            # Step 3: Parse metadata if requested
            parsed_info = None
            if include_metadata:
                parsed_info = self.anime_parser.parse_anime_file(anime_file)
            
            processing_time = time.time() - start_time
            
            return ProcessingResult(
                success=True,
                anime_file=anime_file,
                parsed_info=parsed_info,
                processing_time=processing_time
            )
            
        except Exception as e:
            error_msg = f"Error processing file {file_path}: {e}"
            logger.error(error_msg)
            return ProcessingResult(
                success=False,
                error=error_msg,
                processing_time=time.time() - start_time
            )
    
    def process_file_paths_batch(
        self, 
        file_paths: List[Union[str, Path]], 
        include_metadata: bool = True
    ) -> List[ProcessingResult]:
        """Process multiple file paths in batch.
        
        Args:
            file_paths: List of file paths to process
            include_metadata: Whether to include metadata parsing
            
        Returns:
            List of ProcessingResult objects
        """
        results = []
        
        for file_path in file_paths:
            result = self.process_single_file_path(file_path, include_metadata)
            results.append(result)
        
        return results
    
    def create_anime_file_only(self, file_path: Union[str, Path]) -> Optional[AnimeFile]:
        """Create AnimeFile object from file path only.
        
        This is a lightweight operation for cases where only basic file
        information is needed.
        
        Args:
            file_path: Path to the file
            
        Returns:
            AnimeFile object or None if creation failed
        """
        return self._create_anime_file_safe(Path(file_path))
    
    def parse_anime_file_only(self, anime_file: AnimeFile) -> Optional[ParsedAnimeInfo]:
        """Parse metadata from AnimeFile object only.
        
        Args:
            anime_file: AnimeFile object to parse
            
        Returns:
            ParsedAnimeInfo object or None if parsing failed
        """
        try:
            return self.anime_parser.parse_anime_file(anime_file)
        except Exception as e:
            logger.error(f"Error parsing anime file {anime_file.filename}: {e}")
            return None
    
    def _create_anime_file_safe(self, file_path: Path) -> Optional[AnimeFile]:
        """Safely create AnimeFile object with error handling.
        
        Args:
            file_path: Path to the file
            
        Returns:
            AnimeFile object or None if creation failed
        """
        try:
            # Validate file exists and is accessible
            if not file_path.exists():
                logger.warning(f"File does not exist: {file_path}")
                return None
            
            if not file_path.is_file():
                logger.warning(f"Path is not a file: {file_path}")
                return None
            
            # Get file statistics
            stat = file_path.stat()
            
            # Create AnimeFile object
            anime_file = AnimeFile(
                file_path=file_path,
                filename=file_path.name,
                file_size=stat.st_size,
                file_extension=file_path.suffix.lower(),
                created_at=stat.st_ctime,
                modified_at=stat.st_mtime,
            )
            
            return anime_file
            
        except FileNotFoundError:
            logger.warning(f"File not found: {file_path}")
            return None
        except OSError as e:
            logger.error(f"Cannot access file {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating AnimeFile for {file_path}: {e}")
            return None


# Global instance for use in parallel processing
_global_processor = ParallelFileProcessor()


def process_single_file_path(
    file_path: Union[str, Path], 
    include_metadata: bool = True
) -> ProcessingResult:
    """Process a single file path using the global processor instance.
    
    This function is designed to be used with concurrent.futures
    for parallel execution. Each call uses a fresh processor instance
    to avoid state conflicts.
    
    Args:
        file_path: Path to the file to process
        include_metadata: Whether to include metadata parsing
        
    Returns:
        ProcessingResult containing the processed file information
    """
    # Create a new processor instance for each call to ensure thread safety
    processor = ParallelFileProcessor()
    return processor.process_single_file_path(file_path, include_metadata)


def create_anime_file_only(file_path: Union[str, Path]) -> Optional[AnimeFile]:
    """Create AnimeFile object from file path only using global processor.
    
    Args:
        file_path: Path to the file
        
    Returns:
        AnimeFile object or None if creation failed
    """
    processor = ParallelFileProcessor()
    return processor.create_anime_file_only(file_path)


def parse_anime_file_only(anime_file: AnimeFile) -> Optional[ParsedAnimeInfo]:
    """Parse metadata from AnimeFile object only using global processor.
    
    Args:
        anime_file: AnimeFile object to parse
        
    Returns:
        ParsedAnimeInfo object or None if parsing failed
    """
    processor = ParallelFileProcessor()
    return processor.parse_anime_file_only(anime_file)


def process_file_paths_batch(
    file_paths: List[Union[str, Path]], 
    include_metadata: bool = True
) -> List[ProcessingResult]:
    """Process multiple file paths in batch using global processor.
    
    Args:
        file_paths: List of file paths to process
        include_metadata: Whether to include metadata parsing
        
    Returns:
        List of ProcessingResult objects
    """
    processor = ParallelFileProcessor()
    return processor.process_file_paths_batch(file_paths, include_metadata)


# Utility functions for different processing strategies
def create_file_processing_worker(operation_type: str = "full"):
    """Create a worker function for specific processing operations.
    
    Args:
        operation_type: Type of processing operation
            - "full": Complete processing (file creation + metadata parsing)
            - "file_only": Only create AnimeFile objects
            - "parse_only": Only parse metadata (requires AnimeFile input)
            
    Returns:
        Callable worker function
    """
    if operation_type == "full":
        return process_single_file_path
    elif operation_type == "file_only":
        return create_anime_file_only
    elif operation_type == "parse_only":
        return parse_anime_file_only
    else:
        raise ValueError(f"Unknown operation type: {operation_type}")


def get_processing_statistics(results: List[ProcessingResult]) -> Dict[str, Any]:
    """Generate statistics from processing results.
    
    Args:
        results: List of ProcessingResult objects
        
    Returns:
        Dictionary containing processing statistics
    """
    total_files = len(results)
    successful_files = sum(1 for r in results if r.success)
    failed_files = total_files - successful_files
    
    # Calculate timing statistics
    processing_times = [r.processing_time for r in results if r.success]
    avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
    max_processing_time = max(processing_times) if processing_times else 0
    min_processing_time = min(processing_times) if processing_times else 0
    
    # Count parsed files
    parsed_files = sum(1 for r in results if r.success and r.parsed_info is not None)
    
    return {
        "total_files": total_files,
        "successful_files": successful_files,
        "failed_files": failed_files,
        "success_rate": (successful_files / total_files * 100) if total_files > 0 else 0,
        "parsed_files": parsed_files,
        "parse_success_rate": (parsed_files / successful_files * 100) if successful_files > 0 else 0,
        "avg_processing_time": avg_processing_time,
        "max_processing_time": max_processing_time,
        "min_processing_time": min_processing_time,
        "total_processing_time": sum(processing_times)
    }
