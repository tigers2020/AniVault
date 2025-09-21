"""Thread-safe TMDB client pool manager for optimized parallel processing.

This module provides a thread-safe pool of TMDB client instances that can be
efficiently reused across multiple threads to minimize object creation overhead
and resource consumption.
"""

import threading
import time
from collections import deque
from contextlib import contextmanager
from typing import Any, Generator, Optional

from .tmdb_client import TMDBClient, TMDBConfig


class TMDBClientPool:
    """Thread-safe pool manager for TMDB client instances.
    
    This class manages a pool of TMDB client instances that can be safely
    shared across multiple threads. It provides methods to acquire and release
    clients, ensuring optimal resource utilization and thread safety.
    
    Attributes:
        _pool: Queue of available TMDB client instances
        _lock: Thread lock for pool operations
        _created_clients: Total number of clients created
        _active_clients: Number of clients currently in use
        _max_pool_size: Maximum number of clients in the pool
        _config: TMDB configuration for creating new clients
    """
    
    def __init__(
        self, 
        config: TMDBConfig, 
        initial_size: int = 2, 
        max_size: int = 8,
        pool_name: str = "TMDBPool"
    ):
        """Initialize the TMDB client pool.
        
        Args:
            config: TMDB configuration for creating clients
            initial_size: Initial number of clients to create
            max_size: Maximum number of clients in the pool
            pool_name: Name for logging and identification
        """
        self._config = config
        self._max_pool_size = max_size
        self._pool_name = pool_name
        self._lock = threading.RLock()  # Reentrant lock for nested operations
        self._pool: deque[TMDBClient] = deque()
        self._created_clients = 0
        self._active_clients = 0
        self._stats = {
            "total_requests": 0,
            "pool_hits": 0,
            "pool_misses": 0,
            "clients_created": 0,
            "clients_destroyed": 0,
        }
        
        # Initialize pool with initial clients
        self._initialize_pool(initial_size)
        
    def _initialize_pool(self, initial_size: int) -> None:
        """Initialize the pool with initial client instances.
        
        Args:
            initial_size: Number of initial clients to create
        """
        with self._lock:
            for _ in range(min(initial_size, self._max_pool_size)):
                client = self._create_client()
                self._pool.append(client)
                self._created_clients += 1
                self._stats["clients_created"] += 1
                
    def _create_client(self) -> TMDBClient:
        """Create a new TMDB client instance.
        
        Returns:
            New TMDBClient instance
        """
        # Create a copy of the config to avoid sharing state
        client_config = TMDBConfig(
            api_key=self._config.api_key,
            language=self._config.language,
            fallback_language=self._config.fallback_language,
            base_url=self._config.base_url,
            image_base_url=self._config.image_base_url,
            timeout=self._config.timeout,
            max_retries=self._config.max_retries,
            retry_delay_base=self._config.retry_delay_base,
            retry_delay_max=self._config.retry_delay_max,
            cache_only_mode=self._config.cache_only_mode,
            high_confidence_threshold=self._config.high_confidence_threshold,
            medium_confidence_threshold=self._config.medium_confidence_threshold,
            similarity_weight=self._config.similarity_weight,
            year_weight=self._config.year_weight,
            language_weight=self._config.language_weight,
            include_person_results=self._config.include_person_results,
        )
        
        return TMDBClient(client_config)
    
    def acquire(self, timeout: Optional[float] = None) -> TMDBClient:
        """Acquire a TMDB client from the pool.
        
        Args:
            timeout: Maximum time to wait for a client (None for no timeout)
            
        Returns:
            TMDBClient instance from the pool
            
        Raises:
            TimeoutError: If timeout is reached and no client is available
        """
        self._stats["total_requests"] += 1
        
        with self._lock:
            # Try to get an existing client from the pool
            if self._pool:
                client = self._pool.popleft()
                self._active_clients += 1
                self._stats["pool_hits"] += 1
                return client
            
            # Pool is empty, try to create a new client if under limit
            if self._created_clients < self._max_pool_size:
                client = self._create_client()
                self._created_clients += 1
                self._active_clients += 1
                self._stats["clients_created"] += 1
                self._stats["pool_misses"] += 1
                return client
            
            # Pool is at max capacity, wait for a client to be released
            if timeout is None:
                # Wait indefinitely
                while not self._pool:
                    self._lock.wait()
                client = self._pool.popleft()
                self._active_clients += 1
                self._stats["pool_hits"] += 1
                return client
            else:
                # Wait with timeout
                start_time = time.time()
                while not self._pool:
                    remaining_time = timeout - (time.time() - start_time)
                    if remaining_time <= 0:
                        raise TimeoutError(f"Timeout waiting for TMDB client from pool {self._pool_name}")
                    self._lock.wait(remaining_time)
                
                client = self._pool.popleft()
                self._active_clients += 1
                self._stats["pool_hits"] += 1
                return client
    
    def release(self, client: TMDBClient) -> None:
        """Release a TMDB client back to the pool.
        
        Args:
            client: TMDBClient instance to return to the pool
        """
        with self._lock:
            if self._active_clients > 0:
                self._active_clients -= 1
            
            # Add client back to pool
            self._pool.append(client)
            
            # Notify waiting threads
            self._lock.notify()
    
    @contextmanager
    def get_client(self, timeout: Optional[float] = None) -> Generator[TMDBClient, None, None]:
        """Context manager for acquiring and automatically releasing a TMDB client.
        
        Args:
            timeout: Maximum time to wait for a client
            
        Yields:
            TMDBClient instance from the pool
            
        Example:
            with pool.get_client() as client:
                results = client.search_tv_series("Attack on Titan")
        """
        client = None
        try:
            client = self.acquire(timeout)
            yield client
        finally:
            if client is not None:
                self.release(client)
    
    def get_pool_stats(self) -> dict[str, Any]:
        """Get current pool statistics.
        
        Returns:
            Dictionary containing pool statistics
        """
        with self._lock:
            return {
                "pool_name": self._pool_name,
                "pool_size": len(self._pool),
                "active_clients": self._active_clients,
                "created_clients": self._created_clients,
                "max_pool_size": self._max_pool_size,
                "utilization_rate": (
                    self._active_clients / self._max_pool_size 
                    if self._max_pool_size > 0 else 0.0
                ),
                "pool_hit_rate": (
                    self._stats["pool_hits"] / self._stats["total_requests"]
                    if self._stats["total_requests"] > 0 else 0.0
                ),
                **self._stats,
            }
    
    def resize_pool(self, new_max_size: int) -> None:
        """Resize the pool to a new maximum size.
        
        Args:
            new_max_size: New maximum pool size
        """
        with self._lock:
            old_max_size = self._max_pool_size
            self._max_pool_size = new_max_size
            
            # If shrinking, remove excess clients
            if new_max_size < old_max_size:
                excess_clients = len(self._pool) - new_max_size
                for _ in range(excess_clients):
                    if self._pool:
                        self._pool.popleft()
                        self._created_clients -= 1
                        self._stats["clients_destroyed"] += 1
    
    def clear_pool(self) -> None:
        """Clear all clients from the pool."""
        with self._lock:
            destroyed_count = len(self._pool)
            self._pool.clear()
            self._created_clients = 0
            self._active_clients = 0
            self._stats["clients_destroyed"] += destroyed_count
    
    def health_check(self) -> dict[str, Any]:
        """Perform a health check on the pool.
        
        Returns:
            Dictionary containing health check results
        """
        with self._lock:
            stats = self.get_pool_stats()
            
            # Check for potential issues
            issues = []
            
            # Check utilization rate
            if stats["utilization_rate"] > 0.9:
                issues.append("High utilization rate - consider increasing pool size")
            
            # Check pool hit rate
            if stats["pool_hit_rate"] < 0.5 and stats["total_requests"] > 10:
                issues.append("Low pool hit rate - clients may not be released properly")
            
            # Check for active clients without pool availability
            if stats["active_clients"] > 0 and len(self._pool) == 0:
                issues.append("All clients are active - potential resource contention")
            
            return {
                "healthy": len(issues) == 0,
                "issues": issues,
                "stats": stats,
            }


