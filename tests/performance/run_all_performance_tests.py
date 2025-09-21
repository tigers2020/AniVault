"""Comprehensive performance test runner for all optimization validations.

This module runs all performance tests in sequence and generates
a unified report of optimization results.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.core.database import DatabaseManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PerformanceTestRunner:
    """Runner for all performance tests with unified reporting."""

    def __init__(self) -> None:
        self.test_results: Dict[str, Any] = {}
        self.start_time = 0
        self.end_time = 0

    async def run_bulk_update_performance_test(self) -> Dict[str, Any]:
        """Run bulk update performance tests."""
        logger.info("Running bulk update performance tests...")

        try:
            from test_bulk_update_performance import test_bulk_update_performance
            results = await test_bulk_update_performance()
            logger.info("✅ Bulk update performance tests completed")
            return results
        except Exception as e:
            logger.error(f"❌ Bulk update performance tests failed: {e}")
            return {"error": str(e)}

    async def run_n1_query_elimination_test(self) -> Dict[str, Any]:
        """Run N+1 query elimination tests."""
        logger.info("Running N+1 query elimination tests...")

        try:
            from test_n1_query_elimination import test_n1_query_elimination
            results = await test_n1_query_elimination()
            logger.info("✅ N+1 query elimination tests completed")
            return results
        except Exception as e:
            logger.error(f"❌ N+1 query elimination tests failed: {e}")
            return {"error": str(e)}

    async def run_memory_and_speed_benchmarks(self) -> Dict[str, Any]:
        """Run memory and speed benchmark tests."""
        logger.info("Running memory and speed benchmark tests...")

        try:
            from test_memory_and_speed_benchmarks import test_memory_and_speed_benchmarks
            results = await test_memory_and_speed_benchmarks()
            logger.info("✅ Memory and speed benchmark tests completed")
            return results
        except Exception as e:
            logger.error(f"❌ Memory and speed benchmark tests failed: {e}")
            return {"error": str(e)}

    async def run_large_dataset_batch_processing_test(self) -> Dict[str, Any]:
        """Run large dataset batch processing tests."""
        logger.info("Running large dataset batch processing tests...")

        try:
            from test_large_dataset_batch_processing import test_large_dataset_batch_processing
            results = await test_large_dataset_batch_processing()
            logger.info("✅ Large dataset batch processing tests completed")
            return results
        except Exception as e:
            logger.error(f"❌ Large dataset batch processing tests failed: {e}")
            return {"error": str(e)}

    async def run_performance_analysis_report(self) -> Dict[str, Any]:
        """Run performance analysis and report generation."""
        logger.info("Running performance analysis and report generation...")

        try:
            from test_performance_analysis_report import test_performance_analysis_report
            results = await test_performance_analysis_report()
            logger.info("✅ Performance analysis and report generation completed")
            return results
        except Exception as e:
            logger.error(f"❌ Performance analysis and report generation failed: {e}")
            return {"error": str(e)}

    async def run_all_performance_tests(self) -> Dict[str, Any]:
        """Run all performance tests in sequence."""
        logger.info("Starting comprehensive performance test suite...")
        self.start_time = time.time()

        # Define test sequence
        test_suite = [
            ("bulk_update_performance", self.run_bulk_update_performance_test),
            ("n1_query_elimination", self.run_n1_query_elimination_test),
            ("memory_and_speed_benchmarks", self.run_memory_and_speed_benchmarks),
            ("large_dataset_batch_processing", self.run_large_dataset_batch_processing_test),
            ("performance_analysis_report", self.run_performance_analysis_report)
        ]

        # Run tests sequentially
        for test_name, test_function in test_suite:
            logger.info(f"\n{'='*60}")
            logger.info(f"Running {test_name}...")
            logger.info(f"{'='*60}")

            test_start = time.time()
            try:
                results = await test_function()
                test_end = time.time()
                test_duration = test_end - test_start

                self.test_results[test_name] = {
                    "status": "completed",
                    "duration_seconds": test_duration,
                    "results": results
                }

                logger.info(f"✅ {test_name} completed in {test_duration:.2f}s")

            except Exception as e:
                test_end = time.time()
                test_duration = test_end - test_start

                self.test_results[test_name] = {
                    "status": "failed",
                    "duration_seconds": test_duration,
                    "error": str(e)
                }

                logger.error(f"❌ {test_name} failed after {test_duration:.2f}s: {e}")

        self.end_time = time.time()
        total_duration = self.end_time - self.start_time

        logger.info(f"\n{'='*60}")
        logger.info(f"Performance test suite completed in {total_duration:.2f}s")
        logger.info(f"{'='*60}")

        # Generate unified report
        unified_report = self.generate_unified_report()

        return unified_report

    def generate_unified_report(self) -> Dict[str, Any]:
        """Generate unified report from all test results."""
        logger.info("Generating unified performance test report...")

        # Calculate summary statistics
        total_tests = len(self.test_results)
        completed_tests = sum(1 for result in self.test_results.values() if result["status"] == "completed")
        failed_tests = total_tests - completed_tests

        total_duration = sum(result["duration_seconds"] for result in self.test_results.values())

        # Extract key performance metrics
        performance_metrics = self.extract_performance_metrics()

        # Generate unified report
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_execution_time_seconds": total_duration,
                "test_suite_version": "1.0",
                "optimization_target": "N+1 Query Elimination and Batch Processing"
            },
            "test_summary": {
                "total_tests": total_tests,
                "completed_tests": completed_tests,
                "failed_tests": failed_tests,
                "success_rate_percent": (completed_tests / total_tests) * 100 if total_tests > 0 else 0,
                "total_execution_time_seconds": total_duration
            },
            "performance_metrics": performance_metrics,
            "test_results": self.test_results,
            "optimization_validation": self.validate_optimizations(),
            "recommendations": self.generate_recommendations()
        }

        return report

    def extract_performance_metrics(self) -> Dict[str, Any]:
        """Extract key performance metrics from test results."""
        metrics = {
            "bulk_update_performance": {},
            "n1_elimination_metrics": {},
            "memory_efficiency": {},
            "throughput_performance": {},
            "scalability_metrics": {}
        }

        # Extract from bulk update performance test
        if "bulk_update_performance" in self.test_results:
            bulk_test = self.test_results["bulk_update_performance"]
            if bulk_test["status"] == "completed" and "summary" in bulk_test["results"]:
                summary = bulk_test["results"]["summary"]
                metrics["bulk_update_performance"] = {
                    "anime_avg_execution_time": summary.get("anime_metadata_summary", {}).get("avg_execution_time", 0),
                    "file_avg_execution_time": summary.get("parsed_files_summary", {}).get("avg_execution_time", 0),
                    "avg_time_improvement": summary.get("overall_improvements", {}).get("avg_time_improvement_percent", 0),
                    "avg_query_reduction": summary.get("overall_improvements", {}).get("avg_query_reduction_percent", 0)
                }

        # Extract from N+1 elimination test
        if "n1_query_elimination" in self.test_results:
            n1_test = self.test_results["n1_query_elimination"]
            if n1_test["status"] == "completed" and "summary" in n1_test["results"]:
                summary = n1_test["results"]["summary"]
                metrics["n1_elimination_metrics"] = {
                    "elimination_rate_percent": summary.get("efficiency_metrics", {}).get("n1_elimination_rate", 0),
                    "avg_queries_per_record": summary.get("average_queries_per_record", 0),
                    "total_queries_analyzed": summary.get("efficiency_metrics", {}).get("total_queries_analyzed", 0)
                }

        # Extract from memory and speed benchmarks
        if "memory_and_speed_benchmarks" in self.test_results:
            benchmark_test = self.test_results["memory_and_speed_benchmarks"]
            if benchmark_test["status"] == "completed" and "summary" in benchmark_test["results"]:
                summary = benchmark_test["results"]["summary"]
                metrics["memory_efficiency"] = {
                    "anime_avg_memory_per_record": summary.get("memory_efficiency", {}).get("anime_avg_memory_per_record_mb", 0),
                    "file_avg_memory_per_record": summary.get("memory_efficiency", {}).get("file_avg_memory_per_record_mb", 0)
                }
                metrics["throughput_performance"] = {
                    "avg_throughput_records_per_sec": summary.get("throughput_performance", {}).get("avg_throughput_records_per_sec", 0),
                    "max_throughput_records_per_sec": summary.get("throughput_performance", {}).get("max_throughput_records_per_sec", 0)
                }
                metrics["scalability_metrics"] = {
                    "is_linearly_scalable": summary.get("scaling_characteristics", {}).get("is_linearly_scalable", False),
                    "scaling_efficiency": summary.get("scaling_characteristics", {}).get("scaling_efficiency", 1.0)
                }

        # Extract from large dataset test
        if "large_dataset_batch_processing" in self.test_results:
            large_test = self.test_results["large_dataset_batch_processing"]
            if large_test["status"] == "completed" and "summary" in large_test["results"]:
                summary = large_test["results"]["summary"]
                if "performance_characteristics" in summary:
                    metrics["throughput_performance"]["optimal_batch_size"] = summary["performance_characteristics"].get("optimal_batch_size", 0)
                    metrics["throughput_performance"]["best_throughput"] = summary["performance_characteristics"].get("best_throughput_records_per_sec", 0)

        return metrics

    def validate_optimizations(self) -> Dict[str, Any]:
        """Validate that optimizations meet performance targets."""
        validation = {
            "all_optimizations_validated": True,
            "validation_criteria": {},
            "passed_validations": [],
            "failed_validations": []
        }

        # Define validation criteria
        criteria = {
            "min_time_improvement_percent": 50,
            "min_query_reduction_percent": 80,
            "max_queries_per_record": 0.1,
            "min_throughput_records_per_sec": 1000,
            "min_memory_efficiency_mb_per_record": 0.01
        }

        validation["validation_criteria"] = criteria

        # Validate bulk update performance
        bulk_metrics = self.extract_performance_metrics().get("bulk_update_performance", {})
        if bulk_metrics:
            time_improvement = bulk_metrics.get("avg_time_improvement", 0)
            query_reduction = bulk_metrics.get("avg_query_reduction", 0)

            if time_improvement >= criteria["min_time_improvement_percent"]:
                validation["passed_validations"].append(f"Time improvement: {time_improvement:.1f}% >= {criteria['min_time_improvement_percent']}%")
            else:
                validation["failed_validations"].append(f"Time improvement: {time_improvement:.1f}% < {criteria['min_time_improvement_percent']}%")
                validation["all_optimizations_validated"] = False

            if query_reduction >= criteria["min_query_reduction_percent"]:
                validation["passed_validations"].append(f"Query reduction: {query_reduction:.1f}% >= {criteria['min_query_reduction_percent']}%")
            else:
                validation["failed_validations"].append(f"Query reduction: {query_reduction:.1f}% < {criteria['min_query_reduction_percent']}%")
                validation["all_optimizations_validated"] = False

        # Validate N+1 elimination
        n1_metrics = self.extract_performance_metrics().get("n1_elimination_metrics", {})
        if n1_metrics:
            queries_per_record = n1_metrics.get("avg_queries_per_record", 1)

            if queries_per_record <= criteria["max_queries_per_record"]:
                validation["passed_validations"].append(f"Queries per record: {queries_per_record:.4f} <= {criteria['max_queries_per_record']}")
            else:
                validation["failed_validations"].append(f"Queries per record: {queries_per_record:.4f} > {criteria['max_queries_per_record']}")
                validation["all_optimizations_validated"] = False

        # Validate throughput
        throughput_metrics = self.extract_performance_metrics().get("throughput_performance", {})
        if throughput_metrics:
            avg_throughput = throughput_metrics.get("avg_throughput_records_per_sec", 0)

            if avg_throughput >= criteria["min_throughput_records_per_sec"]:
                validation["passed_validations"].append(f"Average throughput: {avg_throughput:.1f} >= {criteria['min_throughput_records_per_sec']} records/sec")
            else:
                validation["failed_validations"].append(f"Average throughput: {avg_throughput:.1f} < {criteria['min_throughput_records_per_sec']} records/sec")
                validation["all_optimizations_validated"] = False

        return validation

    def generate_recommendations(self) -> Dict[str, List[str]]:
        """Generate recommendations based on test results."""
        recommendations = {
            "immediate_actions": [],
            "production_deployment": [],
            "monitoring_setup": [],
            "future_optimizations": []
        }

        # Check if all optimizations passed
        validation = self.validate_optimizations()

        if validation["all_optimizations_validated"]:
            recommendations["immediate_actions"].extend([
                "✅ All performance optimizations validated successfully",
                "Deploy batch update implementations to production",
                "Update application configuration to use batch processing"
            ])

            recommendations["production_deployment"].extend([
                "Enable batch processing in production environment",
                "Configure optimal batch sizes based on test results",
                "Set up performance monitoring for batch operations"
            ])
        else:
            recommendations["immediate_actions"].extend([
                "❌ Some optimizations did not meet performance targets",
                "Review failed validation criteria",
                "Investigate performance bottlenecks"
            ])

        # Add monitoring recommendations
        recommendations["monitoring_setup"].extend([
            "Monitor query count patterns in production",
            "Set up alerts for batch processing failures",
            "Track memory usage during batch operations",
            "Monitor throughput metrics for batch updates"
        ])

        # Add future optimization recommendations
        recommendations["future_optimizations"].extend([
            "Implement connection pooling for high-concurrency scenarios",
            "Consider read replicas for read-heavy workloads",
            "Implement caching layer for frequently accessed metadata",
            "Explore parallel batch processing for independent operations"
        ])

        return recommendations

    def save_unified_report(self, report: Dict[str, Any], filename: str = None) -> None:
        """Save unified report to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"unified_performance_test_report_{timestamp}.json"

        output_path = Path("reports") / "performance" / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Unified performance report saved to: {output_path}")

    def print_summary_report(self, report: Dict[str, Any]) -> None:
        """Print a summary of the unified report."""
        logger.info("\n" + "="*80)
        logger.info("UNIFIED PERFORMANCE TEST SUITE SUMMARY")
        logger.info("="*80)

        # Test summary
        test_summary = report["test_summary"]
        logger.info(f"Test Execution Summary:")
        logger.info(f"  Total Tests: {test_summary['total_tests']}")
        logger.info(f"  Completed: {test_summary['completed_tests']}")
        logger.info(f"  Failed: {test_summary['failed_tests']}")
        logger.info(f"  Success Rate: {test_summary['success_rate_percent']:.1f}%")
        logger.info(f"  Total Duration: {test_summary['total_execution_time_seconds']:.2f}s")

        # Performance metrics summary
        metrics = report["performance_metrics"]
        logger.info(f"\nKey Performance Metrics:")

        if metrics.get("bulk_update_performance"):
            bulk = metrics["bulk_update_performance"]
            logger.info(f"  Time Improvement: {bulk.get('avg_time_improvement', 0):.1f}%")
            logger.info(f"  Query Reduction: {bulk.get('avg_query_reduction', 0):.1f}%")

        if metrics.get("n1_elimination_metrics"):
            n1 = metrics["n1_elimination_metrics"]
            logger.info(f"  N+1 Elimination Rate: {n1.get('elimination_rate_percent', 0):.1f}%")
            logger.info(f"  Queries per Record: {n1.get('avg_queries_per_record', 0):.4f}")

        if metrics.get("throughput_performance"):
            throughput = metrics["throughput_performance"]
            logger.info(f"  Average Throughput: {throughput.get('avg_throughput_records_per_sec', 0):.1f} records/sec")
            logger.info(f"  Optimal Batch Size: {throughput.get('optimal_batch_size', 0):,} records")

        # Validation results
        validation = report["optimization_validation"]
        logger.info(f"\nOptimization Validation:")
        logger.info(f"  All Optimizations Validated: {'✅' if validation['all_optimizations_validated'] else '❌'}")
        logger.info(f"  Passed Validations: {len(validation['passed_validations'])}")
        logger.info(f"  Failed Validations: {len(validation['failed_validations'])}")

        if validation["failed_validations"]:
            logger.info(f"  Failed Validations:")
            for failure in validation["failed_validations"]:
                logger.info(f"    - {failure}")

        # Recommendations
        recommendations = report["recommendations"]
        logger.info(f"\nKey Recommendations:")

        if recommendations["immediate_actions"]:
            logger.info(f"  Immediate Actions:")
            for action in recommendations["immediate_actions"][:3]:  # Show first 3
                logger.info(f"    - {action}")

        logger.info(f"\n✅ Performance test suite analysis completed!")


async def main():
    """Main entry point for running all performance tests."""
    runner = PerformanceTestRunner()

    try:
        # Run all performance tests
        unified_report = await runner.run_all_performance_tests()

        # Save unified report
        runner.save_unified_report(unified_report)

        # Print summary
        runner.print_summary_report(unified_report)

        return unified_report

    except Exception as e:
        logger.error(f"Performance test suite failed: {e}")
        raise


@pytest.mark.asyncio
async def test_comprehensive_performance_suite():
    """Main test entry point for comprehensive performance testing."""
    return await main()


if __name__ == "__main__":
    # Run comprehensive performance test suite
    asyncio.run(main())
