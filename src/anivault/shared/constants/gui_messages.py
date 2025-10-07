"""
GUI Messages Constants

This module contains all constants for GUI dialog titles, messages,
button texts, and status messages. This ensures consistency across
the application and makes internationalization easier.
"""



class DialogTitles:
    """Dialog title constants."""

    # Generic titles
    ERROR = "Error"
    WARNING = "Warning"
    SUCCESS = "Success"
    INFO = "Information"
    CONFIRMATION = "Confirm"

    # Specific dialog titles
    SETTINGS = "Settings"
    SETTINGS_SAVED = "Settings Saved"
    SAVE_FAILED = "Save Failed"
    API_KEY_REQUIRED = "API Key Required"
    INVALID_API_KEY = "Invalid API Key"

    # File operations
    SELECT_FOLDER = "Select Folder"
    SCAN_COMPLETE = "Scan Complete"
    SCAN_ERROR = "Scan Error"

    # TMDB operations
    TMDB_MATCHING = "TMDB Matching"
    TMDB_ERROR = "TMDB Error"

    # Group operations
    EDIT_GROUP_NAME = "Edit Group Name"
    DELETE_GROUP = "Delete Group"


class DialogMessages:
    """Dialog message constants."""

    # Settings messages
    API_KEY_SAVED = "Settings have been saved successfully."
    API_KEY_REQUIRED = "Please enter your TMDB API key."
    API_KEY_TOO_SHORT = "API key appears to be too short. Please check your input."
    SETTINGS_SAVE_FAILED = "Failed to save settings: {error}"

    # File scanning messages
    SCAN_STARTED = "File scanning started..."
    SCAN_COMPLETE = "File scanning completed! Found {count} files."
    SCAN_ERROR = "File scanning failed: {error}"
    NO_FILES_FOUND = "No anime files found in the selected directory."

    # TMDB matching messages
    TMDB_MATCHING_STARTED = "TMDB matching started..."
    TMDB_MATCHING_COMPLETE = "TMDB matching completed!"
    TMDB_MATCHING_CANCELLED = "TMDB matching cancelled by user."
    TMDB_MATCHING_ERROR = "TMDB matching error: {error}"
    TMDB_API_KEY_MISSING = "TMDB API key is not configured. Please set it in Settings."

    # Group operations
    EDIT_GROUP_NAME_PROMPT = "Enter new group name:"
    DELETE_GROUP_CONFIRM = "Are you sure you want to delete group '{group_name}'?"
    GROUP_NAME_UPDATED = "Group name updated successfully."
    GROUP_NAME_UPDATE_FAILED = "Failed to update group name: {error}"

    # Generic operations
    OPERATION_CANCELLED = "Operation cancelled by user."
    UNEXPECTED_ERROR = "An unexpected error occurred: {error}"


class ButtonTexts:
    """Button text constants."""

    # Standard buttons
    OK = "OK"
    CANCEL = "Cancel"
    YES = "Yes"
    NO = "No"
    SAVE = "Save"
    CLOSE = "Close"
    APPLY = "Apply"

    # Custom buttons
    CANCEL_MATCHING = "Cancel Matching"
    START_SCAN = "Start Scan"
    STOP_SCAN = "Stop Scan"
    SELECT_FOLDER = "Select Folder"
    CLEAR_CACHE = "Clear Cache"


class StatusMessages:
    """Status bar message constants."""

    # Application status
    READY = "Ready"
    INITIALIZING = "Initializing..."

    # File scanning status
    SCANNING_FILES = "Scanning files..."
    FILES_FOUND = "Found {count} files"
    SCANNING_DIRECTORY = "Scanning directory: {path}"

    # TMDB matching status
    MATCHING_FILES = "Matching files with TMDB..."
    MATCHING_PROGRESS = "Matching: {current}/{total} files ({percent}%)"
    MATCHING_COMPLETE = "Matching complete: {matched}/{total} files matched"

    # Group operations
    GROUP_SELECTED = "Selected group: {group_name} ({count} files)"
    GROUPS_LOADED = "Loaded {count} groups"

    # Theme operations
    THEME_LOADED = "Theme loaded: {theme_name}"
    THEME_LOAD_FAILED = "Failed to load theme: {theme_name}"


class ProgressMessages:
    """Progress dialog message constants."""

    # TMDB matching progress
    PREPARING_TMDB = "Preparing TMDB matching..."
    INITIALIZING_TMDB = "Initializing..."
    STARTING_TMDB = "Starting TMDB matching..."
    MATCHING_IN_PROGRESS = "Matching files... {percent}%"
    MATCHING_COMPLETE = "TMDB matching completed!"

    # File scanning progress
    SCANNING_IN_PROGRESS = "Scanning: {current}/{total} files"
    SCANNING_COMPLETE = "Scan complete: {count} files found"


class ToolTips:
    """Tooltip text constants."""

    # Settings dialog
    API_KEY_INPUT = "Enter your TMDB API key (obtained from themoviedb.org)"
    FOLDER_PATH = "Path to your anime collection folder"
    INCLUDE_SUBDIRS = "Include subdirectories in the scan"
    AUTO_SCAN_INTERVAL = "Automatic scan interval in minutes (0 to disable)"

    # Main window
    SCAN_BUTTON = "Scan the selected folder for anime files"
    MATCH_BUTTON = "Match scanned files with TMDB database"
    ORGANIZE_BUTTON = "Organize matched files into folders"
    SETTINGS_BUTTON = "Open settings dialog"
    THEME_MENU = "Change application theme"


class PlaceholderTexts:
    """Placeholder text constants for input fields."""

    API_KEY = "Enter your TMDB API key here..."
    FOLDER_PATH = "Select a folder..."
    GROUP_NAME = "Enter group name..."
    SEARCH = "Search..."


class UIConfig:
    """UI layout and display configuration constants."""

    # Text truncation limits
    GROUP_CARD_TITLE_MAX_LENGTH = 50  # Group card title truncation
    GROUP_CARD_OVERVIEW_MAX_LENGTH = 150  # Overview/description truncation

    # Default/fallback values
    UNKNOWN_TITLE = "Unknown"
    NO_OVERVIEW = ""
    DEFAULT_GROUP_NAME = "Unnamed Group"

    # Icon/emoji constants
    FOLDER_ICON = "📂"
    FILM_ICON = "🎬"
    STAR_ICON = "⭐"


# Export all classes
__all__ = [
    "ButtonTexts",
    "DialogMessages",
    "DialogTitles",
    "PlaceholderTexts",
    "ProgressMessages",
    "StatusMessages",
    "ToolTips",
    "UIConfig",
]

