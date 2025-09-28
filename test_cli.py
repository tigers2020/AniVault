#!/usr/bin/env python3
"""Test script for AniVault CLI commands."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from anivault.cli.main import cli

if __name__ == "__main__":
    # Test basic CLI help
    print("Testing AniVault CLI...")
    print("=" * 50)

    # Test help command
    print("\n1. Testing help command:")
    try:
        cli(["--help"])
    except SystemExit:
        pass

    print("\n2. Testing version command:")
    try:
        cli(["--version"])
    except SystemExit:
        pass

    print("\n3. Testing scan command help:")
    try:
        cli(["scan", "--help"])
    except SystemExit:
        pass

    print("\n4. Testing run command help:")
    try:
        cli(["run", "--help"])
    except SystemExit:
        pass

    print("\n5. Testing status command help:")
    try:
        cli(["status", "--help"])
    except SystemExit:
        pass

    print("\nCLI test completed successfully!")
