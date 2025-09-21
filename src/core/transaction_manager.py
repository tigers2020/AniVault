"""Transaction management system for AniVault application.

This module provides robust transaction management using SQLAlchemy sessions
with support for nested transactions, comprehensive logging, and error handling.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Generator, Optional, TypeVar, Union

from sqlalchemy.orm import Session

# Configure logging
logger = logging.getLogger(__name__)

# Type variables for generic functions
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


@dataclass
class TransactionContext:
    """Represents a single transaction context with metadata.
    
    This class holds the state and metadata for a single transaction,
    including session, timing information, and nesting level.
    """
    
    session: Session
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: float = field(default_factory=time.time)
    nested_level: int = 0
    is_nested: bool = False
    parent_id: Optional[str] = None
    affected_rows: int = 0
    error: Optional[Exception] = None
    is_completed: bool = False
    
    @property
    def is_failed(self) -> bool:
        """Check if transaction has failed."""
        return self.error is not None
    
    @property
    def duration(self) -> float:
        """Get transaction duration in seconds."""
        return time.time() - self.start_time
    


class TransactionError(Exception):
    """Base exception for transaction-related errors."""
    pass


class TransactionTimeoutError(TransactionError):
    """Raised when a transaction exceeds the timeout limit."""
    pass


class TransactionNestingError(TransactionError):
    """Raised when there's an issue with nested transactions."""
    pass


