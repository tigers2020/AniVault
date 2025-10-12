"""Performance optimization configuration model.

This module contains the performance configuration model for managing
performance-related settings including resource limits and profiling.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from anivault.shared.constants import Logging, Memory


class PerformanceSettings(BaseModel):
    """Performance configuration.

    This class manages performance optimization settings including
    resource limits (memory, CPU) and profiling configuration.
    """

    memory_limit: str = Field(
        default=Memory.DEFAULT_LIMIT_STRING,
        description="Memory limit for the application",
    )
    cpu_limit: int = Field(
        default=Memory.DEFAULT_CPU_LIMIT,
        gt=0,
        description="CPU limit for the application",
    )
    enable_profiling: bool = Field(
        default=False,
        description="Enable performance profiling",
    )
    profile_output: str = Field(
        default=Logging.DEFAULT_PROFILING_FILE_PATH,
        description="Profiling output file path",
    )


# Backward compatibility alias
PerformanceConfig = PerformanceSettings


__all__ = [
    "PerformanceConfig",  # Backward compatibility
    "PerformanceSettings",
]
