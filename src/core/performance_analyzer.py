"""
Performance analysis and optimization recommendations for synchronization operations.

This module analyzes performance data collected by the SyncProfiler and provides
actionable recommendations for optimizing synchronization bottlenecks.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import statistics

from .sync_profiler import SyncProfiler, ProfilerEvent, PerformanceMetrics, get_sync_profiler
from .logging_utils import logger


class OptimizationPriority(Enum):
    """Priority levels for optimization recommendations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OptimizationCategory(Enum):
    """Categories of optimization recommendations."""
    DATABASE = "database"
    CACHE = "cache"
    ALGORITHM = "algorithm"
    MEMORY = "memory"
    CPU = "cpu"
    NETWORK = "network"
    CONFIGURATION = "configuration"


@dataclass
class OptimizationRecommendation:
    """An optimization recommendation with actionable steps."""
    category: OptimizationCategory
    priority: OptimizationPriority
    title: str
    description: str
    impact_estimate: str  # e.g., "30-50% performance improvement"
    effort_estimate: str  # e.g., "Low effort", "Medium effort"
    specific_actions: List[str]
    related_operations: List[str]
    performance_targets: Dict[str, float]  # Target metrics after optimization


@dataclass
class BottleneckAnalysis:
    """Analysis of a specific performance bottleneck."""
    operation_name: str
    event_type: ProfilerEvent
    severity_score: float  # 0-100, higher is more critical
    avg_duration_ms: float
    max_duration_ms: float
    total_operations: int
    success_rate: float
    throughput_per_sec: float
    root_causes: List[str]
    recommendations: List[OptimizationRecommendation]


