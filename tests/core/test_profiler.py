"""
Tests for the profiler module.
"""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from anivault.core.profiler import (
    Profiler,
    MemorySnapshot,
    ProfilingReport
)
from anivault.core.statistics import StatisticsCollector, PerformanceMetrics


class TestMemorySnapshot:
    """Test MemorySnapshot dataclass."""
    
    def test_memory_snapshot_creation(self):
        """Test creating a MemorySnapshot."""
        snapshot = MemorySnapshot(
            timestamp="2023-01-01T00:00:00Z",
            current_memory_mb=100.5,
            peak_memory_mb=150.0,
            memory_blocks=1000,
            context="test"
        )
        
        assert snapshot.timestamp == "2023-01-01T00:00:00Z"
        assert snapshot.current_memory_mb == 100.5
        assert snapshot.peak_memory_mb == 150.0
        assert snapshot.memory_blocks == 1000
        assert snapshot.context == "test"


class TestProfilingReport:
    """Test ProfilingReport dataclass."""
    
    def test_profiling_report_creation(self):
        """Test creating a ProfilingReport."""
        metrics = PerformanceMetrics()
        report = ProfilingReport(
            session_id="test_session",
            start_time="2023-01-01T00:00:00Z",
            end_time="2023-01-01T00:01:00Z",
            duration_seconds=60.0,
            memory_snapshots=[],
            performance_metrics=metrics,
            system_info={"platform": "test"},
            recommendations=["test recommendation"]
        )
        
        assert report.session_id == "test_session"
        assert report.duration_seconds == 60.0
        assert len(report.recommendations) == 1


