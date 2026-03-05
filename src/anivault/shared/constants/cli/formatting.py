"""CLI formatting constants (Phase 3-2 domain grouping)."""

from __future__ import annotations


class CLIFormatting:
    """CLI formatting constants."""

    INDENT_SIZE = 2
    SEPARATOR_LENGTH = 60
    DEFAULT_RATE_LIMIT_HELP = "35.0"
    DEFAULT_WORKERS_EXAMPLE = 8
    DEFAULT_RATE_LIMIT_EXAMPLE = 20

    class Colors:
        """Semantic color definitions."""

        PRIMARY = "[bold blue]"
        SECONDARY = "[dim blue]"
        INFO = "[blue]"
        WARNING = "[yellow]"
        ERROR = "[red]"
        SUCCESS = "[green]"
        RESET = "[/]"

    COLOR_RED = "[red]"
    COLOR_GREEN = "[green]"
    COLOR_BLUE = "[blue]"
    COLOR_YELLOW = "[yellow]"
    COLOR_RESET = "[/]"

    @staticmethod
    def format_colored_message(message: str, color_type: str) -> str:
        """Format a message with semantic color."""
        color_map = {
            "primary": CLIFormatting.Colors.PRIMARY,
            "secondary": CLIFormatting.Colors.SECONDARY,
            "info": CLIFormatting.Colors.INFO,
            "warning": CLIFormatting.Colors.WARNING,
            "error": CLIFormatting.Colors.ERROR,
            "success": CLIFormatting.Colors.SUCCESS,
        }
        color_tag = color_map.get(color_type.lower(), "")
        return f"{color_tag}{message}{CLIFormatting.Colors.RESET}"
