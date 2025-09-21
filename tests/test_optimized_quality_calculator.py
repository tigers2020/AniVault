"""Test cases for optimized quality score calculator."""

import time
import pytest
from unittest.mock import Mock
from src.core.optimized_quality_calculator import (
    OptimizedQualityCalculator,
    QualityScoreConfig,
    QualityScoreCalculatorFactory,
    LegacyQualityCalculator
)


class TestOptimizedQualityCalculator:
    """Test cases for the optimized quality score calculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = QualityScoreConfig(
            similarity_weight=0.6,
            year_weight=0.2,
            language_weight=0.2
        )
        self.calculator = OptimizedQualityCalculator(self.config)
        self.legacy_calculator = LegacyQualityCalculator()

    def test_quality_score_calculation_accuracy(self):
        """Test that optimized calculator produces accurate results."""
        test_cases = [
            {
                "result": {
                    "title": "Attack on Titan",
                    "original_title": "進撃の巨人",
                    "release_date": "2023-01-01",
                    "original_language": "ja",
                    "translations": {
                        "translations": [
                            {"iso_639_1": "ko", "name": "Korean"},
                            {"iso_639_1": "en", "name": "English"}
                        ]
                    }
                },
                "query": "Attack on Titan (2023)",
                "language": "ko-KR",
                "year_hint": 2023,
                "expected_min_score": 0.8
            },
            {
                "result": {
                    "title": "One Piece",
                    "original_title": "ワンピース",
                    "first_air_date": "1999-10-20",
                    "original_language": "ja",
                    "translations": {
                        "translations": [
                            {"iso_639_1": "ko", "name": "Korean"}
                        ]
                    }
                },
                "query": "One Piece Season 1",
                "language": "ko-KR",
                "year_hint": None,
                "expected_min_score": 0.6
            },
            {
                "result": {
                    "title": "Naruto Shippuden",
                    "original_title": "ナルト疾風伝",
                    "first_air_date": "2007-02-15",
                    "original_language": "ja",
                    "translations": {
                        "translations": [
                            {"iso_639_1": "en", "name": "English"}
                        ]
                    }
                },
                "query": "Naruto Shippuden 720p",
                "language": "en-US",
                "year_hint": None,
                "expected_min_score": 0.5
            }
        ]

        for case in test_cases:
            score = self.calculator.calculate_quality_score(
                case["result"],
                case["query"],
                case["language"],
                case["year_hint"]
            )

            assert 0.0 <= score <= 1.0, f"Score out of range: {score}"
            assert score >= case["expected_min_score"], f"Score too low: {score} < {case['expected_min_score']}"

    def test_optimized_vs_legacy_accuracy(self):
        """Test that optimized calculator produces same results as legacy."""
        test_cases = [
            {
                "result": {
                    "title": "Attack on Titan",
                    "original_title": "進撃の巨人",
                    "release_date": "2023-01-01",
                    "original_language": "ja",
                    "translations": {
                        "translations": [
                            {"iso_639_1": "ko", "name": "Korean"}
                        ]
                    }
                },
                "query": "Attack on Titan (2023)",
                "language": "ko-KR",
                "year_hint": 2023
            },
            {
                "result": {
                    "title": "One Piece",
                    "original_title": "ワンピース",
                    "first_air_date": "1999-10-20",
                    "original_language": "ja",
                    "translations": {
                        "translations": []
                    }
                },
                "query": "One Piece Season 1",
                "language": "en-US",
                "year_hint": None
            },
            {
                "result": {
                    "title": "Naruto Shippuden",
                    "original_title": "ナルト疾風伝",
                    "first_air_date": "2007-02-15",
                    "original_language": "ja",
                    "translations": {
                        "translations": [
                            {"iso_639_1": "en", "name": "English"}
                        ]
                    }
                },
                "query": "Naruto Shippuden 720p",
                "language": "en-US",
                "year_hint": None
            }
        ]

        for case in test_cases:
            optimized_score = self.calculator.calculate_quality_score(
                case["result"],
                case["query"],
                case["language"],
                case["year_hint"]
            )

            legacy_score = self.legacy_calculator.calculate_quality_score(
                case["result"],
                case["query"],
                case["language"],
                case["year_hint"]
            )

            # Scores should be very close (within 0.001 tolerance for floating point)
            assert abs(optimized_score - legacy_score) < 0.001, \
                f"Score mismatch: optimized={optimized_score}, legacy={legacy_score}"

    def test_performance_improvement(self):
        """Test that optimized calculator is faster than legacy."""
        test_cases = [
            {
                "result": {
                    "title": "Attack on Titan",
                    "original_title": "進撃の巨人",
                    "release_date": "2023-01-01",
                    "original_language": "ja",
                    "translations": {
                        "translations": [
                            {"iso_639_1": "ko", "name": "Korean"}
                        ]
                    }
                },
                "query": "Attack on Titan (2023)",
                "language": "ko-KR",
                "year_hint": 2023
            },
            {
                "result": {
                    "title": "One Piece",
                    "original_title": "ワンピース",
                    "first_air_date": "1999-10-20",
                    "original_language": "ja",
                    "translations": {
                        "translations": []
                    }
                },
                "query": "One Piece Season 1",
                "language": "en-US",
                "year_hint": None
            },
            {
                "result": {
                    "title": "Naruto Shippuden",
                    "original_title": "ナルト疾風伝",
                    "first_air_date": "2007-02-15",
                    "original_language": "ja",
                    "translations": {
                        "translations": [
                            {"iso_639_1": "en", "name": "English"}
                        ]
                    }
                },
                "query": "Naruto Shippuden 720p",
                "language": "en-US",
                "year_hint": None
            }
        ]

        iterations = 1000

        # Time optimized calculator
        start_time = time.time()
        for _ in range(iterations):
            for case in test_cases:
                self.calculator.calculate_quality_score(
                    case["result"],
                    case["query"],
                    case["language"],
                    case["year_hint"]
                )
        optimized_time = time.time() - start_time

        # Time legacy calculator
        start_time = time.time()
        for _ in range(iterations):
            for case in test_cases:
                self.legacy_calculator.calculate_quality_score(
                    case["result"],
                    case["query"],
                    case["language"],
                    case["year_hint"]
                )
        legacy_time = time.time() - start_time

        # Optimized should be faster
        assert optimized_time < legacy_time, \
            f"Optimized calculator not faster: {optimized_time:.3f}s vs {legacy_time:.3f}s"

        # Calculate improvement percentage
        improvement = (legacy_time - optimized_time) / legacy_time * 100
        print(f"Performance improvement: {improvement:.1f}%")

        # Should have at least 20% improvement
        assert improvement >= 20.0, f"Insufficient performance improvement: {improvement:.1f}%"

    def test_caching_effectiveness(self):
        """Test that caching improves performance for repeated calculations."""
        # Test case with repeated queries
        result = {
            "title": "Attack on Titan",
            "original_title": "進撃の巨人",
            "release_date": "2023-01-01",
            "original_language": "ja",
            "translations": {
                "translations": [
                    {"iso_639_1": "ko", "name": "Korean"}
                ]
            }
        }

        query = "Attack on Titan (2023)"
        language = "ko-KR"
        year_hint = 2023

        # First run (cold cache)
        start_time = time.time()
        for _ in range(100):
            self.calculator.calculate_quality_score(result, query, language, year_hint)
        cold_time = time.time() - start_time

        # Second run (warm cache)
        start_time = time.time()
        for _ in range(100):
            self.calculator.calculate_quality_score(result, query, language, year_hint)
        warm_time = time.time() - start_time

        # Warm cache should be faster
        assert warm_time < cold_time, \
            f"Warm cache not faster: {warm_time:.3f}s vs {cold_time:.3f}s"

        # Check cache stats
        cache_stats = self.calculator.get_cache_stats()
        assert cache_stats["token_normalization_cache"] > 0, "Token normalization cache not working"
        assert cache_stats["year_extraction_cache"] > 0, "Year extraction cache not working"

    def test_token_normalization_optimization(self):
        """Test that token normalization is optimized."""
        test_queries = [
            "Attack on Titan [1080p] [SubsPlease]",
            "One Piece Season 1 (2023) [720p]",
            "Naruto Shippuden - Episode 1 [1080p] [Fansub]",
            "Dragon Ball Z - Episode 1 [1080p] [60fps]",
            "My Hero Academia S01E01 [1080p] [Dual Audio]"
        ]

        # Time optimized normalization
        start_time = time.time()
        for _ in range(1000):
            for query in test_queries:
                tokens = self.calculator._normalize_query_tokens_optimized(query)
                assert isinstance(tokens, tuple)
        optimized_time = time.time() - start_time

        # Time legacy normalization
        start_time = time.time()
        for _ in range(1000):
            for query in test_queries:
                tokens = self.legacy_calculator._normalize_query_tokens(query)
                assert isinstance(tokens, set)
        legacy_time = time.time() - start_time

        # Optimized should be faster
        assert optimized_time < legacy_time, \
            f"Optimized normalization not faster: {optimized_time:.3f}s vs {legacy_time:.3f}s"

    def test_jaccard_similarity_optimization(self):
        """Test that Jaccard similarity calculation is optimized."""
        test_cases = [
            (("attack", "on", "titan"), ("attack", "on", "titan")),
            (("one", "piece"), ("one", "piece", "season")),
            (("naruto", "shippuden"), ("naruto", "shippuden", "episode")),
            (("dragon", "ball", "z"), ("dragon", "ball", "z", "episode")),
            (("my", "hero", "academia"), ("my", "hero", "academia", "season"))
        ]

        # Time optimized Jaccard similarity
        start_time = time.time()
        for _ in range(1000):
            for set1, set2 in test_cases:
                similarity = self.calculator._jaccard_similarity_optimized(set1, set2)
                assert 0.0 <= similarity <= 1.0
        optimized_time = time.time() - start_time

        # Time legacy Jaccard similarity
        start_time = time.time()
        for _ in range(1000):
            for set1, set2 in test_cases:
                similarity = self.legacy_calculator._jaccard_similarity(set(set1), set(set2))
                assert 0.0 <= similarity <= 1.0
        legacy_time = time.time() - start_time

        # Optimized should be faster
        assert optimized_time < legacy_time, \
            f"Optimized Jaccard similarity not faster: {optimized_time:.3f}s vs {legacy_time:.3f}s"

    def test_year_score_caching(self):
        """Test that year score calculation uses caching effectively."""
        test_cases = [
            (2023, 2023),  # Exact match
            (2023, 2022),  # 1 year difference
            (2023, 2020),  # 3 years difference
            (2023, 2015),  # 8 years difference
            (None, 2023),  # No result year
            (2023, None),  # No hint year
        ]

        # First run (cold cache)
        start_time = time.time()
        for _ in range(100):
            for result_year, year_hint in test_cases:
                score = self.calculator._calculate_year_score_optimized(result_year, year_hint)
                assert 0.0 <= score <= 1.0
        cold_time = time.time() - start_time

        # Second run (warm cache)
        start_time = time.time()
        for _ in range(100):
            for result_year, year_hint in test_cases:
                score = self.calculator._calculate_year_score_optimized(result_year, year_hint)
                assert 0.0 <= score <= 1.0
        warm_time = time.time() - start_time

        # Warm cache should be faster
        assert warm_time < cold_time, \
            f"Year score caching not effective: {warm_time:.3f}s vs {cold_time:.3f}s"

    def test_language_score_optimization(self):
        """Test that language score calculation is optimized."""
        test_cases = [
            {
                "result": {
                    "original_language": "ja",
                    "translations": {
                        "translations": [
                            {"iso_639_1": "ko", "name": "Korean"},
                            {"iso_639_1": "en", "name": "English"}
                        ]
                    }
                },
                "language": "ko-KR"
            },
            {
                "result": {
                    "original_language": "en",
                    "translations": {
                        "translations": [
                            {"iso_639_1": "ja", "name": "Japanese"}
                        ]
                    }
                },
                "language": "en-US"
            },
            {
                "result": {
                    "original_language": "ja",
                    "translations": {
                        "translations": []
                    }
                },
                "language": "ko-KR"
            }
        ]

        # Time optimized language score
        start_time = time.time()
        for _ in range(1000):
            for case in test_cases:
                score = self.calculator._calculate_language_score_optimized(
                    case["result"], case["language"]
                )
                assert 0.0 <= score <= 1.0
        optimized_time = time.time() - start_time

        # Time legacy language score
        start_time = time.time()
        for _ in range(1000):
            for case in test_cases:
                score = self.legacy_calculator._calculate_language_score(
                    case["result"], case["language"]
                )
                assert 0.0 <= score <= 1.0
        legacy_time = time.time() - start_time

        # Optimized should be faster
        assert optimized_time < legacy_time, \
            f"Optimized language score not faster: {optimized_time:.3f}s vs {legacy_time:.3f}s"

    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Empty result
        empty_result = {}
        score = self.calculator.calculate_quality_score(empty_result, "test", "ko-KR", None)
        assert 0.0 <= score <= 1.0

        # Result with missing fields
        partial_result = {"title": "Test"}
        score = self.calculator.calculate_quality_score(partial_result, "test", "ko-KR", None)
        assert 0.0 <= score <= 1.0

        # Very long query
        long_query = "Attack on Titan " * 100
        score = self.calculator.calculate_quality_score(
            {"title": "Attack on Titan", "original_title": "進撃の巨人"},
            long_query,
            "ko-KR",
            None
        )
        assert 0.0 <= score <= 1.0

        # Special characters in query
        special_query = "Attack on Titan [1080p] (2023) - Episode 1"
        score = self.calculator.calculate_quality_score(
            {"title": "Attack on Titan", "original_title": "進撃の巨人"},
            special_query,
            "ko-KR",
            2023
        )
        assert 0.0 <= score <= 1.0

    def test_cache_management(self):
        """Test cache management functionality."""
        # Test cache clearing
        self.calculator.clear_caches()
        cache_stats = self.calculator.get_cache_stats()

        # All caches should be empty after clearing
        assert cache_stats["year_extraction_cache"] == 0
        assert cache_stats["token_normalization_cache"] == 0
        assert cache_stats["language_code_cache"] == 0
        assert cache_stats["year_diff_cache"] == 0

        # Test cache stats after some operations
        result = {
            "title": "Attack on Titan",
            "original_title": "進撃の巨人",
            "release_date": "2023-01-01",
            "original_language": "ja",
            "translations": {
                "translations": [
                    {"iso_639_1": "ko", "name": "Korean"}
                ]
            }
        }

        self.calculator.calculate_quality_score(result, "Attack on Titan (2023)", "ko-KR", 2023)

        cache_stats = self.calculator.get_cache_stats()
        assert cache_stats["year_extraction_cache"] > 0
        assert cache_stats["token_normalization_cache"] > 0
        assert cache_stats["language_code_cache"] > 0

    def test_factory_methods(self):
        """Test factory methods for creating calculators."""
        # Test optimized calculator factory
        calculator = QualityScoreCalculatorFactory.create_optimized_calculator(
            similarity_weight=0.7,
            year_weight=0.2,
            language_weight=0.1
        )
        assert isinstance(calculator, OptimizedQualityCalculator)
        assert calculator.config.similarity_weight == 0.7
        assert calculator.config.year_weight == 0.2
        assert calculator.config.language_weight == 0.1

        # Test legacy calculator factory
        legacy_calculator = QualityScoreCalculatorFactory.create_legacy_calculator()
        assert isinstance(legacy_calculator, LegacyQualityCalculator)

    def test_memory_usage(self):
        """Test that optimized calculator doesn't use excessive memory."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Run many quality score calculations
        for _ in range(1000):
            result = {
                "title": "Attack on Titan",
                "original_title": "進撃の巨人",
                "release_date": "2023-01-01",
                "original_language": "ja",
                "translations": {
                    "translations": [
                        {"iso_639_1": "ko", "name": "Korean"}
                    ]
                }
            }
            self.calculator.calculate_quality_score(result, "Attack on Titan (2023)", "ko-KR", 2023)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (< 20MB)
        assert memory_increase < 20 * 1024 * 1024, f"Excessive memory usage: {memory_increase / 1024 / 1024:.2f}MB"

    def test_deterministic_results(self):
        """Test that results are deterministic and consistent."""
        result = {
            "title": "Attack on Titan",
            "original_title": "進撃の巨人",
            "release_date": "2023-01-01",
            "original_language": "ja",
            "translations": {
                "translations": [
                    {"iso_639_1": "ko", "name": "Korean"}
                ]
            }
        }

        query = "Attack on Titan (2023)"
        language = "ko-KR"
        year_hint = 2023

        # Calculate score multiple times
        scores = []
        for _ in range(100):
            score = self.calculator.calculate_quality_score(result, query, language, year_hint)
            scores.append(score)

        # All scores should be identical (deterministic)
        assert all(score == scores[0] for score in scores), "Results are not deterministic"

        # Score should be high for this perfect match
        assert scores[0] > 0.8, f"Expected high quality score, got {scores[0]}"
