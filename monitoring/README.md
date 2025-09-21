# AniVault Monitoring Setup Guide

This guide explains how to set up comprehensive monitoring for the AniVault application using Prometheus, Grafana, and the built-in monitoring dashboard.

## Overview

AniVault provides multiple monitoring options:

1. **Built-in Dashboard**: PyQt5-based monitoring widget within the application
2. **Prometheus Integration**: Metrics endpoint for external monitoring
3. **Grafana Dashboards**: Pre-configured dashboards for visualization
4. **Alerting**: Prometheus-based alerting rules

## Built-in Monitoring Dashboard

The AniVault application includes a built-in monitoring dashboard that displays real-time metrics.

### Accessing the Dashboard

1. Start the AniVault application
2. The monitoring dashboard will be available as a separate window/tab
3. Metrics are automatically updated every 5 seconds

### Dashboard Features

- **Sync Operations**: Overview of synchronization operations, success rates, and performance
- **Cache Metrics**: Cache hit rates, memory usage, and performance indicators
- **System Health**: Database health, circuit breaker status, and metrics server status
- **Metrics Log**: Raw metrics output and operation logs

## Prometheus Integration

### Metrics Endpoint

AniVault exposes metrics at: `http://localhost:8080/metrics`

### Available Metrics

#### Sync Operations
- `anivault_sync_operations_total`: Total sync operations by type and status
- `anivault_sync_operation_duration_seconds`: Operation duration histogram
- `anivault_sync_affected_records_total`: Total records affected by operations

#### Cache Performance
- `anivault_cache_events_total`: Cache hits and misses
- `anivault_cache_hit_rate`: Current cache hit rate percentage
- `anivault_cache_size`: Current number of cache entries
- `anivault_cache_memory_usage_bytes`: Current cache memory usage

#### System Health
- `anivault_database_health_status`: Database health status (0/1)
- `anivault_database_connection_errors_total`: Database connection errors
- `anivault_circuit_breaker_state`: Circuit breaker state
- `anivault_circuit_breaker_failures_total`: Circuit breaker failures

#### Consistency & Reconciliation
- `anivault_consistency_check_duration_seconds`: Consistency check duration
- `anivault_consistency_inconsistencies_total`: Data inconsistencies found
- `anivault_reconciliation_operations_total`: Reconciliation operations
- `anivault_reconciliation_duration_seconds`: Reconciliation duration

## Setting Up Prometheus

### 1. Install Prometheus

```bash
# Download and extract Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xzf prometheus-2.45.0.linux-amd64.tar.gz
cd prometheus-2.45.0.linux-amd64
```

### 2. Configure Prometheus

Copy the provided `prometheus.yml` to your Prometheus configuration directory:

```bash
cp monitoring/prometheus.yml /path/to/prometheus/
```

### 3. Start Prometheus

```bash
./prometheus --config.file=prometheus.yml --storage.tsdb.path=./data --web.console.libraries=./console_libraries --web.console.templates=./consoles --web.enable-lifecycle
```

Prometheus will be available at: `http://localhost:9090`

## Setting Up Grafana

### 1. Install Grafana

```bash
# Ubuntu/Debian
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
sudo apt-get update
sudo apt-get install grafana

# CentOS/RHEL
sudo yum install grafana
```

### 2. Start Grafana

```bash
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
```

Grafana will be available at: `http://localhost:3000`

### 3. Configure Data Source

1. Login to Grafana (default: admin/admin)
2. Go to Configuration > Data Sources
3. Add Prometheus data source:
   - URL: `http://localhost:9090`
   - Access: Server (default)
   - Save & Test

### 4. Import Dashboard

1. Go to Dashboards > Import
2. Upload the provided `anivault-dashboard.json` file
3. Select the Prometheus data source
4. Import the dashboard

## Alerting Setup

### 1. Configure Alertmanager

Create an `alertmanager.yml` configuration file:

