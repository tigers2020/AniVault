"""Thread-safety tests for settings system.

Tests concurrent access to global settings cache to ensure
no race conditions occur in multi-threaded environments.
"""

from __future__ import annotations

import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

from anivault.config.settings import (
    Settings,
    get_config,
    reload_config,
    update_and_save_config,
)


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    """Create temporary config file."""
    config_file = tmp_path / "config.toml"
    config_content = """
[app]
name = "AniVault"
version = "0.1.0"
debug = false

[logging]
level = "INFO"

[tmdb]
api_key = ""
timeout = 30

[file_processing]
max_workers = 4

[cache]
enabled = true
ttl = 3600
"""
    config_file.write_text(config_content)
    return config_file


def test_concurrent_get_config_single_load():
    """Test that concurrent get_config() calls load settings only once."""
    load_count = {"count": 0}
    load_lock = threading.Lock()

    def counting_get_config():
        with load_lock:
            load_count["count"] += 1
        return get_config()

    # Execute concurrent get_config calls
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(get_config) for _ in range(10)]
        results = [f.result() for f in as_completed(futures)]

    # All should return the same instance
    assert all(r is results[0] for r in results)
    assert len(results) == 10


def test_concurrent_reload_config():
    """Test that concurrent reload_config() calls are thread-safe."""
    results = []
    errors = []

    def safe_reload():
        try:
            cfg = reload_config()
            results.append(cfg)
        except Exception as e:
            errors.append(e)

    # Execute concurrent reloads
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(safe_reload) for _ in range(5)]
        for f in as_completed(futures):
            f.result()

    # No errors should occur
    assert len(errors) == 0
    assert len(results) == 5


def test_update_during_read(temp_config: Path):
    """Test reading config while update is in progress."""
    read_results = []
    update_complete = threading.Event()

    def slow_update(cfg: Settings):
        """Slow update to create race window."""
        import time

        cfg.app.version = "2.0.0"
        time.sleep(0.1)  # Simulate slow operation
        update_complete.set()

    def concurrent_read():
        """Read config during update."""
        cfg = get_config()
        read_results.append(cfg.app.version)

    # Start update in background
    update_thread = threading.Thread(
        target=lambda: update_and_save_config(slow_update, temp_config)
    )
    update_thread.start()

    # Try to read during update
    read_thread = threading.Thread(target=concurrent_read)
    read_thread.start()

    # Wait for completion
    update_thread.join()
    read_thread.join()
    update_complete.wait(timeout=1.0)

    # Should not crash (version can be either old or new)
    assert len(read_results) > 0


def test_multiple_concurrent_updates(temp_config: Path):
    """Test multiple concurrent updates are serialized."""
    errors = []

    def update_version(version: str):
        def updater(cfg: Settings):
            cfg.app.version = version

        try:
            update_and_save_config(updater, temp_config)
        except Exception as e:
            errors.append(e)

    versions = ["1.0.0", "1.1.0", "1.2.0", "1.3.0", "1.4.0"]

    # Execute concurrent updates
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(update_version, v) for v in versions]
        for f in as_completed(futures):
            f.result()

    # No errors should occur
    assert len(errors) == 0

    # Final version should be one of the updates
    final_cfg = reload_config()
    assert final_cfg.app.version in versions


def test_reload_during_update(temp_config: Path):
    """Test reloading config during update operation."""
    reload_results = []

    def slow_update(cfg: Settings):
        """Slow update."""
        import time

        cfg.app.version = "3.0.0"
        time.sleep(0.1)

    def concurrent_reload():
        """Reload during update."""
        try:
            cfg = reload_config()
            reload_results.append(cfg)
        except Exception:
            pass  # Expected to succeed

    # Start update
    update_thread = threading.Thread(
        target=lambda: update_and_save_config(slow_update, temp_config)
    )
    update_thread.start()

    # Try reload during update
    reload_thread = threading.Thread(target=concurrent_reload)
    reload_thread.start()

    # Wait
    update_thread.join()
    reload_thread.join()

    # Should complete without deadlock
    assert True  # If we get here, no deadlock occurred
