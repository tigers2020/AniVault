#!/usr/bin/env python3
"""
YAML to TOML Configuration Migration Script

This script converts existing config.yaml files to the new config.toml format,
preserving all settings and structure for AniVault configuration migration.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import toml
import yaml


def load_yaml_config(file_path: Path) -> dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        file_path: Path to the YAML configuration file

    Returns:
        Dictionary containing the configuration data

    Raises:
        FileNotFoundError: If the file doesn't exist
        yaml.YAMLError: If the YAML file is malformed
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"❌ Error: Configuration file not found: {file_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"❌ Error: Invalid YAML file: {e}")
        sys.exit(1)


def convert_to_toml(config_data: dict[str, Any]) -> str:
    """Convert configuration dictionary to TOML format.

    Args:
        config_data: Configuration dictionary from YAML

    Returns:
        TOML formatted string
    """
    return toml.dumps(config_data)


def save_toml_config(
    config_data: dict[str, Any],
    output_path: Path,
    force: bool = False,
) -> None:
    """Save configuration to TOML file.

    Args:
        config_data: Configuration dictionary
        output_path: Path where to save the TOML file
        force: Whether to overwrite existing files

    Raises:
        FileExistsError: If file exists and force is False
    """
    if output_path.exists() and not force:
        print(f"❌ Error: Output file already exists: {output_path}")
        print("   Use --force to overwrite existing files")
        sys.exit(1)

    try:
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert and save
        toml_content = convert_to_toml(config_data)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(toml_content)

        print(f"✅ Successfully converted configuration to: {output_path}")

    except Exception as e:
        print(f"❌ Error saving TOML file: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(
        description="Convert AniVault YAML configuration to TOML format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/migrate_config.py config/settings.yaml config/config.toml
  python scripts/migrate_config.py config/settings.yaml config/config.toml --force
        """,
    )

    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to the input YAML configuration file",
    )

    parser.add_argument(
        "output_file",
        type=Path,
        help="Path to the output TOML configuration file",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output file without confirmation",
    )

    args = parser.parse_args()

    print("🔄 Converting YAML configuration to TOML...")
    print(f"   Input:  {args.input_file}")
    print(f"   Output: {args.output_file}")

    # Load YAML configuration
    config_data = load_yaml_config(args.input_file)

    # Save as TOML
    save_toml_config(config_data, args.output_file, args.force)

    print("🎉 Migration completed successfully!")


if __name__ == "__main__":
    main()
