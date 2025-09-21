# AniVault Monitoring System Documentation

## Overview

The AniVault monitoring system provides comprehensive observability for cache-DB synchronization operations, system health, and performance metrics. The system consists of multiple components working together to provide real-time monitoring, alerting, and visualization capabilities.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AniVault      │    │   Metrics        │    │   External      │
│   Application   │───▶│   Exporter       │───▶│   Monitoring    │
│                 │    │                  │    │   (Prometheus)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                        │
         ▼                       ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Built-in      │    │   HTTP Metrics   │    │   Grafana       │
│   Dashboard     │    │   Server         │    │   Dashboards    │
│   (PyQt5)       │    │   (Port 8080)    │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Alerting      │
                       │   (Prometheus   │
                       │    Rules)       │
                       └─────────────────┘
```

## Components

### 1. Metrics Collection (`src/core/sync_monitoring.py`)

The `SyncMonitor` class provides comprehensive monitoring for all synchronization operations:

- **Operation Tracking**: Records start/end times, duration, success/failure status
- **Cache Events**: Tracks cache hits and misses
- **Performance Metrics**: Aggregates statistics for all operation types
- **Thread Safety**: All operations are thread-safe for concurrent access

#### Key Features:
- Context manager for automatic operation monitoring
- Detailed logging with configurable verbosity
- Performance statistics aggregation
- Real-time metrics updates

### 2. Metrics Export (`src/core/metrics_exporter.py`)

The `SyncMetricsExporter` class provides Prometheus-compatible metrics:

#### Metric Types:
- **Counters**: Track total operations, affected records, cache events
- **Histograms**: Measure operation durations with configurable buckets
- **Gauges**: Monitor cache size, memory usage, health status
- **Info**: Application metadata and version information

#### Available Metrics:
```prometheus
# Sync Operations
anivault_sync_operations_total{operation_type, status}
anivault_sync_operation_duration_seconds{operation_type}
anivault_sync_affected_records_total{operation_type}

# Cache Performance
anivault_cache_events_total{event_type, operation_type}
anivault_cache_hit_rate
anivault_cache_size
anivault_cache_memory_usage_bytes

# System Health
anivault_database_health_status
anivault_database_connection_errors_total{error_type}
anivault_circuit_breaker_state{breaker_name}
anivault_circuit_breaker_failures_total{breaker_name}

# Consistency & Reconciliation
anivault_consistency_check_duration_seconds{check_type}
anivault_consistency_inconsistencies_total{check_type, severity}
anivault_reconciliation_operations_total{strategy, status}
anivault_reconciliation_duration_seconds{strategy}

# Application Info
anivault_application_info{name, version, component}
```

### 3. HTTP Metrics Server (`src/core/metrics_server.py`)

Lightweight HTTP server that exposes metrics endpoints:

- **Port**: 8080 (configurable)
- **Endpoints**:
  - `/metrics`: Prometheus metrics in text format
  - `/health`: Simple health check endpoint
- **Thread Safety**: Runs in separate thread to avoid blocking main application

### 4. Built-in Dashboard (`src/gui/monitoring_dashboard.py`)

PyQt5-based monitoring dashboard with real-time updates:

#### Dashboard Tabs:
1. **Sync Operations**: Operation counts, success rates, performance breakdown
2. **Cache Metrics**: Hit rates, memory usage, performance indicators
3. **System Health**: Database status, circuit breaker state, server status
4. **Metrics Log**: Raw metrics output and operation logs

#### Features:
- Auto-refresh every 5 seconds
- Color-coded status indicators
- Detailed operation breakdowns
- Real-time performance charts

### 5. External Monitoring Integration

#### Prometheus Configuration (`monitoring/prometheus.yml`)
- Scrapes metrics from AniVault every 10 seconds
- Configurable targets and intervals
- Label management for multi-instance deployments

#### Grafana Dashboard (`monitoring/grafana/dashboards/anivault-dashboard.json`)
- 11 panels covering all key metrics
- Real-time visualization with 5-second refresh
- Color-coded alerts and status indicators
- Historical trend analysis

#### Alerting Rules (`monitoring/anivault_rules.yml`)
- 15+ alert rules covering critical scenarios
- Multi-level severity (warning/critical)
- Comprehensive annotations with runbook URLs
- Configurable thresholds and evaluation periods

## Usage

### Starting the Monitoring System

The monitoring system starts automatically with the AniVault application:

```python
# In main.py
from src.core.metrics_server import metrics_server

