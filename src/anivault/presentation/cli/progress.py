"""
Progress Display Utility Module

This module provides a centralized system for displaying progress bars and spinners
for long-running operations in the AniVault CLI. It wraps the Rich library's
progress functionality to provide a simple, consistent interface.

The ProgressManager class offers:
- Determinate progress tracking for finite sequences
- Indeterminate progress display (spinners) for unknown duration tasks
- Conditional disabling for non-interactive modes or JSON output
- Consistent styling and formatting across all commands
"""

from __future__ import annotations

import types
from collections.abc import Generator, Iterable
from contextlib import contextmanager
from typing import Any

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from typing_extensions import Self


class ProgressManager:
    """
    A wrapper around Rich's Progress class that provides a simplified interface
    for displaying progress bars and spinners in the AniVault CLI.

    This class handles both determinate progress (for finite sequences) and
    indeterminate progress (for operations of unknown duration) while providing
    the ability to disable progress display for non-interactive modes.
    """

    def __init__(self, *, disabled: bool = False) -> None:
        """
        Initialize the ProgressManager.

        Args:
            disabled: If True, progress display will be disabled. This is useful
                     for non-interactive modes, JSON output, or when progress
                     display would be undesirable.
        """
        self.disabled = disabled

        # Configure the progress display with standard columns
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            disable=disabled,
            expand=True,
        )

    def track(
        self,
        sequence: Iterable[Any],
        description: str = "Processing...",
    ) -> Generator[Any, None, None]:
        """
        Track progress over a finite sequence.

        This method provides an easy-to-use interface similar to rich.progress.track
        for iterating over a sequence while displaying a progress bar.

        Args:
            sequence: The iterable to track progress over
            description: Description text to display with the progress bar

        Yields:
            Items from the input sequence

        Example:
            >>> progress = ProgressManager()
            >>> for item in progress.track(my_list, "Processing files..."):
            ...     process_item(item)
        """
        if self.disabled:
            # If disabled, simply yield items without progress display
            yield from sequence
            return

        # Add a new task to track progress
        # Handle both sequences and generators
        try:
            total = len(sequence) if hasattr(sequence, "__len__") and hasattr(sequence, "__getitem__") else None  # type: ignore[arg-type]
        except TypeError:
            # For generators and other non-length objects,
            # use None for indeterminate progress
            total = None

        task_id = self._progress.add_task(description, total=total)

        try:
            # Start the progress display
            with self._progress:
                for item in sequence:
                    yield item
                    # Only advance if we have a determinate total
                    if total is not None:
                        self._progress.advance(task_id)
        finally:
            # Ensure the task is removed when done
            self._progress.remove_task(task_id)

    @contextmanager
    def spinner(self, description: str = "Working...") -> Generator[None, None, None]:
        """
        Display a spinner for operations of unknown duration.

        This context manager provides visual feedback that the application is
        working on an indeterminate task.

        Args:
            description: Description text to display with the spinner

        Example:
            >>> progress = ProgressManager()
            >>> with progress.spinner("Making API call..."):
            ...     make_api_call()
        """
        if self.disabled:
            # If disabled, perform no actions
            yield
            return

        # Add a new task with indeterminate total
        task_id = self._progress.add_task(description, total=None)

        try:
            # Start the progress display
            with self._progress:
                yield
        finally:
            # Ensure the task is removed when done
            self._progress.remove_task(task_id)

    def start(self) -> None:
        """
        Start the progress display.

        This method should be called when you want to manually control
        the progress display lifecycle.
        """
        if not self.disabled:
            self._progress.start()

    def stop(self) -> None:
        """
        Stop the progress display.

        This method should be called when you want to manually control
        the progress display lifecycle.
        """
        if not self.disabled:
            self._progress.stop()

    def __enter__(self) -> Self:
        """
        Context manager entry.

        Returns:
            Self for use in 'with' statements
        """
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """
        Context manager exit.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        self.stop()


def create_progress_manager(*, disabled: bool = False) -> ProgressManager:
    """
    Factory function to create a ProgressManager instance.

    This function provides a convenient way to create a ProgressManager
    with consistent configuration across the application.

    Args:
        disabled: If True, progress display will be disabled

    Returns:
        A new ProgressManager instance
    """
    return ProgressManager(disabled=disabled)