class TransactionManager:
    """Manages SQLAlchemy transactions with comprehensive logging and error handling.
    
    This class provides a robust transaction management system that supports:
    - Nested transactions using savepoints
    - Comprehensive logging with transaction IDs
    - Automatic rollback on exceptions
    - Transaction timeout handling
    - Performance metrics collection
    """
    
    def __init__(self, timeout_seconds: Optional[int] = None):
        """Initialize the transaction manager.
        
        Args:
            timeout_seconds: Maximum transaction duration before timeout (None for no timeout)
        """
        self.timeout_seconds = timeout_seconds
        self._context_stack: list[TransactionContext] = []
        self._lock = threading.RLock()
        self._stats = {
            "total_transactions": 0,
            "successful_commits": 0,
            "rollbacks": 0,
            "timeouts": 0,
            "nested_transactions": 0,
        }
    
    def begin(self, session: Session, nested: bool = False) -> TransactionContext:
        """Begin a new transaction.
        
        Args:
            session: SQLAlchemy session to use for the transaction
            nested: Whether this is a nested transaction (savepoint)
            
        Returns:
            TransactionContext object representing the new transaction
            
        Raises:
            TransactionNestingError: If trying to create nested transaction without active parent
            TransactionTimeoutError: If transaction would exceed timeout
        """
        with self._lock:
            # Check for timeout on existing transactions
            if self._context_stack and self.timeout_seconds:
                for ctx in self._context_stack:
                    if ctx.duration > self.timeout_seconds:
                        self._stats["timeouts"] += 1
                        raise TransactionTimeoutError(
                            f"Transaction {ctx.id} exceeded timeout of {self.timeout_seconds}s"
                        )
            
            # Create new transaction context
            context = TransactionContext(session=session, nested_level=len(self._context_stack))
            
            if nested:
                if not self._context_stack:
                    raise TransactionNestingError("Cannot create nested transaction without active parent")
                
                # Use savepoint for nested transaction
                session.begin_nested()
                context.is_nested = True
                context.parent_id = self._context_stack[-1].id
                self._stats["nested_transactions"] += 1
                logger.debug(f"Started nested transaction {context.id} (parent: {context.parent_id})")
            else:
                # Start new top-level transaction
                session.begin()
                logger.debug(f"Started transaction {context.id}")
            
            # Add to context stack
            self._context_stack.append(context)
            self._stats["total_transactions"] += 1
            
            # Log transaction start with detailed information
            logger.info(
                f"Transaction {context.id} started (nested: {nested}, level: {context.nested_level}, "
                f"timeout: {self.timeout_seconds}s, session: {id(session)})"
            )
            
            return context
    
    def increment_affected_rows(self, count: int = 1) -> None:
        """Increment the affected rows count for the current transaction.
        
        Args:
            count: Number of rows affected (default: 1)
        """
        with self._lock:
            if self._context_stack:
                self._context_stack[-1].affected_rows += count
    
    def commit(self) -> None:
        """Commit the current transaction.
        
        Raises:
            TransactionError: If no active transaction to commit
        """
        with self._lock:
            if not self._context_stack:
                raise TransactionError("No active transaction to commit")
            
            context = self._context_stack[-1]
            
            try:
                if context.is_nested:
                    # Commit nested transaction (savepoint)
                    context.session.commit()
                    logger.info(
                        f"Nested transaction {context.id} committed successfully "
                        f"(duration: {context.duration:.3f}s, level: {context.nested_level}, "
                        f"parent: {context.parent_id})"
                    )
                else:
                    # Commit top-level transaction
                    context.session.commit()
                    logger.info(
                        f"Transaction {context.id} committed successfully "
                        f"(duration: {context.duration:.3f}s, affected_rows: {context.affected_rows})"
                    )
                
                self._stats["successful_commits"] += 1
                context.is_completed = True
                
            except Exception as e:
                context.error = e
                logger.error(f"Failed to commit transaction {context.id}: {e}")
                raise
            finally:
                # Remove from stack
                self._context_stack.pop()
    
    def rollback(self, error: Optional[Exception] = None) -> None:
        """Rollback the current transaction.
        
        Args:
            error: Optional exception that caused the rollback
        """
        with self._lock:
            if not self._context_stack:
                logger.warning("No active transaction to rollback")
                return
            
            context = self._context_stack[-1]
            context.error = error
            
            try:
                if context.is_nested:
                    # Rollback nested transaction (savepoint)
                    context.session.rollback()
                    logger.warning(
                        f"Nested transaction {context.id} rolled back "
                        f"(duration: {context.duration:.3f}s, level: {context.nested_level}, "
                        f"parent: {context.parent_id})"
                    )
                else:
                    # Rollback top-level transaction
                    context.session.rollback()
                    logger.error(
                        f"Transaction {context.id} rolled back "
                        f"(duration: {context.duration:.3f}s, affected_rows: {context.affected_rows})"
                    )
                
                self._stats["rollbacks"] += 1
                context.is_completed = True
                
                # Log error details if available
                if error:
                    logger.error(
                        f"Rollback reason for transaction {context.id}: "
                        f"{type(error).__name__}: {error}"
                    )
                
            except Exception as rollback_error:
                logger.error(f"Failed to rollback transaction {context.id}: {rollback_error}")
                raise
            finally:
                # Remove from stack
                self._context_stack.pop()
    
    def get_current_context(self) -> Optional[TransactionContext]:
        """Get the current active transaction context.
        
        Returns:
            Current TransactionContext or None if no active transaction
        """
        with self._lock:
            return self._context_stack[-1] if self._context_stack else None
    
    def is_active(self) -> bool:
        """Check if there's an active transaction.
        
        Returns:
            True if there's an active transaction, False otherwise
        """
        with self._lock:
            return len(self._context_stack) > 0
    
    def get_nesting_level(self) -> int:
        """Get the current nesting level.
        
        Returns:
            Current nesting level (0 for no active transaction)
        """
        with self._lock:
            return len(self._context_stack)
    
    def get_stats(self) -> dict[str, Any]:
        """Get transaction statistics.
        
        Returns:
            Dictionary containing transaction statistics
        """
        with self._lock:
            stats = self._stats.copy()
            stats["active_transactions"] = len(self._context_stack)
            stats["current_nesting_level"] = len(self._context_stack)
            return stats
    
    def reset_stats(self) -> None:
        """Reset transaction statistics."""
        with self._lock:
            self._stats = {
                "total_transactions": 0,
                "successful_commits": 0,
                "rollbacks": 0,
                "timeouts": 0,
                "nested_transactions": 0,
            }
    
    @contextmanager
    def transaction_scope(
        self, 
        session: Session, 
        nested: bool = False,
        timeout: Optional[int] = None
    ) -> Generator[Session, None, None]:
        """Context manager for transaction scope.
        
        Args:
            session: SQLAlchemy session to use
            nested: Whether this is a nested transaction
            timeout: Override default timeout for this transaction
            
        Yields:
            Session: The session for database operations
            
        Example:
            with transaction_manager.transaction_scope(session) as tx_session:
                tx_session.add(some_object)
                # Transaction will be committed automatically
        """
        # Use provided timeout or instance default
        effective_timeout = timeout or self.timeout_seconds
        
        # Check timeout before starting
        if effective_timeout and self._context_stack:
            for ctx in self._context_stack:
                if ctx.duration > effective_timeout:
                    raise TransactionTimeoutError(
                        f"Transaction {ctx.id} exceeded timeout of {effective_timeout}s"
                    )
        
        context = self.begin(session, nested=nested)
        
        try:
            yield session
            self.commit()
        except Exception as e:
            self.rollback(error=e)
            raise


