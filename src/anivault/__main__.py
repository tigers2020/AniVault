"""
AniVault Package Main Entry Point

This module serves as the main entry point when the package is run as a module
using `python -m anivault`. It delegates to the CLI main function.
"""

import logging
import sys
from pathlib import Path

# Add the src directory to the Python path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import after path setup
from anivault.cli.common.error_handler import handle_cli_error
from anivault.cli.typer_app import app
from anivault.shared.constants import CLIDefaults

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        logger.info("Command interrupted by user")
        sys.exit(CLIDefaults.EXIT_ERROR)
    except SystemExit:
        # Re-raise SystemExit to preserve exit codes
        raise
    except Exception as e:  # noqa: BLE001
        # Handle unexpected errors with structured logging
        exit_code = handle_cli_error(e, "anivault-main")
        sys.exit(exit_code)
