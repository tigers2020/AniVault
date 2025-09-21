-- =====================================================
-- Performance Optimization Index Creation Scripts
-- =====================================================
-- This script creates B-tree indexes on frequently accessed columns
-- to improve query performance for AniVault application.
--
-- Target Columns:
-- 1. anime_metadata.updated_at - Used in incremental sync operations
-- 2. parsed_files.db_updated_at - Used in incremental sync operations
--
-- Note: tmdb_id and file_path already have indexes
-- =====================================================

-- =====================================================
-- 1. Create Index on anime_metadata.updated_at
-- =====================================================
-- Purpose: Optimize incremental sync operations and timestamp-based queries
-- Usage: ORDER BY updated_at, WHERE updated_at >= timestamp
-- Expected Impact: 80-90% improvement in incremental sync performance

CREATE INDEX IF NOT EXISTS idx_anime_metadata_updated_at
ON anime_metadata (updated_at);

-- =====================================================
-- 2. Create Index on parsed_files.db_updated_at
-- =====================================================
-- Purpose: Optimize incremental sync operations and timestamp-based queries
-- Usage: ORDER BY db_updated_at, WHERE db_updated_at >= timestamp
-- Expected Impact: 80-90% improvement in incremental sync performance

CREATE INDEX IF NOT EXISTS idx_parsed_files_db_updated_at
ON parsed_files (db_updated_at);

-- =====================================================
-- 3. Optional: Composite Index for Incremental Sync Pattern
-- =====================================================
-- Purpose: Optimize the specific incremental sync query pattern
-- Usage: ORDER BY updated_at, version LIMIT N
-- Expected Impact: Additional 10-20% improvement for incremental sync

CREATE INDEX IF NOT EXISTS idx_anime_metadata_updated_at_version
ON anime_metadata (updated_at, version);

CREATE INDEX IF NOT EXISTS idx_parsed_files_db_updated_at_version
ON parsed_files (db_updated_at, version);

-- =====================================================
-- Index Verification Queries
-- =====================================================
-- Use these queries to verify that indexes were created successfully

-- Check anime_metadata indexes
SELECT
    name as index_name,
    tbl_name as table_name,
    sql as index_definition
FROM sqlite_master
WHERE type = 'index'
AND tbl_name = 'anime_metadata'
AND name LIKE '%updated_at%'
ORDER BY name;

-- Check parsed_files indexes
SELECT
    name as index_name,
    tbl_name as table_name,
    sql as index_definition
FROM sqlite_master
WHERE type = 'index'
AND tbl_name = 'parsed_files'
AND name LIKE '%db_updated_at%'
ORDER BY name;

-- =====================================================
-- Performance Test Queries
-- =====================================================
-- Use these queries to test the performance improvements

-- Test 1: ORDER BY updated_at (should use index)
EXPLAIN QUERY PLAN
SELECT * FROM anime_metadata
ORDER BY updated_at
LIMIT 10;

-- Test 2: ORDER BY db_updated_at (should use index)
EXPLAIN QUERY PLAN
SELECT * FROM parsed_files
ORDER BY db_updated_at
LIMIT 10;

-- Test 3: Filter by updated_at (should use index)
EXPLAIN QUERY PLAN
SELECT * FROM anime_metadata
WHERE updated_at >= '2025-01-01'
ORDER BY updated_at
LIMIT 10;

-- Test 4: Filter by db_updated_at (should use index)
EXPLAIN QUERY PLAN
SELECT * FROM parsed_files
WHERE db_updated_at >= '2025-01-01'
ORDER BY db_updated_at
LIMIT 10;

-- Test 5: Incremental sync pattern (should use composite index)
EXPLAIN QUERY PLAN
SELECT * FROM anime_metadata
ORDER BY updated_at, version
LIMIT 50;

-- Test 6: Incremental sync pattern for parsed_files (should use composite index)
EXPLAIN QUERY PLAN
SELECT * FROM parsed_files
ORDER BY db_updated_at, version
LIMIT 50;
