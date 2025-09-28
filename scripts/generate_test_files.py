#!/usr/bin/env python3
"""
Large-scale test directory generator for AniVault performance testing.

This script generates a large directory structure with 100,000+ dummy anime-style files
to be used for performance testing of the file scanning and parsing pipeline.

Usage:
    python scripts/generate_test_files.py --root /path/to/test/dir --count 100000
    python scripts/generate_test_files.py --root ./test_data --count 50000 --depth 4
"""

import argparse
import os
import random
import string
from pathlib import Path
from typing import List, Tuple
import time
import sys


class AnimeTestDataGenerator:
    """Generates realistic anime-style test files for performance testing."""
    
    # Common anime titles for realistic test data
    ANIME_TITLES = [
        "Attack on Titan", "One Piece", "Naruto", "Dragon Ball Z", "Death Note",
        "Fullmetal Alchemist", "Hunter x Hunter", "Bleach", "Demon Slayer",
        "My Hero Academia", "Tokyo Ghoul", "Sword Art Online", "One Punch Man",
        "Steins Gate", "Code Geass", "Neon Genesis Evangelion", "Cowboy Bebop",
        "Spirited Away", "Princess Mononoke", "Your Name", "Weathering With You",
        "A Silent Voice", "The Garden of Words", "5 Centimeters Per Second",
        "Clannad", "Anohana", "Your Lie in April", "Violet Evergarden",
        "Re Zero", "Konosuba", "Overlord", "That Time I Got Reincarnated as a Slime",
        "The Rising of the Shield Hero", "No Game No Life", "Log Horizon",
        "Sword Art Online", "Accel World", "Guilty Crown", "Psycho Pass",
        "Ghost in the Shell", "Akira", "Perfect Blue", "Paprika", "Millennium Actress"
    ]
    
    # Common sub groups and quality indicators
    SUB_GROUPS = [
        "HorribleSubs", "Erai-raws", "SubsPlease", "AnimeRG", "DameDesuYo",
        "Judas", "DKB", "EMBER", "ASW", "YuiSubs", "Commie", "FFF",
        "Coalgirls", "UTW", "gg", "Underwater", "DeadFish", "Doki",
        "Frostii", "Chihiro", "YameteTomete", "EveTaku", "SallySubs"
    ]
    
    # Quality indicators
    QUALITIES = ["480p", "720p", "1080p", "2160p", "4K", "BluRay", "WEB-DL", "HDTV"]
    
    # File extensions commonly used for anime
    EXTENSIONS = [".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".m4v"]
    
    # Common anime file naming patterns
    NAMING_PATTERNS = [
        "[{subgroup}] {title} - {episode} [{quality}].{ext}",
        "[{subgroup}] {title} S{season:02d}E{episode:02d} [{quality}].{ext}",
        "[{subgroup}] {title} - {episode:03d} [{quality}].{ext}",
        "{title} - {episode} [{quality}] [{subgroup}].{ext}",
        "[{subgroup}] {title} - {episode} [{quality}] [v2].{ext}",
        "[{subgroup}] {title} S{season:02d}E{episode:02d} [{quality}] [Dual Audio].{ext}",
        "[{subgroup}] {title} - {episode} [{quality}] [Batch].{ext}",
        "{title} S{season:02d}E{episode:02d} [{quality}] [{subgroup}].{ext}",
        "[{subgroup}] {title} - {episode} [{quality}] [10bit].{ext}",
        "[{subgroup}] {title} S{season:02d}E{episode:02d} [{quality}] [HEVC].{ext}"
    ]
    
    def __init__(self, root_dir: Path, target_count: int, max_depth: int = 5):
        """
        Initialize the test data generator.
        
        Args:
            root_dir: Root directory where test files will be created
            target_count: Target number of files to generate
            max_depth: Maximum directory nesting depth
        """
        self.root_dir = Path(root_dir)
        self.target_count = target_count
        self.max_depth = max_depth
        self.generated_count = 0
        self.start_time = time.time()
        
    def generate_filename(self) -> str:
        """Generate a realistic anime filename."""
        pattern = random.choice(self.NAMING_PATTERNS)
        title = random.choice(self.ANIME_TITLES)
        subgroup = random.choice(self.SUB_GROUPS)
        quality = random.choice(self.QUALITIES)
        ext = random.choice(self.EXTENSIONS)
        
        # Generate episode/season numbers
        episode_num = random.randint(1, 24)
        season = random.randint(1, 4)
        
        # Add some variation to titles
        if random.random() < 0.3:  # 30% chance of adding year
            year = random.randint(1990, 2024)
            title = f"{title} ({year})"
        
        # Add some variation to episode numbers
        if random.random() < 0.1:  # 10% chance of multi-episode
            episode_end = episode_num + random.randint(1, 3)
            episode = f"{episode_num:02d}-{episode_end:02d}"
        else:
            episode = f"{episode_num:02d}"
        
        filename = pattern.format(
            subgroup=subgroup,
            title=title,
            episode=episode_num,  # Use the integer for formatting
            season=season,
            quality=quality,
            ext=ext[1:]  # Remove the dot from extension
        )
        
        return filename
    
    def generate_directory_structure(self) -> List[Path]:
        """Generate a realistic directory structure for anime files."""
        directories = []
        
        # Create main categories
        main_categories = [
            "Anime", "Movies", "OVA", "Specials", "Music", "Extras"
        ]
        
        for category in main_categories:
            category_path = self.root_dir / category
            directories.append(category_path)
            
            # Create subcategories
            if category == "Anime":
                subcategories = ["Ongoing", "Completed", "Dropped", "Plan to Watch"]
            elif category == "Movies":
                subcategories = ["Theatrical", "Direct-to-Video", "Compilation"]
            elif category == "OVA":
                subcategories = ["Original", "Adaptation", "Special"]
            else:
                subcategories = ["Soundtrack", "Opening", "Ending", "Insert Songs"]
            
            for subcat in subcategories:
                subcat_path = category_path / subcat
                directories.append(subcat_path)
                
                # Create some nested directories
                for _ in range(random.randint(2, 5)):
                    nested_name = self._generate_folder_name()
                    nested_path = subcat_path / nested_name
                    directories.append(nested_path)
                    
                    # Add more nesting if we haven't reached max depth
                    if len(nested_path.parts) - len(self.root_dir.parts) < self.max_depth:
                        for _ in range(random.randint(1, 3)):
                            deeper_name = self._generate_folder_name()
                            deeper_path = nested_path / deeper_name
                            directories.append(deeper_path)
        
        return directories
    
    def _generate_folder_name(self) -> str:
        """Generate a realistic folder name."""
        patterns = [
            "{title}",
            "{title} ({year})",
            "{title} - {season}",
            "{title} S{season:02d}",
            "{title} - Complete",
            "{title} - {quality}",
            "{title} - {subgroup}"
        ]
        
        pattern = random.choice(patterns)
        title = random.choice(self.ANIME_TITLES)
        year = random.randint(1990, 2024)
        season = random.randint(1, 4)
        quality = random.choice(self.QUALITIES)
        subgroup = random.choice(self.SUB_GROUPS)
        
        return pattern.format(
            title=title,
            year=year,
            season=season,
            quality=quality,
            subgroup=subgroup
        )
    
    def create_test_files(self) -> Tuple[int, float]:
        """
        Create the test files in the directory structure.
        
        Returns:
            Tuple of (files_created, time_taken)
        """
        print(f"Creating test directory structure at: {self.root_dir}")
        print(f"Target: {self.target_count:,} files")
        print(f"Max depth: {self.max_depth}")
        print("-" * 50)
        
        # Create root directory
        self.root_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate directory structure
        directories = self.generate_directory_structure()
        
        # Create directories
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        print(f"Created {len(directories)} directories")
        
        # Distribute files across directories
        files_per_dir = max(1, self.target_count // len(directories))
        remaining_files = self.target_count
        
        for directory in directories:
            if remaining_files <= 0:
                break
                
            # Determine how many files to create in this directory
            files_in_this_dir = min(files_per_dir, remaining_files)
            
            # Add some randomness to distribution
            files_in_this_dir = random.randint(
                max(1, files_in_this_dir // 2),
                min(files_in_this_dir * 2, remaining_files)
            )
            
            # Create files in this directory
            for _ in range(files_in_this_dir):
                filename = self.generate_filename()
                file_path = directory / filename
                
                # Create empty file
                file_path.touch()
                self.generated_count += 1
                remaining_files -= 1
                
                # Progress reporting
                if self.generated_count % 10000 == 0:
                    elapsed = time.time() - self.start_time
                    rate = self.generated_count / elapsed if elapsed > 0 else 0
                    print(f"Progress: {self.generated_count:,}/{self.target_count:,} files "
                          f"({rate:.0f} files/sec)")
        
        elapsed_time = time.time() - self.start_time
        return self.generated_count, elapsed_time
    
    def print_summary(self, files_created: int, time_taken: float):
        """Print a summary of the generation process."""
        print("\n" + "=" * 50)
        print("GENERATION SUMMARY")
        print("=" * 50)
        print(f"Files created: {files_created:,}")
        print(f"Time taken: {time_taken:.2f} seconds")
        print(f"Average rate: {files_created / time_taken:.0f} files/second")
        print(f"Directory size: {self._get_directory_size():.2f} MB")
        print(f"Root directory: {self.root_dir}")
        print("=" * 50)
    
    def _get_directory_size(self) -> float:
        """Calculate the total size of the generated directory in MB."""
        total_size = 0
        for file_path in self.root_dir.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size / (1024 * 1024)  # Convert to MB


def main():
    """Main entry point for the test data generator."""
    parser = argparse.ArgumentParser(
        description="Generate large-scale test directory with anime-style files"
    )
    parser.add_argument(
        "--root",
        type=Path,
        required=True,
        help="Root directory where test files will be created"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100000,
        help="Number of files to generate (default: 100000)"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=5,
        help="Maximum directory nesting depth (default: 5)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without actually creating files"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.count <= 0:
        print("Error: Count must be positive")
        sys.exit(1)
    
    if args.depth <= 0:
        print("Error: Depth must be positive")
        sys.exit(1)
    
    if args.dry_run:
        print("DRY RUN MODE - No files will be created")
        print(f"Would create {args.count:,} files in {args.root}")
        print(f"Maximum depth: {args.depth}")
        return
    
    # Check if root directory exists and is writable
    try:
        args.root.mkdir(parents=True, exist_ok=True)
        test_file = args.root / ".test_write"
        test_file.touch()
        test_file.unlink()
    except (PermissionError, OSError) as e:
        print(f"Error: Cannot write to {args.root}: {e}")
        sys.exit(1)
    
    # Generate test data
    generator = AnimeTestDataGenerator(
        root_dir=args.root,
        target_count=args.count,
        max_depth=args.depth
    )
    
    try:
        files_created, time_taken = generator.create_test_files()
        generator.print_summary(files_created, time_taken)
        
        print(f"\nTest data generation completed successfully!")
        print(f"Generated {files_created:,} files in {time_taken:.2f} seconds")
        
    except KeyboardInterrupt:
        print("\nGeneration interrupted by user")
        print(f"Created {generator.generated_count:,} files before interruption")
        sys.exit(1)
    except Exception as e:
        print(f"Error during generation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
