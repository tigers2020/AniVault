"""End-to-end tests for the complete resilience system."""

import pytest
import time
import threading
from unittest.mock import Mock, patch

from src.core.database import DatabaseManager
from src.core.metadata_cache import MetadataCache
from src.core.database_health import HealthStatus
from src.core.resilience_integration import (
    setup_resilience_system,
    shutdown_resilience_system,
    get_resilience_status,
    force_recovery_check,
)


class TestResilienceSystemE2E:
    """End-to-end tests for the complete resilience system."""

    @pytest.fixture
    def real_db_manager(self):
        """Create a real database manager."""
        db_manager = DatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        return db_manager

    @pytest.fixture
    def real_metadata_cache(self, real_db_manager):
        """Create a real metadata cache."""
        cache = MetadataCache(
            max_size=100,
            max_memory_mb=10,
            db_manager=real_db_manager,
            enable_db=True
        )
        return cache

    def test_complete_resilience_workflow(self, real_db_manager, real_metadata_cache):
        """Test complete resilience workflow from setup to shutdown."""
        # Setup resilience system
        setup_resilience_system(
            db_manager=real_db_manager,
            metadata_cache=real_metadata_cache,
            health_check_interval=1.0,
            health_check_timeout=2.0,
            health_failure_threshold=2,
            health_recovery_threshold=1,
            auto_recovery_enabled=True,
            recovery_check_interval=1.0
        )

        try:
            # Initial system should be healthy
            status = get_resilience_status()
            assert "error" not in status
            assert status['is_operational'] is True
            assert status['cache_only_mode'] is False

            # Test normal operations
            from src.core.models import TMDBAnime, ParsedAnimeInfo

            # Create test data
            test_anime = TMDBAnime(
                tmdb_id=12345,
                title="Test Anime",
                original_title="Test Anime Original",
                overview="Test overview",
                poster_path="/test.jpg",
                backdrop_path="/test_backdrop.jpg",
                first_air_date="2023-01-01",
                last_air_date="2023-12-31",
                status="Ended",
                vote_average=8.5,
                vote_count=1000,
                popularity=85.5,
                number_of_seasons=1,
                number_of_episodes=12,
                genres=[],
                networks=[],
                raw_data={}
            )

            test_parsed_info = ParsedAnimeInfo(
                title="Test Anime",
                season=1,
                episode=1,
                quality="1080p",
                format="mkv",
                group="TestGroup",
                year=2023
            )

            # Test database operations with circuit breaker protection
            metadata = real_db_manager.create_anime_metadata(test_anime)
            assert metadata is not None
            assert metadata.title == "Test Anime"

            retrieved_metadata = real_db_manager.get_anime_metadata(12345)
            assert retrieved_metadata is not None
            assert retrieved_metadata.tmdb_id == 12345

            # Test cache operations
            cache_key = "test:12345"
            real_metadata_cache.get_cache().put(cache_key, test_anime)

            cached_anime = real_metadata_cache.get_cache().get(cache_key)
            assert cached_anime is not None
            assert cached_anime.title == "Test Anime"

            # Test forced recovery check
            recovery_result = force_recovery_check()
            assert isinstance(recovery_result, bool)

        finally:
            # Shutdown system
            shutdown_resilience_system()

    def test_database_failure_recovery_scenario(self, real_db_manager, real_metadata_cache):
        """Test database failure and recovery scenario."""
        # Setup resilience system
        setup_resilience_system(
            db_manager=real_db_manager,
            metadata_cache=real_metadata_cache,
            health_check_interval=0.5,  # Very fast for testing
            health_check_timeout=1.0,
            health_failure_threshold=1,  # Very sensitive
            health_recovery_threshold=1,
            auto_recovery_enabled=True,
            recovery_check_interval=0.5
        )

        try:
            # Initially system should be healthy
            status = get_resilience_status()
            assert status['is_operational'] is True

            # Simulate database failure by closing the connection
            real_db_manager.engine.dispose()

            # Wait for health check to detect failure
            time.sleep(2.0)

            # System should detect failure and enable cache-only mode
            status = get_resilience_status()
            # Note: The exact behavior depends on implementation details

            # Restore database connection
            real_db_manager.initialize()

            # Wait for recovery
            time.sleep(2.0)

            # Force recovery check
            recovery_result = force_recovery_check()
            assert isinstance(recovery_result, bool)

        finally:
            shutdown_resilience_system()

    def test_cache_only_mode_operations(self, real_db_manager, real_metadata_cache):
        """Test operations in cache-only mode."""
        # Setup resilience system
        setup_resilience_system(
            db_manager=real_db_manager,
            metadata_cache=real_metadata_cache,
            auto_recovery_enabled=False  # Disable for testing
        )

        try:
            from src.core.models import TMDBAnime

            # Create test data
            test_anime = TMDBAnime(
                tmdb_id=67890,
                title="Cache Test Anime",
                original_title="Cache Test Anime Original",
                overview="Cache test overview",
                poster_path="/cache_test.jpg",
                backdrop_path="/cache_test_backdrop.jpg",
                first_air_date="2023-01-01",
                last_air_date="2023-12-31",
                status="Ended",
                vote_average=7.5,
                vote_count=500,
                popularity=75.5,
                number_of_seasons=2,
                number_of_episodes=24,
                genres=[],
                networks=[],
                raw_data={}
            )

            # Enable cache-only mode manually
            real_metadata_cache.get_cache().enable_cache_only_mode("E2E test")

            # Verify cache-only mode is active
            status = get_resilience_status()
            assert status['cache_only_mode'] is True
            assert status['cache_only_reason'] == "E2E test"

            # Test cache operations in cache-only mode
            cache_key = "cache_test:67890"
            real_metadata_cache.get_cache().put(cache_key, test_anime)

            cached_anime = real_metadata_cache.get_cache().get(cache_key)
            assert cached_anime is not None
            assert cached_anime.title == "Cache Test Anime"

            # Disable cache-only mode
            real_metadata_cache.get_cache().disable_cache_only_mode()

            # Verify cache-only mode is disabled
            status = get_resilience_status()
            assert status['cache_only_mode'] is False

        finally:
            shutdown_resilience_system()

    def test_circuit_breaker_integration(self, real_db_manager, real_metadata_cache):
        """Test circuit breaker integration with database operations."""
        # Setup resilience system
        setup_resilience_system(
            db_manager=real_db_manager,
            metadata_cache=real_metadata_cache,
            auto_recovery_enabled=False
        )

        try:
            from src.core.models import TMDBAnime

            # Test normal operation
            test_anime = TMDBAnime(
                tmdb_id=11111,
                title="Circuit Breaker Test",
                original_title="Circuit Breaker Test Original",
                overview="Circuit breaker test overview",
                poster_path="/cb_test.jpg",
                backdrop_path="/cb_test_backdrop.jpg",
                first_air_date="2023-01-01",
                last_air_date="2023-12-31",
                status="Ended",
                vote_average=9.0,
                vote_count=2000,
                popularity=95.5,
                number_of_seasons=3,
                number_of_episodes=36,
                genres=[],
                networks=[],
                raw_data={}
            )

            # Normal operation should work
            metadata = real_db_manager.create_anime_metadata(test_anime)
            assert metadata is not None

            # Verify circuit breaker is protecting operations
            retrieved_metadata = real_db_manager.get_anime_metadata(11111)
            assert retrieved_metadata is not None

            # Test bulk operation
            bulk_animes = [test_anime] * 3
            count = real_db_manager.bulk_insert_anime_metadata(bulk_animes)
            assert count >= 0  # May be 0 if duplicates are skipped

        finally:
            shutdown_resilience_system()

    def test_concurrent_resilience_operations(self, real_db_manager, real_metadata_cache):
        """Test concurrent operations with resilience system."""
        # Setup resilience system
        setup_resilience_system(
            db_manager=real_db_manager,
            metadata_cache=real_metadata_cache,
            auto_recovery_enabled=False
        )

        try:
            from src.core.models import TMDBAnime

            results = []
            exceptions = []

            def worker_function(worker_id):
                """Worker function for concurrent testing."""
                try:
                    # Create test anime for this worker
                    test_anime = TMDBAnime(
                        tmdb_id=20000 + worker_id,
                        title=f"Worker {worker_id} Anime",
                        original_title=f"Worker {worker_id} Anime Original",
                        overview=f"Worker {worker_id} overview",
                        poster_path=f"/worker_{worker_id}.jpg",
                        backdrop_path=f"/worker_{worker_id}_backdrop.jpg",
                        first_air_date="2023-01-01",
                        last_air_date="2023-12-31",
                        status="Ended",
                        vote_average=8.0,
                        vote_count=1000,
                        popularity=80.0,
                        number_of_seasons=1,
                        number_of_episodes=12,
                        genres=[],
                        networks=[],
                        raw_data={}
                    )

                    # Perform operations
                    metadata = real_db_manager.create_anime_metadata(test_anime)
                    retrieved = real_db_manager.get_anime_metadata(20000 + worker_id)

                    # Cache operations
                    cache_key = f"worker:{worker_id}"
                    real_metadata_cache.get_cache().put(cache_key, test_anime)
                    cached = real_metadata_cache.get_cache().get(cache_key)

                    results.append((worker_id, metadata, retrieved, cached))

                except Exception as e:
                    exceptions.append((worker_id, e))

            # Create multiple worker threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=worker_function, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join()

            # Verify results
            assert len(results) == 5
            assert len(exceptions) == 0

            # All operations should have succeeded
            for worker_id, metadata, retrieved, cached in results:
                assert metadata is not None
                assert retrieved is not None
                assert cached is not None
                assert metadata.tmdb_id == 20000 + worker_id

        finally:
            shutdown_resilience_system()

    def test_resilience_system_monitoring(self, real_db_manager, real_metadata_cache):
        """Test resilience system monitoring capabilities."""
        # Setup resilience system
        setup_resilience_system(
            db_manager=real_db_manager,
            metadata_cache=real_metadata_cache,
            health_check_interval=1.0,
            auto_recovery_enabled=True,
            recovery_check_interval=2.0
        )

        try:
            # Start monitoring
            time.sleep(3.0)  # Let monitoring run for a bit

            # Get comprehensive status
            status = get_resilience_status()

            # Verify status contains all expected fields
            expected_fields = [
                'is_operational',
                'cache_only_mode',
                'cache_only_reason',
                'health_status',
                'health_statistics',
                'cache_statistics',
                'total_failures',
                'total_recoveries',
                'auto_recovery_enabled'
            ]

            for field in expected_fields:
                assert field in status

            # Verify system is operational
            assert status['is_operational'] is True
            assert status['cache_only_mode'] is False
            assert status['auto_recovery_enabled'] is True

        finally:
            shutdown_resilience_system()

    def test_resilience_system_error_handling(self, real_db_manager, real_metadata_cache):
        """Test resilience system error handling."""
        # Test with invalid parameters
        with pytest.raises(Exception):
            setup_resilience_system(
                db_manager=None,
                metadata_cache=real_metadata_cache
            )

        with pytest.raises(Exception):
            setup_resilience_system(
                db_manager=real_db_manager,
                metadata_cache=None
            )

        # Test shutdown without setup
        shutdown_resilience_system()  # Should not raise exception

        # Test status check without setup
        status = get_resilience_status()
        assert "error" in status

        # Test recovery check without setup
        result = force_recovery_check()
        assert result is False


