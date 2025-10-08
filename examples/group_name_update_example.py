"""Example usage of group name update functionality.

This example demonstrates how the FileGrouper automatically updates
group names using parser for more accurate titles.
"""

from pathlib import Path

from anivault.core.file_grouper import FileGrouper
from anivault.core.models import ScannedFile
from anivault.core.parser.models import ParsingResult


def main():
    """Demonstrate group name update functionality."""
    print("=== AniVault Group Name Update Example ===\n")

    # Create sample files with various anime filenames
    sample_files = [
        ScannedFile(
            file_path=Path("[SubsPlease] Attack on Titan - 01 [1080p].mkv"),
            metadata=ParsingResult(title="Attack on Titan - 01", parser_used="example"),
            file_size=1000,
            last_modified=1234567890.0,
        ),
        ScannedFile(
            file_path=Path("[SubsPlease] Attack on Titan - 02 [1080p].mkv"),
            metadata=ParsingResult(title="Attack on Titan - 02", parser_used="example"),
            file_size=1000,
            last_modified=1234567890.0,
        ),
        ScannedFile(
            file_path=Path("[Erai-raws] One Piece - 1000 [1080p].mkv"),
            metadata=ParsingResult(title="One Piece - 1000", parser_used="example"),
            file_size=1000,
            last_modified=1234567890.0,
        ),
        ScannedFile(
            file_path=Path(
                "Demon Slayer - Entertainment District Arc - 01 [1080p].mkv",
            ),
            metadata=ParsingResult(
                title="Demon Slayer - Entertainment District Arc - 01",
                parser_used="example",
            ),
            file_size=1000,
            last_modified=1234567890.0,
        ),
    ]

    print("Original files:")
    for file in sample_files:
        print(f"  - {file.file_path.name}")
    print()

    # Create file grouper
    try:
        grouper = FileGrouper()
        print("✅ FileGrouper initialized with parser support")
    except ImportError:
        print("⚠️  FileGrouper initialized without parser (anitopy not available)")
        grouper = FileGrouper()

    # Group files
    print("\nGrouping files...")
    grouped_files = grouper.group_files(sample_files)

    print(f"\n✅ Grouped {len(sample_files)} files into {len(grouped_files)} groups")
    print("\nGrouped results:")

    for group_name, files in grouped_files.items():
        print(f"\n📁 Group: '{group_name}'")
        print(f"   Files: {len(files)}")
        for file in files:
            print(f"   - {file.file_path.name}")

    print("\n=== Key Features Demonstrated ===")
    print("1. ✅ Automatic file grouping based on filename similarity")
    print("2. ✅ Group name updates using parser for better titles")
    print("3. ✅ Representative file selection for parsing")
    print("4. ✅ Fallback to original names when parser fails")
    print("5. ✅ Unique group name handling")

    if grouper.parser:
        print("\n🎯 Parser Integration:")
        print("   - AnitopyParser extracts clean anime titles")
        print("   - Group names are more descriptive and accurate")
        print("   - Better organization for large anime collections")
    else:
        print("\n📝 Basic Grouping:")
        print("   - Uses filename similarity for grouping")
        print("   - Install 'anitopy' for enhanced title extraction")


if __name__ == "__main__":
    main()
