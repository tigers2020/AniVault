"""Cache-related constants."""


class Cache:
    """Cache configuration constants."""

    TTL = 3600  # 1 hour in seconds
    MAX_SIZE = 1000
    TYPE_SEARCH = "search"
    TYPE_DETAILS = "details"
    TYPE_PARSER = "parser"

    # Cache TTL values (in seconds)
    DEFAULT_TTL = 3600  # 1 hour
    SEARCH_TTL = 1800  # 30 minutes
    DETAILS_TTL = 3600  # 1 hour
    PARSER_CACHE_TTL = 86400  # 24 hours

    # Legacy constants for backward compatibility
    CACHE_TYPE_DETAILS = TYPE_DETAILS
    CACHE_TYPE_SEARCH = TYPE_SEARCH


__all__ = ["Cache"]