class ThreadLocalTMDBClient:
    """Thread-local TMDB client manager using threading.local().
    
    This class provides a thread-safe way to manage TMDB client instances
    by ensuring each thread gets its own client instance. This approach
    avoids the complexity of pool management while ensuring thread safety.
    
    Attributes:
        _local: Thread-local storage for client instances
        _config: TMDB configuration for creating clients
    """
    
    def __init__(self, config: TMDBConfig):
        """Initialize the thread-local TMDB client manager.
        
        Args:
            config: TMDB configuration for creating clients
        """
        self._local = threading.local()
        self._config = config
        self._stats = {
            "threads_served": 0,
            "clients_created": 0,
        }
    
    def get_client(self) -> TMDBClient:
        """Get a TMDB client for the current thread.
        
        Returns:
            TMDBClient instance for the current thread
        """
        if not hasattr(self._local, 'client'):
            # Create a new client for this thread
            client_config = TMDBConfig(
                api_key=self._config.api_key,
                language=self._config.language,
                fallback_language=self._config.fallback_language,
                base_url=self._config.base_url,
                image_base_url=self._config.image_base_url,
                timeout=self._config.timeout,
                max_retries=self._config.max_retries,
                retry_delay_base=self._config.retry_delay_base,
                retry_delay_max=self._config.retry_delay_max,
                cache_only_mode=self._config.cache_only_mode,
                high_confidence_threshold=self._config.high_confidence_threshold,
                medium_confidence_threshold=self._config.medium_confidence_threshold,
                similarity_weight=self._config.similarity_weight,
                year_weight=self._config.year_weight,
                language_weight=self._config.language_weight,
                include_person_results=self._config.include_person_results,
            )
            
            self._local.client = TMDBClient(client_config)
            self._stats["threads_served"] += 1
            self._stats["clients_created"] += 1
        
        return self._local.client
    
    def get_stats(self) -> dict[str, Any]:
        """Get statistics for the thread-local client manager.
        
        Returns:
            Dictionary containing statistics
        """
        return {
            "threads_served": self._stats["threads_served"],
            "clients_created": self._stats["clients_created"],
            "current_thread": threading.current_thread().name,
        }


