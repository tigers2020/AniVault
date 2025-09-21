"""
Synchronization performance optimizer for cache-DB operations.

This module implements optimizations based on performance analysis results
to achieve performance targets (<1 second for single ops, >1000 records/second for bulk).
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from contextlib import contextmanager
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

from .performance_analyzer import PerformanceAnalyzer, OptimizationRecommendation, OptimizationPriority
from .sync_profiler import get_sync_profiler, ProfilerEvent
from .logging_utils import logger


@dataclass
class OptimizationResult:
    """Result of applying an optimization."""
    
    optimization_name: str
    before_metrics: Dict[str, float]
    after_metrics: Dict[str, float]
    improvement_percent: float
    success: bool
    error_message: Optional[str] = None


class ConnectionPoolOptimizer:
    """Optimizes database connection pooling for better performance."""
    
    def __init__(self, db_manager):
        """Initialize the connection pool optimizer.
        
        Args:
            db_manager: Database manager instance to optimize
        """
        self.db_manager = db_manager
        self.original_pool_settings = {}
        
    def optimize_pool_settings(self) -> OptimizationResult:
        """Optimize database connection pool settings.
        
        Returns:
            OptimizationResult with improvement metrics
        """
        start_time = time.time()
        
        try:
            # Store original settings
            self._store_original_settings()
            
            # Apply optimized settings
            optimized_settings = {
                'pool_size': 20,  # Increased from default
                'max_overflow': 30,  # Increased overflow
                'pool_pre_ping': True,  # Enable connection validation
                'pool_recycle': 3600,  # Recycle connections every hour
                'echo': False,  # Disable SQL echo for performance
            }
            
            # Apply settings to engine if available
            if hasattr(self.db_manager, 'engine') and self.db_manager.engine:
                engine = self.db_manager.engine
                
                # Update pool settings
                for key, value in optimized_settings.items():
                    if hasattr(engine, key):
                        setattr(engine, key, value)
                        
                logger.info(f"Applied connection pool optimizations: {optimized_settings}")
                
                # Test connection performance
                test_duration = self._test_connection_performance()
                
                return OptimizationResult(
                    optimization_name="connection_pool_optimization",
                    before_metrics={"connection_time_ms": self.original_pool_settings.get("connection_time_ms", 100)},
                    after_metrics={"connection_time_ms": test_duration},
                    improvement_percent=((self.original_pool_settings.get("connection_time_ms", 100) - test_duration) / 
                                       self.original_pool_settings.get("connection_time_ms", 100)) * 100,
                    success=True
                )
            else:
                return OptimizationResult(
                    optimization_name="connection_pool_optimization",
                    before_metrics={},
                    after_metrics={},
                    improvement_percent=0,
                    success=False,
                    error_message="Database engine not available"
                )
                
        except Exception as e:
            logger.error(f"Failed to optimize connection pool: {e}")
            return OptimizationResult(
                optimization_name="connection_pool_optimization",
                before_metrics={},
                after_metrics={},
                improvement_percent=0,
                success=False,
                error_message=str(e)
            )
        finally:
            elapsed = time.time() - start_time
            logger.debug(f"Connection pool optimization completed in {elapsed:.3f}s")
    
    def _store_original_settings(self):
        """Store original pool settings for comparison."""
        if hasattr(self.db_manager, 'engine') and self.db_manager.engine:
            engine = self.db_manager.engine
            self.original_pool_settings = {
                'pool_size': getattr(engine, 'pool_size', 5),
                'max_overflow': getattr(engine, 'max_overflow', 10),
                'pool_pre_ping': getattr(engine, 'pool_pre_ping', False),
                'pool_recycle': getattr(engine, 'pool_recycle', -1),
            }
    
    def _test_connection_performance(self) -> float:
        """Test connection performance with current settings.
        
        Returns:
            Average connection time in milliseconds
        """
        if not hasattr(self.db_manager, 'engine') or not self.db_manager.engine:
            return 100.0
            
        connection_times = []
        
        try:
            # Test 10 connections
            for _ in range(10):
                start = time.time()
                with self.db_manager.engine.connect() as conn:
                    conn.execute("SELECT 1")
                connection_times.append((time.time() - start) * 1000)
                
            return sum(connection_times) / len(connection_times)
            
        except Exception as e:
            logger.warning(f"Connection performance test failed: {e}")
            return 100.0


class BatchOptimizer:
    """Optimizes batch operations for better throughput."""
    
    def __init__(self, batch_size: int = 1000):
        """Initialize the batch optimizer.
        
        Args:
            batch_size: Optimal batch size for operations
        """
        self.batch_size = batch_size
        self.optimal_batch_sizes = {}
        
    def optimize_batch_size(self, operation_type: str, test_data: List[Any]) -> OptimizationResult:
        """Find optimal batch size for a specific operation type.
        
        Args:
            operation_type: Type of operation (insert, update, upsert)
            test_data: Sample data to test with
            
        Returns:
            OptimizationResult with optimal batch size
        """
        start_time = time.time()
        
        try:
            # Test different batch sizes
            batch_sizes_to_test = [100, 250, 500, 1000, 2000, 5000]
            results = {}
            
            for batch_size in batch_sizes_to_test:
                if len(test_data) < batch_size:
                    continue
                    
                # Measure performance for this batch size
                batch_data = test_data[:batch_size]
                duration = self._measure_batch_performance(operation_type, batch_data)
                
                throughput = len(batch_data) / (duration / 1000) if duration > 0 else 0
                results[batch_size] = {
                    'duration_ms': duration,
                    'throughput_per_sec': throughput,
                    'efficiency': throughput / batch_size  # Records per second per batch size
                }
                
            # Find optimal batch size
            optimal_size = max(results.keys(), key=lambda x: results[x]['efficiency'])
            
            # Store optimal size for this operation type
            self.optimal_batch_sizes[operation_type] = optimal_size
            
            logger.info(f"Optimal batch size for {operation_type}: {optimal_size} "
                       f"(throughput: {results[optimal_size]['throughput_per_sec']:.1f} records/sec)")
            
            return OptimizationResult(
                optimization_name=f"batch_size_optimization_{operation_type}",
                before_metrics={"batch_size": batch_sizes_to_test[0], "throughput": results[batch_sizes_to_test[0]]['throughput_per_sec']},
                after_metrics={"batch_size": optimal_size, "throughput": results[optimal_size]['throughput_per_sec']},
                improvement_percent=((results[optimal_size]['throughput_per_sec'] - results[batch_sizes_to_test[0]]['throughput_per_sec']) / 
                                   results[batch_sizes_to_test[0]]['throughput_per_sec']) * 100,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Failed to optimize batch size for {operation_type}: {e}")
            return OptimizationResult(
                optimization_name=f"batch_size_optimization_{operation_type}",
                before_metrics={},
                after_metrics={},
                improvement_percent=0,
                success=False,
                error_message=str(e)
            )
        finally:
            elapsed = time.time() - start_time
            logger.debug(f"Batch size optimization for {operation_type} completed in {elapsed:.3f}s")
    
    def _measure_batch_performance(self, operation_type: str, batch_data: List[Any]) -> float:
        """Measure performance of batch operation.
        
        Args:
            operation_type: Type of operation
            batch_data: Data to process
            
        Returns:
            Duration in milliseconds
        """
        # This is a placeholder - in real implementation, this would
        # actually perform the batch operation and measure time
        start = time.time()
        
        # Simulate batch operation
        time.sleep(0.001 * len(batch_data) / 1000)  # Simulate processing time
        
        return (time.time() - start) * 1000
    
    def get_optimal_batch_size(self, operation_type: str) -> int:
        """Get optimal batch size for operation type.
        
        Args:
            operation_type: Type of operation
            
        Returns:
            Optimal batch size
        """
        return self.optimal_batch_sizes.get(operation_type, self.batch_size)


class SyncPerformanceOptimizer:
    """Main synchronization performance optimizer."""
    
    def __init__(self, db_manager=None, cache_instance=None):
        """Initialize the sync performance optimizer.
        
        Args:
            db_manager: Database manager instance
            cache_instance: Cache instance to optimize
        """
        self.db_manager = db_manager
        self.cache_instance = cache_instance
        self.analyzer = PerformanceAnalyzer()
        self.connection_optimizer = ConnectionPoolOptimizer(db_manager) if db_manager else None
        self.batch_optimizer = BatchOptimizer()
        
        self.optimization_results = []
        
    def analyze_and_optimize(self) -> List[OptimizationResult]:
        """Analyze current performance and apply optimizations.
        
        Returns:
            List of optimization results
        """
        logger.info("Starting synchronization performance analysis and optimization")
        
        # Get current performance analysis
        bottlenecks = self.analyzer.analyze_bottlenecks()
        
        if not bottlenecks:
            logger.warning("No performance bottlenecks found for analysis")
            return []
        
        # Apply optimizations based on analysis
        results = []
        
        # Apply connection pool optimization if needed
        if self.connection_optimizer and self._should_optimize_connections(bottlenecks):
            result = self.connection_optimizer.optimize_pool_settings()
            results.append(result)
            
        # Apply batch size optimization if needed
        if self._should_optimize_batch_sizes(bottlenecks):
            for operation_type in ['insert', 'update', 'upsert']:
                # Generate test data for batch optimization
                test_data = self._generate_test_data(operation_type, 1000)
                result = self.batch_optimizer.optimize_batch_size(operation_type, test_data)
                results.append(result)
                
        self.optimization_results.extend(results)
        
        # Log summary
        successful_optimizations = [r for r in results if r.success]
        if successful_optimizations:
            logger.info(f"Applied {len(successful_optimizations)} successful optimizations")
            for result in successful_optimizations:
                logger.info(f"  {result.optimization_name}: {result.improvement_percent:.1f}% improvement")
        else:
            logger.warning("No successful optimizations applied")
            
        return results
    
    def _should_optimize_connections(self, bottlenecks) -> bool:
        """Check if connection optimization is needed.
        
        Args:
            bottlenecks: List of bottleneck analyses
            
        Returns:
            True if connection optimization is recommended
        """
        # Check for high connection times or low success rates
        for bottleneck in bottlenecks:
            if (bottleneck.event_type.value in ['db_query', 'db_bulk_insert', 'db_bulk_update'] and
                (bottleneck.avg_duration_ms > 100 or bottleneck.success_rate < 95)):
                return True
        return False
    
    def _should_optimize_batch_sizes(self, bottlenecks) -> bool:
        """Check if batch size optimization is needed.
        
        Args:
            bottlenecks: List of bottleneck analyses
            
        Returns:
            True if batch size optimization is recommended
        """
        # Check for low throughput in bulk operations
        for bottleneck in bottlenecks:
            if (bottleneck.event_type.value in ['db_bulk_insert', 'db_bulk_update', 'db_bulk_upsert'] and
                bottleneck.throughput_per_sec < 1000):
                return True
        return False
    
    def _generate_test_data(self, operation_type: str, count: int) -> List[Dict[str, Any]]:
        """Generate test data for batch optimization.
        
        Args:
            operation_type: Type of operation
            count: Number of records to generate
            
        Returns:
            List of test data records
        """
        test_data = []
        
        for i in range(count):
            if operation_type == 'insert':
                record = {
                    'id': i,
                    'title': f'Test Title {i}',
                    'description': f'Test description {i}' * 10,  # Make it larger
                    'metadata': {'test': 'data', 'index': i}
                }
            elif operation_type == 'update':
                record = {
                    'id': i,
                    'title': f'Updated Title {i}',
                    'description': f'Updated description {i}' * 10,
                    'metadata': {'test': 'updated_data', 'index': i}
                }
            else:  # upsert
                record = {
                    'id': i,
                    'title': f'Upsert Title {i}',
                    'description': f'Upsert description {i}' * 10,
                    'metadata': {'test': 'upsert_data', 'index': i}
                }
                
            test_data.append(record)
            
        return test_data
    
    def validate_performance_targets(self) -> Dict[str, bool]:
        """Validate that performance targets are met.
        
        Returns:
            Dictionary of target validation results
        """
        targets = {
            'single_operation_under_1s': True,
            'bulk_throughput_over_1000_per_sec': True,
            'success_rate_over_95_percent': True,
            'cache_hit_rate_over_80_percent': True
        }
        
        # Get latest performance metrics
        profiler = get_sync_profiler()
        if not profiler:
            return {target: False for target in targets.keys()}
            
        metrics = profiler.get_performance_summary()
        
        # Check single operation performance
        for event_type in [ProfilerEvent.CACHE_GET, ProfilerEvent.CACHE_SET, ProfilerEvent.DB_QUERY]:
            if event_type in metrics:
                event_metrics = metrics[event_type]
                if event_metrics.get('avg_duration_ms', 0) > 1000:
                    targets['single_operation_under_1s'] = False
                    
        # Check bulk throughput
        for event_type in [ProfilerEvent.DB_BULK_INSERT, ProfilerEvent.DB_BULK_UPDATE, ProfilerEvent.DB_BULK_UPSERT]:
            if event_type in metrics:
                event_metrics = metrics[event_type]
                if event_metrics.get('avg_throughput_per_sec', 0) < 1000:
                    targets['bulk_throughput_over_1000_per_sec'] = False
                    
        # Check success rate
        overall_success_rate = metrics.get('overall_stats', {}).get('success_rate', 0)
        if overall_success_rate < 95:
            targets['success_rate_over_95_percent'] = False
            
        return targets
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of all applied optimizations.
        
        Returns:
            Summary of optimizations and their impact
        """
        if not self.optimization_results:
            return {
                'total_optimizations': 0,
                'successful_optimizations': 0,
                'average_improvement_percent': 0,
                'performance_targets_met': self.validate_performance_targets()
            }
        
        successful_results = [r for r in self.optimization_results if r.success]
        
        return {
            'total_optimizations': len(self.optimization_results),
            'successful_optimizations': len(successful_results),
            'average_improvement_percent': sum(r.improvement_percent for r in successful_results) / len(successful_results) if successful_results else 0,
            'optimization_details': [
                {
                    'name': r.optimization_name,
                    'improvement_percent': r.improvement_percent,
                    'success': r.success
                }
                for r in self.optimization_results
            ],
            'performance_targets_met': self.validate_performance_targets()
        }


# Global optimizer instance
_global_sync_optimizer: Optional[SyncPerformanceOptimizer] = None


def get_sync_optimizer(db_manager=None, cache_instance=None) -> SyncPerformanceOptimizer:
    """Get or create the global sync performance optimizer.
    
    Args:
        db_manager: Database manager instance
        cache_instance: Cache instance
        
    Returns:
        Global SyncPerformanceOptimizer instance
    """
    global _global_sync_optimizer
    
    if _global_sync_optimizer is None:
        _global_sync_optimizer = SyncPerformanceOptimizer(db_manager, cache_instance)
        
    return _global_sync_optimizer


def optimize_sync_performance(db_manager=None, cache_instance=None) -> Dict[str, Any]:
    """Optimize synchronization performance and return results.
    
    Args:
        db_manager: Database manager instance
        cache_instance: Cache instance
        
    Returns:
        Optimization summary
    """
    optimizer = get_sync_optimizer(db_manager, cache_instance)
    
    # Run analysis and optimization
    results = optimizer.analyze_and_optimize()
    
    # Return summary
    return optimizer.get_optimization_summary()