def transactional(
    func: Optional[F] = None,
    *,
    nested: bool = False,
    timeout: Optional[int] = None,
    auto_session: bool = True,
    track_rows: bool = True
) -> Union[F, Callable[[F], F]]:
    """Decorator for automatic transaction management.
    
    Args:
        func: Function to decorate (when used without parentheses)
        nested: Whether to create a nested transaction
        timeout: Transaction timeout in seconds
        auto_session: Whether to automatically inject session parameter
        track_rows: Whether to track affected rows count
        
    Returns:
        Decorated function with transaction management
        
    Example:
            @transactional
            def create_user(self, session, user_data):
                # session is automatically provided
                return UserRepository(session).create(user_data)
                
            @transactional(nested=True)
            def update_user_profile(self, session, user_id, profile_data):
                # This will create a nested transaction
                return ProfileRepository(session).update(user_id, profile_data)
    """
    def decorator(f: F) -> F:
        def wrapper(*args, **kwargs):
            # Capture the decorator parameters
            current_nested = nested
            current_timeout = timeout
            current_auto_session = auto_session
            current_track_rows = track_rows
            # Extract session from various possible sources
            session = None
            
            # Try to get session from kwargs first
            if 'session' in kwargs:
                session = kwargs['session']
            # Try to get session from self (if method)
            elif args and hasattr(args[0], 'db_manager'):
                # Assuming the first arg is self and has db_manager
                db_manager = getattr(args[0], 'db_manager', None)
                if db_manager:
                    session = db_manager.get_session()
            
            # Try to get from global db_manager as fallback
            if not session:
                try:
                    from .database import db_manager
                    session = db_manager.get_session()
                except (ImportError, AttributeError):
                    pass
            
            if not session:
                raise TransactionError("No session available for transaction")
            
            # Get or create transaction manager
            if hasattr(session, '_transaction_manager') and session._transaction_manager is not None:
                tx_manager = session._transaction_manager
            else:
                tx_manager = TransactionManager(timeout_seconds=current_timeout)
                session._transaction_manager = tx_manager
            
            # Use transaction scope
            with tx_manager.transaction_scope(session, nested=current_nested, timeout=current_timeout):
                if current_auto_session and 'session' not in kwargs:
                    # Only add session to kwargs if it's not already in the function signature
                    import inspect
                    sig = inspect.signature(f)
                    if 'session' in sig.parameters:
                        # Function expects session as positional argument
                        # Find the position of 'session' parameter and insert it there
                        params = list(sig.parameters.keys())
                        session_index = params.index('session')
                        
                        # Adjust for self parameter in methods (index 0)
                        if len(args) > 0 and hasattr(args[0], '__class__'):
                            # This is a method call, session should be inserted after self
                            actual_session_index = session_index
                        else:
                            # This is a function call, session should be inserted at its position
                            actual_session_index = session_index
                        
                        # Insert session at the correct position
                        args = args[:actual_session_index] + (session,) + args[actual_session_index:]
                    else:
                        # Function doesn't expect session, add to kwargs
                        kwargs['session'] = session
                
                # Track affected rows if enabled
                if current_track_rows:
                    # Hook into session events to track row counts
                    original_add = session.add
                    original_merge = session.merge
                    original_delete = session.delete
                    
                    def tracked_add(instance):
                        result = original_add(instance)
                        tx_manager.increment_affected_rows()
                        return result
                    
                    def tracked_merge(instance, load=True):
                        result = original_merge(instance, load)
                        tx_manager.increment_affected_rows()
                        return result
                    
                    def tracked_delete(instance):
                        result = original_delete(instance)
                        tx_manager.increment_affected_rows()
                        return result
                    
                    session.add = tracked_add
                    session.merge = tracked_merge
                    session.delete = tracked_delete
                
                try:
                    return f(*args, **kwargs)
                finally:
                    # Restore original methods
                    if current_track_rows:
                        session.add = original_add
                        session.merge = original_merge
                        session.delete = original_delete
        
        # Apply wraps manually to preserve function metadata
        wrapper.__name__ = f.__name__
        wrapper.__doc__ = f.__doc__
        wrapper.__module__ = f.__module__
        wrapper.__qualname__ = f.__qualname__
        wrapper.__annotations__ = f.__annotations__
        return wrapper
    
    # Handle both @transactional and @transactional(...) cases
    if func is None:
        # Called with arguments: @transactional(nested=True)
        return decorator
    else:
        # Called without arguments: @transactional
        return decorator(func)


def get_transaction_manager() -> TransactionManager:
    """Get a new transaction manager instance.
    
    Returns:
        New TransactionManager instance
    """
    return TransactionManager()
