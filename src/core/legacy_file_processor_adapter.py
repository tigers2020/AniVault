"""Adapter for integrating parallel file processing with existing legacy systems.

This module provides compatibility layers to integrate the new parallel
processing capabilities with existing file processing workflows.
"""

import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from .file_scanner import FileScanner, ScanResult
from .integrated_parallel_processor import IntegratedParallelProcessor
from .parallel_file_processor import ProcessingResult, get_processing_statistics
from .models import AnimeFile, ParsedAnimeInfo

logger = logging.getLogger(__name__)


class LegacyFileProcessorAdapter:
    """Adapter to integrate parallel processing with existing file processing systems.
    
    This class provides a drop-in replacement for the existing FileScanner
    while leveraging the new parallel processing capabilities.
    """
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        executor_type: str = "hybrid",
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> None:
        """Initialize the legacy adapter.
        
        Args:
            max_workers: Maximum number of workers for parallel processing
            executor_type: Type of executor to use ('thread', 'process', 'hybrid')
            progress_callback: Progress callback function (compatible with FileScanner)
        """
        self.max_workers = max_workers
        self.executor_type = executor_type
        self.progress_callback = progress_callback
        self._cancelled = False
        
        # Initialize the parallel processor
        self.parallel_processor = IntegratedParallelProcessor(
            max_workers=max_workers,
            executor_type=executor_type,
            operation_type="legacy_file_processing"
        )
        
        # Initialize legacy scanner for fallback
        self.legacy_scanner = FileScanner(
            max_workers=1,  # Single worker for legacy compatibility
            progress_callback=progress_callback
        )
        
        logger.info(
            f"LegacyFileProcessorAdapter initialized: "
            f"max_workers={max_workers}, executor_type={executor_type}"
        )
    
    def scan_directory(
        self, 
        directory: Path, 
        recursive: bool = True, 
        follow_symlinks: bool = False,
        use_parallel: bool = True
    ) -> ScanResult:
        """Scan directory using parallel processing with legacy compatibility.
        
        Args:
            directory: Directory path to scan
            recursive: Whether to scan subdirectories recursively
            follow_symlinks: Whether to follow symbolic links
            use_parallel: Whether to use parallel processing (fallback to legacy if False)
            
        Returns:
            ScanResult compatible with existing FileScanner
        """
        if not use_parallel:
            # Fallback to legacy scanner
            return self.legacy_scanner.scan_directory(directory, recursive, follow_symlinks)
        
        start_time = time.time()
        
        try:
            # Validate directory
            if not directory.exists():
                raise FileNotFoundError(f"Directory does not exist: {directory}")
            
            if not directory.is_dir():
                raise NotADirectoryError(f"Path is not a directory: {directory}")
            
            # Get file paths using legacy scanner logic
            file_paths = self._collect_file_paths(directory, recursive, follow_symlinks)
            total_files = len(file_paths)
            
            # Count all files for total_files_found
            all_files = self._collect_all_files(directory, recursive, follow_symlinks)
            total_files_found = len(all_files)
            
            if self.progress_callback:
                self.progress_callback(0, f"Found {total_files} files to process...")
            
            # Process files in parallel
            files = []
            errors = []
            
            if total_files > 0:
                files, errors = self._process_files_parallel_adapted(file_paths, total_files)
            
            scan_duration = time.time() - start_time
            
            if self.progress_callback:
                self.progress_callback(100, f"Scan completed: {len(files)} files processed")
            
            return ScanResult(
                files=files,
                scan_duration=scan_duration,
                total_files_found=total_files_found,
                supported_files=len(files),
                errors=errors,
            )
            
        except Exception as e:
            error_msg = f"Error scanning directory {directory}: {e!s}"
            errors = [error_msg]
            
            if self.progress_callback:
                self.progress_callback(0, f"Error: {error_msg}")
            
            return ScanResult(
                files=[],
                scan_duration=time.time() - start_time,
                total_files_found=0,
                supported_files=0,
                errors=errors,
            )
    
    def _collect_file_paths(
        self, directory: Path, recursive: bool, follow_symlinks: bool
    ) -> List[Path]:
        """Collect file paths using legacy scanner logic."""
        return self.legacy_scanner._collect_file_paths(directory, recursive, follow_symlinks)
    
    def _collect_all_files(
        self, directory: Path, recursive: bool, follow_symlinks: bool
    ) -> List[Path]:
        """Collect all files using legacy scanner logic."""
        return self.legacy_scanner._collect_all_files(directory, recursive, follow_symlinks)
    
    def _process_files_parallel_adapted(
        self, file_paths: List[Path], total_files: int
    ) -> tuple[List[AnimeFile], List[str]]:
        """Process files in parallel using the new parallel processor."""
        files: List[AnimeFile] = []
        errors: List[str] = []
        
        def progress_callback_wrapper(processed: int, total: int, message: str):
            """Convert progress callback to legacy format."""
            if self.progress_callback:
                progress = int((processed / total) * 100) if total > 0 else 0
                self.progress_callback(progress, message)
        
        try:
            # Use the parallel processor
            results = self.parallel_processor.process_files_with_progress(
                file_paths,
                progress_callback=progress_callback_wrapper,
                include_metadata=True
            )
            
            # Convert results to legacy format
            for result in results:
                if result.success and result.anime_file:
                    files.append(result.anime_file)
                else:
                    error_msg = result.error or "Unknown processing error"
                    errors.append(error_msg)
            
        except Exception as e:
            logger.error(f"Error in parallel processing: {e}")
            errors.append(f"Parallel processing failed: {e}")
        
        return files, errors
    
    def cancel_scan(self) -> None:
        """Cancel the current scanning operation."""
        self._cancelled = True
        self.legacy_scanner.cancel_scan()
    
    def reset(self) -> None:
        """Reset the adapter state."""
        self._cancelled = False
        self.legacy_scanner.reset()
    
    def shutdown(self) -> None:
        """Shutdown the adapter and clean up resources."""
        self.parallel_processor.shutdown()
        logger.info("LegacyFileProcessorAdapter shutdown completed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()


class PerformanceTestRunner:
    """Runner for performance testing of parallel file processing."""
    
    def __init__(
        self,
        test_data_dir: Optional[Path] = None,
        max_workers: Optional[int] = None
    ) -> None:
        """Initialize the performance test runner.
        
        Args:
            test_data_dir: Directory containing test files
            max_workers: Maximum number of workers for testing
        """
        self.test_data_dir = test_data_dir
        self.max_workers = max_workers
        self.results: Dict[str, Any] = {}
    
    def create_test_files(self, count: int, directory: Optional[Path] = None) -> List[Path]:
        """Create test files for performance testing.
        
        Args:
            count: Number of test files to create
            directory: Directory to create files in (uses temp dir if None)
            
        Returns:
            List of created file paths
        """
        import tempfile
        import os
        
        if directory is None:
            directory = Path(tempfile.mkdtemp())
        
        directory.mkdir(parents=True, exist_ok=True)
        
        test_files = []
        for i in range(count):
            filename = f"test_anime_{i:04d}_720p.mkv"
            file_path = directory / filename
            
            # Create a small test file
            file_path.write_text(f"Test content for {filename}")
            test_files.append(file_path)
        
        logger.info(f"Created {count} test files in {directory}")
        return test_files
    
    def run_sequential_test(self, file_paths: List[Path]) -> Dict[str, Any]:
        """Run sequential processing test.
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            Dictionary containing test results
        """
        logger.info(f"Running sequential test with {len(file_paths)} files")
        
        start_time = time.time()
        
        # Use legacy scanner for sequential processing
        scanner = FileScanner(max_workers=1)
        files = []
        errors = []
        
        for file_path in file_paths:
            try:
                anime_file = scanner._create_anime_file(file_path)
                if anime_file:
                    files.append(anime_file)
            except Exception as e:
                errors.append(f"Error processing {file_path}: {e}")
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        result = {
            "test_type": "sequential",
            "total_files": len(file_paths),
            "processed_files": len(files),
            "failed_files": len(errors),
            "processing_time": processing_time,
            "files_per_second": len(file_paths) / processing_time if processing_time > 0 else 0,
            "errors": errors
        }
        
        self.results["sequential"] = result
        return result
    
    def run_parallel_test(
        self, 
        file_paths: List[Path], 
        executor_type: str = "hybrid"
    ) -> Dict[str, Any]:
        """Run parallel processing test.
        
        Args:
            file_paths: List of file paths to process
            executor_type: Type of executor to use
            
        Returns:
            Dictionary containing test results
        """
        logger.info(f"Running parallel test with {len(file_paths)} files, executor: {executor_type}")
        
        start_time = time.time()
        
        with IntegratedParallelProcessor(
            max_workers=self.max_workers,
            executor_type=executor_type
        ) as processor:
            results = processor.process_files_parallel(
                file_paths, 
                include_metadata=True, 
                use_queue=False
            )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Analyze results
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        result = {
            "test_type": f"parallel_{executor_type}",
            "total_files": len(file_paths),
            "processed_files": len(successful_results),
            "failed_files": len(failed_results),
            "processing_time": processing_time,
            "files_per_second": len(file_paths) / processing_time if processing_time > 0 else 0,
            "errors": [r.error for r in failed_results if r.error],
            "avg_processing_time": sum(r.processing_time for r in successful_results) / len(successful_results) if successful_results else 0
        }
        
        self.results[f"parallel_{executor_type}"] = result
        return result
    
    def run_comprehensive_test(
        self, 
        file_count: int = 100,
        test_directory: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Run comprehensive performance test comparing sequential vs parallel processing.
        
        Args:
            file_count: Number of test files to create and process
            test_directory: Directory to create test files in
            
        Returns:
            Dictionary containing comprehensive test results
        """
        logger.info(f"Starting comprehensive performance test with {file_count} files")
        
        # Create test files
        test_files = self.create_test_files(file_count, test_directory)
        
        # Run sequential test
        sequential_result = self.run_sequential_test(test_files)
        
        # Run parallel tests with different executor types
        parallel_results = {}
        for executor_type in ["thread", "hybrid"]:
            parallel_results[executor_type] = self.run_parallel_test(test_files, executor_type)
        
        # Calculate speedup
        comprehensive_result = {
            "test_summary": {
                "file_count": file_count,
                "test_directory": str(test_directory) if test_directory else "temporary",
                "timestamp": time.time()
            },
            "sequential": sequential_result,
            "parallel": parallel_results,
            "speedup_analysis": {}
        }
        
        # Calculate speedup for each parallel configuration
        sequential_time = sequential_result["processing_time"]
        for executor_type, parallel_result in parallel_results.items():
            parallel_time = parallel_result["processing_time"]
            speedup = sequential_time / parallel_time if parallel_time > 0 else 0
            
            comprehensive_result["speedup_analysis"][executor_type] = {
                "speedup": speedup,
                "efficiency": (speedup / self.max_workers * 100) if self.max_workers else 0,
                "time_saved": sequential_time - parallel_time
            }
        
        self.results["comprehensive"] = comprehensive_result
        return comprehensive_result
    
    def generate_report(self) -> str:
        """Generate a performance test report.
        
        Returns:
            Formatted report string
        """
        if "comprehensive" not in self.results:
            return "No comprehensive test results available. Run run_comprehensive_test() first."
        
        result = self.results["comprehensive"]
        
        report = []
        report.append("=" * 60)
        report.append("PARALLEL FILE PROCESSING PERFORMANCE TEST REPORT")
        report.append("=" * 60)
        
        # Test summary
        summary = result["test_summary"]
        report.append(f"Test Date: {time.ctime(summary['timestamp'])}")
        report.append(f"Files Processed: {summary['file_count']}")
        report.append(f"Test Directory: {summary['test_directory']}")
        report.append("")
        
        # Sequential results
        seq = result["sequential"]
        report.append("SEQUENTIAL PROCESSING:")
        report.append(f"  Processing Time: {seq['processing_time']:.2f} seconds")
        report.append(f"  Files/Second: {seq['files_per_second']:.2f}")
        report.append(f"  Success Rate: {(seq['processed_files']/seq['total_files']*100):.1f}%")
        report.append("")
        
        # Parallel results
        report.append("PARALLEL PROCESSING:")
        for executor_type, parallel in result["parallel"].items():
            report.append(f"  {executor_type.upper()} EXECUTOR:")
            report.append(f"    Processing Time: {parallel['processing_time']:.2f} seconds")
            report.append(f"    Files/Second: {parallel['files_per_second']:.2f}")
            report.append(f"    Success Rate: {(parallel['processed_files']/parallel['total_files']*100):.1f}%")
            if "avg_processing_time" in parallel:
                report.append(f"    Avg File Time: {parallel['avg_processing_time']:.4f} seconds")
        report.append("")
        
        # Speedup analysis
        report.append("SPEEDUP ANALYSIS:")
        for executor_type, analysis in result["speedup_analysis"].items():
            report.append(f"  {executor_type.upper()}:")
            report.append(f"    Speedup: {analysis['speedup']:.2f}x")
            report.append(f"    Efficiency: {analysis['efficiency']:.1f}%")
            report.append(f"    Time Saved: {analysis['time_saved']:.2f} seconds")
        report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS:")
        best_speedup = max(result["speedup_analysis"].values(), key=lambda x: x["speedup"])
        best_executor = [k for k, v in result["speedup_analysis"].items() if v == best_speedup][0]
        report.append(f"  Best performing executor: {best_executor.upper()}")
        report.append(f"  Recommended speedup: {best_speedup['speedup']:.2f}x")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def save_results(self, file_path: Union[str, Path]) -> None:
        """Save test results to a file.
        
        Args:
            file_path: Path to save results to
        """
        import json
        
        with open(file_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"Test results saved to {file_path}")
