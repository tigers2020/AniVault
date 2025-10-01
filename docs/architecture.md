# AniVault Rate Limiting Architecture

This document describes the rate limiting, concurrency control, and state management architecture implemented in AniVault for TMDB API integration.

## Overview

AniVault implements a sophisticated multi-layered approach to API rate limiting and error handling to ensure reliable and efficient interaction with the TMDB API. The system consists of four main components working together:

1. **Token Bucket Rate Limiter** - Controls request rate
2. **Semaphore Manager** - Controls concurrency
3. **State Machine** - Manages operational states
4. **TMDB Client** - Orchestrates all components

## Architecture Components

### 1. Token Bucket Rate Limiter

The `TokenBucketRateLimiter` implements a token bucket algorithm to control the rate of API requests.

**Key Features:**
- Thread-safe token bucket implementation
- Configurable capacity and refill rate (default: 35 tokens, 35 RPS)
- Automatic token refill based on elapsed time
- Non-blocking token acquisition with immediate feedback

**How it works:**
- Tokens are added to the bucket at a constant rate (refill_rate)
- Each API request consumes one token
- If no tokens are available, requests are rejected immediately
- Tokens are refilled continuously based on elapsed time

**Configuration:**
```python
rate_limiter = TokenBucketRateLimiter(
    capacity=35,      # Maximum tokens in bucket
    refill_rate=35.0  # Tokens added per second
)
```

### 2. Semaphore Manager

The `SemaphoreManager` controls the number of concurrent API requests to prevent overwhelming the API server.

**Key Features:**
- Thread-safe semaphore implementation
- Configurable concurrency limit (default: 4 concurrent requests)
- Context manager support for automatic resource management
- Timeout support for acquisition attempts

**How it works:**
- Each API request must acquire a semaphore before proceeding
- Only a limited number of requests can run concurrently
- Semaphores are automatically released when requests complete
- Failed acquisitions timeout after a configurable period

**Configuration:**
```python
semaphore_manager = SemaphoreManager(
    concurrency_limit=4  # Maximum concurrent requests
)
```

### 3. Rate Limiting State Machine

The `RateLimitStateMachine` manages the operational state of the TMDB client based on API responses and error conditions.

**States:**
- **NORMAL** - Normal operation, making API requests
- **THROTTLE** - Rate limited, waiting for retry delay
- **SLEEP_THEN_RESUME** - Temporary pause before resuming
- **CACHE_ONLY** - Circuit breaker activated, no API requests

**State Transitions:**
- `NORMAL → THROTTLE`: On 429 (Too Many Requests) response
- `THROTTLE → NORMAL`: After retry delay expires and successful request
- `NORMAL → CACHE_ONLY`: When error rate exceeds threshold (60% over 5 minutes)
- `CACHE_ONLY → NORMAL`: When error rate drops below threshold

**Circuit Breaker Logic:**
- Monitors error rate over a sliding 5-minute window
- Activates when 429/5xx errors exceed 60% of total requests
- Requires minimum 10 requests for reliable calculation
- Automatically resets when error rate improves

**Configuration:**
```python
state_machine = RateLimitStateMachine(
    error_threshold=60.0,  # Error rate threshold (%)
    time_window=300,       # Monitoring window (seconds)
    max_retry_after=300    # Maximum retry delay (seconds)
)
```

### 4. TMDB Client

The `TMDBClient` orchestrates all components to provide a robust API interface.

**Key Features:**
- Integrated rate limiting and concurrency control
- Automatic retry logic with exponential backoff
- 429 error recovery with Retry-After header support
- Circuit breaker integration
- Comprehensive error handling

**Request Flow:**
1. Check state machine - proceed only if not in CACHE_ONLY state
2. Acquire semaphore for concurrency control
3. Acquire token from rate limiter
4. Make API request
5. Handle response:
   - Success: Update state machine, release resources
   - 429 Error: Parse Retry-After header, update state machine, reset rate limiter
   - Other Errors: Update state machine, apply exponential backoff
6. Release semaphore

## Integration with File Processing Pipeline

The TMDB client integrates with AniVault's file processing pipeline through the `MetadataEnricher` service:

```python
# Initialize services
rate_limiter = TokenBucketRateLimiter(capacity=35, refill_rate=35.0)
semaphore_manager = SemaphoreManager(concurrency_limit=4)
state_machine = RateLimitStateMachine()
tmdb_client = TMDBClient(rate_limiter, semaphore_manager, state_machine)

# Create enricher
enricher = MetadataEnricher(tmdb_client=tmdb_client)

# Enrich parsed file metadata
enriched_metadata = await enricher.enrich_metadata(parsing_result)
```

## Configuration

### Environment Variables

The system can be configured through environment variables:

```bash
# TMDB API Configuration
TMDB_API_KEY=your_api_key_here
TMDB_BASE_URL=https://api.themoviedb.org/3
TMDB_TIMEOUT=30
TMDB_RETRY_ATTEMPTS=3
TMDB_RETRY_DELAY=1.0
TMDB_RATE_LIMIT_DELAY=0.25
TMDB_RATE_LIMIT_RPS=35.0
TMDB_CONCURRENT_REQUESTS=4
```

### Configuration File