# Start metrics server
if metrics_server.start():
    logger.info("Metrics server started successfully")
```

### Accessing Metrics

#### Built-in Dashboard
1. Launch AniVault application
2. Open the monitoring dashboard from the application menu
3. View real-time metrics across all tabs

#### HTTP Endpoints
```bash
# Get metrics in Prometheus format
curl http://localhost:8080/metrics

# Check health status
curl http://localhost:8080/health
```

#### Programmatic Access
```python
from src.core.sync_monitoring import sync_monitor
from src.core.metrics_exporter import metrics_exporter

# Get performance statistics
stats = sync_monitor.get_performance_stats()
print(f"Success rate: {stats.success_rate:.1f}%")

# Get Prometheus metrics
metrics_output = metrics_exporter.generate_metrics()
print(metrics_output)
```

### Monitoring Operations

#### Automatic Monitoring
All synchronization operations are automatically monitored when using the context manager:

```python
from src.core.sync_monitoring import sync_monitor, SyncOperationType

with sync_monitor.monitor_operation(
    SyncOperationType.READ_THROUGH,
    cache_hit=False,
    key="example_key"
) as metrics:
    # Perform operation
    result = perform_sync_operation()

    # Metrics are automatically recorded
    metrics.complete(SyncOperationStatus.SUCCESS, affected_records=1)
```

#### Manual Metrics Recording
```python
# Record cache events
sync_monitor.log_cache_hit("key", SyncOperationType.READ_THROUGH)
sync_monitor.log_cache_miss("key", SyncOperationType.WRITE_THROUGH)

# Record bulk operations
sync_monitor.log_bulk_operation_start(
    SyncOperationType.BULK_INSERT,
    record_count=100
)

# Update system health
sync_monitor.update_database_health(True)
sync_monitor.update_cache_metrics(hit_rate=85.0, size=1000, memory_bytes=512*1024)
```

## Configuration

### Metrics Server Configuration

```python
from src.core.metrics_server import MetricsServer

# Custom configuration
server = MetricsServer(host='0.0.0.0', port=9090)
server.start()
```

### Prometheus Configuration

Edit `monitoring/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'anivault'
    static_configs:
      - targets: ['your-anivault-host:8080']
    scrape_interval: 15s  # Adjust based on needs
    scrape_timeout: 5s
```

### Grafana Dashboard Configuration

1. Import the dashboard from `monitoring/grafana/dashboards/anivault-dashboard.json`
2. Configure the Prometheus data source
3. Adjust refresh intervals and time ranges as needed

### Alerting Configuration

Edit `monitoring/anivault_rules.yml` to customize alert thresholds:

```yaml
- alert: HighSyncFailureRate
  expr: rate(anivault_sync_operations_total{status="failed"}[5m]) / rate(anivault_sync_operations_total[5m]) > 0.05  # 5% threshold
  for: 2m
  labels:
    severity: warning
```

## Performance Considerations

### Metrics Collection Overhead
- **CPU Impact**: < 1% for typical workloads
- **Memory Usage**: ~1-2MB for metrics storage
- **Network**: < 1KB per metrics request

### Optimization Recommendations

1. **Scrape Intervals**: Adjust based on monitoring needs
   - Development: 30-60 seconds
   - Production: 10-15 seconds
   - Critical systems: 5-10 seconds

2. **Retention Policies**: Configure Prometheus retention
   ```bash
   ./prometheus --storage.tsdb.retention.time=30d
   ```

3. **Metrics Filtering**: Disable unnecessary metrics in high-load environments

### Scalability

The monitoring system is designed to handle:
- **Concurrent Operations**: Thread-safe metrics collection
- **High Throughput**: Efficient metrics aggregation
- **Multiple Instances**: Prometheus federation support

## Troubleshooting

### Common Issues

#### Metrics Server Not Starting
```bash
# Check port availability
netstat -tulpn | grep 8080

