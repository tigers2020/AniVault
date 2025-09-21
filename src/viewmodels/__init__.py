"""AniVault ViewModels Package.

This package contains all ViewModel classes that manage the state and business logic
for the MVVM architecture pattern.
"""

from .base_viewmodel import BaseViewModel, ViewModelFactory
from .file_processing_vm import FileProcessingViewModel

__version__ = "1.0.0"

__all__ = ["BaseViewModel", "FileProcessingViewModel", "ViewModelFactory"]
