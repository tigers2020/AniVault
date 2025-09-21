# Database Indexing Analysis - Task 1.1

## Current Database Schema Analysis

### AnimeMetadata Table
- **Primary Key**: `tmdb_id` (Integer) - Already indexed as PK
- **Target Column**: `updated_at` (DateTime) - **NEEDS INDEX**
- **Current Indexes**:
  - `idx_anime_metadata_title` (title)
  - `idx_anime_metadata_korean_title` (korean_title)
  - `idx_anime_metadata_status` (status)
  - `idx_anime_metadata_vote_average` (vote_average)
  - `idx_anime_metadata_first_air_date` (first_air_date)
  - `idx_anime_metadata_version` (version)

### ParsedFile Table
- **Primary Key**: `id` (Integer, autoincrement) - Already indexed as PK
- **Target Columns**:
  - `file_path` (String(1000), unique=True) - **ALREADY HAS INDEX** (`idx_parsed_files_file_path`)
  - `db_updated_at` (DateTime) - **NEEDS INDEX**
- **Current Indexes**:
  - `idx_parsed_files_file_path` (file_path) - Already exists
  - `idx_parsed_files_parsed_title` (parsed_title)
  - `idx_parsed_files_season_episode` (season, episode)
  - `idx_parsed_files_resolution` (resolution)
  - `idx_parsed_files_release_group` (release_group)
  - `idx_parsed_files_year` (year)
  - `idx_parsed_files_is_processed` (is_processed)
  - `idx_parsed_files_metadata_id` (metadata_id)
  - `idx_parsed_files_version` (version)

## Critical Queries Identified

### High-Frequency Queries by tmdb_id:
1. `session.query(AnimeMetadata).filter_by(tmdb_id=anime.tmdb_id).first()` - Used in bulk upsert operations
2. `session.query(AnimeMetadata).filter(AnimeMetadata.tmdb_id.in_(tmdb_ids)).all()` - Bulk operations
3. Cache operations: `f"tmdb:{anime.tmdb_id}"` - Frequent cache key lookups

### High-Frequency Queries by file_path:
1. `session.query(ParsedFile).filter_by(file_path=str(file_path)).first()` - File processing
2. `session.query(ParsedFile).filter(ParsedFile.file_path.in_(file_paths)).all()` - Bulk operations
3. Cache operations: `f"file:{file_path}"` - Frequent cache key lookups

### High-Frequency Queries by updated_at/db_updated_at:
1. Incremental sync operations - Ordering by updated_at for change tracking
2. Consistency validation - Comparing timestamps between cache and DB
3. Bulk update operations - Setting updated_at timestamps

## Performance Bottlenecks Identified

### 1. Missing Indexes
- `anime_metadata.updated_at` - Used in incremental sync and consistency checks
- `parsed_files.db_updated_at` - Used in incremental sync and consistency checks

### 2. Existing Performance Issues
- Bulk operations with `tmdb_id` lookups in loops (N+1 query pattern)
- Frequent file_path lookups during file processing
- Timestamp-based queries for incremental sync without proper indexing

## Next Steps
1. Create baseline performance measurements for these queries
2. Develop index creation scripts for missing indexes
3. Test in development environment
4. Measure performance improvements
5. Deploy to production
