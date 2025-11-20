#!/usr/bin/env python
"""
Build Script for AniVault Application

This script automates the process of building a standalone Windows executable
for the AniVault application using PyInstaller.

Usage:
    python build.py [options]

Options:
    --clean     Clean build artifacts before building
    --debug     Build with debug mode enabled
    --onedir    Build as one directory instead of one file
    --help      Show this help message
"""

import argparse
import logging
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class AniVaultBuilder:
    """Builder for AniVault application."""

    def __init__(self, root_dir: Path):
        """Initialize builder.

        Args:
            root_dir: Project root directory
        """
        self.root_dir = root_dir
        self.build_dir = root_dir / "build"
        self.dist_dir = root_dir / "dist"
        self.spec_file = root_dir / "AniVault.spec"

    def clean(self) -> None:
        """Clean build artifacts."""
        logger.info("Cleaning build artifacts...")

        dirs_to_clean = [self.build_dir, self.dist_dir]
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                logger.info("Removing %s", dir_path)
                shutil.rmtree(dir_path)

        logger.info("Clean completed")

    def check_dependencies(self) -> bool:
        """Check if required dependencies are installed.

        Returns:
            True if all dependencies are available, False otherwise
        """
        logger.info("Checking dependencies...")

        try:
            import PyInstaller

            logger.info("PyInstaller version: %s", PyInstaller.__version__)
        except ImportError:
            logger.exception("PyInstaller is not installed")
            logger.info("Install it with: pip install pyinstaller==6.16.0")
            return False

        try:
            import PySide6

            logger.info("PySide6 version: %s", PySide6.__version__)
        except ImportError:
            logger.exception("PySide6 is not installed")
            logger.info("Install dependencies with: pip install -e .[dev]")
            return False

        logger.info("All dependencies are available")
        return True

    def build(self, onedir: bool = False, debug: bool = False) -> bool:  # noqa: ARG002
        """Build the application.

        Args:
            onedir: Build as one directory instead of one file
            debug: Enable debug mode

        Returns:
            True if build succeeded, False otherwise
        """
        logger.info("Starting build process...")

        if not self.spec_file.exists():
            logger.error("Spec file not found: %s", self.spec_file)
            return False

        # Build PyInstaller command
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            str(self.spec_file),
            "--noconfirm",
        ]

        if debug:
            cmd.append("--debug=all")
            logger.info("Debug mode enabled")

        # Run PyInstaller
        try:
            logger.info("Running: %s", " ".join(cmd))
            result = subprocess.run(  # nosec B603  # noqa: S603
                cmd, cwd=self.root_dir, check=True, capture_output=True, text=True
            )

            logger.info("Build output:")
            for line in result.stdout.splitlines():
                logger.info("  %s", line)

            if result.stderr:
                logger.warning("Build warnings/errors:")
                for line in result.stderr.splitlines():
                    logger.warning("  %s", line)

            logger.info("Build completed successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.exception("Build failed")
            logger.exception("Exit code: %s", e.returncode)
            if e.stdout:
                logger.exception("Output:")
                for line in e.stdout.splitlines():
                    logger.exception("  %s", line)
            if e.stderr:
                logger.exception("Errors:")
                for line in e.stderr.splitlines():
                    logger.exception("  %s", line)
            return False

    def verify_build(self) -> bool:
        """Verify that the build artifacts were created.

        Returns:
            True if build artifacts exist, False otherwise
        """
        logger.info("Verifying build artifacts...")

        exe_path = self.dist_dir / "AniVault.exe"

        if not exe_path.exists():
            logger.error("Executable not found: %s", exe_path)
            return False

        file_size = exe_path.stat().st_size / (1024 * 1024)  # MB
        logger.info("Executable created: %s", exe_path)
        logger.info("Executable size: %.2f MB", file_size)

        return True


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Build AniVault application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build.py                # Build with default settings
  python build.py --clean        # Clean and build
  python build.py --debug        # Build with debug enabled
        """,
    )

    parser.add_argument(
        "--clean", action="store_true", help="Clean build artifacts before building"
    )

    parser.add_argument(
        "--debug", action="store_true", help="Build with debug mode enabled"
    )

    parser.add_argument(
        "--onedir",
        action="store_true",
        help="Build as one directory instead of one file",
    )

    args = parser.parse_args()

    # Initialize builder
    root_dir = Path(__file__).parent.absolute()
    builder = AniVaultBuilder(root_dir)

    try:
        # Clean if requested
        if args.clean:
            builder.clean()

        # Check dependencies
        if not builder.check_dependencies():
            return 1

        # Build
        if not builder.build(onedir=args.onedir, debug=args.debug):
            return 1

        # Verify
        if not builder.verify_build():
            return 1

        logger.info("=" * 60)
        logger.info("Build completed successfully!")
        logger.info("Executable location: %s", builder.dist_dir / "AniVault.exe")
        logger.info("=" * 60)

        return 0

    except KeyboardInterrupt:
        logger.info("Build interrupted by user")
        return 1

    except Exception:
        logger.exception("Unexpected error during build")
        return 1


if __name__ == "__main__":
    sys.exit(main())
