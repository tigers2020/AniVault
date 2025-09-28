#!/usr/bin/env python3
"""
Memory profiling test script for AniVault directory scanning.

This script tests memory usage of directory scanning operations on large
directory structures to ensure memory efficiency and compliance with
the 500MB memory limit requirement.
"""

import argparse
import os
import sys
import time
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Iterator
import psutil
import gc

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from anivault.scanner.file_scanner import (
    scan_directory,
    scan_directory_paths,
    scan_directory_with_stats,
    get_media_files_count
)
from anivault.scanner.producer_scanner import Scanner
from anivault.scanner.scan_parse_pool import ScanParsePool
from anivault.core.logging import get_logger

logger = get_logger(__name__)


class MemoryProfiler:
    """Memory profiler for directory scanning operations."""
    
    def __init__(self):
        """Initialize the memory profiler."""
        self.process = psutil.Process(os.getpid())
        self.initial_memory = self.process.memory_info().rss
        self.peak_memory = self.initial_memory
        self.memory_samples: List[int] = []
        self.sample_times: List[float] = []
        
    def start_monitoring(self) -> None:
        """Start memory monitoring."""
        self.initial_memory = self.process.memory_info().rss
        self.peak_memory = self.initial_memory
        self.memory_samples = [self.initial_memory]
        self.sample_times = [time.time()]
        
    def sample_memory(self) -> int:
        """Take a memory sample and update peak memory."""
        current_memory = self.process.memory_info().rss
        self.memory_samples.append(current_memory)
        self.sample_times.append(time.time())
        self.peak_memory = max(self.peak_memory, current_memory)
        return current_memory
        
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        final_memory = self.process.memory_info().rss
        memory_used = final_memory - self.initial_memory
        peak_memory_used = self.peak_memory - self.initial_memory
        
        # Calculate memory growth rate
        if len(self.memory_samples) > 1:
            time_span = self.sample_times[-1] - self.sample_times[0]
            memory_growth = (self.memory_samples[-1] - self.memory_samples[0]) / (1024 * 1024)
            growth_rate = memory_growth / time_span if time_span > 0 else 0
        else:
            growth_rate = 0
        
        return {
            "initial_memory_mb": self.initial_memory / (1024 * 1024),
            "final_memory_mb": final_memory / (1024 * 1024),
            "peak_memory_mb": self.peak_memory / (1024 * 1024),
            "memory_used_mb": memory_used / (1024 * 1024),
            "peak_memory_used_mb": peak_memory_used / (1024 * 1024),
            "samples_taken": len(self.memory_samples),
            "memory_growth_rate_mb_per_sec": growth_rate,
            "memory_efficient": peak_memory_used < (500 * 1024 * 1024),  # 500MB limit
            "memory_stable": growth_rate < 1.0  # Less than 1MB/sec growth
        }


