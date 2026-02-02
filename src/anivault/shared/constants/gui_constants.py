"""GUI constants for type safety and consistency."""


class DialogConstants:
    """Constants for dialog settings."""

    # Dialog dimensions
    DIALOG_WIDTH = 500
    DIALOG_HEIGHT = 400

    # Dialog title
    DIALOG_TITLE = "AniVault Settings"

    # Font settings
    MONOSPACE_FONT = "Consolas, Monaco, monospace"


class LabelConstants:
    """Constants for GUI labels."""

    # API Key section
    API_KEY_LABEL = "TMDB API Key:"
    API_KEY_PLACEHOLDER = "Enter your TMDB API key"
    API_KEY_STYLE = "infoLabel"
    API_KEY_FIELD = "API Key"

    # Folder settings
    SOURCE_FOLDER_LABEL = "Source Folder:"
    SOURCE_FOLDER_BUTTON = "Browse..."
    SOURCE_FOLDER_PLACEHOLDER = "Select source folder for media files"

    TARGET_FOLDER_LABEL = "Target Folder:"
    TARGET_FOLDER_BUTTON = "Browse..."
    TARGET_FOLDER_PLACEHOLDER = "Select target folder for organized files"

    # Organization options
    ORGANIZE_PATH_TEMPLATE_LABEL = "정리 경로 템플릿"
    ORGANIZE_PATH_TEMPLATE_PLACEHOLDER = "{해상도}/{연도}/{제목}/{시즌}"

    # Auto scan settings
    AUTO_SCAN_TITLE = "Auto Scan Settings"
    AUTO_SCAN_STARTUP = "Scan source folder on startup"
    AUTO_SCAN_INTERVAL = "Scan Interval:"
    AUTO_SCAN_INTERVAL_MINUTES = " minutes"
    AUTO_SCAN_DISABLED = "Disabled"
    AUTO_SCAN_SUBDIRS = "Include subdirectories"

    # Folder management
    FOLDERS_TAB = "Folders"
    FOLDERS_PLACEHOLDER = "folders"


class MessageConstants:
    """Constants for GUI messages."""

    # Dialog messages
    SELECT_SOURCE_FOLDER = "Select Source Folder"
    SELECT_TARGET_FOLDER = "Select Target Folder"
    INVALID_FOLDER = "Invalid Folder"


class SettingKeys:
    """Constants for setting keys."""

    # API settings
    SAVE_API_KEY = "save_api_key"
    TMDB_API_KEY = "TMDB_API_KEY="

    # Folder settings
    SAVE_FOLDER_SETTINGS = "save_folder_settings"
    SOURCE_FOLDER = "source_folder"
    DESTINATION_FOLDER = "destination_folder"
    ORGANIZE_PATH_TEMPLATE = "organize_path_template"


class AutoScanConstants:
    """Constants for auto scan settings."""

    # Default values
    DEFAULT_SCAN_INTERVAL = 1440  # 24 hours in minutes
    DEFAULT_SCAN_INTERVAL_DAYS = 90
    DEFAULT_SCAN_INTERVAL_YEAR = 365
    DEFAULT_SCAN_INTERVAL_MINUTES = 1440

    # Setting keys
    SHOULD_AUTO_SCAN_ON_STARTUP = "should_auto_scan_on_startup"
    GET_FOLDER_SETTINGS = "get_folder_settings"

    # Status messages
    SCAN_ALREADY_IN_PROGRESS = "Scan already in progress"
    NO_SCAN_CALLBACK = "No scan callback configured"
    NO_FOLDER_SETTINGS = "No folder settings configured"
    NO_SOURCE_FOLDER = "No source folder configured"
    AUTO_SCAN_COMPLETED = "Auto scan completed"

    # Setting keys for status
    ENABLED = "enabled"
    SOURCE_FOLDER = "source_folder"
    TARGET_FOLDER = "target_folder"
    AUTO_SCAN_ON_STARTUP = "auto_scan_on_startup"
    AUTO_SCAN_INTERVAL_MINUTES = "auto_scan_interval_minutes"
    INCLUDE_SUBDIRECTORIES = "include_subdirectories"
    CAN_SCAN = "can_scan"
    SCAN_IN_PROGRESS = "scan_in_progress"