class TestProfiler:
    """Test Profiler class."""
    
    @pytest.fixture
    def profiler(self):
        """Create a Profiler instance for testing."""
        return Profiler(StatisticsCollector())
    
    def test_initialization(self, profiler):
        """Test Profiler initialization."""
        assert profiler.session_id.startswith("profiler_")
        assert profiler.start_time is None
        assert profiler.end_time is None
        assert len(profiler.memory_snapshots) == 0
        assert profiler.tracemalloc_started is False
    
    def test_start_profiling(self, profiler):
        """Test starting profiling session."""
        profiler.start_profiling()
        
        assert profiler.start_time is not None
        assert profiler.tracemalloc_started is True
    
    def test_stop_profiling(self, profiler):
        """Test stopping profiling session."""
        profiler.start_profiling()
        profiler.stop_profiling()
        
        assert profiler.end_time is not None
        assert profiler.tracemalloc_started is False
    
    def test_take_memory_snapshot_with_tracing(self, profiler):
        """Test taking memory snapshot with tracing enabled."""
        profiler.start_profiling()
        snapshot = profiler.take_memory_snapshot("test_context")
        
        assert snapshot.context == "test_context"
        assert snapshot.current_memory_mb >= 0
        assert snapshot.peak_memory_mb >= 0
        assert len(profiler.memory_snapshots) == 1
        
        profiler.stop_profiling()
    
    def test_take_memory_snapshot_without_tracing(self, profiler):
        """Test taking memory snapshot without tracing enabled."""
        snapshot = profiler.take_memory_snapshot("test_context")
        
        assert snapshot.context == "test_context"
        assert snapshot.current_memory_mb == 0.0
        assert snapshot.peak_memory_mb == 0.0
        assert snapshot.memory_blocks == 0
    
    def test_profile_section_context_manager(self, profiler):
        """Test profile_section context manager."""
        profiler.start_profiling()
        
        with profiler.profile_section("test_section"):
            time.sleep(0.01)  # Small delay to ensure timing works
        
        # Should have taken 2 snapshots (start and end)
        assert len(profiler.memory_snapshots) == 2
        assert profiler.memory_snapshots[0].context == "start_test_section"
        assert profiler.memory_snapshots[1].context == "end_test_section"
        
        profiler.stop_profiling()
    
    def test_get_system_info(self, profiler):
        """Test getting system information."""
        system_info = profiler.get_system_info()
        
        assert "platform" in system_info
        assert "python_version" in system_info
        assert "cpu_count" in system_info
    
    def test_generate_recommendations_low_cache_hit_ratio(self, profiler):
        """Test generating recommendations for low cache hit ratio."""
        # Set up low cache hit ratio
        profiler.statistics.metrics.cache_hits = 10
        profiler.statistics.metrics.cache_misses = 90
        
        recommendations = profiler.generate_recommendations()
        
        assert len(recommendations) > 0
        assert any("cache hit ratio" in rec.lower() for rec in recommendations)
    
    def test_generate_recommendations_high_api_errors(self, profiler):
        """Test generating recommendations for high API errors."""
        # Set up high API error rate
        profiler.statistics.metrics.api_calls = 10
        profiler.statistics.metrics.api_errors = 5
        
        recommendations = profiler.generate_recommendations()
        
        assert len(recommendations) > 0
        assert any("api error" in rec.lower() for rec in recommendations)
    
    def test_generate_recommendations_high_memory_usage(self, profiler):
        """Test generating recommendations for high memory usage."""
        # Set up high memory usage
        profiler.memory_snapshots = [
            MemorySnapshot(
                timestamp="2023-01-01T00:00:00Z",
                current_memory_mb=1500.0,
                peak_memory_mb=1500.0,
                memory_blocks=1000,
                context="test"
            )
        ]
        
        recommendations = profiler.generate_recommendations()
        
        assert len(recommendations) > 0
        assert any("memory usage" in rec.lower() for rec in recommendations)
    
    def test_generate_report_without_starting(self, profiler):
        """Test generating report without starting profiling."""
        with pytest.raises(ValueError, match="Profiling not started"):
            profiler.generate_report()
    
    def test_generate_report_success(self, profiler):
        """Test generating report successfully."""
        profiler.start_profiling()
        profiler.take_memory_snapshot("test")
        profiler.stop_profiling()
        
        report = profiler.generate_report()
        
        assert report.session_id == profiler.session_id
        assert report.start_time is not None
        assert report.end_time is not None
        assert report.duration_seconds > 0
        assert len(report.memory_snapshots) == 1
        assert len(report.recommendations) >= 0
    
    def test_save_report(self, profiler, tmp_path):
        """Test saving report to file."""
        profiler.start_profiling()
        profiler.take_memory_snapshot("test")
        profiler.stop_profiling()
        
        report = profiler.generate_report()
        output_path = tmp_path / "report.json"
        
        profiler.save_report(report, output_path)
        
        assert output_path.exists()
        
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data["session_id"] == report.session_id
        assert "memory_snapshots" in data
        assert "performance_metrics" in data
    
    def test_print_summary(self, profiler, capsys):
        """Test printing report summary."""
        profiler.start_profiling()
        profiler.take_memory_snapshot("test")
        profiler.stop_profiling()
        
        report = profiler.generate_report()
        profiler.print_summary(report)
        
        captured = capsys.readouterr()
        assert "PROFILING REPORT SUMMARY" in captured.out
        assert profiler.session_id in captured.out
        assert "PERFORMANCE METRICS:" in captured.out
        assert "MEMORY SNAPSHOTS:" in captured.out
        assert "SYSTEM INFORMATION:" in captured.out
    
    def test_export_detailed_analysis(self, profiler, tmp_path):
        """Test exporting detailed analysis."""
        profiler.start_profiling()
        profiler.take_memory_snapshot("test")
        profiler.stop_profiling()
        
        report = profiler.generate_report()
        output_path = tmp_path / "analysis.json"
        
        profiler.export_detailed_analysis(report, output_path)
        
        assert output_path.exists()
        
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert "session_summary" in data
        assert "performance_analysis" in data
        assert "memory_analysis" in data
        assert "recommendations" in data
        assert "system_info" in data
    
    def test_calculate_memory_growth(self, profiler):
        """Test calculating memory growth patterns."""
        snapshots = [
            MemorySnapshot(
                timestamp="2023-01-01T00:00:00Z",
                current_memory_mb=100.0,
                peak_memory_mb=100.0,
                memory_blocks=1000,
                context="start"
            ),
            MemorySnapshot(
                timestamp="2023-01-01T00:01:00Z",
                current_memory_mb=150.0,
                peak_memory_mb=150.0,
                memory_blocks=1500,
                context="middle"
            ),
            MemorySnapshot(
                timestamp="2023-01-01T00:02:00Z",
                current_memory_mb=200.0,
                peak_memory_mb=200.0,
                memory_blocks=2000,
                context="end"
            )
        ]
        
        growth = profiler._calculate_memory_growth(snapshots)
        
        assert growth["total_growth_mb"] == 100.0
        assert growth["growth_rate_mb_per_snapshot"] == 50.0
    
    def test_calculate_memory_growth_insufficient_snapshots(self, profiler):
        """Test calculating memory growth with insufficient snapshots."""
        snapshots = [
            MemorySnapshot(
                timestamp="2023-01-01T00:00:00Z",
                current_memory_mb=100.0,
                peak_memory_mb=100.0,
                memory_blocks=1000,
                context="single"
            )
        ]
        
        growth = profiler._calculate_memory_growth(snapshots)
        
        assert growth["total_growth_mb"] == 0.0
        assert growth["growth_rate_mb_per_snapshot"] == 0.0
