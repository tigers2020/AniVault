#!/usr/bin/env python3
"""
AniVault Development Helper Script

This script provides common development tasks and utilities.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command: str, description: str = None) -> bool:
    """Run a command and return success status."""
    if description:
        print(f"🔄 {description}...")
    
    try:
        result = subprocess.run(command, shell=True, check=True)
        if description:
            print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        if description:
            print(f"❌ {description} failed: {e}")
        return False


def lint_code():
    """Run code linting."""
    print("🔍 Running code linting...")
    commands = [
        "ruff check src/",
        "ruff format --check src/",
        "mypy src/",
    ]
    
    for command in commands:
        if not run_command(command):
            return False
    return True


def run_tests():
    """Run test suite."""
    print("🧪 Running tests...")
    return run_command("pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing")


def run_tests_fast():
    """Run fast tests only."""
    print("⚡ Running fast tests...")
    return run_command("pytest tests/ -v -m 'not slow'")


def build_package():
    """Build the package."""
    print("📦 Building package...")
    return run_command("python -m build")


def clean_build():
    """Clean build artifacts."""
    print("🧹 Cleaning build artifacts...")
    commands = [
        "rm -rf build/",
        "rm -rf dist/",
        "rm -rf *.egg-info/",
        "rm -rf htmlcov/",
        "rm -rf .coverage",
        "rm -rf .pytest_cache/",
        "find . -type d -name __pycache__ -exec rm -rf {} +",
        "find . -type f -name '*.pyc' -delete",
    ]
    
    for command in commands:
        run_command(command)


def format_code():
    """Format code using ruff."""
    print("🎨 Formatting code...")
    return run_command("ruff format src/ tests/")


def check_dependencies():
    """Check for dependency issues."""
    print("🔍 Checking dependencies...")
    return run_command("pip check")


def run_security_check():
    """Run security checks."""
    print("🔒 Running security checks...")
    return run_command("ruff check src/ --select S")


def generate_docs():
    """Generate documentation."""
    print("📚 Generating documentation...")
    # This would be implemented when documentation tools are added
    print("⚠️  Documentation generation not yet implemented")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="AniVault Development Helper")
    parser.add_argument("command", choices=[
        "lint", "test", "test-fast", "build", "clean", "format", 
        "check-deps", "security", "docs", "all"
    ], help="Command to run")
    
    args = parser.parse_args()
    
    if args.command == "lint":
        success = lint_code()
    elif args.command == "test":
        success = run_tests()
    elif args.command == "test-fast":
        success = run_tests_fast()
    elif args.command == "build":
        success = build_package()
    elif args.command == "clean":
        clean_build()
        success = True
    elif args.command == "format":
        success = format_code()
    elif args.command == "check-deps":
        success = check_dependencies()
    elif args.command == "security":
        success = run_security_check()
    elif args.command == "docs":
        generate_docs()
        success = True
    elif args.command == "all":
        success = (
            format_code() and
            lint_code() and
            run_tests() and
            check_dependencies() and
            run_security_check()
        )
    
    if success:
        print("✅ Command completed successfully")
        sys.exit(0)
    else:
        print("❌ Command failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
