# AniVault v3 CLI Development Tag Order

## Overview
This document outlines the priority-based development tag structure for AniVault v3 CLI, aligned with the 36-week development plan and Definition of Done requirements. Each tag represents a specific development phase with clear deliverables and dependencies.

## Tag Structure Summary

| Priority | Tag Name | Phase | Weeks | Focus Area |
|----------|----------|-------|-------|------------|
| 1 | `1-foundation-setup` | Phase 1 | W1-W2 | Project foundation, quality gates, library compatibility |
| 2 | `2-single-exe-poc` | Phase 1 | W3-W4 | Single executable POC, PyInstaller validation |
| 3 | `3-scan-parse-pipeline` | Phase 1 | W5-W8 | File scanning, parsing, threading, memory optimization |
| 4 | `4-tmdb-rate-limiting` | Phase 1 | W9-W10 | TMDB client, rate limiting state machine |
| 5 | `5-json-cache-system` | Phase 1 | W11-W12 | JSON cache system, schema versioning |
| 6 | `6-cli-commands` | Phase 2 | W15-W16 | Complete CLI command implementation |
| 7 | `7-organize-safety` | Phase 2 | W13-W14 | File organization, dry-run safety, rollback |
| 8 | `8-windows-compatibility` | Phase 2 | W19-W20 | Windows-specific features, edge cases |
| 9 | `9-performance-optimization` | Phase 2 | W21-W22 | Performance tuning, memory management |
| 10 | `10-testing-quality` | Phase 2 | W23-W24 | Comprehensive testing, integration |
| 11 | `11-security-config` | Phase 2 | W17-W18 | Security features, API key encryption |
| 12 | `12-logging-monitoring` | Phase 3 | W25-W28 | UTF-8 logging, monitoring, observability |
| 13 | `13-packaging-deployment` | Phase 3 | W35-W36 | Final packaging, SBOM, release |
| 14 | `14-documentation` | Phase 3 | W31-W32 | User docs, API docs, tutorials |

---

## Phase 1: Foundation (W1-W12)
*Tags 1-5: Core infrastructure and basic functionality*

### 1. `1-foundation-setup` (W1-W2)
**Priority: CRITICAL** - Project foundation and quality gates

**Key Deliverables:**
- [ ] `pyproject.toml` with core dependencies (Click, tmdbv3api, anitopy, rich, cryptography)
- [ ] `src/` directory skeleton with proper module structure
- [ ] Pre-commit hooks (Ruff/Black/Pyright), pytest base setup
- [ ] UTF-8 enforcement across all I/O operations
- [ ] Logger rotation template implementation
- [ ] **Critical library compatibility validation:**
  - [ ] anitopy C extension + PyInstaller compatibility (HIGHEST PRIORITY)
  - [ ] cryptography native libraries + PyInstaller compatibility
  - [ ] tmdbv3api detailed verification:
    - [ ] Actual rate limiting handling verification
    - [ ] 429 error Retry-After header processing tests
    - [ ] Long-running memory usage pattern verification
    - [ ] Network timeout handling verification
  - [ ] Windows 7/8/10/11 exe execution testing
  - [ ] SSD vs HDD performance difference measurement
  - [ ] TMDB API key issuance process verification

**DoD Criteria:**
- [ ] `pytest` passes, log file creation/rotation demonstrated
- [ ] All library compatibility verification completed
- [ ] Memory profiling baseline established (100k+ files, 500MB limit)
- [ ] Performance baseline established (SSD vs HDD differences)

### 2. `2-single-exe-poc` (W3-W4)
**Priority: CRITICAL** - Single executable proof of concept

**Key Deliverables:**
- [ ] PyInstaller `--onefile --console` POC implementation
- [ ] Nuitka fallback option preparation
- [ ] Clean VM execution testing
- [ ] Early risk factor validation
- [ ] `anivault-mini.exe` execution success
- [ ] TMDB API actual rate limit verification
- [ ] Windows various version testing

**DoD Criteria:**
- [ ] `anivault-mini.exe` runs successfully on clean Windows 10/11
- [ ] TMDB API rate limit verification completed
- [ ] Windows version compatibility confirmed
- [ ] All critical dependencies bundled correctly

### 3. `3-scan-parse-pipeline` (W5-W8)
**Priority: HIGH** - Core file processing pipeline

