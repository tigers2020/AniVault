#!/usr/bin/env python3
"""Test data generation script for AniVault benchmarking.

This script creates a large, nested directory structure with configurable
number of empty files for performance testing of the directory scanner.
"""

import argparse
import random
import sys
from pathlib import Path


def create_test_files(
    root_path: Path,
    num_files: int,
    max_depth: int,
    current_depth: int = 0,
) -> int:
    """Create test files in a nested directory structure.

    Args:
        root_path: Root directory where files will be created.
        num_files: Total number of files to create.
        max_depth: Maximum directory nesting depth.
        current_depth: Current nesting depth (for recursion).

    Returns:
        Number of files actually created.
    """
    if num_files <= 0:
        return 0

    created_files = 0

    # If we're at max depth, create all remaining files in current directory
    if current_depth >= max_depth:
        for i in range(num_files):
            extensions = [
                ".mp4",
                ".mkv",
                ".avi",
                ".mov",
                ".m4v",
                ".wmv",
                ".flv",
                ".webm",
            ]
            ext = random.choice(extensions)
            filename = f"test_file_{i:06d}{ext}"
            file_path = root_path / filename

            try:
                file_path.touch()
                created_files += 1
            except Exception as e:
                print(f"Warning: Failed to create file {file_path}: {e}")
        return created_files

    # Create some files in current directory (10-30% of remaining files)
    files_in_current_dir = max(
        0,
        random.randint(max(1, num_files // 10), min(num_files, max(1, num_files // 3))),
    )

    for i in range(files_in_current_dir):
        extensions = [".mp4", ".mkv", ".avi", ".mov", ".m4v", ".wmv", ".flv", ".webm"]
        ext = random.choice(extensions)
        filename = f"test_file_{created_files + i:06d}{ext}"
        file_path = root_path / filename

        try:
            file_path.touch()
            created_files += 1
        except Exception as e:
            print(f"Warning: Failed to create file {file_path}: {e}")

    remaining_files = num_files - files_in_current_dir

    # If no remaining files, return what we created
    if remaining_files <= 0:
        return created_files

    # Create subdirectories and distribute remaining files
    # Create 2-5 subdirectories depending on remaining files
    num_subdirs = min(5, max(2, min(remaining_files // 10 + 1, 5)))

    for subdir_idx in range(num_subdirs):
        subdir_name = f"subdir_{subdir_idx:03d}"
        subdir_path = root_path / subdir_name

        try:
            subdir_path.mkdir(exist_ok=True)

            # Distribute remaining files among subdirectories
            files_for_subdir = remaining_files // num_subdirs
            if subdir_idx == num_subdirs - 1:  # Last subdirectory gets remaining files
                files_for_subdir = remaining_files

            created_in_subdir = create_test_files(
                subdir_path,
                files_for_subdir,
                max_depth,
                current_depth + 1,
            )
            created_files += created_in_subdir
            remaining_files -= created_in_subdir

        except Exception as e:
            print(f"Warning: Failed to create subdirectory {subdir_path}: {e}")

    return created_files


def verify_structure(root_path: Path) -> dict:
    """Verify the created directory structure and return statistics.

    Args:
        root_path: Root directory to verify.

    Returns:
        Dictionary with verification statistics.
    """
    total_files = 0
    total_dirs = 0
    max_depth_found = 0

    def count_recursive(path: Path, current_depth: int = 0):
        nonlocal total_files, total_dirs, max_depth_found

        max_depth_found = max(max_depth_found, current_depth)

        try:
            for item in path.iterdir():
                if item.is_file():
                    total_files += 1
                elif item.is_dir():
                    total_dirs += 1
                    count_recursive(item, current_depth + 1)
        except PermissionError:
            print(f"Warning: Permission denied accessing {path}")
        except Exception as e:
            print(f"Warning: Error accessing {path}: {e}")

    count_recursive(root_path)

    return {
        "total_files": total_files,
        "total_directories": total_dirs,
        "max_depth": max_depth_found,
        "root_path": str(root_path.absolute()),
    }


def main():
    """Main function to parse arguments and generate test data."""
    parser = argparse.ArgumentParser(
        description="Generate test data for AniVault directory scanning benchmarks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --path ./test_data --files 1000 --depth 3
  %(prog)s --path ./benchmark_data --files 100000 --depth 5 --verify
        """,
    )

    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Root directory path where test data will be created",
    )

    parser.add_argument(
        "--files",
        type=int,
        default=1000,
        help="Total number of files to create (default: 1000)",
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Maximum directory nesting depth (default: 3)",
    )

    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify the created structure after generation",
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean existing directory before creating new data",
    )

    args = parser.parse_args()

    # Convert path to Path object
    root_path = Path(args.path).resolve()

    # Clean existing directory if requested
    if args.clean and root_path.exists():
        print(f"Cleaning existing directory: {root_path}")
        import shutil

        shutil.rmtree(root_path)

    # Create root directory
    try:
        root_path.mkdir(parents=True, exist_ok=True)
        print(f"Created/verified root directory: {root_path}")
    except Exception as e:
        print(f"Error creating root directory {root_path}: {e}")
        sys.exit(1)

    # Generate test data
    print(f"Generating {args.files} files with max depth {args.depth}...")
    created_files = create_test_files(root_path, args.files, args.depth)

    print(f"Created {created_files} files successfully.")

    # Verify structure if requested
    if args.verify:
        print("Verifying created structure...")
        stats = verify_structure(root_path)
        print("Verification results:")
        print(f"  Total files found: {stats['total_files']}")
        print(f"  Total directories found: {stats['total_directories']}")
        print(f"  Maximum depth found: {stats['max_depth']}")
        print(f"  Root path: {stats['root_path']}")

        if stats["total_files"] != created_files:
            print(
                f"Warning: Verification found {stats['total_files']} files, but {created_files} were created.",
            )
            return 1

    print("Test data generation completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
