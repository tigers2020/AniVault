"""Resolution detection module for AniVault.

This module provides functionality to detect video resolution from filenames
and group files by resolution for organization purposes.
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from anivault.core.constants import ParsingConfidence
from anivault.shared.constants.file_formats import VideoFormats
from anivault.core.models import ScannedFile
from anivault.shared.errors import (
    AniVaultError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)
from anivault.shared.logging import log_operation_error

logger = logging.getLogger(__name__)


@dataclass
class ResolutionInfo:
    """Information about detected resolution."""

    width: int | None = None
    height: int | None = None
    quality: str | None = None
    confidence: float = 0.0


class ResolutionDetector:
    """Detects video resolution from filenames and file properties."""

    def __init__(self) -> None:
        """Initialize the resolution detector."""
        # Resolution patterns in order of preference
        self.resolution_patterns = [
            # 4K patterns
            (r"4K|2160p|3840x2160", 3840, 2160, "4K"),
            # 1080p patterns
            (r"1080p|1920x1080|Full HD", 1920, 1080, "1080p"),
            # 720p patterns
            (r"720p|1280x720|HD", 1280, 720, "720p"),
            # 480p patterns
            (r"480p|854x480|SD", 854, 480, "480p"),
            # Custom resolution patterns
            (r"(\d+)x(\d+)", None, None, "custom"),
        ]

    def detect_resolution(self, file_path: Path) -> ResolutionInfo:
        """Detect resolution from filename.

        Args:
            file_path: Path to the video file

        Returns:
            ResolutionInfo with detected resolution data

        Raises:
            InfrastructureError: If detection fails
        """
        context = ErrorContext(
            operation="detect_resolution",
            additional_data={"file_path": str(file_path)},
        )

        try:
            resolution_info = self._try_detect_from_filename(file_path.name)
            if not resolution_info.quality:
                resolution_info = self._detect_from_file_properties(file_path)

            logger.debug(
                "Detected resolution for %s: %s",
                file_path.name,
                resolution_info.quality or "unknown",
            )
            return resolution_info

        except Exception as e:  # noqa: BLE001 - intentionally catch all to wrap as InfrastructureError
            self._raise_detection_error(e, file_path, context)

    def _try_detect_from_filename(self, filename: str) -> ResolutionInfo:
        """Try to detect resolution from filename using configured patterns."""
        resolution_info = ResolutionInfo()
        for pattern, width, height, quality in self.resolution_patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match and self._apply_pattern_match(match, pattern, width, height, quality, resolution_info):
                break
        return resolution_info

    def _apply_pattern_match(
        self,
        match: re.Match[str],
        pattern: str,
        width: int | None,
        height: int | None,
        quality: str | None,
        resolution_info: ResolutionInfo,
    ) -> bool:
        """Apply a single pattern match to resolution_info. Returns True if done."""
        if width is not None and height is not None:
            resolution_info.width = width
            resolution_info.height = height
            resolution_info.quality = quality
            resolution_info.confidence = 0.9
            return True
        if pattern == r"(\d+)x(\d+)":
            try:
                resolution_info.width = int(match.group(1))
                resolution_info.height = int(match.group(2))
                resolution_info.quality = self._classify_resolution(
                    resolution_info.width,
                    resolution_info.height,
                )
                resolution_info.confidence = ParsingConfidence.RESOLUTION_DETECTED
                return True
            except (ValueError, IndexError):
                pass
        return False

    def _raise_detection_error(
        self,
        e: Exception,
        file_path: Path,
        context: ErrorContext,
    ) -> NoReturn:
        """Log and re-raise resolution detection error. Always raises."""
        if isinstance(e, AniVaultError):
            log_operation_error(
                logger=logger,
                operation="detect_resolution",
                error=e,
                additional_context=context.additional_data if context else None,
            )
        else:
            error = InfrastructureError(
                code=ErrorCode.RESOLUTION_DETECTION_FAILED,
                message=f"Failed to detect resolution for {file_path}: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="detect_resolution",
                error=error,
                additional_context=context.additional_data if context else None,
            )
        raise InfrastructureError(
            code=ErrorCode.RESOLUTION_DETECTION_FAILED,
            message=f"Failed to detect resolution for {file_path}: {e!s}",
            context=context,
            original_error=e,
        ) from e

    def _classify_resolution(self, width: int, height: int) -> str:
        """Classify resolution based on dimensions.

        Args:
            width: Video width in pixels
            height: Video height in pixels

        Returns:
            Resolution quality string
        """
        if width >= 3840 or height >= 2160:
            return "4K"
        if width >= 1920 or height >= 1080:
            return "1080p"
        if width >= 1280 or height >= 720:
            return "720p"
        if width >= 854 or height >= 480:
            return "480p"
        return "SD"

    def _detect_from_file_properties(self, file_path: Path) -> ResolutionInfo:
        """Detect resolution by probing the video file with ffprobe.

        Reads the first video stream width/height and classifies to a standard
        resolution string (e.g. 1080p, 720p). Requires ffprobe (ffmpeg) on PATH.
        On failure (missing ffprobe, timeout, or parse error), returns unknown
        resolution without raising.

        Args:
            file_path: Path to the video file

        Returns:
            ResolutionInfo with width, height, quality when probe succeeds;
            otherwise ResolutionInfo with confidence=0.0
        """
        video_extensions = {ext.lower() for ext in VideoFormats.ALL_EXTENSIONS}
        if not file_path.is_file() or file_path.suffix.lower() not in video_extensions:
            return ResolutionInfo(confidence=0.0)

        try:
            width, height = self._probe_video_dimensions(file_path)
        except (OSError, subprocess.TimeoutExpired, ValueError) as e:
            logger.debug(
                "Could not probe resolution for %s: %s",
                file_path.name,
                e,
            )
            return ResolutionInfo(confidence=0.0)

        if width is None or height is None or width <= 0 or height <= 0:
            return ResolutionInfo(confidence=0.0)

        quality = self._classify_resolution(width, height)
        return ResolutionInfo(
            width=width,
            height=height,
            quality=quality,
            confidence=0.8,
        )

    def _probe_video_dimensions(self, file_path: Path) -> tuple[int, int]:
        """Run ffprobe to get first video stream width and height.

        Returns:
            (width, height) in pixels.

        Raises:
            FileNotFoundError: ffprobe not found on PATH.
            subprocess.TimeoutExpired: Probe took longer than timeout.
            ValueError: Output could not be parsed.
            OSError: Other subprocess/IO errors.
        """
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0",
            str(file_path.resolve()),
        ]
        kwargs: dict = {
            "capture_output": True,
            "timeout": 10,
            "text": True,
            "check": False,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

        result = subprocess.run(cmd, **kwargs)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise ValueError(f"ffprobe exited {result.returncode}: {stderr}")

        line = (result.stdout or "").strip()
        if not line:
            raise ValueError("ffprobe produced no output")

        parts = line.split(",")
        if len(parts) != 2:
            raise ValueError(f"Expected width,height; got: {line!r}")

        width = int(parts[0].strip())
        height = int(parts[1].strip())
        return (width, height)

    def group_by_resolution(
        self,
        files: list[ScannedFile],
    ) -> dict[str, list[ScannedFile]]:
        """Group files by their detected resolution.

        Args:
            files: List of scanned files to group

        Returns:
            Dictionary mapping resolution quality to lists of files

        Raises:
            InfrastructureError: If grouping fails
        """
        context = ErrorContext(
            operation="group_by_resolution",
            additional_data={"file_count": len(files)},
        )

        try:
            resolution_groups = defaultdict(list)

            for file in files:
                resolution_info = self.detect_resolution(file.file_path)
                quality = resolution_info.quality or "unknown"
                resolution_groups[quality].append(file)

            logger.info(
                "Grouped %d files by resolution: %s",
                len(files),
                dict(resolution_groups),
            )

            return dict(resolution_groups)

        except Exception as e:
            logger.exception(
                "Failed to group files by resolution",
                extra={"context": context.additional_data if context else None},
            )
            raise InfrastructureError(
                code=ErrorCode.RESOLUTION_GROUPING_FAILED,
                message=f"Failed to group files by resolution: {e!s}",
                context=context,
                original_error=e,
            ) from e

    def find_highest_resolution(self, files: list[ScannedFile]) -> ScannedFile | None:
        """Find the file with the highest resolution in a group.

        Args:
            files: List of files to compare

        Returns:
            File with highest resolution, or None if no files provided

        Raises:
            InfrastructureError: If comparison fails
        """
        if not files:
            return None

        context = ErrorContext(
            operation="find_highest_resolution",
            additional_data={"file_count": len(files)},
        )

        try:
            best_file, best_resolution = self._select_best_resolution(files)
            logger.debug(
                "Selected highest resolution file: %s (%s)",
                best_file.file_path.name if best_file else "None",
                best_resolution.quality or "unknown",
            )
            return best_file

        except Exception as e:  # noqa: BLE001 - intentionally catch all to wrap as InfrastructureError
            self._raise_comparison_error(e, context)

    def _select_best_resolution(self, files: list[ScannedFile]) -> tuple[ScannedFile | None, ResolutionInfo]:
        """Select the file with the best resolution from the list. Caller must pass non-empty files."""
        best_file = None
        best_resolution = ResolutionInfo()
        for file in files:
            resolution_info = self.detect_resolution(file.file_path)
            if self._is_better_resolution(resolution_info, best_resolution):
                best_file = file
                best_resolution = resolution_info
        return best_file, best_resolution

    def _raise_comparison_error(self, e: Exception, context: ErrorContext) -> NoReturn:
        """Log and re-raise resolution comparison error. Always raises."""
        if isinstance(e, AniVaultError):
            log_operation_error(
                logger=logger,
                operation="find_highest_resolution",
                error=e,
                additional_context=context.additional_data if context else None,
            )
        else:
            error = InfrastructureError(
                code=ErrorCode.RESOLUTION_COMPARISON_FAILED,
                message=f"Failed to find highest resolution file: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                operation="find_highest_resolution",
                error=error,
                additional_context=context.additional_data if context else None,
            )
        raise InfrastructureError(
            code=ErrorCode.RESOLUTION_COMPARISON_FAILED,
            message=f"Failed to find highest resolution file: {e!s}",
            context=context,
            original_error=e,
        ) from e

    def _is_better_resolution(
        self,
        current: ResolutionInfo,
        best: ResolutionInfo,
    ) -> bool:
        """Compare two resolution infos to determine which is better.

        Args:
            current: Current resolution info
            best: Best resolution info so far

        Returns:
            True if current is better than best
        """
        if not best.quality:
            return True

        if not current.quality:
            return False

        # Resolution hierarchy (higher is better)
        resolution_hierarchy = {
            "4K": 4,
            "1080p": 3,
            "720p": 2,
            "480p": 1,
            "SD": 0,
        }

        current_rank = resolution_hierarchy.get(current.quality, 0)
        best_rank = resolution_hierarchy.get(best.quality, 0)

        return current_rank > best_rank


def detect_file_resolution(file_path: Path) -> ResolutionInfo:
    """Convenience function to detect resolution from a single file.

    Args:
        file_path: Path to the video file

    Returns:
        ResolutionInfo with detected resolution data
    """
    detector = ResolutionDetector()
    return detector.detect_resolution(file_path)