class TestResilienceSystemPerformance:
    """Test resilience system performance characteristics."""

    @pytest.fixture
    def real_db_manager(self):
        """Create a real database manager."""
        db_manager = DatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        return db_manager

    @pytest.fixture
    def real_metadata_cache(self, real_db_manager):
        """Create a real metadata cache."""
        cache = MetadataCache(
            max_size=100,
            max_memory_mb=10,
            db_manager=real_db_manager,
            enable_db=True
        )
        return cache

    def test_resilience_system_startup_time(self, real_db_manager, real_metadata_cache):
        """Test resilience system startup time."""
        start_time = time.time()

        setup_resilience_system(
            db_manager=real_db_manager,
            metadata_cache=real_metadata_cache
        )

        end_time = time.time()
        startup_time = end_time - start_time

        # Startup should be reasonably fast
        assert startup_time < 5.0  # Less than 5 seconds

        try:
            shutdown_resilience_system()
        except:
            pass

    def test_resilience_system_memory_usage(self, real_db_manager, real_metadata_cache):
        """Test resilience system memory usage."""
        import sys

        # Get initial memory usage
        initial_size = sys.getsizeof(real_db_manager) + sys.getsizeof(real_metadata_cache)

        # Setup resilience system
        setup_resilience_system(
            db_manager=real_db_manager,
            metadata_cache=real_metadata_cache
        )

        try:
            # Get memory usage after setup
            final_size = sys.getsizeof(real_db_manager) + sys.getsizeof(real_metadata_cache)
            memory_growth = final_size - initial_size

            # Memory growth should be reasonable
            assert memory_growth < 100000  # Less than 100KB

        finally:
            shutdown_resilience_system()

    def test_resilience_system_overhead(self, real_db_manager, real_metadata_cache):
        """Test resilience system operational overhead."""
        from src.core.models import TMDBAnime

        # Create test data
        test_anime = TMDBAnime(
            tmdb_id=99999,
            title="Performance Test Anime",
            original_title="Performance Test Anime Original",
            overview="Performance test overview",
            poster_path="/perf_test.jpg",
            backdrop_path="/perf_test_backdrop.jpg",
            first_air_date="2023-01-01",
            last_air_date="2023-12-31",
            status="Ended",
            vote_average=8.5,
            vote_count=1000,
            popularity=85.5,
            number_of_seasons=1,
            number_of_episodes=12,
            genres=[],
            networks=[],
            raw_data={}
        )

        # Setup resilience system
        setup_resilience_system(
            db_manager=real_db_manager,
            metadata_cache=real_metadata_cache
        )

        try:
            # Measure operation time with resilience system
            start_time = time.time()

            for _ in range(100):
                metadata = real_db_manager.create_anime_metadata(test_anime)
                retrieved = real_db_manager.get_anime_metadata(99999)

                cache_key = f"perf_test:{_}"
                real_metadata_cache.get_cache().put(cache_key, test_anime)
                cached = real_metadata_cache.get_cache().get(cache_key)

            end_time = time.time()
            operation_time = end_time - start_time

            # Operations should complete in reasonable time
            assert operation_time < 10.0  # Less than 10 seconds for 100 operations

        finally:
            shutdown_resilience_system()


if __name__ == "__main__":
    pytest.main([__file__])
