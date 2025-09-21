"""Main entry point for AniVault application."""

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from .app import AniVaultApp
from .core.metrics_server import metrics_server
from .utils.logger import get_logger, setup_logging


def main() -> int:
    """Main entry point for the application."""
    # Set up logging first
    log_manager = setup_logging()
    logger = get_logger(__name__)

    logger.info("Starting AniVault application")

    try:
        # Validate database schema before starting the application
        from .core.database import db_manager

        # Initialize the database manager
        db_manager.initialize()

        logger.info("Starting comprehensive database schema validation...")

        # Basic schema validation
        if not db_manager.validate_schema():
            logger.error("Database schema validation failed!")
            logger.info("Attempting to run database migrations automatically...")

            try:
                import os
                import subprocess

                # Run alembic upgrade head
                result = subprocess.run(
                    ["alembic", "upgrade", "head"],
                    cwd=os.getcwd(),
                    capture_output=True,
                    text=True,
                    timeout=60,  # 60 second timeout
                )

                if result.returncode == 0:
                    logger.info("Database migrations completed successfully")
                    logger.info("Re-validating schema...")

                    # Re-initialize and validate
                    db_manager.initialize()
                    if db_manager.validate_schema():
                        logger.info("Schema validation successful after migration")
                    else:
                        logger.error("Schema validation still failed after migration")
                        return 1
                else:
                    logger.error(f"Migration failed: {result.stderr}")
                    logger.error(
                        "Please run 'alembic upgrade head' manually or recreate the database"
                    )
                    return 1

            except subprocess.TimeoutExpired:
                logger.error("Migration timed out after 60 seconds")
                return 1
            except FileNotFoundError:
                logger.error("Alembic not found. Please install alembic or run migrations manually")
                return 1
            except Exception as e:
                logger.error(f"Failed to run automatic migration: {e}")
                logger.error("Please run 'alembic upgrade head' manually or recreate the database")
                return 1

        # Check schema version
        schema_version = db_manager.get_schema_version()
        if schema_version:
            logger.info(f"Database schema version: {schema_version}")
        else:
            logger.warning("No schema version found - database may not be properly initialized")

        # Check if schema is up to date
        if not db_manager.is_schema_up_to_date():
            logger.warning("Database schema may not be up to date")
            logger.warning("Consider running 'alembic upgrade head' to update the schema")

        # Validate database connectivity and basic operations
        try:
            stats = db_manager.get_database_stats()
            logger.info(f"Database connectivity test successful. Stats: {stats}")
        except Exception as e:
            logger.error(f"Database connectivity test failed: {e}")
            return 1

        # Validate transaction manager
        try:
            transaction_stats = db_manager.get_transaction_stats()
            logger.info(f"Transaction manager initialized successfully. Stats: {transaction_stats}")
        except Exception as e:
            logger.error(f"Transaction manager validation failed: {e}")
            return 1

        logger.info("Database schema validation completed successfully")

        # Start metrics server for monitoring
        try:
            if metrics_server.start():
                logger.info("Metrics server started successfully")
            else:
                logger.warning("Failed to start metrics server - monitoring disabled")
        except Exception as e:
            logger.warning(f"Failed to start metrics server: {e} - monitoring disabled")

        # Enable High DPI scaling
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv)
        app.setApplicationName("AniVault")
        app.setApplicationVersion("0.1.0")
        app.setOrganizationName("AniVault")

        logger.info("QApplication created successfully")

        # Apply global dark theme to QApplication
        from .themes.theme_manager import get_theme_manager

        theme_manager = get_theme_manager()
        app.setStyleSheet(theme_manager.current_theme.get_complete_style())
        logger.info("Theme applied successfully")

        # Create and show main window
        main_window = AniVaultApp()
        main_window.show()
        logger.info("Main window created and shown")

        # Run application
        result = int(app.exec_())
        logger.info(f"Application exited with code {result}")
        return result

    except Exception as e:
        logger.critical(f"Fatal error in main: {e}", exc_info=True)
        return 1
    finally:
        # Stop metrics server
        try:
            metrics_server.stop()
        except Exception as e:
            logger.warning(f"Error stopping metrics server: {e}")

        # Clean up logging
        log_manager.cleanup()


if __name__ == "__main__":
    sys.exit(main())