class PerformanceAnalyzer:
    """Analyzes performance data and provides optimization recommendations."""
    
    def __init__(self, profiler: Optional[SyncProfiler] = None):
        """Initialize the performance analyzer.
        
        Args:
            profiler: SyncProfiler instance to analyze (uses global if None)
        """
        self.profiler = profiler or get_sync_profiler()
        
        # Performance thresholds for different operation types
        self.performance_thresholds = {
            ProfilerEvent.CACHE_GET: {
                "warning_duration_ms": 5,
                "critical_duration_ms": 10,
                "min_throughput_per_sec": 1000,
            },
            ProfilerEvent.CACHE_SET: {
                "warning_duration_ms": 10,
                "critical_duration_ms": 20,
                "min_throughput_per_sec": 500,
            },
            ProfilerEvent.DB_QUERY: {
                "warning_duration_ms": 50,
                "critical_duration_ms": 100,
                "min_throughput_per_sec": 100,
            },
            ProfilerEvent.DB_BULK_INSERT: {
                "warning_duration_ms": 500,
                "critical_duration_ms": 1000,
                "min_throughput_per_sec": 1000,
            },
            ProfilerEvent.DB_BULK_UPDATE: {
                "warning_duration_ms": 500,
                "critical_duration_ms": 1000,
                "min_throughput_per_sec": 1000,
            },
            ProfilerEvent.DB_BULK_UPSERT: {
                "warning_duration_ms": 750,
                "critical_duration_ms": 1500,
                "min_throughput_per_sec": 800,
            },
            ProfilerEvent.SYNC_OPERATION: {
                "warning_duration_ms": 2000,
                "critical_duration_ms": 5000,
                "min_throughput_per_sec": 100,
            },
            ProfilerEvent.INCREMENTAL_SYNC: {
                "warning_duration_ms": 10000,
                "critical_duration_ms": 30000,
                "min_throughput_per_sec": 50,
            },
            ProfilerEvent.CONSISTENCY_CHECK: {
                "warning_duration_ms": 5000,
                "critical_duration_ms": 10000,
                "min_throughput_per_sec": 10,
            },
        }
    
    def analyze_bottlenecks(self) -> List[BottleneckAnalysis]:
        """Analyze all performance bottlenecks and return recommendations.
        
        Returns:
            List of bottleneck analyses with optimization recommendations
        """
        bottlenecks = []
        
        # Get top bottlenecks from profiler
        top_bottlenecks = self.profiler.get_top_bottlenecks(limit=20)
        
        for bottleneck_data in top_bottlenecks:
            analysis = self._analyze_single_bottleneck(bottleneck_data)
            if analysis:
                bottlenecks.append(analysis)
        
        return bottlenecks
    
    def _analyze_single_bottleneck(self, bottleneck_data: Dict[str, Any]) -> Optional[BottleneckAnalysis]:
        """Analyze a single bottleneck and generate recommendations.
        
        Args:
            bottleneck_data: Bottleneck data from profiler
            
        Returns:
            BottleneckAnalysis with recommendations
        """
        operation_name = bottleneck_data["operation_name"]
        event_type = ProfilerEvent(bottleneck_data["event_type"])
        
        # Calculate severity score
        severity_score = self._calculate_severity_score(bottleneck_data, event_type)
        
        # Skip if not significant
        if severity_score < 20:
            return None
        
        # Identify root causes
        root_causes = self._identify_root_causes(bottleneck_data, event_type)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            operation_name, event_type, bottleneck_data, root_causes
        )
        
        return BottleneckAnalysis(
            operation_name=operation_name,
            event_type=event_type,
            severity_score=severity_score,
            avg_duration_ms=bottleneck_data["avg_duration_ms"],
            max_duration_ms=bottleneck_data["max_duration_ms"],
            total_operations=bottleneck_data["total_operations"],
            success_rate=bottleneck_data["success_rate"],
            throughput_per_sec=bottleneck_data["avg_throughput_per_sec"],
            root_causes=root_causes,
            recommendations=recommendations
        )
    
    def _calculate_severity_score(self, bottleneck_data: Dict[str, Any], event_type: ProfilerEvent) -> float:
        """Calculate severity score for a bottleneck (0-100).
        
        Args:
            bottleneck_data: Bottleneck data
            event_type: Type of operation
            
        Returns:
            Severity score (0-100)
        """
        if event_type not in self.performance_thresholds:
            return 0
        
        thresholds = self.performance_thresholds[event_type]
        avg_duration = bottleneck_data["avg_duration_ms"]
        max_duration = bottleneck_data["max_duration_ms"]
        throughput = bottleneck_data["avg_throughput_per_sec"]
        total_ops = bottleneck_data["total_operations"]
        success_rate = bottleneck_data["success_rate"]
        
        # Duration-based score (40% weight)
        duration_score = 0
        if avg_duration > thresholds["critical_duration_ms"]:
            duration_score = 40
        elif avg_duration > thresholds["warning_duration_ms"]:
            duration_score = 20
        
        # Throughput-based score (30% weight)
        throughput_score = 0
        if throughput > 0 and throughput < thresholds["min_throughput_per_sec"]:
            throughput_ratio = throughput / thresholds["min_throughput_per_sec"]
            throughput_score = (1 - throughput_ratio) * 30
        
        # Frequency-based score (20% weight) - more operations = higher impact
        frequency_score = min(total_ops / 1000, 1) * 20
        
        # Success rate score (10% weight)
        success_score = max(0, (100 - success_rate) / 10)
        
        return min(100, duration_score + throughput_score + frequency_score + success_score)
    
    def _identify_root_causes(self, bottleneck_data: Dict[str, Any], event_type: ProfilerEvent) -> List[str]:
        """Identify potential root causes for a bottleneck.
        
        Args:
            bottleneck_data: Bottleneck data
            event_type: Type of operation
            
        Returns:
            List of potential root causes
        """
        root_causes = []
        
        avg_duration = bottleneck_data["avg_duration_ms"]
        max_duration = bottleneck_data["max_duration_ms"]
        throughput = bottleneck_data["avg_throughput_per_sec"]
        success_rate = bottleneck_data["success_rate"]
        
        # High variance between avg and max suggests inconsistent performance
        if max_duration > avg_duration * 3:
            root_causes.append("High performance variance - inconsistent execution times")
        
        # Low throughput for bulk operations
        if event_type in [ProfilerEvent.DB_BULK_INSERT, ProfilerEvent.DB_BULK_UPDATE, ProfilerEvent.DB_BULK_UPSERT]:
            if throughput < 500:
                root_causes.append("Low bulk operation throughput - potential database indexing issues")
        
        # Cache-related issues
        if event_type in [ProfilerEvent.CACHE_GET, ProfilerEvent.CACHE_SET]:
            if avg_duration > 10:
                root_causes.append("Slow cache operations - potential memory pressure or large object sizes")
        
        # Database query issues
        if event_type == ProfilerEvent.DB_QUERY:
            if avg_duration > 50:
                root_causes.append("Slow database queries - missing indexes or inefficient query patterns")
        
        # Sync operation issues
        if event_type == ProfilerEvent.SYNC_OPERATION:
            if avg_duration > 2000:
                root_causes.append("Slow synchronization - potential network or serialization bottlenecks")
        
        # Consistency check issues
        if event_type == ProfilerEvent.CONSISTENCY_CHECK:
            if avg_duration > 5000:
                root_causes.append("Slow consistency checks - large dataset comparison overhead")
        
        # High failure rate
        if success_rate < 95:
            root_causes.append(f"High failure rate ({100-success_rate:.1f}%) - reliability issues")
        
        # Memory-related issues (if available)
        if "memory_mb" in bottleneck_data:
            memory_mb = bottleneck_data["memory_mb"]
            if memory_mb > 100:  # High memory usage
                root_causes.append("High memory usage - potential memory leaks or inefficient data structures")
        
        return root_causes
    
    def _generate_recommendations(
        self,
        operation_name: str,
        event_type: ProfilerEvent,
        bottleneck_data: Dict[str, Any],
        root_causes: List[str]
    ) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations for a bottleneck.
        
        Args:
            operation_name: Name of the operation
            event_type: Type of operation
            bottleneck_data: Bottleneck data
            root_causes: Identified root causes
            
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        # Database-related recommendations
        if event_type in [ProfilerEvent.DB_QUERY, ProfilerEvent.DB_BULK_INSERT, ProfilerEvent.DB_BULK_UPDATE, ProfilerEvent.DB_BULK_UPSERT]:
            recommendations.extend(self._get_database_recommendations(operation_name, event_type, bottleneck_data))
        
        # Cache-related recommendations
        if event_type in [ProfilerEvent.CACHE_GET, ProfilerEvent.CACHE_SET, ProfilerEvent.CACHE_DELETE]:
            recommendations.extend(self._get_cache_recommendations(operation_name, event_type, bottleneck_data))
        
        # Sync operation recommendations
        if event_type == ProfilerEvent.SYNC_OPERATION:
            recommendations.extend(self._get_sync_recommendations(operation_name, bottleneck_data))
        
        # Consistency check recommendations
        if event_type == ProfilerEvent.CONSISTENCY_CHECK:
            recommendations.extend(self._get_consistency_recommendations(operation_name, bottleneck_data))
        
        # Memory-related recommendations
        if "High memory usage" in root_causes:
            recommendations.extend(self._get_memory_recommendations(operation_name, bottleneck_data))
        
        return recommendations
    
    def _get_database_recommendations(
        self,
        operation_name: str,
        event_type: ProfilerEvent,
        bottleneck_data: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """Get database-related optimization recommendations."""
        recommendations = []
        
        if event_type == ProfilerEvent.DB_QUERY:
            recommendations.append(OptimizationRecommendation(
                category=OptimizationCategory.DATABASE,
                priority=OptimizationPriority.HIGH,
                title="Optimize Database Queries",
                description="Database queries are taking too long. Consider adding indexes and optimizing query patterns.",
                impact_estimate="50-80% performance improvement",
                effort_estimate="Medium effort",
                specific_actions=[
                    "Add database indexes on frequently queried columns",
                    "Review and optimize SQL query patterns",
                    "Consider query result caching",
                    "Implement connection pooling if not already present",
                    "Use prepared statements for repeated queries"
                ],
                related_operations=[operation_name],
                performance_targets={"avg_duration_ms": 25, "throughput_per_sec": 200}
            ))
        
        elif event_type in [ProfilerEvent.DB_BULK_INSERT, ProfilerEvent.DB_BULK_UPDATE, ProfilerEvent.DB_BULK_UPSERT]:
            throughput = bottleneck_data["avg_throughput_per_sec"]
            if throughput < 1000:
                recommendations.append(OptimizationRecommendation(
                    category=OptimizationCategory.DATABASE,
                    priority=OptimizationPriority.CRITICAL,
                    title="Optimize Bulk Database Operations",
                    description="Bulk operations are not meeting performance targets. Multiple optimization opportunities exist.",
                    impact_estimate="200-500% performance improvement",
                    effort_estimate="Medium effort",
                    specific_actions=[
                        "Use database-specific bulk insert optimizations (e.g., PostgreSQL COPY)",
                        "Implement batch processing with optimal batch sizes",
                        "Disable foreign key constraints during bulk operations",
                        "Use transaction batching to reduce commit overhead",
                        "Consider using database-specific upsert operations (ON CONFLICT, MERGE)",
                        "Optimize database configuration for bulk operations"
                    ],
                    related_operations=[operation_name],
                    performance_targets={"throughput_per_sec": 2000, "avg_duration_ms": 250}
                ))
        
        return recommendations
    
    def _get_cache_recommendations(
        self,
        operation_name: str,
        event_type: ProfilerEvent,
        bottleneck_data: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """Get cache-related optimization recommendations."""
        recommendations = []
        
        avg_duration = bottleneck_data["avg_duration_ms"]
        
        if avg_duration > 10:
            recommendations.append(OptimizationRecommendation(
                category=OptimizationCategory.CACHE,
                priority=OptimizationPriority.HIGH,
                title="Optimize Cache Operations",
                description="Cache operations are slower than expected. Consider optimizing cache implementation.",
                impact_estimate="60-90% performance improvement",
                effort_estimate="Low effort",
                specific_actions=[
                    "Review cache key generation efficiency",
                    "Optimize cache serialization/deserialization",
                    "Consider using faster cache backends (Redis, Memcached)",
                    "Implement cache compression for large objects",
                    "Optimize cache eviction policies",
                    "Use cache warming strategies"
                ],
                related_operations=[operation_name],
                performance_targets={"avg_duration_ms": 5, "throughput_per_sec": 2000}
            ))
        
        return recommendations
    
    def _get_sync_recommendations(
        self,
        operation_name: str,
        bottleneck_data: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """Get synchronization-related optimization recommendations."""
        recommendations = []
        
        avg_duration = bottleneck_data["avg_duration_ms"]
        
        if avg_duration > 2000:
            recommendations.append(OptimizationRecommendation(
                category=OptimizationCategory.ALGORITHM,
                priority=OptimizationPriority.HIGH,
                title="Optimize Synchronization Algorithm",
                description="Synchronization operations are taking too long. Consider algorithmic improvements.",
                impact_estimate="40-70% performance improvement",
                effort_estimate="High effort",
                specific_actions=[
                    "Implement incremental synchronization instead of full sync",
                    "Use change tracking to identify only modified data",
                    "Implement parallel processing for independent operations",
                    "Optimize data serialization and transfer",
                    "Use compression for large data transfers",
                    "Implement smart conflict resolution strategies"
                ],
                related_operations=[operation_name],
                performance_targets={"avg_duration_ms": 1000, "throughput_per_sec": 200}
            ))
        
        return recommendations
    
    def _get_consistency_recommendations(
        self,
        operation_name: str,
        bottleneck_data: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """Get consistency check optimization recommendations."""
        recommendations = []
        
        avg_duration = bottleneck_data["avg_duration_ms"]
        
        if avg_duration > 5000:
            recommendations.append(OptimizationRecommendation(
                category=OptimizationCategory.ALGORITHM,
                priority=OptimizationPriority.MEDIUM,
                title="Optimize Consistency Checks",
                description="Consistency checks are taking too long. Consider sampling and incremental approaches.",
                impact_estimate="60-80% performance improvement",
                effort_estimate="Medium effort",
                specific_actions=[
                    "Implement sampling-based consistency checks",
                    "Use incremental consistency validation",
                    "Parallelize consistency checks across data partitions",
                    "Implement smart scheduling to avoid peak usage times",
                    "Use checksums or hashes for faster comparison",
                    "Cache consistency check results"
                ],
                related_operations=[operation_name],
                performance_targets={"avg_duration_ms": 2000, "throughput_per_sec": 50}
            ))
        
        return recommendations
    
    def _get_memory_recommendations(
        self,
        operation_name: str,
        bottleneck_data: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """Get memory-related optimization recommendations."""
        recommendations = []
        
        recommendations.append(OptimizationRecommendation(
            category=OptimizationCategory.MEMORY,
            priority=OptimizationPriority.MEDIUM,
            title="Optimize Memory Usage",
            description="High memory usage detected. Consider memory optimization strategies.",
            impact_estimate="30-50% memory reduction",
            effort_estimate="Medium effort",
            specific_actions=[
                "Implement object pooling for frequently created objects",
                "Use streaming for large data processing",
                "Optimize data structures to reduce memory footprint",
                "Implement memory-mapped files for large datasets",
                "Use lazy loading for non-critical data",
                "Implement garbage collection optimization"
            ],
            related_operations=[operation_name],
            performance_targets={"memory_mb": 50}
        ))
        
        return recommendations
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate a comprehensive performance analysis report.
        
        Returns:
            Dictionary containing performance analysis report
        """
        bottlenecks = self.analyze_bottlenecks()
        
        # Categorize recommendations by priority
        critical_recommendations = []
        high_recommendations = []
        medium_recommendations = []
        low_recommendations = []
        
        for bottleneck in bottlenecks:
            for recommendation in bottleneck.recommendations:
                if recommendation.priority == OptimizationPriority.CRITICAL:
                    critical_recommendations.append(recommendation)
                elif recommendation.priority == OptimizationPriority.HIGH:
                    high_recommendations.append(recommendation)
                elif recommendation.priority == OptimizationPriority.MEDIUM:
                    medium_recommendations.append(recommendation)
                else:
                    low_recommendations.append(recommendation)
        
        # Get overall performance summary
        performance_summary = self.profiler.get_performance_summary()
        
        return {
            "analysis_timestamp": performance_summary.get("time_range", {}).get("end"),
            "overall_performance": performance_summary,
            "bottleneck_analysis": [
                {
                    "operation_name": b.operation_name,
                    "event_type": b.event_type.value,
                    "severity_score": b.severity_score,
                    "avg_duration_ms": b.avg_duration_ms,
                    "max_duration_ms": b.max_duration_ms,
                    "total_operations": b.total_operations,
                    "success_rate": b.success_rate,
                    "throughput_per_sec": b.throughput_per_sec,
                    "root_causes": b.root_causes,
                    "recommendations": [
                        {
                            "category": r.category.value,
                            "priority": r.priority.value,
                            "title": r.title,
                            "description": r.description,
                            "impact_estimate": r.impact_estimate,
                            "effort_estimate": r.effort_estimate,
                            "specific_actions": r.specific_actions,
                            "related_operations": r.related_operations,
                            "performance_targets": r.performance_targets
                        }
                        for r in b.recommendations
                    ]
                }
                for b in bottlenecks
            ],
            "optimization_recommendations": {
                "critical": [
                    {
                        "title": r.title,
                        "category": r.category.value,
                        "impact_estimate": r.impact_estimate,
                        "effort_estimate": r.effort_estimate,
                        "specific_actions": r.specific_actions
                    }
                    for r in critical_recommendations
                ],
                "high": [
                    {
                        "title": r.title,
                        "category": r.category.value,
                        "impact_estimate": r.impact_estimate,
                        "effort_estimate": r.effort_estimate,
                        "specific_actions": r.specific_actions
                    }
                    for r in high_recommendations
                ],
                "medium": [
                    {
                        "title": r.title,
                        "category": r.category.value,
                        "impact_estimate": r.impact_estimate,
                        "effort_estimate": r.effort_estimate,
                        "specific_actions": r.specific_actions
                    }
                    for r in medium_recommendations
                ],
                "low": [
                    {
                        "title": r.title,
                        "category": r.category.value,
                        "impact_estimate": r.impact_estimate,
                        "effort_estimate": r.effort_estimate,
                        "specific_actions": r.specific_actions
                    }
                    for r in low_recommendations
                ]
            },
            "performance_targets": {
                "single_operations": {"max_duration_ms": 1000},
                "bulk_operations": {"min_throughput_per_sec": 1000},
                "cache_operations": {"max_duration_ms": 10},
                "sync_operations": {"max_duration_ms": 5000}
            }
        }
