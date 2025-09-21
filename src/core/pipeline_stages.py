"""Pipeline stage definitions for parallel execution."""

from enum import Enum


class PipelineStage(Enum):
    """Enumeration of pipeline stages."""

    SCANNING = "scanning"
    GROUPING = "grouping"
    PARSING = "parsing"
    METADATA_RETRIEVAL = "metadata_retrieval"
    GROUP_METADATA_RETRIEVAL = "group_metadata_retrieval"
    FILE_MOVING = "file_moving"