Settings can also be configured in `config/settings.yaml`:

```yaml
tmdb:
  api_key: "your_api_key_here"
  base_url: "https://api.themoviedb.org/3"
  timeout: 30
  retry_attempts: 3
  retry_delay: 1.0
  rate_limit_delay: 0.25
  rate_limit_rps: 35.0
  concurrent_requests: 4
```

## Performance Characteristics

### Rate Limiting
- **Target Rate**: 35 requests per second
- **Burst Capacity**: 35 requests (1 second at full rate)
- **Recovery Time**: Immediate (tokens refill continuously)

### Concurrency Control
- **Max Concurrent Requests**: 4
- **Acquisition Timeout**: 30 seconds
- **Resource Management**: Automatic via context managers

### Error Handling
- **429 Recovery**: Respects Retry-After headers (max 5 minutes)
- **Exponential Backoff**: 1s, 2s, 4s, 8s, 16s (max 5 retries)
- **Circuit Breaker**: Activates at 60% error rate over 5 minutes

### Memory Usage
- **Rate Limiter**: ~1KB (minimal state)
- **Semaphore Manager**: ~1KB (minimal state)
- **State Machine**: ~10KB (error tracking over time window)
- **TMDB Client**: ~50KB (API client overhead)

## Monitoring and Statistics

The system provides comprehensive statistics for monitoring:

```python
# Get client statistics
stats = tmdb_client.get_stats()

# Rate limiter stats
print(f"Tokens available: {stats['rate_limiter']['tokens_available']}")
print(f"Capacity: {stats['rate_limiter']['capacity']}")
print(f"Refill rate: {stats['rate_limiter']['refill_rate']}")

# Semaphore stats
print(f"Active requests: {stats['semaphore_manager']['active_requests']}")
print(f"Available slots: {stats['semaphore_manager']['available_slots']}")

# State machine stats
print(f"Current state: {stats['state_machine']['state']}")
print(f"Error rate: {stats['state_machine']['error_rate_percent']:.1f}%")
print(f"Retry delay: {stats['state_machine']['retry_delay']:.1f}s")
```

## Error Scenarios and Recovery

### 1. Rate Limiting (429 Errors)
- **Detection**: HTTP 429 status code
- **Recovery**: Parse Retry-After header, wait specified time
- **Fallback**: Exponential backoff if no Retry-After header
- **State**: Transitions to THROTTLE, then back to NORMAL

### 2. Server Errors (5xx)
- **Detection**: HTTP 5xx status codes
- **Recovery**: Exponential backoff retry
- **Circuit Breaker**: Counts toward error rate threshold
- **State**: May trigger CACHE_ONLY if error rate too high

### 3. Network Timeouts
- **Detection**: Request timeout exceptions
- **Recovery**: Exponential backoff retry
- **Circuit Breaker**: Counts toward error rate threshold
- **State**: May trigger CACHE_ONLY if error rate too high

### 4. API Key Issues
- **Detection**: HTTP 401/403 status codes
- **Recovery**: Immediate failure (no retry)
- **State**: Remains in current state
- **Action**: Requires configuration fix

## Best Practices

### 1. Configuration
- Set rate limits conservatively (start with 30 RPS)
- Monitor error rates and adjust thresholds accordingly
- Use appropriate concurrency limits for your use case

### 2. Error Handling
- Always check enrichment status before using TMDB data
- Implement fallback behavior for failed enrichments
- Monitor circuit breaker state for system health

### 3. Performance
- Use batch processing for multiple files when possible
- Monitor memory usage during large batch operations
- Consider caching successful results to reduce API calls

### 4. Monitoring
- Log state transitions and error rates
- Monitor API quota usage
- Set up alerts for circuit breaker activation

## Troubleshooting

### Common Issues

1. **High Error Rates**
   - Check API key validity
   - Verify network connectivity
   - Review rate limit settings

2. **Circuit Breaker Activation**
   - Check error logs for patterns
   - Verify API endpoint availability
   - Consider reducing concurrency

3. **Slow Performance**
   - Check rate limiter settings
   - Verify semaphore configuration
   - Monitor network latency

4. **Memory Usage**
   - Check for memory leaks in error tracking
   - Monitor batch sizes
   - Consider reducing time window

### Debug Mode

Enable debug logging to see detailed operation:

```python
import logging
logging.getLogger('anivault.services').setLevel(logging.DEBUG)
```

This will show:
- Token acquisition/release
- Semaphore operations
- State transitions
- API request/response details
- Error handling decisions

## Future Enhancements

### Planned Features
1. **Adaptive Rate Limiting** - Adjust rates based on API response times
2. **Request Prioritization** - Priority queues for different request types
3. **Distributed Rate Limiting** - Support for multiple client instances
4. **Advanced Caching** - Intelligent caching with TTL management
5. **Metrics Export** - Prometheus/InfluxDB integration for monitoring

### Configuration Improvements
1. **Dynamic Configuration** - Runtime configuration updates
2. **Profile-Based Settings** - Different configs for different use cases
3. **A/B Testing** - Compare different rate limiting strategies
4. **Auto-Tuning** - Automatic parameter optimization based on performance

This architecture provides a robust foundation for reliable TMDB API integration while maintaining high performance and graceful error handling.
