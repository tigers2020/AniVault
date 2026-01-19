"""Pipeline-related constants."""


class Pipeline:
    """Pipeline configuration constants."""

    QUEUE_SIZE = 1000
    SENTINEL = object()  # Unique sentinel object


__all__ = ["Pipeline"]
