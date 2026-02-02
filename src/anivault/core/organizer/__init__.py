"""File organization engine for AniVault.

This package provides the FileOrganizer class and supporting services
for organizing anime files into a structured directory layout.
"""

from __future__ import annotations

from .file_organizer import OptimizedFileOrganizer
from .main import FileOrganizer
from .organize_service import (
    execute_organization_plan,
    generate_enhanced_organization_plan,
    generate_organization_plan,
)

__all__ = [
    "FileOrganizer",
    "OptimizedFileOrganizer",
    "execute_organization_plan",
    "generate_enhanced_organization_plan",
    "generate_organization_plan",
]