class DirectoryScannerProfiler:
    """Profiler for directory scanning operations."""
    
    def __init__(self, test_dir: Path):
        """Initialize the profiler.
        
        Args:
            test_dir: Directory to profile against.
        """
        self.test_dir = test_dir
        self.results: List[Dict[str, Any]] = []
        
    def profile_scan_directory(self) -> Dict[str, Any]:
        """Profile the basic scan_directory function."""
        print("📁 Profiling scan_directory()...")
        
        profiler = MemoryProfiler()
        profiler.start_monitoring()
        
        start_time = time.perf_counter()
        files = list(scan_directory(self.test_dir))
        end_time = time.perf_counter()
        
        execution_time = end_time - start_time
        file_count = len(files)
        rate_files_per_sec = file_count / execution_time if execution_time > 0 else 0
        
        memory_stats = profiler.get_memory_stats()
        
        result = {
            "function": "scan_directory",
            "files_found": file_count,
            "execution_time": execution_time,
            "rate_files_per_sec": rate_files_per_sec,
            "memory_efficient": memory_stats["memory_efficient"],
            "peak_memory_used_mb": memory_stats["peak_memory_used_mb"],
            "memory_stable": memory_stats["memory_stable"],
            **memory_stats
        }
        
        self.results.append(result)
        return result
    
    def profile_scan_directory_paths(self) -> Dict[str, Any]:
        """Profile the scan_directory_paths function."""
        print("📁 Profiling scan_directory_paths()...")
        
        profiler = MemoryProfiler()
        profiler.start_monitoring()
        
        start_time = time.perf_counter()
        files = list(scan_directory_paths(self.test_dir))
        end_time = time.perf_counter()
        
        execution_time = end_time - start_time
        file_count = len(files)
        rate_files_per_sec = file_count / execution_time if execution_time > 0 else 0
        
        memory_stats = profiler.get_memory_stats()
        
        result = {
            "function": "scan_directory_paths",
            "files_found": file_count,
            "execution_time": execution_time,
            "rate_files_per_sec": rate_files_per_sec,
            "memory_efficient": memory_stats["memory_efficient"],
            "peak_memory_used_mb": memory_stats["peak_memory_used_mb"],
            "memory_stable": memory_stats["memory_stable"],
            **memory_stats
        }
        
        self.results.append(result)
        return result
    
    def profile_scan_with_stats(self) -> Dict[str, Any]:
        """Profile the scan_directory_with_stats function."""
        print("📁 Profiling scan_directory_with_stats()...")
        
        profiler = MemoryProfiler()
        profiler.start_monitoring()
        
        start_time = time.perf_counter()
        file_iterator, stats = scan_directory_with_stats(self.test_dir)
        files = list(file_iterator)
        end_time = time.perf_counter()
        
        execution_time = end_time - start_time
        file_count = len(files)
        rate_files_per_sec = file_count / execution_time if execution_time > 0 else 0
        
        memory_stats = profiler.get_memory_stats()
        
        result = {
            "function": "scan_directory_with_stats",
            "files_found": file_count,
            "execution_time": execution_time,
            "rate_files_per_sec": rate_files_per_sec,
            "memory_efficient": memory_stats["memory_efficient"],
            "peak_memory_used_mb": memory_stats["peak_memory_used_mb"],
            "memory_stable": memory_stats["memory_stable"],
            "directories_scanned": stats["directories_scanned"],
            "permission_errors": stats["permission_errors"],
            "other_errors": stats["other_errors"],
            **memory_stats
        }
        
        self.results.append(result)
        return result
    
    def profile_scan_parse_pool(self) -> Dict[str, Any]:
        """Profile the ScanParsePool."""
        print("📁 Profiling ScanParsePool...")
        
        profiler = MemoryProfiler()
        profiler.start_monitoring()
        
        start_time = time.perf_counter()
        
        with ScanParsePool(max_workers=4, queue_size=1000) as pool:
            files = list(pool.process_directory(self.test_dir))
        
        end_time = time.perf_counter()
        
        execution_time = end_time - start_time
        file_count = len(files)
        rate_files_per_sec = file_count / execution_time if execution_time > 0 else 0
        
        memory_stats = profiler.get_memory_stats()
        
        result = {
            "function": "ScanParsePool",
            "files_found": file_count,
            "execution_time": execution_time,
            "rate_files_per_sec": rate_files_per_sec,
            "memory_efficient": memory_stats["memory_efficient"],
            "peak_memory_used_mb": memory_stats["peak_memory_used_mb"],
            "memory_stable": memory_stats["memory_stable"],
            **memory_stats
        }
        
        self.results.append(result)
        return result
    
    def profile_streaming_scan(self) -> Dict[str, Any]:
        """Profile streaming scan without loading all files into memory."""
        print("📁 Profiling streaming scan...")
        
        profiler = MemoryProfiler()
        profiler.start_monitoring()
        
        start_time = time.perf_counter()
        file_count = 0
        
        # Process files one by one without storing them
        for entry in scan_directory(self.test_dir):
            file_count += 1
            
            # Sample memory every 1000 files
            if file_count % 1000 == 0:
                profiler.sample_memory()
                current_memory = profiler.process.memory_info().rss
                memory_mb = (current_memory - profiler.initial_memory) / (1024 * 1024)
                
                # Check memory limit
                if memory_mb > 500:
                    print(f"  ⚠️  Memory usage exceeded 500MB at {file_count} files: {memory_mb:.2f}MB")
                    break
        
        end_time = time.perf_counter()
        
        execution_time = end_time - start_time
        rate_files_per_sec = file_count / execution_time if execution_time > 0 else 0
        
        memory_stats = profiler.get_memory_stats()
        
        result = {
            "function": "streaming_scan",
            "files_found": file_count,
            "execution_time": execution_time,
            "rate_files_per_sec": rate_files_per_sec,
            "memory_efficient": memory_stats["memory_efficient"],
            "peak_memory_used_mb": memory_stats["peak_memory_used_mb"],
            "memory_stable": memory_stats["memory_stable"],
            **memory_stats
        }
        
        self.results.append(result)
        return result
    
    def print_results(self) -> None:
        """Print profiling results."""
        print("\n" + "=" * 80)
        print("📊 MEMORY PROFILING RESULTS")
        print("=" * 80)
        
        for result in self.results:
            print(f"\n🔍 {result['function']}:")
            print(f"  Files found: {result['files_found']:,}")
            print(f"  Execution time: {result['execution_time']:.2f}s")
            print(f"  Rate: {result['rate_files_per_sec']:.0f} files/sec")
            print(f"  Peak memory used: {result['peak_memory_used_mb']:.2f}MB")
            print(f"  Memory efficient: {'✅' if result['memory_efficient'] else '❌'}")
            print(f"  Memory stable: {'✅' if result['memory_stable'] else '❌'}")
            
            if result['peak_memory_used_mb'] > 500:
                print(f"  ⚠️  WARNING: Memory usage exceeded 500MB limit!")
        
        # Summary
        print(f"\n📈 SUMMARY:")
        all_efficient = all(r['memory_efficient'] for r in self.results)
        all_stable = all(r['memory_stable'] for r in self.results)
        
        print(f"  All functions memory efficient: {'✅' if all_efficient else '❌'}")
        print(f"  All functions memory stable: {'✅' if all_stable else '❌'}")
        
        if all_efficient and all_stable:
            print(f"  🎉 All tests passed! Directory scanning is memory efficient.")
        else:
            print(f"  ⚠️  Some tests failed. Memory optimization may be needed.")


