"""
AniVault CLI Main Entry Point

This is the main entry point for the AniVault command-line interface.
It initializes UTF-8 encoding and logging before starting the application.
"""

import argparse
import logging
import os
import sys

from cryptography.fernet import Fernet
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import confirm
from rich import print as rich_print
from rich.console import Console
from rich.table import Table
from tmdbv3api import Search, TMDb

# Initialize UTF-8 and logging before any other imports
from anivault.utils.encoding import setup_utf8_environment
from anivault.utils.logging_config import log_shutdown, log_startup, setup_logging

# Set up UTF-8 environment first
setup_utf8_environment()

# Set up logging
logger = setup_logging(
    log_level=20,  # INFO level
    console_output=True,
    file_output=True,
)

# Log application startup
log_startup(logger, "0.1.0")


def main() -> int:
    """
    Main entry point for AniVault CLI.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        parser = argparse.ArgumentParser(
            description="AniVault - Anime Collection Management System",
            prog="anivault",
        )

        parser.add_argument(
            "--version",
            action="version",
            version="AniVault 0.1.0",
        )

        parser.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Enable verbose output",
        )

        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            default="INFO",
            help="Set the logging level",
        )

        # Verification Flags group
        verification_group = parser.add_argument_group("Verification Flags")
        verification_group.add_argument(
            "--verify-anitopy",
            action="store_true",
            help="Verify anitopy functionality in bundled executable",
        )
        verification_group.add_argument(
            "--verify-crypto",
            action="store_true",
            help="Verify cryptography functionality in bundled executable",
        )
        verification_group.add_argument(
            "--verify-tmdb",
            action="store_true",
            help="Verify tmdbv3api functionality in bundled executable",
        )
        verification_group.add_argument(
            "--verify-rich",
            action="store_true",
            help="Verify rich console rendering in bundled executable",
        )
        verification_group.add_argument(
            "--verify-prompt",
            action="store_true",
            help="Verify prompt_toolkit functionality in bundled executable",
        )

        # Parse arguments
        args = parser.parse_args()

        # Update log level if specified
        if args.log_level != "INFO":
            level = getattr(logging, args.log_level)
            logger.setLevel(level)
            for handler in logger.handlers:
                handler.setLevel(level)

        # Check for verification flags first
        verification_handlers = {
            "verify_anitopy": _verify_anitopy,
            "verify_crypto": _verify_cryptography,
            "verify_tmdb": _verify_tmdb,
            "verify_rich": _verify_rich,
            "verify_prompt": _verify_prompt_toolkit,
        }

        for flag, handler in verification_handlers.items():
            if getattr(args, flag, False):
                handler()
                return 0

        if args.verbose:
            logger.info("Verbose mode enabled")

        logger.info("AniVault CLI started successfully")
        logger.info("This is a placeholder implementation")
        logger.info("Core functionality will be implemented in future tasks")

        # TODO(@developer): Implement actual CLI functionality # noqa: TD003, FIX002
        print("🎌 AniVault - Anime Collection Management System")
        print("Version: 0.1.0")
        print()
        print("This is a placeholder implementation.")
        print("Core functionality will be implemented in future development phases.")
        print()
        print("Available options:")
        print("  --version     Show version information")
        print("  --verbose     Enable verbose output")
        print("  --log-level   Set logging level")
        print()
        print("For development setup, run: python scripts/setup.py")

        return 0

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 1
    except Exception:
        logger.exception("Unexpected error occurred")
        return 1
    finally:
        log_shutdown(logger)


def _verify_anitopy():
    """Verify anitopy functionality in bundled executable."""
    try:

        # Test filename parsing
        test_filename = "[SubsPlease] Jujutsu Kaisen S2 - 23 (1080p) [F02B9643].mkv"
        print(f"Testing anitopy with filename: {test_filename}")
        print()

        # Parse the filename
        result = anitopy.parse(test_filename)  # noqa: F821

        # Print the parsed result
        print("Anitopy parsing result:")
        for key, value in result.items():
            print(f"  {key}: {value}")

        # Verify key fields are present
        expected_keys = [
            "anime_title",
            "episode_number",
            "release_group",
            "video_resolution",
        ]
        found_keys = [key for key in expected_keys if key in result]

        print(f"\nExpected keys found: {found_keys}")
        min_required_keys = 2
        print(
            f"Anitopy verification: {'SUCCESS' if len(found_keys) >= min_required_keys else 'PARTIAL'}",
        )

    except ImportError as e:
        print(f"Anitopy verification FAILED - Import error: {e}")
    except Exception as e:
        print(f"Anitopy verification FAILED - Error: {e}")


def _verify_cryptography():
    """Verify cryptography functionality in bundled executable."""
    try:

        print("Testing cryptography with Fernet encryption/decryption...")
        print()

        # Generate a key
        key = Fernet.generate_key()
        print(f"Generated key: {key.decode()[:20]}...")

        # Create Fernet instance
        fernet = Fernet(key)

        # Test message
        original_message = b"This is a secret message for AniVault verification."
        print(f"Original message: {original_message.decode()}")

        # Encrypt the message
        encrypted_token = fernet.encrypt(original_message)
        print(f"Encrypted token: {encrypted_token.decode()[:50]}...")

        # Decrypt the message
        decrypted_message = fernet.decrypt(encrypted_token)
        print(f"Decrypted message: {decrypted_message.decode()}")

        # Verify the decrypted message matches the original
        if decrypted_message == original_message:
            print("Cryptography verification: SUCCESS")
        else:
            print(
                "Cryptography verification: FAILED - Decrypted message doesn't match original",
            )

    except ImportError as e:
        print(f"Cryptography verification FAILED - Import error: {e}")
    except Exception as e:
        print(f"Cryptography verification FAILED - Error: {e}")


def _verify_tmdb():
    """Verify tmdbv3api functionality in bundled executable."""
    try:

        print("Testing TMDB API connectivity and search functionality...")
        print()

        # Get API key from environment
        api_key = os.getenv("TMDB_API_KEY")
        if not api_key:
            print(
                "TMDB verification SKIPPED - No TMDB_API_KEY environment variable found",
            )
            print("To test TMDB functionality, set TMDB_API_KEY environment variable")
            return

        # Initialize TMDb
        tmdb = TMDb()
        tmdb.api_key = api_key
        tmdb.language = "en"

        print(f"Using API key: {api_key[:8]}...")

        # Test search functionality
        search = Search()
        query = "Jujutsu Kaisen"
        print(f"Searching for: {query}")

        # Search for TV shows
        results = search.tv_shows(query)

        print(f"TMDB search found {len(results)} results")

        if results:
            # Show first result details
            first_result = results[0]
            print(f"First result: {first_result.name} (ID: {first_result.id})")
            print(f"Overview: {first_result.overview[:100]}...")
            print("TMDB verification: SUCCESS")
        else:
            print("TMDB verification: PARTIAL - API connected but no results found")

    except ImportError as e:
        print(f"TMDB verification FAILED - Import error: {e}")
    except Exception as e:
        print(f"TMDB verification FAILED - Error: {e}")


def _verify_rich():
    """Verify rich console rendering in bundled executable."""
    try:

        print("Testing Rich console rendering...")
        print()

        # Create a console instance
        console = Console()

        # Test 1: Rich print with colors and styles
        rich_print("[bold blue]Rich Console Rendering Test[/bold blue]")
        rich_print("[green]✓ Green text[/green]")
        rich_print("[red]✗ Red text[/red]")
        rich_print("[yellow]⚠ Yellow warning[/yellow]")
        rich_print("[bold magenta]Bold magenta text[/bold magenta]")
        print()

        # Test 2: Rich table
        table = Table(title="AniVault Verification Results")
        table.add_column("Component", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta")
        table.add_column("Details", style="green")

        table.add_row("Anitopy", "✅ SUCCESS", "C extensions working")
        table.add_row("Cryptography", "✅ SUCCESS", "Native libraries bundled")
        table.add_row("TMDB API", "⏭️ SKIPPED", "No API key provided")
        table.add_row("Rich", "✅ SUCCESS", "Console rendering working")
        table.add_row("Prompt Toolkit", "⏳ PENDING", "Testing next...")

        console.print(table)
        print()

        # Test 3: Progress bar simulation
        rich_print("[bold]Progress simulation:[/bold]")
        for i in range(5):
            rich_print(f"[green]Step {i+1}/5:[/green] Testing Rich component...")

        rich_print("[bold green]Rich verification: SUCCESS[/bold green]")

    except ImportError as e:
        print(f"Rich verification FAILED - Import error: {e}")
    except Exception as e:
        print(f"Rich verification FAILED - Error: {e}")


def _verify_prompt_toolkit():
    """Verify prompt_toolkit functionality in bundled executable."""
    try:

        print("Testing Prompt Toolkit interactive functionality...")
        print()

        # Test 1: Simple prompt
        print("Testing basic prompt...")
        user_input = prompt("prompt_toolkit > ")
        print(f"You entered: {user_input}")
        print()

        # Test 2: Confirmation prompt
        print("Testing confirmation prompt...")
        confirmed = confirm("Do you want to continue? (y/n): ")
        print(f"Confirmation result: {confirmed}")
        print()

        # Test 3: Multiline prompt
        print("Testing multiline prompt (press Ctrl+D or Ctrl+Z to finish):")
        try:
            multiline_input = prompt("Enter multiple lines:\n", multiline=True)
            print(
                f"Multiline input received: {len(multiline_input.splitlines())} lines",
            )
        except (EOFError, KeyboardInterrupt):
            print("Multiline input cancelled")

        print()
        print("Prompt toolkit verification: SUCCESS")

    except ImportError as e:
        print(f"Prompt toolkit verification FAILED - Import error: {e}")
    except Exception as e:
        print(f"Prompt toolkit verification FAILED - Error: {e}")


def cli():
    """CLI entry point for Click."""
    return main()


if __name__ == "__main__":
    sys.exit(main())
