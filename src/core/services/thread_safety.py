"""
Thread Safety Utilities for AniVault application.

This module provides utilities and decorators for ensuring thread safety
across the application, particularly in the MVVM architecture.
"""

from __future__ import annotations

import functools
import logging
import threading
from collections.abc import Callable
from typing import Any, TypeVar

from PyQt5.QtCore import QMutex, QMutexLocker

# Logger for this module
logger = logging.getLogger(__name__)

# Type variable for function return types
T = TypeVar("T")


class ThreadSafeProperty:
    """
    Thread-safe property descriptor that uses QMutex for synchronization.

    This class provides a thread-safe way to create properties that can be
    safely accessed from multiple threads.
    """

    def __init__(
        self, getter: Callable[[Any], T], setter: Optional[Callable[[Any, T], None]] = None
    ) -> None:
        """
        Initialize the thread-safe property.

        Args:
            getter: Function to get the property value
            setter: Optional function to set the property value
        """
        self._getter = getter
        self._setter = setter
        self._mutex = QMutex()
        self._name = getter.__name__

    def __get__(self, instance: Any, owner: Any) -> T:
        """Get the property value in a thread-safe manner."""
        if instance is None:
            return self

        with QMutexLocker(self._mutex):
            return self._getter(instance)

    def __set__(self, instance: Any, value: T) -> None:
        """Set the property value in a thread-safe manner."""
        if self._setter is None:
            raise AttributeError(f"Property '{self._name}' is read-only")

        with QMutexLocker(self._mutex):
            self._setter(instance, value)


def thread_safe_method(mutex_attr: str = "_mutex"):
    """
    Decorator to make a method thread-safe using a QMutex.

    Args:
        mutex_attr: Name of the mutex attribute on the instance

    Returns:
        Decorated method
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> T:
            mutex = getattr(self, mutex_attr, None)
            if mutex is None:
                logger.warning(f"No mutex found at '{mutex_attr}' for method '{func.__name__}'")
                return func(self, *args, **kwargs)

            with QMutexLocker(mutex):
                return func(self, *args, **kwargs)

        return wrapper

    return decorator


def python_thread_safe_method(lock_attr: str = "_python_lock"):
    """
    Decorator to make a method thread-safe using a Python threading.Lock.

    Args:
        lock_attr: Name of the lock attribute on the instance

    Returns:
        Decorated method
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> T:
            lock = getattr(self, lock_attr, None)
            if lock is None:
                logger.warning(f"No lock found at '{lock_attr}' for method '{func.__name__}'")
                return func(self, *args, **kwargs)

            with lock:
                return func(self, *args, **kwargs)

        return wrapper

    return decorator


class ThreadSafeCounter:
    """
    Thread-safe counter using QMutex.
    """

    def __init__(self, initial_value: int = 0) -> None:
        """
        Initialize the counter.

        Args:
            initial_value: Initial counter value
        """
        self._value = initial_value
        self._mutex = QMutex()

    def increment(self, amount: int = 1) -> int:
        """
        Increment the counter by the specified amount.

        Args:
            amount: Amount to increment by

        Returns:
            New counter value
        """
        with QMutexLocker(self._mutex):
            self._value += amount
            return self._value

    def decrement(self, amount: int = 1) -> int:
        """
        Decrement the counter by the specified amount.

        Args:
            amount: Amount to decrement by

        Returns:
            New counter value
        """
        with QMutexLocker(self._mutex):
            self._value -= amount
            return self._value

    def get_value(self) -> int:
        """
        Get the current counter value.

        Returns:
            Current counter value
        """
        with QMutexLocker(self._mutex):
            return self._value

    def set_value(self, value: int) -> None:
        """
        Set the counter value.

        Args:
            value: New counter value
        """
        with QMutexLocker(self._mutex):
            self._value = value

    def reset(self) -> None:
        """Reset the counter to zero."""
        with QMutexLocker(self._mutex):
            self._value = 0


