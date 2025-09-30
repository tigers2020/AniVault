# AniVault Project Architecture

## Current Architecture

### Core Components (Implemented)
- **BoundedQueue**: Thread-safe bounded queue for pipeline data transfer
- **Statistics**: Base classes for collecting pipeline metrics
- **Encoding Utils**: UTF-8 encoding utilities for international support
- **Logging Config**: Structured logging system

### Pipeline Architecture (In Development)
The project follows a producer-consumer pipeline pattern:

```
DirectoryScanner (Producer) → BoundedQueue → ParserWorkerPool (Consumer) → ResultCollector
```

#### Components:
1. **DirectoryScanner**: Scans directories for anime files
2. **BoundedQueue**: Thread-safe queue for file path transfer
3. **ParserWorkerPool**: Concurrent file processing workers
4. **CacheV1**: JSON-based caching system
5. **ResultCollector**: Collects and stores processed results

### Design Patterns
- **Producer-Consumer**: For file processing pipeline
- **Thread Pool**: For concurrent parsing
- **Observer**: For statistics collection
- **Cache-Aside**: For file result caching
- **Strategy**: For different parsing approaches

### Key Design Principles
- **Thread Safety**: All shared resources are thread-safe
- **Memory Efficiency**: Bounded queues prevent memory overflow
- **Fault Tolerance**: Graceful error handling and recovery
- **Performance**: Concurrent processing for large file sets
- **Extensibility**: Modular design for easy feature addition

### Data Flow
1. **Input**: Directory path with file extensions
2. **Scanning**: Recursive directory traversal
3. **Queuing**: File paths queued for processing
4. **Parsing**: Concurrent file metadata extraction
5. **Caching**: Results stored for future use
6. **Collection**: Processed results aggregated
7. **Output**: Structured metadata and statistics

### Configuration Management
- **Environment Variables**: API keys and settings
- **YAML Config**: Application settings
- **pyproject.toml**: Tool configurations
- **TaskMaster**: Project task management

### Testing Strategy
- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction testing
- **Performance Tests**: Throughput and memory benchmarks
- **Concurrency Tests**: Thread safety validation