**Key Deliverables:**
- [ ] File scanning pipeline with threading (ScanParsePool)
- [ ] Bounded queues with backpressure handling
- [ ] Progress indicators and real-time statistics
- [ ] Extension whitelist filtering
- [ ] `cache/search/*.json` schema v1 implementation
- [ ] **Memory profiling and optimization:**
  - [ ] 100k+ files with 500MB limit validation
  - [ ] Generator/streaming pattern verification
  - [ ] Memory usage profiling for large directories
- [ ] anitopy + fallback parser implementation
- [ ] Hypothesis 1k case fuzzing without crashes
- [ ] Labeled sample dataset preparation for matching accuracy

**DoD Criteria:**
- [ ] Scan P95 metrics achieved
- [ ] Cache hit/miss counters implemented
- [ ] Memory usage verification completed
- [ ] Parsing failure rate ≤3%
- [ ] Matching accuracy evaluation sample dataset completed

### 4. `4-tmdb-rate-limiting` (W9-W10)
**Priority: HIGH** - TMDB API integration with rate limiting

**Key Deliverables:**
- [ ] **Token bucket implementation:**
  - [ ] Default 35 rps (TMDB ceiling ~50 rps safety margin)
  - [ ] Semaphore concurrency control (default 4)
  - [ ] Multi-process safety considerations
- [ ] **Rate limiting state machine:**
  - [ ] States: Normal ↔ Throttle ↔ Sleep ↔ HalfOpen ↔ CacheOnly
  - [ ] 429→Throttle transition with Retry-After priority
  - [ ] Sliding window error ratio calculation
  - [ ] Circuit breaker with hysteresis (flapping prevention)
- [ ] **Retry-After handling:**
  - [ ] Seconds and HTTP-date format support
  - [ ] Clock skew correction (negative/past times → 1s minimum)
  - [ ] Full Jitter backoff strategy
- [ ] **Error classification:**
  - [ ] Backoff targets: 429, 5xx, ConnectTimeout, ReadTimeout, DNS/ConnectionError
  - [ ] Non-backoff targets: 401/403/404/422 (client responsibility)

**DoD Criteria:**
- [ ] 429 scenario automatic recovery demonstrated
- [ ] State machine transitions working correctly
- [ ] Retry-After header parsing (seconds/HTTP-date)
- [ ] Exponential backoff logic verified
- [ ] Multi-process environment stability confirmed

### 5. `5-json-cache-system` (W11-W12)
**Priority: HIGH** - JSON cache system with versioning

**Key Deliverables:**
- [ ] **JSON cache schema v2:**
  - [ ] `cache/objects/{tmdb_id}.json` structure
  - [ ] `cache/search/{qhash}.json` structure
  - [ ] Schema versioning with migration support
  - [ ] TTL and LRU simultaneous application
- [ ] **Query normalization:**
  - [ ] `q_norm` algorithm (lowercase + basic cleanup + year hint)
  - [ ] Language and year hint processing
  - [ ] Cache TTL and version management
- [ ] **Cache corruption recovery:**
  - [ ] Automatic quarantine for corrupted files
  - [ ] Schema migration with backup
  - [ ] Disk space limits with LRU+TTL priority deletion
- [ ] **Index file implementation:**
  - [ ] `cache/index.jsonl` for query tracking
  - [ ] Hit/miss counters and last access tracking

**DoD Criteria:**
- [ ] @1 ≥90% / @3 ≥96% matching accuracy achieved
- [ ] MVP demo (scan → match → organize basic flow) completed
- [ ] Cache hit rate ≥90% on second run
- [ ] Schema migration working correctly
- [ ] Corruption recovery tested and verified

---

## Phase 2: Core Features (W13-W24)
*Tags 6-11: Complete feature implementation and optimization*

### 6. `6-cli-commands` (W15-W16)
**Priority: HIGH** - Complete CLI command implementation

**Key Deliverables:**
- [ ] **Core commands implementation:**
  - [ ] `run`: Complete scan→parse→match→organize workflow
  - [ ] `scan`: File enumeration with filters and concurrency
  - [ ] `match`: Cache-first TMDB search and detail retrieval
  - [ ] `organize`: Naming schema application (default dry-run)
  - [ ] `cache`: Query/delete/warmup/hit rate statistics
  - [ ] `settings`: TMDB key configuration and parameter management
  - [ ] `status`: Last operation snapshot and metrics
- [ ] **Common options standardization:**
  - [ ] `--lang`, `--max-workers`, `--tmdb-concurrency`, `--rate`
  - [ ] `--dry-run`, `--resume`, `--log-level`, `--no-color`, `--json`