```yaml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@anivault.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
- name: 'web.hook'
  webhook_configs:
  - url: 'http://localhost:5001/'
    send_resolved: true
```

### 2. Start Alertmanager

```bash
./alertmanager --config.file=alertmanager.yml
```

### 3. Configure Prometheus Alerting

Update `prometheus.yml` to include the alerting rules:

```yaml
rule_files:
  - "anivault_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - localhost:9093
```

## Monitoring Best Practices

### 1. Key Metrics to Monitor

- **Sync Operation Success Rate**: Should be > 95%
- **Cache Hit Rate**: Should be > 80%
- **Average Operation Duration**: Should be < 1 second
- **Database Health**: Should always be healthy
- **Circuit Breaker Status**: Should be closed during normal operation

### 2. Alert Thresholds

The provided alerting rules include recommended thresholds:

- **Warning**: Sync failure rate > 10%
- **Critical**: Sync failure rate > 30%
- **Warning**: Cache hit rate < 50%
- **Critical**: Cache hit rate < 20%
- **Warning**: 95th percentile latency > 5 seconds
- **Critical**: 95th percentile latency > 10 seconds

### 3. Dashboard Refresh Rates

- **Built-in Dashboard**: 5 seconds (automatic)
- **Grafana Dashboard**: 5 seconds (configurable)
- **Prometheus Scraping**: 10 seconds

## Troubleshooting

### Metrics Server Not Starting

1. Check if port 8080 is available:
   ```bash
   netstat -tulpn | grep 8080
   ```

2. Check application logs for errors

3. Verify Prometheus client library is installed:
   ```bash
   pip install prometheus-client>=0.19.0
   ```

### No Metrics in Prometheus

1. Verify AniVault is running and metrics server is started
2. Check Prometheus targets: `http://localhost:9090/targets`
3. Verify network connectivity between Prometheus and AniVault

### Dashboard Not Loading

1. Check Grafana data source configuration
2. Verify Prometheus is running and accessible
3. Check Grafana logs for errors

## Performance Considerations

### Metrics Collection Overhead

- Built-in metrics collection has minimal overhead (< 1% CPU)
- Prometheus scraping interval can be adjusted based on needs
- Consider reducing scrape frequency in high-load environments

### Storage Requirements

- Prometheus storage grows with metrics retention
- Consider setting retention policies:
  ```bash
  ./prometheus --storage.tsdb.retention.time=30d
  ```

### Network Bandwidth

- Metrics endpoint typically serves < 1KB per request
- Adjust scraping interval if bandwidth is limited

## Security Considerations

### Metrics Endpoint Security

The metrics endpoint is currently exposed on localhost only. For production deployments:

1. Consider authentication/authorization
2. Use HTTPS if exposing externally
3. Implement network-level security (firewall, VPN)

### Alerting Security

1. Secure Alertmanager webhook endpoints
2. Use encrypted communication channels
3. Implement proper authentication for alert receivers

## Advanced Configuration

### Custom Metrics

You can add custom metrics by extending the `SyncMetricsExporter` class:

```python
from prometheus_client import Counter

# Add custom metric
custom_operations = Counter('anivault_custom_operations_total', 'Custom operations')

# Record metric
custom_operations.inc()
```

### Multiple Instances

For monitoring multiple AniVault instances:

1. Configure different ports for each instance
2. Update Prometheus targets configuration
3. Use instance labels to distinguish metrics

### High Availability

For production deployments:

1. Set up Prometheus federation
2. Configure Grafana with multiple data sources
3. Implement alerting redundancy
4. Use external storage backends (e.g., Thanos, Cortex)

## Support

For monitoring-related issues:

1. Check application logs
2. Verify Prometheus/Grafana configuration
3. Review alerting rule syntax
4. Consult the runbook URLs in alert annotations

For additional help, refer to:
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [AniVault Monitoring Documentation](https://docs.anivault.com/monitoring)
