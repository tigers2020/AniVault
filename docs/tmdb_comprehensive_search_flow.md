# TMDB Comprehensive Search Flow

This document describes the new comprehensive TMDB search flow implemented in AniVault, which provides intelligent fallback mechanisms and user interaction for optimal search results.

## Overview

The comprehensive search flow implements the following strategy:

1. **TMDB TV Search** → If no results → **TMDB Movie Search**
2. If no results → **Recursive Word Reduction** (until 1 word left)
3. If still no results → **Manual Search Dialog**
4. If 2+ results → **Manual Selection Dialog**

## Implementation Details

### Core Methods

#### `search_comprehensive(query, language, min_quality)`

The main comprehensive search method that implements the complete flow.

**Parameters:**
- `query`: Search query string
- `language`: Language code for search (defaults to config language)
- `min_quality`: Minimum quality threshold for results (default: 0.3)

**Returns:**
- `tuple[Optional[SearchResult], bool]`: (SearchResult or None, needs_manual_selection)

**Flow:**
1. Try TV search with original query
2. If good results found:
   - If 2+ results → return (results, True) for manual selection
   - If 1 result → return (results, False) for direct use
3. If no TV results → try Movie search with original query
4. If good results found:
   - If 2+ results → return (results, True) for manual selection
   - If 1 result → return (results, False) for direct use
5. If no results → try recursive word reduction:
   - Remove last word from query
   - Try TV search with reduced query
   - Try Movie search with reduced query
   - Repeat until 1 word left or results found
6. If still no results → return (None, False) for manual dialog

#### `search_with_dialog_integration(query, language, min_quality, parent_widget, theme_manager)`

High-level method that automatically handles dialog integration.

**Parameters:**
- `query`: Search query string
- `language`: Language code for search
- `min_quality`: Minimum quality threshold
- `parent_widget`: Parent widget for dialogs
- `theme_manager`: Theme manager for styling

**Returns:**
- `Optional[SearchResult]`: Selected result or None if cancelled

**Flow:**
1. Call `search_comprehensive()`
2. If 2+ results → show selection dialog
3. If no results → show manual search dialog
4. Return selected result

### Search Strategies

The system uses several search strategies defined in `SearchStrategy` enum:

- `ORIGINAL`: Use the original query as-is
- `NORMALIZED`: Clean and normalize the query
- `WORD_REDUCTION`: Remove words from the end
- `PARTIAL_MATCH`: Use partial word matching
- `WORD_REORDER`: Try different word orders
- `LANGUAGE_FALLBACK`: Try with fallback language
- `TYPE_FALLBACK`: Switch between TV and Movie search

### Quality Assessment

The system uses a quality scoring mechanism to determine if results are "good enough":

- **Similarity Score**: Compares query with result titles using SequenceMatcher
- **Count Score**: Based on number of results found
- **Combined Score**: 70% similarity + 30% count
- **Threshold**: Results must meet minimum quality threshold (default: 0.3)

## Usage Examples

### Basic Comprehensive Search

```python
from core.tmdb_client import create_tmdb_client

# Create TMDB client
client = create_tmdb_client()

# Perform comprehensive search
search_result, needs_manual_selection = client.search_comprehensive(
    "Attack on Titan",
    language="ko-KR",
    min_quality=0.3
)

if search_result:
    if needs_manual_selection:
        print(f"Found {len(search_result.results)} results - manual selection needed")
    else:
        print(f"Found 1 good result: {search_result.results[0]['name']}")
else:
    print("No results found - manual search needed")
```

### Dialog-Integrated Search

```python
from core.tmdb_client import create_tmdb_client

# Create TMDB client
client = create_tmdb_client()

# Perform search with automatic dialog handling
search_result = client.search_with_dialog_integration(
    "Attack on Titan",
    language="ko-KR",
    min_quality=0.3,
    parent_widget=self,  # Your parent widget
    theme_manager=theme_manager  # Your theme manager
)

if search_result:
    print(f"Selected: {search_result.results[0]['name']}")
else:
    print("Search cancelled or no results")
```

### Metadata Retrieval with Dialog

```python
from core.tmdb_client import create_tmdb_client

# Create TMDB client
client = create_tmdb_client()

# Search and get metadata with dialog integration
anime_metadata = client.search_and_get_metadata_with_dialog(
    "Attack on Titan",
    language="ko-KR",
    similarity_threshold=0.3,
    parent_widget=self,
    theme_manager=theme_manager
)

if anime_metadata:
    print(f"Found: {anime_metadata.display_title}")
    print(f"Korean Title: {anime_metadata.korean_title}")
    print(f"Overview: {anime_metadata.overview}")
```

## Dialog Integration

### TMDBSelectionDialog

The `TMDBSelectionDialog` class provides a user-friendly interface for:

- **Manual Search**: When no automatic results are found
- **Result Selection**: When multiple results are found
- **Search Refinement**: Users can modify search queries

**Features:**
- Search input with real-time search
- Results table with poster, title, original title, and air date
- Double-click to select
- Theme integration
- Comprehensive error handling

### Dialog States

1. **No Results State**: Shows search input with "no results" message
2. **Multiple Results State**: Shows search results table for selection
3. **Searching State**: Shows "searching..." status with disabled controls
4. **Error State**: Shows error messages with retry options

## Error Handling

The system includes comprehensive error handling:

- **API Errors**: Rate limiting, server errors, network issues
- **Validation Errors**: Invalid queries, missing API keys
- **Dialog Errors**: Import failures, UI errors
- **Search Errors**: Empty results, quality threshold failures

All errors are logged with appropriate detail levels and user-friendly messages.

## Performance Considerations

- **Caching**: Results are cached to avoid duplicate API calls
- **Rate Limiting**: Automatic retry with exponential backoff
- **Quality Thresholds**: Configurable quality thresholds to balance accuracy vs. performance
- **Lazy Loading**: Dialogs are only created when needed

## Configuration

The search behavior can be configured through:

- **Language Settings**: Primary and fallback languages
- **Quality Thresholds**: Minimum quality for "good" results
- **Retry Settings**: Maximum retries and delays
- **Cache Settings**: Cache size and TTL

## Migration from Old Search

The new comprehensive search is backward compatible. Existing code using:

- `search()` method → Use `search_comprehensive()` for better results
- `search_and_get_metadata()` → Use `search_and_get_metadata_with_dialog()` for UI integration
- `search_tv_series_progressive()` → Use `search_comprehensive()` for unified approach

## Best Practices

1. **Use Dialog Integration**: For UI applications, use `search_with_dialog_integration()`
2. **Set Appropriate Quality Thresholds**: Balance between accuracy and performance
3. **Handle Manual Selection**: Always check the `needs_manual_selection` flag
4. **Provide User Feedback**: Show search progress and status messages
5. **Error Handling**: Implement proper error handling for all scenarios

## Example Application

See `examples/tmdb_comprehensive_search_example.py` for a complete working example that demonstrates all features of the comprehensive search flow.