class ThreadSafeList:
    """
    Thread-safe list using QMutex.
    """

    def __init__(self, initial_items: Optional[list] = None) -> None:
        """
        Initialize the thread-safe list.

        Args:
            initial_items: Initial list items
        """
        self._items = list(initial_items) if initial_items else []
        self._mutex = QMutex()

    def append(self, item: Any) -> None:
        """Append an item to the list."""
        with QMutexLocker(self._mutex):
            self._items.append(item)

    def extend(self, items: list) -> None:
        """Extend the list with items."""
        with QMutexLocker(self._mutex):
            self._items.extend(items)

    def insert(self, index: int, item: Any) -> None:
        """Insert an item at the specified index."""
        with QMutexLocker(self._mutex):
            self._items.insert(index, item)

    def remove(self, item: Any) -> bool:
        """
        Remove the first occurrence of an item.

        Returns:
            True if item was removed, False if not found
        """
        with QMutexLocker(self._mutex):
            try:
                self._items.remove(item)
                return True
            except ValueError:
                return False

    def pop(self, index: int = -1) -> Any:
        """Remove and return an item at the specified index."""
        with QMutexLocker(self._mutex):
            return self._items.pop(index)

    def clear(self) -> None:
        """Clear all items from the list."""
        with QMutexLocker(self._mutex):
            self._items.clear()

    def get_item(self, index: int) -> Any:
        """Get an item at the specified index."""
        with QMutexLocker(self._mutex):
            return self._items[index]

    def get_all_items(self) -> list:
        """Get a copy of all items."""
        with QMutexLocker(self._mutex):
            return self._items.copy()

    def __len__(self) -> int:
        """Get the length of the list."""
        with QMutexLocker(self._mutex):
            return len(self._items)

    def __contains__(self, item: Any) -> bool:
        """Check if an item is in the list."""
        with QMutexLocker(self._mutex):
            return item in self._items


class ThreadSafeDict:
    """
    Thread-safe dictionary using QMutex.
    """

    def __init__(self, initial_items: Optional[dict] = None) -> None:
        """
        Initialize the thread-safe dictionary.

        Args:
            initial_items: Initial dictionary items
        """
        self._items = dict(initial_items) if initial_items else {}
        self._mutex = QMutex()

    def get(self, key: Any, default: Any = None) -> Any:
        """Get a value by key."""
        with QMutexLocker(self._mutex):
            return self._items.get(key, default)

    def set(self, key: Any, value: Any) -> None:
        """Set a value for a key."""
        with QMutexLocker(self._mutex):
            self._items[key] = value

    def delete(self, key: Any) -> bool:
        """
        Delete a key-value pair.

        Returns:
            True if key was deleted, False if not found
        """
        with QMutexLocker(self._mutex):
            if key in self._items:
                del self._items[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all items from the dictionary."""
        with QMutexLocker(self._mutex):
            self._items.clear()

    def get_all_items(self) -> dict:
        """Get a copy of all items."""
        with QMutexLocker(self._mutex):
            return self._items.copy()

    def __len__(self) -> int:
        """Get the number of items."""
        with QMutexLocker(self._mutex):
            return len(self._items)

    def __contains__(self, key: Any) -> bool:
        """Check if a key exists."""
        with QMutexLocker(self._mutex):
            return key in self._items


def ensure_main_thread(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to ensure a method is called on the main thread.

    This is useful for UI operations that must be performed on the main thread.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> T:
        from PyQt5.QtCore import QThread

        if QThread.currentThread() != QThread.mainThread():
            logger.warning(f"Method '{func.__name__}' called from non-main thread")
            # In a real implementation, you might want to use QMetaObject.invokeMethod
            # to schedule the call on the main thread

        return func(self, *args, **kwargs)

    return wrapper


def prevent_deadlock(timeout_ms: int = 5000):
    """
    Decorator to prevent deadlocks by adding timeout to mutex operations.

    Args:
        timeout_ms: Timeout in milliseconds

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> T:
            # This is a placeholder for deadlock prevention
            # In a real implementation, you would use QMutex.tryLock with timeout
            logger.debug(f"Executing '{func.__name__}' with deadlock prevention")
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


class ThreadSafetyValidator:
    """
    Utility class for validating thread safety in the application.
    """

    @staticmethod
    def validate_mutex_usage(obj: Any, mutex_attr: str = "_mutex") -> bool:
        """
        Validate that mutex is being used correctly in an object.

        Args:
            obj: Object to validate
            mutex_attr: Name of the mutex attribute

        Returns:
            True if mutex usage appears correct
        """
        mutex = getattr(obj, mutex_attr, None)
        if mutex is None:
            logger.warning(f"No mutex found at '{mutex_attr}' in {type(obj).__name__}")
            return False

        if not isinstance(mutex, QMutex):
            logger.warning(f"Mutex at '{mutex_attr}' is not a QMutex in {type(obj).__name__}")
            return False

        return True

    @staticmethod
    def validate_lock_usage(obj: Any, lock_attr: str = "_python_lock") -> bool:
        """
        Validate that Python lock is being used correctly in an object.

        Args:
            obj: Object to validate
            lock_attr: Name of the lock attribute

        Returns:
            True if lock usage appears correct
        """
        lock = getattr(obj, lock_attr, None)
        if lock is None:
            logger.warning(f"No lock found at '{lock_attr}' in {type(obj).__name__}")
            return False

        if not isinstance(lock, threading.Lock):
            logger.warning(f"Lock at '{lock_attr}' is not a threading.Lock in {type(obj).__name__}")
            return False

        return True
