"""
Statistics - Base class for metrics collection and analysis.

Provides a foundation for collecting, aggregating, and analyzing
performance metrics and operational statistics.
"""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class MetricType(Enum):
    """Types of metrics that can be collected."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    RATE = "rate"


@dataclass
class MetricValue:
    """Container for a metric value with metadata."""

    value: int | float
    timestamp: float
    tags: dict[str, str] = field(default_factory=dict)
    unit: str | None = None


@dataclass
class HistogramData:
    """Histogram data structure."""

    count: int
    sum: float
    min: float
    max: float
    mean: float
    percentiles: dict[float, float] = field(default_factory=dict)


class Statistics(ABC):
    """
    Base class for statistics collection and analysis.

    Provides a foundation for collecting various types of metrics
    including counters, gauges, histograms, and timers.
    """

    def __init__(self, name: str, max_history: int = 1000) -> None:
        """
        Initialize statistics collector.

        Args:
            name: Name of the statistics collector
            max_history: Maximum number of historical values to keep
        """
        self.name = name
        self.max_history = max_history
        self._lock = threading.RLock()
        self._metrics: dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._timers: dict[str, list[float]] = defaultdict(list)
        self._rates: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=60),
        )  # 60 seconds
        self._start_time = time.time()

    def increment_counter(
        self,
        name: str,
        value: int = 1,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Increment a counter metric.

        Args:
            name: Name of the counter
            value: Value to increment by
            tags: Optional tags for the metric
        """
        with self._lock:
            self._counters[name] += value
            self._record_metric(name, MetricType.COUNTER, self._counters[name], tags)

    def set_gauge(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Set a gauge metric value.

        Args:
            name: Name of the gauge
            value: Value to set
            tags: Optional tags for the metric
        """
        with self._lock:
            self._gauges[name] = value
            self._record_metric(name, MetricType.GAUGE, value, tags)

    def record_histogram(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Record a value in a histogram.

        Args:
            name: Name of the histogram
            value: Value to record
            tags: Optional tags for the metric
        """
        with self._lock:
            self._histograms[name].append(value)
            # Keep only recent values
            if len(self._histograms[name]) > self.max_history:
                self._histograms[name] = self._histograms[name][-self.max_history :]
            self._record_metric(name, MetricType.HISTOGRAM, value, tags)

    def record_timer(
        self,
        name: str,
        duration: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Record a timer duration.

        Args:
            name: Name of the timer
            duration: Duration in seconds
            tags: Optional tags for the metric
        """
        with self._lock:
            self._timers[name].append(duration)
            # Keep only recent values
            if len(self._timers[name]) > self.max_history:
                self._timers[name] = self._timers[name][-self.max_history :]
            self._record_metric(name, MetricType.TIMER, duration, tags)

    def record_rate(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Record a rate value.

        Args:
            name: Name of the rate metric
            value: Value to record
            tags: Optional tags for the metric
        """
        with self._lock:
            current_time = time.time()
            self._rates[name].append((current_time, value))
            self._record_metric(name, MetricType.RATE, value, tags)

    def time_function(self, name: str, func: Callable, *args, **kwargs) -> Any:
        """
        Time a function execution and record the duration.

        Args:
            name: Name of the timer
            func: Function to time
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function execution
        """
        start_time = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            duration = time.time() - start_time
            self.record_timer(name, duration)

    def get_counter(self, name: str) -> int:
        """Get the current value of a counter."""
        with self._lock:
            return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> float | None:
        """Get the current value of a gauge."""
        with self._lock:
            return self._gauges.get(name)

    def get_histogram_data(self, name: str) -> HistogramData | None:
        """
        Get histogram statistics for a metric.

        Args:
            name: Name of the histogram

        Returns:
            HistogramData object with statistics, or None if no data
        """
        with self._lock:
            values = self._histograms.get(name, [])
            if not values:
                return None

            return HistogramData(
                count=len(values),
                sum=sum(values),
                min=min(values),
                max=max(values),
                mean=sum(values) / len(values),
                percentiles=self._calculate_percentiles(values),
            )

    def get_timer_data(self, name: str) -> HistogramData | None:
        """
        Get timer statistics for a metric.

        Args:
            name: Name of the timer

        Returns:
            HistogramData object with statistics, or None if no data
        """
        with self._lock:
            values = self._timers.get(name, [])
            if not values:
                return None

            return HistogramData(
                count=len(values),
                sum=sum(values),
                min=min(values),
                max=max(values),
                mean=sum(values) / len(values),
                percentiles=self._calculate_percentiles(values),
            )

    def get_rate(self, name: str, window_seconds: int = 60) -> float | None:
        """
        Get the current rate for a metric.

        Args:
            name: Name of the rate metric
            window_seconds: Time window in seconds

        Returns:
            Rate value, or None if no data
        """
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - window_seconds

            # Filter recent values
            recent_values = [
                (timestamp, value)
                for timestamp, value in self._rates[name]
                if timestamp >= cutoff_time
            ]

            if not recent_values:
                return None

            # Calculate rate (values per second)
            time_span = recent_values[-1][0] - recent_values[0][0]
            if time_span == 0:
                return 0.0

            total_value = sum(value for _, value in recent_values)
            return total_value / time_span

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all current metric values."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    name: self.get_histogram_data(name) for name in self._histograms
                },
                "timers": {name: self.get_timer_data(name) for name in self._timers},
                "rates": {name: self.get_rate(name) for name in self._rates},
            }

    def reset(self) -> None:
        """Reset all metrics to initial state."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timers.clear()
            self._rates.clear()
            self._metrics.clear()
            self._start_time = time.time()

    def get_uptime(self) -> float:
        """Get the uptime in seconds since initialization."""
        return time.time() - self._start_time

    def export_metrics(self) -> dict[str, Any]:
        """
        Export metrics in a standardized format.

        Returns:
            Dictionary containing all metrics in export format
        """
        with self._lock:
            return {
                "name": self.name,
                "uptime": self.get_uptime(),
                "timestamp": time.time(),
                "metrics": self.get_all_metrics(),
            }

    @abstractmethod
    def _record_metric(
        self,
        name: str,
        metric_type: MetricType,
        value: float,
        tags: dict[str, str] | None,
    ) -> None:
        """
        Record a metric value (to be implemented by subclasses).

        Args:
            name: Name of the metric
            metric_type: Type of the metric
            value: Value to record
            tags: Optional tags for the metric
        """

    def _calculate_percentiles(
        self,
        values: list[float],
        percentiles: list[float] | None = None,
    ) -> dict[float, float]:
        """
        Calculate percentiles for a list of values.

        Args:
            values: List of values to calculate percentiles for
            percentiles: List of percentile values to calculate

        Returns:
            Dictionary mapping percentile to value
        """
        if percentiles is None:
            percentiles = [50.0, 90.0, 95.0, 99.0]

        if not values:
            return {}

        sorted_values = sorted(values)
        result = {}

        max_percentile = 100.0
        for percentile in percentiles:
            if percentile == max_percentile:
                result[percentile] = sorted_values[-1]
            else:
                index = (percentile / 100.0) * (len(sorted_values) - 1)
                if index.is_integer():
                    result[percentile] = sorted_values[int(index)]
                else:
                    lower = sorted_values[int(index)]
                    upper = sorted_values[int(index) + 1]
                    result[percentile] = lower + (upper - lower) * (index - int(index))

        return result

    def __repr__(self) -> str:
        """Return a string representation of the statistics collector."""
        return f"Statistics(name='{self.name}', uptime={self.get_uptime():.2f}s)"