- [ ] **Machine-readable output:**
  - [ ] NDJSON format for structured logging
  - [ ] Real-time progress indicators
  - [ ] Statistics and metrics output

**DoD Criteria:**
- [ ] `run` command completes E2E in one line
- [ ] Progress bars and statistics update correctly
- [ ] All commands implement common options consistently
- [ ] JSON output format validated against schema

### 7. `7-organize-safety` (W13-W14)
**Priority: HIGH** - File organization with safety features

**Key Deliverables:**
- [ ] **Naming schema v1:**
  - [ ] Pattern: `{title_ascii_or_native} ({year}) S{season:02d}{episode_token}.{ext}`
  - [ ] Multi-episode: `E{ep_start:02d}-E{ep_end:02d}`
  - [ ] Special episodes: `Season 00` fixed
  - [ ] Multi-language processing: `--lang` → TMDB translations → English fallback
- [ ] **Conflict resolution rules:**
  - [ ] File collision detection and handling
  - [ ] User confirmation for overwrites
  - [ ] Skip options for problematic files
- [ ] **Rollback system:**
  - [ ] Complete rollback logs for all file operations
  - [ ] Path before/after, timestamp, hash tracking
  - [ ] Partial failure recovery to last success point
  - [ ] Rollback script generation and validation
- [ ] **Safety defaults:**
  - [ ] Default dry-run mode (no actual changes)
  - [ ] `--apply` flag required for real changes
  - [ ] Plan file generation for user review

**DoD Criteria:**
- [ ] Dry-run shows 0 actual changes
- [ ] Rollback script generation and verification
- [ ] File collision handling tested
- [ ] Multi-language naming working correctly

### 8. `8-windows-compatibility` (W19-W20)
**Priority: MEDIUM** - Windows-specific features and edge cases

**Key Deliverables:**
- [ ] **Long Path handling:**
  - [ ] Automatic `\\?\` prefix for paths >260 characters
  - [ ] UNC/network drive detection and warnings
  - [ ] Performance impact measurement and reporting
- [ ] **Reserved names and forbidden characters:**
  - [ ] CON/PRN/AUX/NUL handling with substitution
  - [ ] `< > : " | ? *` character replacement rules
  - [ ] Hash suffix for collision avoidance
- [ ] **Network and connectivity issues:**
  - [ ] Unstable Wi-Fi environment retry logic
  - [ ] Windows Defender real-time protection interaction
  - [ ] Very long filename (260 char limit) handling
- [ ] **UAC and permissions:**
  - [ ] No administrator privileges required
  - [ ] Permission error handling and reporting
  - [ ] Skip options for inaccessible files

**DoD Criteria:**
- [ ] Three modes (Online/Throttle/CacheOnly) E2E working
- [ ] Real usage environment testing passed
- [ ] Long path handling verified
- [ ] Network drive compatibility confirmed
- [ ] Windows Defender interaction tested

### 9. `9-performance-optimization` (W21-W22)
**Priority: MEDIUM** - Performance tuning and memory management

**Key Deliverables:**
- [ ] **Throughput optimization:**
  - [ ] Target: 120k paths/min P95 (minimum: 60k paths/min P95)
  - [ ] Worker and queue tuning
  - [ ] I/O streaming optimization
  - [ ] Cache warmup strategies
- [ ] **Memory management:**
  - [ ] Target: ≤500MB for 300k files (minimum: ≤600MB)
  - [ ] Large directory memory profiling
  - [ ] Generator/streaming pattern optimization
  - [ ] Memory leak detection and prevention
- [ ] **Cache optimization:**
  - [ ] Cache hit rate ≥90% optimization
  - [ ] LRU + TTL simultaneous application
  - [ ] Disk space management with size limits
- [ ] **Performance monitoring:**
  - [ ] Real-time metrics collection
  - [ ] Performance regression detection
  - [ ] Bottleneck identification and resolution

**DoD Criteria:**
- [ ] Cache hit rate ≥90% achieved
- [ ] Throughput targets met
- [ ] Memory usage within limits for 100k+ files
- [ ] Performance benchmarks documented

### 10. `10-testing-quality` (W23-W24)
**Priority: HIGH** - Comprehensive testing and quality assurance

