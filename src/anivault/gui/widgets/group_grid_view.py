"""
Group Grid View Widget - Displays file groups as a grid of cards.

This widget manages a grid layout of GroupCardWidget instances and handles
group management operations like adding, updating, and renaming groups.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QInputDialog,
    QMessageBox,
    QScrollArea,
    QWidget,
)

from anivault.shared.constants.gui_messages import UIConfig

from .group_card_widget import GroupCardWidget

logger = logging.getLogger(__name__)


class GroupGridViewWidget(QScrollArea):
    """Grid view widget for displaying file groups as cards."""

    # Signal emitted when a group card is clicked
    groupSelected: Signal = Signal(
        str,
        list,
    )  # Emits (group_name: str, files: list)

    def __init__(self, parent: QWidget | None = None):
        """
        Initialize the group grid view widget.

        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)

        # Create scroll area content
        self.scroll_content = QWidget()
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)

        # Main grid layout
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setSpacing(UIConfig.GRID_SPACING)
        self.grid_layout.setContentsMargins(
            UIConfig.GRID_MARGIN,
            UIConfig.GRID_MARGIN,
            UIConfig.GRID_MARGIN,
            UIConfig.GRID_MARGIN,
        )

        # Configure scroll area
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Store cards for reference
        self.group_cards = {}

        logger.debug("GroupGridViewWidget initialized")

    def clear_groups(self) -> None:
        """Clear all group cards from the grid."""
        # Remove all widgets from layout
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.group_cards.clear()
        logger.debug("Cleared all group cards")

    def add_group(
        self,
        group_name: str,
        files: list[Any],
        on_card_click: Callable[[str, list[Any]], None] | None = None,
    ) -> None:
        """
        Add a group card to the grid.

        Args:
            group_name: Name of the group
            files: List of files in the group
            on_card_click: Optional callback function for card clicks (for backward compatibility)
        """
        # Create group card with parent for better lifecycle management
        card = GroupCardWidget(group_name, files, self)
        self.group_cards[group_name] = card

        # Connect card's signal to our signal (propagate upward)
        card.cardClicked.connect(self._on_card_clicked)

        # Also support legacy callback for backward compatibility
        if on_card_click:
            card.cardClicked.connect(lambda gn, f: on_card_click(gn, f))

        # Calculate position in grid (3 columns)
        row = len(self.group_cards) // 3
        col = len(self.group_cards) % 3

        # Add to grid
        self.grid_layout.addWidget(card, row, col)

        logger.debug("Added group card: %s at (%d, %d)", group_name, row, col)

    def _on_card_clicked(self, group_name: str, files: list[Any]) -> None:
        """
        Handle card click event - propagate signal upward.

        Args:
            group_name: Name of the clicked group
            files: List of files in the group
        """
        logger.debug("Card clicked, emitting groupSelected signal: %s", group_name)
        self.groupSelected.emit(group_name, files)

    def update_groups(
        self,
        grouped_files: dict[str, list[Any]],
        on_card_click: Callable[[str, list[Any]], None] | None = None,
    ) -> None:
        """
        Update the grid with grouped files.

        Args:
            grouped_files: Dictionary mapping group names to file lists
            on_card_click: Optional callback function for card clicks
        """
        self.clear_groups()

        # Sort groups by size (largest first)
        sorted_groups = sorted(
            grouped_files.items(),
            key=lambda x: len(x[1]),
            reverse=True,
        )

        for group_name, files in sorted_groups:
            # Use ScannedFile objects directly to preserve metadata
            self.add_group(group_name, files, on_card_click)

        total_files = sum(len(files) for files in grouped_files.values())
        logger.info(
            "Updated grid view with %d groups containing %d total files",
            len(grouped_files),
            total_files,
        )

    def update_group_name_with_parser(self, old_group_name: str, files: list[Any]) -> None:
        """
        Update group name using parser.

        Args:
            old_group_name: Current group name
            files: List of files in the group
        """
        try:
            # Find the card widget for this group
            if old_group_name not in self.group_cards:
                logger.warning("Group card not found: %s", old_group_name)
                return

            # Get the first file to parse
            if not files:
                logger.warning("No files in group: %s", old_group_name)
                return

            # Use the file grouper's parser to get a better title
            from anivault.core.parser.anitopy_parser import AnitopyParser

            try:
                parser = AnitopyParser()
                # Use the first file as representative
                representative_file = files[0]
                parsed_result = parser.parse(representative_file.file_path.name)

                new_group_name = (
                    parsed_result.title if parsed_result.title else old_group_name
                )

                # Update the group name
                self._update_group_card_name(old_group_name, new_group_name, files)

                logger.info(
                    "Updated group name using parser: '%s' -> '%s'",
                    old_group_name,
                    new_group_name,
                )

            except ImportError:
                logger.warning("AnitopyParser not available")
                QMessageBox.warning(
                    self,
                    "Parser Unavailable",
                    "AnitopyParser is not available. Please install anitopy library.",
                )
            except Exception as e:
                logger.exception("Failed to update group name with parser")
                QMessageBox.critical(
                    self,
                    "Update Failed",
                    f"Failed to update group name: {e!s}",
                )

        except Exception as e:
            logger.exception("Error updating group name with parser")
            QMessageBox.critical(self, "Error", f"Error updating group name: {e!s}")

    def edit_group_name(self, old_group_name: str, files: list[Any]) -> None:
        """
        Edit group name manually.

        Args:
            old_group_name: Current group name
            files: List of files in the group
        """
        try:
            # Show input dialog for new group name
            new_group_name, ok = QInputDialog.getText(
                self,
                "Edit Group Name",
                "Enter new group name:",
                text=old_group_name,
            )

            if ok and new_group_name.strip():
                new_group_name = new_group_name.strip()

                # Check if name is different
                if new_group_name != old_group_name:
                    # Update the group name
                    self._update_group_card_name(old_group_name, new_group_name, files)
                    logger.info(
                        "Manually updated group name: '%s' -> '%s'",
                        old_group_name,
                        new_group_name,
                    )
                else:
                    logger.debug("Group name unchanged: %s", old_group_name)

        except Exception as e:
            logger.exception("Error editing group name")
            QMessageBox.critical(self, "Error", f"Error editing group name: {e!s}")

    def _update_group_card_name(
        self,
        old_group_name: str,
        new_group_name: str,
        files: list[Any],
    ) -> None:
        """
        Update the group card with new name.

        Args:
            old_group_name: Current group name
            new_group_name: New group name
            files: List of files in the group
        """
        try:
            # Check if new name already exists
            if new_group_name in self.group_cards and new_group_name != old_group_name:
                # Generate unique name
                counter = 1
                while f"{new_group_name} ({counter})" in self.group_cards:
                    counter += 1
                new_group_name = f"{new_group_name} ({counter})"

            # Remove old card
            if old_group_name in self.group_cards:
                old_card = self.group_cards.pop(old_group_name)
                self.grid_layout.removeWidget(old_card)
                old_card.deleteLater()

            # Create new card with updated name
            new_card = GroupCardWidget(new_group_name, files, self)
            # Connect the new card's signal
            new_card.cardClicked.connect(self._on_card_clicked)

            # Also maintain backward compatibility with legacy callback
            if hasattr(self.parent(), "on_group_selected"):
                new_card.cardClicked.connect(
                    lambda gn, f: self.parent().on_group_selected(gn, f),
                )

            self.group_cards[new_group_name] = new_card

            # Add to grid layout
            row = len(self.group_cards) // 3
            col = len(self.group_cards) % 3
            self.grid_layout.addWidget(new_card, row, col)

            # Update parent window's group details if this group is currently selected
            if hasattr(self.parent(), "group_details_label"):
                current_text = self.parent().group_details_label.text()
                if f"📁 {old_group_name}" in current_text:
                    self.parent().group_details_label.setText(
                        f"📁 {new_group_name} ({len(files)} files)",
                    )

            logger.debug(
                "Updated group card: '%s' -> '%s'",
                old_group_name,
                new_group_name,
            )

        except Exception:
            logger.exception("Error updating group card name")
            raise
