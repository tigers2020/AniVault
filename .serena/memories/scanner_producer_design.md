# Scanner Producer Design

## Current State
- ScanParsePool has integrated bounded queue functionality
- Need to refactor scanner logic into dedicated Scanner class
- Scanner should act as producer, putting files into bounded queue

## Implementation Plan
1. Create new `src/anivault/scanner/producer_scanner.py` module
2. Move producer logic from `ScanParsePool._scan_directory_task()` to new `Scanner` class
3. Scanner class should have `scan(directory, file_queue, extension_filter)` method
4. Refactor ScanParsePool to use new Scanner class
5. Update shutdown signaling to use Scanner for None sentinel values

## Key Requirements
- Scanner acts as producer, putting file paths into bounded queue
- Proper backpressure handling when queue is full
- Statistics tracking for producer operations
- Clean separation of concerns between Scanner and ScanParsePool