# Global instances for application-wide use
_tmdb_pool: Optional[TMDBClientPool] = None
_tmdb_thread_local: Optional[ThreadLocalTMDBClient] = None
_pool_lock = threading.Lock()


def get_tmdb_client_pool(config: Optional[TMDBConfig] = None) -> TMDBClientPool:
    """Get or create the global TMDB client pool.
    
    Args:
        config: TMDB configuration (required for first call)
        
    Returns:
        Global TMDBClientPool instance
        
    Raises:
        ValueError: If config is not provided and pool doesn't exist
    """
    global _tmdb_pool
    
    if _tmdb_pool is None:
        if config is None:
            raise ValueError("TMDB config is required for first pool creation")
        
        with _pool_lock:
            if _tmdb_pool is None:  # Double-check locking
                _tmdb_pool = TMDBClientPool(config, initial_size=4, max_size=12)
    
    return _tmdb_pool


def get_tmdb_thread_local_client(config: Optional[TMDBConfig] = None) -> ThreadLocalTMDBClient:
    """Get or create the global thread-local TMDB client manager.
    
    Args:
        config: TMDB configuration (required for first call)
        
    Returns:
        Global ThreadLocalTMDBClient instance
        
    Raises:
        ValueError: If config is not provided and manager doesn't exist
    """
    global _tmdb_thread_local
    
    if _tmdb_thread_local is None:
        if config is None:
            raise ValueError("TMDB config is required for first thread-local client creation")
        
        with _pool_lock:
            if _tmdb_thread_local is None:  # Double-check locking
                _tmdb_thread_local = ThreadLocalTMDBClient(config)
    
    return _tmdb_thread_local


def reset_tmdb_client_managers() -> None:
    """Reset the global TMDB client managers.
    
    This is useful for testing or when configuration changes.
    """
    global _tmdb_pool, _tmdb_thread_local
    
    with _pool_lock:
        if _tmdb_pool is not None:
            _tmdb_pool.clear_pool()
            _tmdb_pool = None
        
        _tmdb_thread_local = None
