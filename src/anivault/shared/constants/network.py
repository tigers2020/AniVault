"""
Network Configuration Constants

This module contains all constants related to network operations,
downloaders, and HTTP client configurations.
"""

from typing import ClassVar

from .system import BASE_SECOND


class NetworkConfig:
    """Network configuration constants."""
    
    # Timeout settings
    DEFAULT_TIMEOUT = 1.0  # 1 second for queue operations
    CONNECT_TIMEOUT = 10 * BASE_SECOND  # 10 seconds
    READ_TIMEOUT = 30 * BASE_SECOND     # 30 seconds
    
    # Retry settings
    DEFAULT_RETRIES = 5
    RETRY_DELAY = 1.0 * BASE_SECOND
    MAX_RETRY_DELAY = 60 * BASE_SECOND
    
    # Chunk size for downloads
    DEFAULT_CHUNK_SIZE = 8192  # 8KB
    LARGE_CHUNK_SIZE = 65536   # 64KB
    
    # User agent
    USER_AGENT = "AniVault/1.0.0 (https://github.com/anivault/anivault)"
    
    # HTTP headers
    CONTENT_TYPE_JSON = "application/json"
    CONTENT_TYPE_FORM = "application/x-www-form-urlencoded"
    ACCEPT_JSON = "application/json"
    
    # Rate limiting
    DEFAULT_RATE_LIMIT = 20  # requests per minute
    BURST_LIMIT = 5          # burst requests allowed
    DEFAULT_TOKEN_BUCKET_CAPACITY = 20  # token bucket capacity
    DEFAULT_TOKEN_REFILL_RATE = 1.0  # tokens per second
    DEFAULT_CONCURRENT_REQUESTS = 10  # concurrent requests limit


class DownloadConfig:
    """Download-specific configuration constants."""
    
    # File size limits
    MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB
    MIN_FILE_SIZE = 1024  # 1KB
    
    # Concurrent downloads
    MAX_CONCURRENT_DOWNLOADS = 4
    DOWNLOAD_QUEUE_SIZE = 100
    
    # Progress reporting
    PROGRESS_INTERVAL = 0.1 * BASE_SECOND  # 100ms
    PROGRESS_THRESHOLD = 1024 * 1024       # 1MB
