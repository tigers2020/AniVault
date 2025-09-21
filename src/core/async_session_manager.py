"""Async HTTP session manager for AniVault application.

This module provides a centralized way to manage aiohttp.ClientSession
instances for asynchronous HTTP operations, particularly for TMDB API calls.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Optional

import aiohttp
from PyQt5.QtCore import QObject, pyqtSignal

from .config_manager import ConfigManager

logger = logging.getLogger(__name__)


class AsyncSessionManager(QObject):
    """Manages aiohttp.ClientSession lifecycle for the application.

    This class provides a singleton pattern for managing HTTP sessions
    in a PyQt5 application context. It ensures proper resource cleanup
    and provides thread-safe access to the session.
    """

    # Signal emitted when session is ready
    session_ready = pyqtSignal()

    # Signal emitted when session is closed
    session_closed = pyqtSignal()

    _instance: Optional["AsyncSessionManager"] = None
    _session: aiohttp.ClientSession | None = None
    _loop: asyncio.AbstractEventLoop | None = None
    _initialized: bool = False

    def __new__(cls: type["AsyncSessionManager"]) -> "AsyncSessionManager":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the session manager."""
        if not self._initialized:
            super().__init__()
            self._initialized = True
            self._config = ConfigManager()
            self._session_lock = asyncio.Lock()
            logger.info("AsyncSessionManager initialized")

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create the HTTP session.

        Returns:
            aiohttp.ClientSession: The managed HTTP session.

        Raises:
            RuntimeError: If the session cannot be created.
        """
        async with self._session_lock:
            if self._session is None or self._session.closed:
                await self._create_session()
            return self._session

    async def _create_session(self) -> None:
        """Create a new aiohttp.ClientSession with optimized configuration."""
        try:
            # Configure connection limits and timeouts for TMDB API optimization
            connector = aiohttp.TCPConnector(
                limit=200,  # Total connection pool size (increased for better concurrency)
                limit_per_host=20,  # Per-host connection limit (optimized for TMDB)
                use_dns_cache=True,  # Enable DNS cache (10 minutes - longer for stability)
                keepalive_timeout=60,  # Increased keepalive for better connection reuse
                enable_cleanup_closed=True,
                force_close=False,  # Allow connection reuse
                ssl=True,  # Ensure SSL is enabled for HTTPS
                family=0,  # Use both IPv4 and IPv6
                local_addr=None,  # Let OS choose local address
                resolver=None,  # Use default resolver
                happy_eyeballs_delay=0.25,  # Enable Happy Eyeballs for faster IPv6 fallback
                loop=None,  # Use current event loop
            )

            timeout = aiohttp.ClientTimeout(
                total=60,  # Total timeout (increased for better reliability)
                connect=15,  # Connection timeout (increased for slow networks)
                sock_read=30,  # Socket read timeout (increased for large responses)
            )

            headers = {
                "User-Agent": f'AniVault/{self._config.get("app_version", "1.0.0")}',
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate, br",  # Added brotli support
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",  # Language preferences
                "Connection": "keep-alive",  # Explicit keep-alive
                "Cache-Control": "no-cache",  # Prevent caching of API responses
            }

            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=headers,
                raise_for_status=True,
                auto_decompress=True,  # Automatically decompress responses
                version=aiohttp.HttpVersion11,  # Use HTTP/1.1 for better compatibility
                cookie_jar=aiohttp.CookieJar(),  # Cookie jar for session management
                json_serialize=None,  # Use default JSON serialization
                requote_redirect_url=True,  # Requote redirect URLs
                read_bufsize=65536,  # Read buffer size (64KB)
                max_line_size=8192,  # Max line size for headers
                max_field_size=8192,  # Max field size for headers
            )

            logger.info("aiohttp.ClientSession created successfully")
            self.session_ready.emit()

        except Exception as e:
            logger.error(f"Failed to create aiohttp.ClientSession: {e}")
            raise RuntimeError(f"Failed to create HTTP session: {e}") from e

    async def close_session(self) -> None:
        """Close the HTTP session and clean up resources."""
        async with self._session_lock:
            if self._session and not self._session.closed:
                try:
                    await self._session.close()
                    logger.info("aiohttp.ClientSession closed successfully")
                    self.session_closed.emit()
                except Exception as e:
                    logger.warning(f"Error closing aiohttp.ClientSession: {e}")
                finally:
                    self._session = None

    def get_event_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create the event loop for this thread.

        Returns:
            asyncio.AbstractEventLoop: The event loop for async operations.
        """
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop in current thread, create a new one
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)

        return self._loop

    def run_async(self, coro: Any) -> Any:
        """Run an async coroutine in the event loop.

        Args:
            coro: The coroutine to run.

        Returns:
            The result of the coroutine.
        """
        loop = self.get_event_loop()
        if loop.is_running():
            # If loop is already running, schedule the coroutine
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()
        else:
            # If no loop is running, run it directly
            return loop.run_until_complete(coro)

    @asynccontextmanager
    async def session_context(self) -> AsyncIterator[aiohttp.ClientSession]:
        """Context manager for HTTP session operations.

        Yields:
            aiohttp.ClientSession: The managed HTTP session.
        """
        session = await self.get_session()
        try:
            yield session
        finally:
            # Session cleanup is handled by the manager
            pass

    def is_session_ready(self) -> bool:
        """Check if the session is ready for use.

        Returns:
            bool: True if session is ready, False otherwise.
        """
        return self._session is not None and not self._session.closed

    async def health_check(self) -> bool:
        """Perform a health check on the session.

        Returns:
            bool: True if session is healthy, False otherwise.
        """
        try:
            if not self.is_session_ready():
                return False

            # Test with a simple request
            async with self._session.get("https://httpbin.org/get", timeout=5) as response:
                return response.status == 200
        except Exception as e:
            logger.warning(f"Session health check failed: {e}")
            return False

    def get_connection_stats(self) -> dict[str, Any]:
        """Get connection pool statistics.

        Returns:
            Dict containing connection pool statistics.
        """
        if not self._session or self._session.closed:
            return {"error": "Session not available"}

        connector = self._session.connector
        if not connector:
            return {"error": "Connector not available"}

        return {
            "total_connections": connector.limit,
            "per_host_limit": connector.limit_per_host,
            "dns_cache_ttl": connector.ttl_dns_cache,
            "keepalive_timeout": connector.keepalive_timeout,
            "closed_connections": connector._closed,
            "acquired_connections": len(connector._acquired),
            "available_connections": len(connector._available),
            "is_ssl_enabled": connector.ssl,
            "family": connector.family,
        }


# Global session manager instance
session_manager = AsyncSessionManager()


def get_session_manager() -> AsyncSessionManager:
    """Get the global session manager instance.

    Returns:
        AsyncSessionManager: The singleton session manager.
    """
    return session_manager


async def get_http_session() -> aiohttp.ClientSession:
    """Get the current HTTP session.

    Returns:
        aiohttp.ClientSession: The managed HTTP session.
    """
    return await session_manager.get_session()


def run_async(coro: Any) -> Any:
    """Run an async coroutine using the session manager.

    Args:
        coro: The coroutine to run.

    Returns:
        The result of the coroutine.
    """
    return session_manager.run_async(coro)
