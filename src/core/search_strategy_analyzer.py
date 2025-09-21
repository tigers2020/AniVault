"""Search strategy performance analyzer for TMDB optimization.

This module provides tools to analyze the effectiveness of different
search strategies and measure API call patterns.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .tmdb_client import TMDBClient

logger = logging.getLogger(__name__)


@dataclass
class StrategyMetrics:
    """Metrics for a single search strategy."""

    strategy_name: str
    api_calls_made: int = 0
    success_count: int = 0
    total_queries: int = 0
    avg_quality_score: float = 0.0
    avg_response_time: float = 0.0
    high_confidence_matches: int = 0
    medium_confidence_matches: int = 0
    low_confidence_matches: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_queries == 0:
            return 0.0
        return self.success_count / self.total_queries

    @property
    def high_confidence_rate(self) -> float:
        """Calculate high confidence match rate."""
        if self.total_queries == 0:
            return 0.0
        return self.high_confidence_matches / self.total_queries


@dataclass
class SearchAnalysisResult:
    """Result of search strategy analysis."""

    query: str
    total_api_calls: int = 0
    strategies_used: list[str] = field(default_factory=list)
    success: bool = False
    final_quality_score: float = 0.0
    response_time: float = 0.0
    early_exit_strategy: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class SearchStrategyAnalyzer:
    """Analyzer for TMDB search strategy performance."""

    def __init__(self, tmdb_client: TMDBClient) -> None:
        """Initialize the analyzer.

        Args:
            tmdb_client: TMDB client instance
        """
        self.tmdb_client = tmdb_client
        self.metrics: dict[str, StrategyMetrics] = {}
        self.analysis_results: list[SearchAnalysisResult] = []

        # Initialize metrics for each strategy
        self._initialize_metrics()

    def _initialize_metrics(self) -> None:
        """Initialize metrics for all strategies."""
        strategies = [
            "initial_multi_search",
            "normalized_query",
            "word_reduction",
            "language_fallback",
        ]

        for strategy in strategies:
            self.metrics[strategy] = StrategyMetrics(strategy_name=strategy)

    def analyze_search_strategies(self, test_queries: list[str]) -> dict[str, Any]:
        """Analyze search strategies with test queries.

        Args:
            test_queries: List of test search queries

        Returns:
            Analysis results summary
        """
        logger.info(f"Starting search strategy analysis with {len(test_queries)} queries")

        # Reset metrics
        self._initialize_metrics()
        self.analysis_results.clear()

        for query in test_queries:
            logger.info(f"Analyzing query: '{query}'")
            result = self._analyze_single_query(query)
            self.analysis_results.append(result)

        return self._generate_summary()

    def _analyze_single_query(self, query: str) -> SearchAnalysisResult:
        """Analyze a single query through all strategies.

        Args:
            query: Search query to analyze

        Returns:
            Analysis result for the query
        """
        start_time = time.time()
        result = SearchAnalysisResult(query=query)

        try:
            # Track API calls by patching the search method
            original_search = self.tmdb_client.search_multi

            def tracked_search(*args: Any, **kwargs: Any) -> Any:
                result.total_api_calls += 1
                return original_search(*args, **kwargs)

            # Apply the patch
            self.tmdb_client.search_multi = tracked_search

            # Run comprehensive search
            search_results, _needs_selection = self.tmdb_client.search_comprehensive(query)

            # Restore original method
            self.tmdb_client.search_multi = original_search

            result.success = search_results is not None and len(search_results) > 0
            result.response_time = time.time() - start_time

            if search_results:
                result.final_quality_score = max(r.quality_score for r in search_results)

                # Categorize by quality score
                high_confidence = self.tmdb_client.config.high_confidence_threshold
                medium_confidence = self.tmdb_client.config.medium_confidence_threshold

                for search_result in search_results:
                    if search_result.quality_score >= high_confidence:
                        result.details["high_confidence_matches"] = (
                            result.details.get("high_confidence_matches", 0) + 1
                        )
                    elif search_result.quality_score >= medium_confidence:
                        result.details["medium_confidence_matches"] = (
                            result.details.get("medium_confidence_matches", 0) + 1
                        )
                    else:
                        result.details["low_confidence_matches"] = (
                            result.details.get("low_confidence_matches", 0) + 1
                        )

            # Determine which strategies were used based on API calls
            if result.total_api_calls >= 1:
                result.strategies_used.append("initial_multi_search")
            if result.total_api_calls >= 2:
                result.strategies_used.append("normalized_query")
            if result.total_api_calls >= 3:
                result.strategies_used.append("word_reduction")
            if result.total_api_calls >= 4:
                result.strategies_used.append("language_fallback")

            # Update metrics
            self._update_metrics(result)

        except Exception as e:
            logger.error(f"Error analyzing query '{query}': {e}")
            result.details["error"] = str(e)

        return result

    def _update_metrics(self, result: SearchAnalysisResult) -> None:
        """Update metrics based on analysis result.

        Args:
            result: Analysis result to process
        """
        for strategy in result.strategies_used:
            if strategy in self.metrics:
                metrics = self.metrics[strategy]
                metrics.total_queries += 1
                metrics.api_calls_made += 1

                if result.success:
                    metrics.success_count += 1

                if result.final_quality_score > 0:
                    # Update average quality score
                    total_score = metrics.avg_quality_score * (metrics.success_count - 1)
                    metrics.avg_quality_score = (
                        total_score + result.final_quality_score
                    ) / metrics.success_count

                # Update response time
                total_time = metrics.avg_response_time * (metrics.api_calls_made - 1)
                metrics.avg_response_time = (
                    total_time + result.response_time
                ) / metrics.api_calls_made

                # Update confidence match counts
                high_conf = result.details.get("high_confidence_matches", 0)
                medium_conf = result.details.get("medium_confidence_matches", 0)
                low_conf = result.details.get("low_confidence_matches", 0)

                metrics.high_confidence_matches += high_conf
                metrics.medium_confidence_matches += medium_conf
                metrics.low_confidence_matches += low_conf

    def _generate_summary(self) -> dict[str, Any]:
        """Generate analysis summary.

        Returns:
            Summary of analysis results
        """
        total_queries = len(self.analysis_results)
        successful_queries = sum(1 for r in self.analysis_results if r.success)
        total_api_calls = sum(r.total_api_calls for r in self.analysis_results)

        # Calculate average metrics per strategy
        strategy_summary = {}
        for strategy, metrics in self.metrics.items():
            if metrics.total_queries > 0:
                strategy_summary[strategy] = {
                    "success_rate": metrics.success_rate,
                    "high_confidence_rate": metrics.high_confidence_rate,
                    "avg_quality_score": metrics.avg_quality_score,
                    "avg_response_time": metrics.avg_response_time,
                    "api_calls_made": metrics.api_calls_made,
                    "total_queries": metrics.total_queries,
                }

        # API call distribution
        api_call_distribution = {}
        for result in self.analysis_results:
            calls = result.total_api_calls
            api_call_distribution[calls] = api_call_distribution.get(calls, 0) + 1

        return {
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "overall_success_rate": successful_queries / total_queries if total_queries > 0 else 0,
            "total_api_calls": total_api_calls,
            "avg_api_calls_per_query": total_api_calls / total_queries if total_queries > 0 else 0,
            "strategy_metrics": strategy_summary,
            "api_call_distribution": api_call_distribution,
            "recommendations": self._generate_recommendations(),
        }

    def _generate_recommendations(self) -> list[str]:
        """Generate recommendations based on analysis.

        Returns:
            List of recommendations
        """
        recommendations = []

        # Check if we can reduce API calls
        total_calls = sum(r.total_api_calls for r in self.analysis_results)
        avg_calls = total_calls / len(self.analysis_results) if self.analysis_results else 0

        if avg_calls > 3:
            recommendations.append(
                f"Current average API calls per query: {avg_calls:.2f}. Target: 3.0"
            )

        # Analyze strategy effectiveness
        strategy_effectiveness = []
        for strategy, metrics in self.metrics.items():
            if metrics.total_queries > 0:
                effectiveness = metrics.success_rate * metrics.high_confidence_rate
                strategy_effectiveness.append((strategy, effectiveness))

        # Sort by effectiveness
        strategy_effectiveness.sort(key=lambda x: x[1], reverse=True)

        if len(strategy_effectiveness) >= 3:
            top_3 = [s[0] for s in strategy_effectiveness[:3]]
            recommendations.append(f"Top 3 most effective strategies: {', '.join(top_3)}")

        # Check for early exit opportunities
        early_exits = sum(1 for r in self.analysis_results if r.total_api_calls < 4)
        if early_exits > 0:
            recommendations.append(
                f"Early exit opportunities: {early_exits}/{len(self.analysis_results)} queries could exit early"
            )

        return recommendations

    def get_detailed_results(self) -> list[SearchAnalysisResult]:
        """Get detailed analysis results.

        Returns:
            List of detailed analysis results
        """
        return self.analysis_results.copy()

    def export_analysis(self, filename: str) -> None:
        """Export analysis results to file.

        Args:
            filename: Output filename
        """
        import json

        export_data = {
            "summary": self._generate_summary(),
            "detailed_results": [
                {
                    "query": r.query,
                    "total_api_calls": r.total_api_calls,
                    "strategies_used": r.strategies_used,
                    "success": r.success,
                    "final_quality_score": r.final_quality_score,
                    "response_time": r.response_time,
                    "early_exit_strategy": r.early_exit_strategy,
                    "details": r.details,
                }
                for r in self.analysis_results
            ],
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Analysis results exported to {filename}")
