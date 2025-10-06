"""
GUI Controllers Package

This package contains controller classes that manage business logic
and coordinate between the UI layer and the core services.

Controllers follow the MVC pattern by:
- Managing business logic and data flow
- Coordinating between UI components and core services
- Providing a clean interface for the UI layer
- Enabling better testability and separation of concerns
"""

from .scan_controller import ScanController
from .tmdb_controller import TMDBController

__all__ = ["ScanController", "TMDBController"]