**Key Deliverables:**
- [ ] **Unit testing:**
  - [ ] 100% coverage for core business logic
  - [ ] pytest with mocking for external dependencies
  - [ ] Boundary value and exception case testing
- [ ] **Integration testing:**
  - [ ] Component interaction testing
  - [ ] TMDB API integration with 429 scenarios
  - [ ] Cache system integration testing
- [ ] **E2E testing:**
  - [ ] Complete workflow validation
  - [ ] Click command testing
  - [ ] JSON output format validation
  - [ ] Error code response testing
- [ ] **Stress testing:**
  - [ ] File name fuzzing (emojis, Unicode, RTL, NFC/NFD)
  - [ ] FS error injection (permission denied, locks, disk full)
  - [ ] Cache corruption/migration testing
  - [ ] Long-running stress tests (>3h) with memory leak detection
- [ ] **Performance testing:**
  - [ ] Benchmark scripts execution
  - [ ] Throughput and memory usage validation
  - [ ] Token bucket accuracy verification
  - [ ] TMDB API test scenarios

**DoD Criteria:**
- [ ] All tests pass with ≥70% coverage
- [ ] E2E test suite completed
- [ ] Performance benchmarks met
- [ ] Stress testing without crashes
- [ ] Memory leak detection working

### 11. `11-security-config` (W17-W18)
**Priority: MEDIUM** - Security features and configuration management

**Key Deliverables:**
- [ ] **API key encryption:**
  - [ ] Fernet symmetric encryption with PIN
  - [ ] Cross-platform key storage
  - [ ] Key rotation and migration support
- [ ] **Configuration management:**
  - [ ] `anivault.toml` configuration file structure
  - [ ] Environment variable priority (ENV → exe_dir → user_home)
  - [ ] Configuration validation and error handling
- [ ] **Security scanning:**
  - [ ] gitleaks/trufflehog integration
  - [ ] pip-audit for vulnerability scanning
  - [ ] License compliance tracking
  - [ ] SBOM generation with CycloneDX
- [ ] **Sensitive information handling:**
  - [ ] TMDB key masking in logs
  - [ ] User home path prefix masking
  - [ ] Secure configuration storage

**DoD Criteria:**
- [ ] Configuration save/decrypt E2E working
- [ ] `anivault.toml` example documentation completed
- [ ] Security scanning integrated into CI
- [ ] Sensitive information properly masked

---

## Phase 3: Stabilization & Release (W25-W36)
*Tags 12-14: Polish, documentation, and release preparation*

### 12. `12-logging-monitoring` (W25-W28)
**Priority: MEDIUM** - UTF-8 logging and monitoring system

**Key Deliverables:**
- [ ] **UTF-8 logging system:**
  - [ ] Global UTF-8 encoding enforcement
  - [ ] File rotation with TimedRotatingFileHandler
  - [ ] Log level separation (app.log, network.log, pipeline.log)
  - [ ] Size limits with automatic cleanup
- [ ] **Structured logging:**
  - [ ] NDJSON format for machine-readable output
  - [ ] Standardized log keys and values
  - [ ] UTC ISO8601 timestamp format
  - [ ] Component-based logging (ratelimiter, cache, pipeline)
- [ ] **Monitoring and metrics:**
  - [ ] Real-time performance metrics
  - [ ] Cache hit/miss statistics
  - [ ] Error rate monitoring
  - [ ] Memory usage tracking
- [ ] **Log security:**
  - [ ] Sensitive information masking
  - [ ] API key and path sanitization
  - [ ] Secure log file permissions

**DoD Criteria:**
- [ ] UTF-8 logging working across all components
- [ ] Log rotation and cleanup working correctly
- [ ] NDJSON output format validated
- [ ] Sensitive information properly masked
- [ ] Monitoring metrics collection working

### 13. `13-packaging-deployment` (W35-W36)
**Priority: HIGH** - Final packaging and release preparation

**Key Deliverables:**
- [ ] **Single executable packaging:**
  - [ ] PyInstaller `--onefile --console` build success
  - [ ] Nuitka fallback option ready
  - [ ] Clean Windows 10/11 VM execution verified
  - [ ] Native module bundling validation (anitopy, cryptography)
- [ ] **Release artifacts:**
  - [ ] `anivault.exe` single executable
  - [ ] `LICENSES/` third-party license files
  - [ ] `schemas/` JSON schema files
  - [ ] `docs/` documentation
  - [ ] `CHANGELOG.md` release notes
  - [ ] `SBOM.json` software bill of materials
  - [ ] `SHA256SUMS` file integrity verification
