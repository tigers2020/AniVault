"""Async TMDB client pool manager for optimized concurrent processing.

This module provides an async pool of TMDB client instances that can be
efficiently reused across multiple async operations to minimize object creation
overhead and resource consumption.
"""

import asyncio
import time
from collections import deque
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from .async_tmdb_client import AsyncTMDBClient, TMDBConfig


class AsyncTMDBClientPool:
    """Async pool manager for TMDB client instances.

    This class manages a pool of async TMDB client instances that can be safely
    shared across multiple async operations. It provides methods to acquire and release
    clients, ensuring optimal resource utilization and async safety.

    Attributes:
        _pool: Queue of available async TMDB client instances
        _lock: Async lock for pool operations
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
        pool_name: str = "AsyncTMDBPool",
    ):
        """Initialize the async TMDB client pool.

        Args:
            config: TMDB configuration for creating clients
            initial_size: Initial number of clients to create
            max_size: Maximum number of clients in the pool
            pool_name: Name for logging and identification
        """
        self._config = config
        self._max_pool_size = max_size
        self._pool_name = pool_name
        self._lock = asyncio.Lock()
        self._pool: deque[AsyncTMDBClient] = deque()
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
        asyncio.create_task(self._initialize_pool(initial_size))

    async def _initialize_pool(self, initial_size: int) -> None:
        """Initialize the pool with initial client instances.

        Args:
            initial_size: Number of initial clients to create
        """
        async with self._lock:
            for _ in range(min(initial_size, self._max_pool_size)):
                client = await self._create_client()
                self._pool.append(client)
                self._created_clients += 1
                self._stats["clients_created"] += 1

    async def _create_client(self) -> AsyncTMDBClient:
        """Create a new async TMDB client instance.

        Returns:
            New AsyncTMDBClient instance
        """
        from .async_tmdb_client import create_async_tmdb_client

        return await create_async_tmdb_client(self._config)

    async def acquire(self, timeout: float | None = None) -> AsyncTMDBClient:
        """Acquire an async TMDB client from the pool.

        Args:
            timeout: Maximum time to wait for a client (None for no timeout)

        Returns:
            AsyncTMDBClient instance from the pool

        Raises:
            asyncio.TimeoutError: If timeout is reached and no client is available
        """
        self._stats["total_requests"] += 1

        async with self._lock:
            # Try to get an existing client from the pool
            if self._pool:
                client = self._pool.popleft()
                self._active_clients += 1
                self._stats["pool_hits"] += 1
                return client

            # Pool is empty, try to create a new client if under limit
            if self._created_clients < self._max_pool_size:
                client = await self._create_client()
                self._created_clients += 1
                self._active_clients += 1
                self._stats["clients_created"] += 1
                self._stats["pool_misses"] += 1
                return client

            # Pool is at max capacity, wait for a client to be released
            if timeout is None:
                # Wait indefinitely
                while not self._pool:
                    await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
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
                        raise asyncio.TimeoutError(
                            f"Timeout waiting for async TMDB client from pool {self._pool_name}"
                        )
                    await asyncio.sleep(min(0.1, remaining_time))

                client = self._pool.popleft()
                self._active_clients += 1
                self._stats["pool_hits"] += 1
                return client

    async def release(self, client: AsyncTMDBClient) -> None:
        """Release an async TMDB client back to the pool.

        Args:
            client: AsyncTMDBClient instance to return to the pool
        """
        async with self._lock:
            if self._active_clients > 0:
                self._active_clients -= 1

            # Add client back to pool
            self._pool.append(client)

    @asynccontextmanager
    async def get_client(
        self, timeout: float | None = None
    ) -> AsyncGenerator[AsyncTMDBClient, None]:
        """Context manager for acquiring and automatically releasing an async TMDB client.

        Args:
            timeout: Maximum time to wait for a client

        Yields:
            AsyncTMDBClient instance from the pool

        Example:
            async with pool.get_client() as client:
                results = await client.search_tv_series("Attack on Titan")
        """
        client = None
        try:
            client = await self.acquire(timeout)
            yield client
        finally:
            if client is not None:
                await self.release(client)

    async def get_pool_stats(self) -> dict[str, Any]:
        """Get current pool statistics.

        Returns:
            Dictionary containing pool statistics
        """
        async with self._lock:
            return {
                "pool_name": self._pool_name,
                "pool_size": len(self._pool),
                "active_clients": self._active_clients,
                "created_clients": self._created_clients,
                "max_pool_size": self._max_pool_size,
                "utilization_rate": (
                    self._active_clients / self._max_pool_size if self._max_pool_size > 0 else 0.0
                ),
                "pool_hit_rate": (
                    self._stats["pool_hits"] / self._stats["total_requests"]
                    if self._stats["total_requests"] > 0
                    else 0.0
                ),
                **self._stats,
            }

    async def resize_pool(self, new_max_size: int) -> None:
        """Resize the pool to a new maximum size.

        Args:
            new_max_size: New maximum pool size
        """
        async with self._lock:
            old_max_size = self._max_pool_size
            self._max_pool_size = new_max_size

            # If shrinking, remove excess clients
            if new_max_size < old_max_size:
                excess_clients = len(self._pool) - new_max_size
                for _ in range(excess_clients):
                    if self._pool:
                        client = self._pool.popleft()
                        await client.close()
                        self._created_clients -= 1
                        self._stats["clients_destroyed"] += 1

    async def clear_pool(self) -> None:
        """Clear all clients from the pool."""
        async with self._lock:
            destroyed_count = len(self._pool)
            for client in self._pool:
                await client.close()
            self._pool.clear()
            self._created_clients = 0
            self._active_clients = 0
            self._stats["clients_destroyed"] += destroyed_count

    async def health_check(self) -> dict[str, Any]:
        """Perform a health check on the pool.

        Returns:
            Dictionary containing health check results
        """
        async with self._lock:
            stats = await self.get_pool_stats()

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

    async def close(self) -> None:
        """Close the pool and all its clients."""
        await self.clear_pool()


# Global instances for application-wide use
_async_tmdb_pool: AsyncTMDBClientPool | None = None
_pool_lock = asyncio.Lock()


async def get_async_tmdb_client_pool(config: TMDBConfig | None = None) -> AsyncTMDBClientPool:
    """Get or create the global async TMDB client pool.

    Args:
        config: TMDB configuration (required for first call)

    Returns:
        Global AsyncTMDBClientPool instance

    Raises:
        ValueError: If config is not provided and pool doesn't exist
    """
    global _async_tmdb_pool

    if _async_tmdb_pool is None:
        if config is None:
            raise ValueError("TMDB config is required for first async pool creation")

        async with _pool_lock:
            if _async_tmdb_pool is None:  # Double-check locking
                _async_tmdb_pool = AsyncTMDBClientPool(config, initial_size=4, max_size=12)

    return _async_tmdb_pool


async def reset_async_tmdb_client_pool() -> None:
    """Reset the global async TMDB client pool.

    This is useful for testing or when configuration changes.
    """
    global _async_tmdb_pool

    async with _pool_lock:
        if _async_tmdb_pool is not None:
            await _async_tmdb_pool.close()
            _async_tmdb_pool = None


# Convenience functions for backward compatibility
async def get_async_tmdb_client() -> AsyncTMDBClient:
    """Get an async TMDB client from the global pool.

    Returns:
        AsyncTMDBClient instance
    """
    pool = await get_async_tmdb_client_pool()
    return await pool.acquire()


async def release_async_tmdb_client(client: AsyncTMDBClient) -> None:
    """Release an async TMDB client back to the global pool.

    Args:
        client: AsyncTMDBClient instance to release
    """
    pool = await get_async_tmdb_client_pool()
    await pool.release(client)


@asynccontextmanager
async def async_tmdb_client_context() -> AsyncGenerator[AsyncTMDBClient, None]:
    """Context manager for getting an async TMDB client.

    Yields:
        AsyncTMDBClient instance

    Example:
        async with async_tmdb_client_context() as client:
            results = await client.search_tv_series("Attack on Titan")
    """
    pool = await get_async_tmdb_client_pool()
    async with pool.get_client() as client:
        yield client
