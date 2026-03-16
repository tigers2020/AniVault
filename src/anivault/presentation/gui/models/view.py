"""View kind and target constants for GUI v2.

Centralizes view/target literals to avoid magic strings across
main_window and event handlers.
"""

from enum import Enum


class ViewKind(str, Enum):
    """Content view / target kind for scan and match results."""

    SUBTITLES = "subtitles"
    VIDEOS = "videos"


# Tab names used by sidebar/workspace (for reference; comparison stays string-based)
VIEW_NAME_WORK = "work"
VIEW_NAME_SUBTITLES = "subtitles"
