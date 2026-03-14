"""Grouping and subtitle matching strategy constants."""


class SubtitleMatchingStrategy:
    """Subtitle matching strategy names (single source of truth).

    Used by core/subtitle_matcher and config/models/grouping_settings.
    """

    INDEXED = "indexed"
    FALLBACK = "fallback"
    LEGACY = "legacy"

    @classmethod
    def all_values(cls) -> tuple[str, ...]:
        """Return all valid strategy values for validation."""
        return (cls.INDEXED, cls.FALLBACK, cls.LEGACY)
