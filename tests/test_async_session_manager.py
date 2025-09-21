"""Tests for AsyncSessionManager functionality.

This module contains comprehensive tests for the AsyncSessionManager including
connection pooling, session management, and health checks.
"""

from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from src.core.async_session_manager import (
    AsyncSessionManager,
    get_http_session,
    get_session_manager,
    run_async,
)


class TestAsyncSessionManager:
    """Test AsyncSessionManager functionality."""

    @pytest.fixture
    def session_manager(self) -> AsyncSessionManager:
        """Create test session manager."""
        return AsyncSessionManager()

    @pytest.fixture
    def mock_config(self) -> Mock:
        """Create mock config manager."""
        config = Mock()
        config.get.side_effect = lambda key, default=None: {"app_version": "1.0.0"}.get(
            key, default
        )
        return config

    def test_singleton_pattern(self) -> None:
        """Test that AsyncSessionManager follows singleton pattern."""
        manager1 = AsyncSessionManager()
        manager2 = AsyncSessionManager()

        assert manager1 is manager2

    def test_initialization(self, session_manager: AsyncSessionManager) -> None:
        """Test session manager initialization."""
        assert session_manager._session is None
        assert session_manager._loop is None
        assert hasattr(session_manager, "_session_lock")

    @pytest.mark.asyncio
    async def test_get_session_creates_new_session(
        self, session_manager: AsyncSessionManager, mock_config
    ) -> None:
        """Test that get_session creates a new session when none exists."""
        with patch.object(session_manager, "_config", mock_config):
            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_session.closed = False
                mock_session_class.return_value = mock_session

                session = await session_manager.get_session()

                assert session == mock_session
                assert session_manager._session == mock_session
                mock_session_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_reuses_existing_session(
        self, session_manager: AsyncSessionManager, mock_config
    ) -> None:
        """Test that get_session reuses existing session."""
        with patch.object(session_manager, "_config", mock_config):
            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_session.closed = False
                mock_session_class.return_value = mock_session

                # Get session first time
                session1 = await session_manager.get_session()

                # Get session second time
                session2 = await session_manager.get_session()

                assert session1 == session2
                assert mock_session_class.call_count == 1

    @pytest.mark.asyncio
    async def test_get_session_recreates_closed_session(
        self, session_manager: AsyncSessionManager, mock_config
    ) -> None:
        """Test that get_session recreates session when closed."""
        with patch.object(session_manager, "_config", mock_config):
            with patch("aiohttp.ClientSession") as mock_session_class:
                # First session
                mock_session1 = AsyncMock()
                mock_session1.closed = True

                # Second session
                mock_session2 = AsyncMock()
                mock_session2.closed = False

                mock_session_class.side_effect = [mock_session1, mock_session2]

                # Set first session as current
                session_manager._session = mock_session1

                # Get session should create new one
                session = await session_manager.get_session()

                assert session == mock_session2
                assert session_manager._session == mock_session2
                assert mock_session_class.call_count == 2

    @pytest.mark.asyncio
    async def test_create_session_configuration(
        self, session_manager: AsyncSessionManager, mock_config
    ) -> None:
        """Test that session is created with proper configuration."""
        with patch.object(session_manager, "_config", mock_config):
            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value = mock_session

                await session_manager._create_session()

                # Verify ClientSession was called with correct parameters
                call_args = mock_session_class.call_args
                assert call_args is not None

                # Check connector configuration
                connector = call_args[1]["connector"]
                assert isinstance(connector, aiohttp.TCPConnector)
                assert connector.limit == 200
                assert connector.limit_per_host == 20
                assert connector.use_dns_cache is True

                # Check timeout configuration
                timeout = call_args[1]["timeout"]
                assert isinstance(timeout, aiohttp.ClientTimeout)
                assert timeout.total == 60
                assert timeout.connect == 15
                assert timeout.sock_read == 30

                # Check headers
                headers = call_args[1]["headers"]
                assert headers["User-Agent"] == "AniVault/1.0.0"
                assert headers["Accept"] == "application/json"
                assert headers["Accept-Encoding"] == "gzip, deflate, br"
                assert headers["Accept-Language"] == "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
                assert headers["Connection"] == "keep-alive"
                assert headers["Cache-Control"] == "no-cache"

    @pytest.mark.asyncio
    async def test_close_session(self, session_manager: AsyncSessionManager) -> None:
        """Test closing session."""
        mock_session = AsyncMock()
        mock_session.closed = False
        session_manager._session = mock_session

        await session_manager.close_session()

        mock_session.close.assert_called_once()
        assert session_manager._session is None

    @pytest.mark.asyncio
    async def test_close_session_already_closed(self, session_manager: AsyncSessionManager) -> None:
        """Test closing already closed session."""
        mock_session = AsyncMock()
        mock_session.closed = True
        session_manager._session = mock_session

        await session_manager.close_session()

        mock_session.close.assert_not_called()
        assert session_manager._session is None

    @pytest.mark.asyncio
    async def test_close_session_none(self, session_manager: AsyncSessionManager) -> None:
        """Test closing when no session exists."""
        session_manager._session = None

        await session_manager.close_session()

        # Should not raise any errors
        assert session_manager._session is None

    def test_get_event_loop_existing(self, session_manager: AsyncSessionManager) -> None:
        """Test getting existing event loop."""
        mock_loop = Mock()
        session_manager._loop = mock_loop

        loop = session_manager.get_event_loop()

        assert loop == mock_loop

    def test_get_event_loop_new(self, session_manager: AsyncSessionManager) -> None:
        """Test creating new event loop."""
        session_manager._loop = None

        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop

            loop = session_manager.get_event_loop()

            assert loop == mock_loop
            assert session_manager._loop == mock_loop

    def test_get_event_loop_runtime_error(self, session_manager: AsyncSessionManager) -> None:
        """Test creating new event loop when none exists."""
        session_manager._loop = None

        with patch("asyncio.get_event_loop") as mock_get_loop:
            with patch("asyncio.new_event_loop") as mock_new_loop:
                with patch("asyncio.set_event_loop") as mock_set_loop:
                    mock_get_loop.side_effect = RuntimeError("No event loop")
                    mock_loop = Mock()
                    mock_new_loop.return_value = mock_loop

                    loop = session_manager.get_event_loop()

                    assert loop == mock_loop
                    assert session_manager._loop == mock_loop
                    mock_new_loop.assert_called_once()
                    mock_set_loop.assert_called_once_with(mock_loop)

    def test_run_async_with_running_loop(self, session_manager: AsyncSessionManager) -> None:
        """Test running async coroutine with running event loop."""
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        session_manager._loop = mock_loop

        async def test_coro() -> str:
            return "test_result"

        with patch("asyncio.run_coroutine_threadsafe") as mock_run_safe:
            mock_future = Mock()
            mock_future.result.return_value = "test_result"
            mock_run_safe.return_value = mock_future

            result = session_manager.run_async(test_coro())

            assert result == "test_result"
            mock_run_safe.assert_called_once()

    def test_run_async_without_running_loop(self, session_manager: AsyncSessionManager) -> None:
        """Test running async coroutine without running event loop."""
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        session_manager._loop = mock_loop

        async def test_coro() -> str:
            return "test_result"

        with patch.object(mock_loop, "run_until_complete") as mock_run_until:
            mock_run_until.return_value = "test_result"

            result = session_manager.run_async(test_coro())

            assert result == "test_result"
            mock_run_until.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_context(self, session_manager: AsyncSessionManager, mock_config) -> None:
        """Test session context manager."""
        with patch.object(session_manager, "_config", mock_config):
            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_session.closed = False
                mock_session_class.return_value = mock_session

                async with session_manager.session_context() as session:
                    assert session == mock_session

    def test_is_session_ready_true(self, session_manager: AsyncSessionManager) -> None:
        """Test is_session_ready when session is ready."""
        mock_session = Mock()
        mock_session.closed = False
        session_manager._session = mock_session

        assert session_manager.is_session_ready() is True

    def test_is_session_ready_false_none(self, session_manager: AsyncSessionManager) -> None:
        """Test is_session_ready when session is None."""
        session_manager._session = None

        assert session_manager.is_session_ready() is False

    def test_is_session_ready_false_closed(self, session_manager: AsyncSessionManager) -> None:
        """Test is_session_ready when session is closed."""
        mock_session = Mock()
        mock_session.closed = True
        session_manager._session = mock_session

        assert session_manager.is_session_ready() is False

    @pytest.mark.asyncio
    async def test_health_check_success(self, session_manager: AsyncSessionManager) -> None:
        """Test successful health check."""
        mock_session = AsyncMock()
        mock_session.closed = False
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_session.get.return_value.__aenter__.return_value = mock_response
        session_manager._session = mock_session

        result = await session_manager.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_session_not_ready(
        self, session_manager: AsyncSessionManager
    ) -> None:
        """Test health check when session is not ready."""
        session_manager._session = None

        result = await session_manager.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_failure(self, session_manager: AsyncSessionManager) -> None:
        """Test health check failure."""
        mock_session = AsyncMock()
        mock_session.closed = False
        mock_session.get.side_effect = Exception("Network error")
        session_manager._session = mock_session

        result = await session_manager.health_check()

        assert result is False

    def test_get_connection_stats_no_session(self, session_manager: AsyncSessionManager) -> None:
        """Test get_connection_stats when no session."""
        session_manager._session = None

        stats = session_manager.get_connection_stats()

        assert stats == {"error": "Session not available"}

    def test_get_connection_stats_closed_session(
        self, session_manager: AsyncSessionManager
    ) -> None:
        """Test get_connection_stats when session is closed."""
        mock_session = Mock()
        mock_session.closed = True
        session_manager._session = mock_session

        stats = session_manager.get_connection_stats()

        assert stats == {"error": "Session not available"}

    def test_get_connection_stats_success(self, session_manager: AsyncSessionManager) -> None:
        """Test successful get_connection_stats."""
        mock_connector = Mock()
        mock_connector.limit = 200
        mock_connector.limit_per_host = 20
        mock_connector.ttl_dns_cache = 600
        mock_connector.keepalive_timeout = 60
        mock_connector._closed = set()
        mock_connector._acquired = {1, 2, 3}
        mock_connector._available = {4, 5}
        mock_connector.ssl = True
        mock_connector.family = 0

        mock_session = Mock()
        mock_session.closed = False
        mock_session.connector = mock_connector
        session_manager._session = mock_session

        stats = session_manager.get_connection_stats()

        assert stats["total_connections"] == 200
        assert stats["per_host_limit"] == 20
        assert stats["dns_cache_ttl"] == 600
        assert stats["keepalive_timeout"] == 60
        assert stats["closed_connections"] == set()
        assert stats["acquired_connections"] == 3
        assert stats["available_connections"] == 2
        assert stats["is_ssl_enabled"] is True
        assert stats["family"] == 0

    def test_get_connection_stats_no_connector(self, session_manager: AsyncSessionManager) -> None:
        """Test get_connection_stats when no connector."""
        mock_session = Mock()
        mock_session.closed = False
        mock_session.connector = None
        session_manager._session = mock_session

        stats = session_manager.get_connection_stats()

        assert stats == {"error": "Connector not available"}

    @pytest.mark.asyncio
    async def test_optimized_tcp_connector_settings(
        self, session_manager: AsyncSessionManager, mock_config
    ) -> None:
        """Test that optimized TCPConnector settings are applied correctly."""
        with patch.object(session_manager, "_config", mock_config):
            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_session.closed = False
                mock_session_class.return_value = mock_session

                await session_manager._create_session()

                # Verify ClientSession was called with optimized TCPConnector
                call_args = mock_session_class.call_args
                assert call_args is not None

                # Check optimized connector configuration
                connector = call_args[1]["connector"]
                assert isinstance(connector, aiohttp.TCPConnector)

                # Verify optimized settings
                assert connector.limit == 200  # Total connection pool size
                assert connector.limit_per_host == 20  # Per-host connection limit
                assert connector.use_dns_cache is True  # DNS cache enabled
                assert connector._keepalive_timeout == 60  # Keepalive timeout (private attribute)
                # Note: Some attributes may not be directly accessible in all aiohttp versions
                # We'll test the core functionality instead
                assert connector.family == 0  # Use both IPv4 and IPv6

    @pytest.mark.asyncio
    async def test_optimized_timeout_settings(
        self, session_manager: AsyncSessionManager, mock_config
    ) -> None:
        """Test that optimized timeout settings are applied correctly."""
        with patch.object(session_manager, "_config", mock_config):
            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_session.closed = False
                mock_session_class.return_value = mock_session

                await session_manager._create_session()

                # Verify timeout configuration
                call_args = mock_session_class.call_args
                assert call_args is not None

                timeout = call_args[1]["timeout"]
                assert isinstance(timeout, aiohttp.ClientTimeout)

                # Verify optimized timeout settings
                assert timeout.total == 60  # Total timeout (increased for reliability)
                assert timeout.connect == 15  # Connection timeout (increased for slow networks)
                assert (
                    timeout.sock_read == 30
                )  # Socket read timeout (increased for large responses)

    @pytest.mark.asyncio
    async def test_optimized_headers_configuration(
        self, session_manager: AsyncSessionManager, mock_config
    ) -> None:
        """Test that optimized headers are configured correctly."""
        with patch.object(session_manager, "_config", mock_config):
            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_session.closed = False
                mock_session_class.return_value = mock_session

                await session_manager._create_session()

                # Verify headers configuration
                call_args = mock_session_class.call_args
                assert call_args is not None

                headers = call_args[1]["headers"]

                # Verify optimized headers
                assert headers["User-Agent"] == "AniVault/1.0.0"
                assert headers["Accept"] == "application/json"
                assert headers["Accept-Encoding"] == "gzip, deflate, br"  # Added brotli support
                assert (
                    headers["Accept-Language"] == "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
                )  # Language preferences
                assert headers["Connection"] == "keep-alive"  # Explicit keep-alive
                assert headers["Cache-Control"] == "no-cache"  # Prevent caching of API responses

    @pytest.mark.asyncio
    async def test_optimized_session_configuration(
        self, session_manager: AsyncSessionManager, mock_config
    ) -> None:
        """Test that optimized session configuration is applied correctly."""
        with patch.object(session_manager, "_config", mock_config):
            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_session.closed = False
                mock_session_class.return_value = mock_session

                await session_manager._create_session()

                # Verify session configuration
                call_args = mock_session_class.call_args
                assert call_args is not None

                # Check optimized session settings
                assert call_args[1]["raise_for_status"] is True  # Raise for HTTP errors
                assert call_args[1]["auto_decompress"] is True  # Automatically decompress responses
                assert call_args[1]["version"] == aiohttp.HttpVersion11  # Use HTTP/1.1
                assert isinstance(
                    call_args[1]["cookie_jar"], aiohttp.CookieJar
                )  # Cookie jar for session management
                assert call_args[1]["json_serialize"] is None  # Use default JSON serialization
                assert call_args[1]["requote_redirect_url"] is True  # Requote redirect URLs
                assert call_args[1]["read_bufsize"] == 65536  # Read buffer size (64KB)
                assert call_args[1]["max_line_size"] == 8192  # Max line size for headers
                assert call_args[1]["max_field_size"] == 8192  # Max field size for headers

    @pytest.mark.asyncio
    async def test_connection_pool_monitoring(
        self, session_manager: AsyncSessionManager, mock_config
    ) -> None:
        """Test connection pool monitoring and statistics."""
        with patch.object(session_manager, "_config", mock_config):
            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_session.closed = False

                # Mock connector with statistics
                mock_connector = Mock()
                mock_connector.limit = 200
                mock_connector.limit_per_host = 20
                mock_connector.ttl_dns_cache = 600
                mock_connector.keepalive_timeout = 60
                mock_connector._closed = set()
                mock_connector._acquired = {1, 2, 3}
                mock_connector._available = {4, 5}
                mock_connector.ssl = True
                mock_connector.family = 0

                mock_session.connector = mock_connector
                mock_session_class.return_value = mock_session

                await session_manager._create_session()

                # Test connection statistics
                stats = session_manager.get_connection_stats()

                # Verify statistics are accessible
                assert stats["total_connections"] == 200
                assert stats["per_host_limit"] == 20
                assert stats["dns_cache_ttl"] == 600
                assert stats["keepalive_timeout"] == 60
                assert stats["closed_connections"] == set()
                assert stats["acquired_connections"] == 3
                assert stats["available_connections"] == 2
                assert stats["is_ssl_enabled"] is True
                assert stats["family"] == 0

    @pytest.mark.asyncio
    async def test_connection_pool_efficiency(
        self, session_manager: AsyncSessionManager, mock_config
    ) -> None:
        """Test that connection pool is efficiently managed."""
        with patch.object(session_manager, "_config", mock_config):
            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_session.closed = False
                mock_session_class.return_value = mock_session

                # Test session reuse
                session1 = await session_manager.get_session()
                session2 = await session_manager.get_session()

                # Should return the same session instance
                assert session1 is session2
                assert mock_session_class.call_count == 1

                # Test session recreation when closed
                mock_session.closed = True
                session3 = await session_manager.get_session()

                # Should create a new session
                assert session3 is not session1
                assert mock_session_class.call_count == 2


class TestAsyncSessionManagerGlobals:
    """Test global functions and instances."""

    def test_get_session_manager(self) -> None:
        """Test get_session_manager function."""
        manager = get_session_manager()

        assert isinstance(manager, AsyncSessionManager)

    @pytest.mark.asyncio
    async def test_get_http_session(self) -> None:
        """Test get_http_session function."""
        with patch("src.core.async_session_manager.session_manager") as mock_manager:
            mock_session = AsyncMock()
            mock_manager.get_session.return_value = mock_session

            session = await get_http_session()

            assert session == mock_session
            mock_manager.get_session.assert_called_once()

    def test_run_async_global(self) -> None:
        """Test global run_async function."""
        with patch("src.core.async_session_manager.session_manager") as mock_manager:
            mock_manager.run_async.return_value = "test_result"

            async def test_coro() -> str:
                return "test_result"

            result = run_async(test_coro())

            assert result == "test_result"
            mock_manager.run_async.assert_called_once()
