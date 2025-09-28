#!/usr/bin/env python3
"""
Script to generate a large test directory structure for memory profiling.

This script creates a directory structure with 100k+ files to test
memory efficiency of directory scanning operations.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List
import time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from anivault.core.logging import get_logger

logger = get_logger(__name__)


class LargeDirectoryGenerator:
    """Generator for creating large directory structures for testing."""
    
    def __init__(self, base_path: Path, target_files: int = 100000):
        """Initialize the directory generator.
        
        Args:
            base_path: Base path for the test directory.
            target_files: Target number of files to create.
        """
        self.base_path = base_path
        self.target_files = target_files
        self.files_created = 0
        self.directories_created = 0
        
    def create_large_directory_structure(self) -> Path:
        """Create a large directory structure with many files.
        
        Returns:
            Path to the created test directory.
        """
        test_dir = self.base_path / "large_test_directory"
        test_dir.mkdir(exist_ok=True)
        self.directories_created += 1
        
        print(f"Creating large directory structure with {self.target_files} files...")
        start_time = time.time()
        
        # Create subdirectories and files
        files_per_dir = 1000  # Files per subdirectory
        num_dirs = (self.target_files + files_per_dir - 1) // files_per_dir
        
        for i in range(num_dirs):
            subdir = test_dir / f"subdir_{i:06d}"
            subdir.mkdir()
            self.directories_created += 1
            
            # Create files in this subdirectory
            files_in_this_dir = min(files_per_dir, self.target_files - self.files_created)
            for j in range(files_in_this_dir):
                # Create media files (mkv, mp4, avi, etc.)
                if j % 10 == 0:  # 10% are media files
                    ext = ['.mkv', '.mp4', '.avi', '.mov', '.wmv'][j % 5]
                    filename = f"media_{i:06d}_{j:06d}{ext}"
                else:
                    # 90% are non-media files
                    ext = ['.txt', '.log', '.tmp', '.bak', '.old'][j % 5]
                    filename = f"file_{i:06d}_{j:06d}{ext}"
                
                file_path = subdir / filename
                file_path.touch()
                self.files_created += 1
                
                # Progress reporting
                if self.files_created % 10000 == 0:
                    elapsed = time.time() - start_time
                    rate = self.files_created / elapsed if elapsed > 0 else 0
                    print(f"  Created {self.files_created} files ({rate:.0f} files/sec)")
                
                if self.files_created >= self.target_files:
                    break
            
            if self.files_created >= self.target_files:
                break
        
        elapsed = time.time() - start_time
        rate = self.files_created / elapsed if elapsed > 0 else 0
        
        print(f"Directory creation completed:")
        print(f"  Files created: {self.files_created}")
        print(f"  Directories created: {self.directories_created}")
        print(f"  Time elapsed: {elapsed:.2f} seconds")
        print(f"  Creation rate: {rate:.0f} files/sec")
        
        return test_dir
    
    def create_nested_directory_structure(self, depth: int = 5, files_per_level: int = 1000) -> Path:
        """Create a deeply nested directory structure.
        
        Args:
            depth: Maximum nesting depth.
            files_per_level: Number of files per directory level.
            
        Returns:
            Path to the created test directory.
        """
        test_dir = self.base_path / "nested_test_directory"
        test_dir.mkdir(exist_ok=True)
        self.directories_created += 1
        
        print(f"Creating nested directory structure with depth {depth}...")
        start_time = time.time()
        
        def create_nested_dir(current_dir: Path, current_depth: int):
            """Recursively create nested directories."""
            if current_depth >= depth:
                return
            
            # Create files in current directory
            for i in range(files_per_level):
                if i % 10 == 0:  # 10% are media files
                    ext = ['.mkv', '.mp4', '.avi', '.mov', '.wmv'][i % 5]
                    filename = f"media_depth_{current_depth}_{i:06d}{ext}"
                else:
                    ext = ['.txt', '.log', '.tmp', '.bak', '.old'][i % 5]
                    filename = f"file_depth_{current_depth}_{i:06d}{ext}"
                
                file_path = current_dir / filename
                file_path.touch()
                self.files_created += 1
            
            # Create subdirectories
            for i in range(10):  # 10 subdirectories per level
                subdir = current_dir / f"subdir_{i:02d}"
                subdir.mkdir()
                self.directories_created += 1
                create_nested_dir(subdir, current_depth + 1)
        
        create_nested_dir(test_dir, 0)
        
        elapsed = time.time() - start_time
        rate = self.files_created / elapsed if elapsed > 0 else 0
        
        print(f"Nested directory creation completed:")
        print(f"  Files created: {self.files_created}")
        print(f"  Directories created: {self.directories_created}")
        print(f"  Time elapsed: {elapsed:.2f} seconds")
        print(f"  Creation rate: {rate:.0f} files/sec")
        
        return test_dir


def main():
    """Main entry point for the directory generation script."""
    parser = argparse.ArgumentParser(
        description="Generate large test directory structures for memory profiling"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./test_data_large",
        help="Output directory for generated test data (default: ./test_data_large)"
    )
    parser.add_argument(
        "--files",
        type=int,
        default=100000,
        help="Number of files to create (default: 100000)"
    )
    parser.add_argument(
        "--nested",
        action="store_true",
        help="Create nested directory structure instead of flat structure"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=5,
        help="Maximum nesting depth for nested structure (default: 5)"
    )
    parser.add_argument(
        "--files-per-level",
        type=int,
        default=1000,
        help="Number of files per directory level for nested structure (default: 1000)"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("🚀 Starting Large Directory Generation")
    print("=" * 50)
    print(f"Output directory: {output_path}")
    print(f"Target files: {args.files}")
    
    # Create generator
    generator = LargeDirectoryGenerator(output_path, target_files=args.files)
    
    try:
        if args.nested:
            # Create nested structure
            test_dir = generator.create_nested_directory_structure(
                depth=args.depth,
                files_per_level=args.files_per_level
            )
        else:
            # Create flat structure
            test_dir = generator.create_large_directory_structure()
        
        print(f"\n✅ Directory generation completed successfully!")
        print(f"Test directory: {test_dir}")
        print(f"Total files created: {generator.files_created}")
        print(f"Total directories created: {generator.directories_created}")
        
        # Verify the directory structure
        print(f"\n📊 Directory structure verification:")
        print(f"  Test directory exists: {test_dir.exists()}")
        print(f"  Test directory is directory: {test_dir.is_dir()}")
        
        # Count actual files
        actual_files = 0
        for root, dirs, files in os.walk(test_dir):
            actual_files += len(files)
        
        print(f"  Actual files found: {actual_files}")
        print(f"  Expected files: {generator.files_created}")
        
        if actual_files == generator.files_created:
            print("  ✅ File count matches expected")
        else:
            print("  ⚠️  File count mismatch")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Directory generation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
