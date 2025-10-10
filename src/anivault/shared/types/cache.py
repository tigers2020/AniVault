"""
Cache-related Type Definitions

This module provides type aliases and models for cache serialization
and deserialization.

Focus Areas:
- SQLite row → Pydantic model conversion
- JSON serialization/deserialization safety
- Cache key type definitions
"""

from __future__ import annotations

# Cache key types
# Note: Using simple assignment instead of TypeAlias for Python 3.9 compatibility
CacheKey = str  # Placeholder for future refinement
Timestamp = int  # Unix timestamp

# NOTE: Cache entry models will be added in Task 5 (Cache Serialization Refactor)
# NOTE: orjson serialization helpers defined in ModelConverter (Task 2)