- [ ] **Security and compliance:**
  - [ ] Code signing (optional)
  - [ ] SmartScreen/AV whitelist guidance
  - [ ] Third-party license compliance
  - [ ] Vulnerability scanning results
- [ ] **Deployment verification:**
  - [ ] Clean Windows installation testing
  - [ ] No external dependencies required
  - [ ] Performance benchmarks on target hardware
  - [ ] User acceptance testing

**DoD Criteria:**
- [ ] v1.0 tag created
- [ ] Clean Windows exe execution confirmed
- [ ] All release artifacts generated
- [ ] Security scanning completed
- [ ] Official release ready

### 14. `14-documentation` (W31-W32)
**Priority: MEDIUM** - Complete documentation and tutorials

**Key Deliverables:**
- [ ] **User documentation:**
  - [ ] User manual with step-by-step guides
  - [ ] Command reference with examples
  - [ ] Configuration guide
  - [ ] Troubleshooting section
- [ ] **API documentation:**
  - [ ] Internal API documentation
  - [ ] JSON schema documentation
  - [ ] Error code reference
  - [ ] Configuration file schema
- [ ] **Developer documentation:**
  - [ ] Architecture overview
  - [ ] Development setup guide
  - [ ] Contributing guidelines
  - [ ] Testing procedures
- [ ] **Tutorials and examples:**
  - [ ] Getting started tutorial
  - [ ] Advanced usage examples
  - [ ] Performance tuning guide
  - [ ] Windows-specific setup guide

**DoD Criteria:**
- [ ] Complete documentation suite
- [ ] User guide completed
- [ ] API documentation up to date
- [ ] Tutorials tested and verified
- [ ] Developer guide comprehensive

---

## Development Workflow

### Tag Switching
```bash
# Switch to specific tag
task-master use-tag 1-foundation-setup

# List all available tags
task-master tags

# Show current tag status
task-master status
```

### Task Management
```bash
# Get tasks for current tag
task-master list

# Get next task to work on
task-master next

# Show specific task details
task-master show <task-id>

# Update task status
task-master set-status --id=<task-id> --status=done
```

### Quality Gates
Each tag must pass specific quality gates before proceeding to the next:

1. **Code Quality**: Ruff, mypy, pytest with ≥70% coverage
2. **Performance**: Benchmarks meet minimum requirements
3. **Security**: Vulnerability scanning passes
4. **Documentation**: DoD criteria met
5. **Testing**: All test suites pass

### Dependencies
- Tags 1-5 must be completed in sequence (Phase 1)
- Tags 6-11 can be developed in parallel after Phase 1 completion
- Tags 12-14 require Phase 2 completion
- Each tag builds upon previous tags' deliverables

---

## Success Criteria

### Phase 1 Completion (Tags 1-5)
- [ ] Single executable runs on clean Windows 10/11
- [ ] All critical library compatibility verified
- [ ] Basic scan→parse→match→organize flow working
- [ ] Performance targets met (60k+ paths/min, ≤600MB memory)
- [ ] Rate limiting state machine operational

### Phase 2 Completion (Tags 6-11)
- [ ] All CLI commands implemented and tested
- [ ] File organization with safety features working
- [ ] Windows compatibility issues resolved
- [ ] Performance optimization targets achieved
- [ ] Comprehensive testing suite passing
- [ ] Security features implemented

### Phase 3 Completion (Tags 12-14)
- [ ] Complete logging and monitoring system
- [ ] Final packaging and deployment ready
- [ ] Comprehensive documentation completed
- [ ] User acceptance testing passed
- [ ] Official v1.0 release ready

---

## Risk Mitigation

### High-Risk Areas
1. **Library Compatibility** (Tag 1): anitopy C extension, cryptography native libs
2. **Single Executable** (Tag 2): PyInstaller bundling complexity
3. **Rate Limiting** (Tag 4): TMDB API policy changes, 429 handling
4. **Windows Compatibility** (Tag 8): Long paths, reserved names, network drives
5. **Performance** (Tag 9): Memory usage, throughput targets

### Mitigation Strategies
- Early validation of critical components
- Fallback options for high-risk areas
- Continuous performance monitoring
- User testing and feedback integration
- Incremental delivery with rollback options

---

**Last Updated**: 2025-01-27  
**Version**: 1.0  
**Status**: Active Development  
**Next Review**: Weekly during development