# Check application logs
tail -f logs/anivault.log | grep -i metrics
```

#### No Metrics in Prometheus
1. Verify AniVault is running
2. Check Prometheus targets: `http://localhost:9090/targets`
3. Verify network connectivity
4. Check firewall settings

#### Dashboard Not Loading
1. Verify PyQt5 installation
2. Check application logs for errors
3. Ensure metrics server is running

#### High Memory Usage
1. Check metrics retention settings
2. Review operation volume
3. Consider reducing scrape frequency
4. Monitor cache size limits

### Debug Mode

Enable detailed logging for troubleshooting:

```python
from src.core.sync_monitoring import sync_monitor

# Enable detailed logging
sync_monitor.enable_detailed_logging = True

# Check recent operations
recent_ops = sync_monitor.get_recent_operations(limit=10)
for op in recent_ops:
    print(f"{op.operation_type.value}: {op.status.value} ({op.duration_ms:.2f}ms)")
```

### Performance Profiling

Monitor system performance:

```python
# Get performance summary
sync_monitor.log_performance_summary()

# Check operation type statistics
for op_type in SyncOperationType:
    stats = sync_monitor.get_operation_type_stats(op_type)
    if stats:
        print(f"{op_type.value}: {stats}")
```

## Security Considerations

### Metrics Endpoint Security
- Currently exposed on localhost only
- For production: implement authentication/authorization
- Use HTTPS for external exposure
- Configure firewall rules

### Alerting Security
- Secure Alertmanager webhook endpoints
- Use encrypted communication channels
- Implement proper authentication
- Regular security audits

### Data Privacy
- Metrics contain operation counts and performance data
- No sensitive user data is exposed
- Consider data retention policies
- Implement access controls

## Best Practices

### Monitoring Strategy
1. **Key Metrics**: Focus on success rates, latency, and error rates
2. **Alert Thresholds**: Set realistic thresholds based on baseline performance
3. **Dashboard Design**: Keep dashboards focused and actionable
4. **Documentation**: Maintain runbooks for all alerts

### Operational Excellence
1. **Regular Reviews**: Weekly review of metrics and alerts
2. **Capacity Planning**: Monitor trends for capacity planning
3. **Incident Response**: Use metrics for incident investigation
4. **Continuous Improvement**: Regular optimization of monitoring setup

### Development Workflow
1. **Local Development**: Use built-in dashboard for development
2. **Testing**: Include monitoring in integration tests
3. **Deployment**: Verify monitoring in staging environments
4. **Production**: Monitor during deployments and rollbacks

## Future Enhancements

### Planned Features
1. **Custom Metrics**: Support for application-specific metrics
2. **Advanced Alerting**: Machine learning-based anomaly detection
3. **Historical Analysis**: Long-term trend analysis and reporting
4. **Multi-Instance Support**: Enhanced support for distributed deployments

### Integration Opportunities
1. **Log Aggregation**: Integration with ELK stack or similar
2. **Distributed Tracing**: OpenTelemetry integration
3. **APM Tools**: Integration with application performance monitoring
4. **Cloud Platforms**: Native cloud monitoring integration

## Support and Maintenance

### Regular Maintenance Tasks
1. **Metrics Cleanup**: Regular cleanup of old metrics data
2. **Alert Tuning**: Adjust alert thresholds based on operational experience
3. **Dashboard Updates**: Keep dashboards aligned with application changes
4. **Documentation Updates**: Maintain current documentation

### Monitoring the Monitoring System
1. **Health Checks**: Regular health checks of monitoring components
2. **Performance Monitoring**: Monitor monitoring system performance
3. **Backup and Recovery**: Backup monitoring configurations
4. **Version Updates**: Keep monitoring tools updated

For additional support, refer to:
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [AniVault Project Documentation](../README.md)
- [Monitoring Setup Guide](../monitoring/README.md)
