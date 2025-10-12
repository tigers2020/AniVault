# PathBuilder Design Documentation

## Overview

The `PathBuilder` service is responsible for constructing destination file paths for organized anime files based on metadata and naming conventions.

## Architecture

### Core Components

1. **PathContext** (Dataclass)
   - Immutable context for path building operations
   - Contains: `ScannedFile`, resolution flags, target folder, media type, settings

2. **PathBuilder** (Service Class)
   - Orchestrates path construction
   - Handles series title extraction, sanitization, resolution-based organization
   - Provides utilities for filename sanitization

## Design Decisions

### Dependency Injection

The `PathBuilder` is designed to be dependency-injected with minimal coupling:

```python
# Constructor signature
def __init__(self, settings: Any = None) -> None:
    self.settings = settings
    self.logger = logger
```

**Rationale**:
- `settings` parameter allows configuration injection without hard dependencies
- Logger is module-level for simplicity
- No direct dependency on heavy frameworks or global state

### Immutable Context Pattern

`PathContext` is a frozen dataclass:

```python
@dataclass(frozen=True)
class PathContext:
    scanned_file: ScannedFile
    series_has_mixed_resolutions: bool
    target_folder: Path
    media_type: str
    organize_by_resolution: bool
```

**Rationale**:
- Thread-safe
- Prevents accidental mutations
- Clear data flow (input → transformation → output)
- Easier to test and reason about

### Resolution Detection Strategy

Resolution detection follows a priority order:

1. **TMDB Metadata** (highest priority)
   - Most reliable source
   - Already normalized

2. **Filename Patterns**
   - Multiple regex patterns for flexibility
   - Handles common naming conventions

3. **Dimension Patterns**
   - Fallback for files with resolution as "1920x1080"
   - Maps dimensions to standard resolution strings

**Rationale**: This prioritization ensures accuracy while maintaining flexibility for various file naming conventions.

### Separation of Concerns

The `PathBuilder` is split into focused methods:

- `build_path()`: Main orchestration
- `_extract_series_title()`: Title extraction logic
- `_extract_season_number()`: Season detection
- `_build_folder_structure()`: Folder hierarchy construction
- `_extract_resolution()`: Resolution detection
- `_apply_resolution_folder()`: Resolution-based organization
- `sanitize_filename()`: Filename sanitization

**Rationale**:
- Single Responsibility Principle
- Easy to test individual components
- Clear method boundaries
- Reusable logic

## Error Handling Strategy

### Input Validation

`PathContext` validates input in `__post_init__`:

```python
def __post_init__(self) -> None:
    if not self.target_folder:
        raise ValueError("target_folder cannot be empty")
    if not self.media_type:
        raise ValueError("media_type cannot be empty")
```

**Rationale**: Fail fast at the boundary, before any processing begins.

### Fallback Strategies

- **Series Title**: Falls back through multiple extraction methods, ultimately to "Unknown Series"
- **Season Number**: Defaults to 1 if not specified
- **Resolution**: Gracefully handles missing resolution data

**Rationale**: Defensive programming ensures the service never fails catastrophically.

### Error Propagation

Errors from external dependencies (e.g., file system errors) are allowed to propagate:

```python
# No try/except wrapping Path operations
result = series_dir / original_filename
return result
```

**Rationale**:
- `FileOrganizer` (caller) handles file system errors
- PathBuilder focuses on path construction logic
- Clear separation of error handling responsibilities

## Extension Points

### Adding New Resolution Patterns

To add new resolution detection patterns:

1. Add pattern to `PathBuilder.RESOLUTION_PATTERNS`
2. Pattern is automatically used by `_extract_resolution()`

Example:
```python
RESOLUTION_PATTERNS: list[str] = [
    r"\[(\d+p|4K|UHD|SD)\]",
    r"\((\d+p|4K|UHD|SD)\)",
    # Add new pattern here
    r"_(\d+p|4K|UHD|SD)_",  # Matches _1080p_
]
```

### Custom Sanitization Rules

To customize filename sanitization:

1. Modify `PathBuilder.INVALID_FILENAME_CHARS`
2. Or override `sanitize_filename()` in a subclass

### Alternative Folder Structures

To implement different folder organization schemes:

1. Subclass `PathBuilder`
2. Override `_build_folder_structure()`
3. Inject custom PathBuilder into `FileOrganizer`

Example:
```python
class CustomPathBuilder(PathBuilder):
    def _build_folder_structure(
        self, context: PathContext, series_title: str, season_dir: str
    ) -> Path:
        # Custom folder logic
        return context.target_folder / "Custom" / series_title
```

## Testing Strategy

### Unit Testing

Each method can be tested independently:

- `_extract_series_title()`: Test with various metadata configurations
- `_extract_resolution()`: Test with different filename patterns
- `sanitize_filename()`: Test edge cases (empty, special chars, etc.)
- `_map_dimensions_to_resolution()`: Test dimension boundaries

### Integration Testing

Full path construction can be tested with `PathContext`:

```python
context = PathContext(
    scanned_file=mock_file,
    series_has_mixed_resolutions=True,
    target_folder=Path("/media"),
    media_type="TV",
    organize_by_resolution=True,
)
builder = PathBuilder()
result = builder.build_path(context)
assert result == expected_path
```

## Performance Considerations

### Regex Compilation

Resolution patterns are defined as class attributes and compiled once by Python's `re` module (which caches compiled patterns).

### String Operations

Filename sanitization uses simple string operations (replace, strip) rather than complex regex for performance.

### Path Construction

Uses `pathlib.Path` for cross-platform compatibility and performance.

## Future Enhancements

### Potential Improvements

1. **Caching**: Cache sanitized series titles for repeated operations
2. **Validation**: Add path length validation (Windows MAX_PATH)
3. **Localization**: Support for non-ASCII characters in filenames
4. **Templates**: User-defined folder structure templates

### Extensibility

The current design supports these enhancements without major refactoring:

- Dependency injection allows alternative settings sources
- Immutable context pattern supports caching strategies
- Clear method boundaries allow incremental improvements

## Migration Guide

### From FileOrganizer._construct_destination_path()

Old usage:
```python
# Inside FileOrganizer
path = self._construct_destination_path(scanned_file, series_has_mixed)
```

New usage:
```python
# Inside FileOrganizer
from anivault.core.organizer.path_builder import PathBuilder, PathContext

context = PathContext(
    scanned_file=scanned_file,
    series_has_mixed_resolutions=series_has_mixed,
    target_folder=self.target_folder,
    media_type=self.media_type,
    organize_by_resolution=self.organize_by_resolution,
)
path_builder = PathBuilder(settings=self.settings)
path = path_builder.build_path(context)
```

## Conclusion

The `PathBuilder` design prioritizes:

1. **Simplicity**: Clear, focused methods
2. **Testability**: Easy to unit test individual components
3. **Extensibility**: Easy to add new patterns or customize behavior
4. **Maintainability**: Well-documented, follows SOLID principles
5. **Safety**: Immutable data structures, defensive programming

This design makes path construction logic reusable, testable, and maintainable.
