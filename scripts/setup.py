#!/usr/bin/env python3
"""
AniVault Setup Script

This script helps set up the development environment for AniVault.
It handles dependency installation, environment configuration, and initial setup.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def run_command(command: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9 or higher is required")
        sys.exit(1)
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")


def create_directories():
    """Create necessary directories."""
    directories = [
        "logs",
        "data",
        "config",
        "tests",
        "src/anivault",
        "scripts"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"📁 Created directory: {directory}")


def install_dependencies():
    """Install project dependencies."""
    commands = [
        ("pip install --upgrade pip", "Upgrading pip"),
        ("pip install -e .", "Installing AniVault in development mode"),
        ("pip install -e .[dev]", "Installing development dependencies"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    return True


def setup_pre_commit():
    """Set up pre-commit hooks."""
    if not run_command("pre-commit install", "Installing pre-commit hooks"):
        print("⚠️  Pre-commit setup failed, continuing without it")
        return False
    return True


def setup_git_hooks():
    """Set up Git hooks."""
    if not run_command("git config core.hooksPath .githooks", "Configuring Git hooks"):
        print("⚠️  Git hooks setup failed, continuing without it")
        return False
    return True


def main():
    """Main setup function."""
    print("🚀 Setting up AniVault development environment...")
    print(f"Platform: {platform.system()} {platform.release()}")
    
    # Check Python version
    check_python_version()
    
    # Create directories
    print("\n📁 Creating project directories...")
    create_directories()
    
    # Install dependencies
    print("\n📦 Installing dependencies...")
    if not install_dependencies():
        print("❌ Dependency installation failed")
        sys.exit(1)
    
    # Setup pre-commit
    print("\n🔧 Setting up development tools...")
    setup_pre_commit()
    setup_git_hooks()
    
    print("\n✅ AniVault setup completed successfully!")
    print("\nNext steps:")
    print("1. Set up your TMDB API key in environment variables")
    print("2. Run tests: pytest")
    print("3. Start development: python -m anivault.cli.main --help")


if __name__ == "__main__":
    main()