def main():
    """Main entry point for the memory profiling script."""
    parser = argparse.ArgumentParser(
        description="Profile memory usage of AniVault directory scanning"
    )
    parser.add_argument(
        "--target",
        type=str,
        required=True,
        help="Target directory to profile (must exist)"
    )
    parser.add_argument(
        "--functions",
        nargs="+",
        choices=["scan_directory", "scan_directory_paths", "scan_with_stats", "scan_parse_pool", "streaming_scan", "all"],
        default=["all"],
        help="Functions to profile (default: all)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Validate target directory
    target_path = Path(args.target)
    if not target_path.exists():
        print(f"❌ Target directory does not exist: {target_path}")
        return 1
    
    if not target_path.is_dir():
        print(f"❌ Target path is not a directory: {target_path}")
        return 1
    
    print("🚀 Starting AniVault Memory Profiling")
    print("=" * 50)
    print(f"Target directory: {target_path}")
    print(f"Functions to profile: {args.functions}")
    
    # Create profiler
    profiler = DirectoryScannerProfiler(target_path)
    
    # Force garbage collection before starting
    gc.collect()
    
    try:
        # Profile requested functions
        if "all" in args.functions or "scan_directory" in args.functions:
            profiler.profile_scan_directory()
            gc.collect()  # Force garbage collection between tests
        
        if "all" in args.functions or "scan_directory_paths" in args.functions:
            profiler.profile_scan_directory_paths()
            gc.collect()
        
        if "all" in args.functions or "scan_with_stats" in args.functions:
            profiler.profile_scan_with_stats()
            gc.collect()
        
        if "all" in args.functions or "scan_parse_pool" in args.functions:
            profiler.profile_scan_parse_pool()
            gc.collect()
        
        if "all" in args.functions or "streaming_scan" in args.functions:
            profiler.profile_streaming_scan()
            gc.collect()
        
        # Print results
        profiler.print_results()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Memory profiling failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
