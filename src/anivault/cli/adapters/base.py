"""
Base Adapter for CLI Handlers

This module provides the base adapter class that handles the conversion
between Typer callbacks and legacy argparse handlers. It ensures consistent
error handling, logging, and context management across all command adapters.
"""

from __future__ import annotations

import argparse
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable

from anivault.cli.common.context import get_cli_context
from anivault.shared.errors import ApplicationError

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """
    Base adapter class for converting Typer callbacks to argparse handlers.

    This class provides the common functionality for all command adapters,
    including type conversion, error handling, and context management.
    """

    def __init__(self, handler_func: Callable[[Any], int]):
        """
        Initialize the adapter with a legacy handler function.

        Args:
            handler_func: The legacy argparse handler function to wrap
        """
        self.handler_func = handler_func
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def __call__(self, *args: Any, **kwargs: Any) -> int:
        """
        Call the adapter, converting Typer parameters to argparse format.

        Returns:
            Exit code from the handler function
        """
        try:
            # Convert Typer parameters to argparse.Namespace
            args_namespace = self._convert_parameters(*args, **kwargs)

            # Log command start
            self.logger.info("Command started: %s", self._get_command_name())

            # Call the legacy handler
            result = self.handler_func(args_namespace)

            # Log command completion
            if result == 0:
                self.logger.info(
                    "Command completed successfully: %s", self._get_command_name(),
                )
            else:
                self.logger.error(
                    "Command failed with exit code %s: %s",
                    result,
                    self._get_command_name(),
                )

            return result

        except Exception:
            self.logger.exception("Unexpected error in %s", self._get_command_name())
            return 1

    @abstractmethod
    def _convert_parameters(self, *args: Any, **kwargs: Any) -> argparse.Namespace:
        """
        Convert Typer parameters to argparse.Namespace.

        This method must be implemented by subclasses to handle the specific
        parameter conversion for each command.

        Args:
            *args: Positional arguments from Typer
            **kwargs: Keyword arguments from Typer

        Returns:
            argparse.Namespace object compatible with legacy handlers
        """

    @abstractmethod
    def _get_command_name(self) -> str:
        """
        Get the command name for logging purposes.

        Returns:
            String name of the command
        """

    def _create_base_namespace(self) -> argparse.Namespace:
        """
        Create a base argparse.Namespace with common options from CLI context.

        Returns:
            argparse.Namespace with common options populated
        """
        context = get_cli_context()

        # Create namespace with common options
        namespace = argparse.Namespace()
        namespace.verbose = context.verbose > 0
        namespace.log_level = context.log_level.value
        namespace.json = context.json_output

        return namespace

    def _handle_common_errors(self, e: Exception) -> int:
        """
        Handle common errors and return appropriate exit code.

        Args:
            e: The exception that occurred

        Returns:
            Exit code (1 for error)
        """
        if isinstance(e, ApplicationError):
            self.logger.error(
                "Application error: %s",
                e.message,
                extra={"context": e.context, "error_code": e.code},
            )
        else:
            self.logger.exception("Unexpected error: %s", e)

        return 1


def create_adapter(
    handler_func: Callable[[Any], int],
    adapter_class: type[BaseAdapter],
    **adapter_kwargs: Any,
) -> BaseAdapter:
    """
    Factory function to create adapters with proper configuration.

    Args:
        handler_func: The legacy handler function to wrap
        adapter_class: The adapter class to instantiate
        **adapter_kwargs: Additional keyword arguments for the adapter

    Returns:
        Configured adapter instance
    """
    return adapter_class(handler_func, **adapter_kwargs)
