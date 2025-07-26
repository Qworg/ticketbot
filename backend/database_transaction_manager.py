"""Database transaction manager with comprehensive error handling.

This module provides transaction management utilities with automatic
rollback, retry logic, and structured error handling for database operations.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable, Any, Optional, Dict
from functools import wraps

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import (
    SQLAlchemyError,
    IntegrityError,
    OperationalError,
    TimeoutError as SQLTimeoutError,
    DisconnectionError,
    StatementError
)

from backend.exceptions import DatabaseError, ConflictError, ValidationError
from backend.database_service import DatabaseService, get_database_service

# Configure logger
logger = logging.getLogger(__name__)


class TransactionManager:
    """Advanced transaction manager with retry logic and error handling."""
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        exponential_backoff: bool = True
    ):
        """Initialize transaction manager.
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (seconds)
            exponential_backoff: Whether to use exponential backoff
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff
    
    @asynccontextmanager
    async def transaction(
        self,
        db_service: DatabaseService,
        isolation_level: Optional[str] = None
    ) -> AsyncGenerator[DatabaseService, None]:
        """Execute operations within a database transaction.
        
        Args:
            db_service: Database service instance
            isolation_level: Transaction isolation level
            
        Yields:
            Database service instance
            
        Raises:
            DatabaseError: If transaction fails after all retries
        """
        attempt = 0
        last_error = None
        
        while attempt <= self.max_retries:
            try:
                # Set isolation level if specified
                if isolation_level:
                    await db_service.session.execute(
                        f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"
                    )
                
                # Begin transaction (implicit with session)
                yield db_service
                
                # Commit transaction
                await db_service.commit()
                logger.debug(f"Transaction committed successfully on attempt {attempt + 1}")
                return
                
            except (OperationalError, DisconnectionError, SQLTimeoutError) as e:
                # These errors might be transient, so we retry
                last_error = e
                attempt += 1
                
                # Rollback the failed transaction
                try:
                    await db_service.rollback()
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback transaction: {rollback_error}")
                
                if attempt <= self.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"Transaction failed (attempt {attempt}/{self.max_retries + 1}), "
                        f"retrying in {delay}s: {str(e)}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Transaction failed after {self.max_retries + 1} attempts")
                    break
                    
            except IntegrityError as e:
                # Integrity errors are not transient, don't retry
                await db_service.rollback()
                raise ConflictError(
                    message="Database integrity constraint violation",
                    details={
                        "constraint_error": str(e.orig) if hasattr(e, 'orig') else str(e),
                        "statement": str(e.statement) if hasattr(e, 'statement') else None
                    }
                )
                
            except StatementError as e:
                # Statement errors are usually not transient
                await db_service.rollback()
                raise ValidationError(
                    message="Invalid database operation",
                    details={
                        "statement_error": str(e.orig) if hasattr(e, 'orig') else str(e),
                        "statement": str(e.statement) if hasattr(e, 'statement') else None
                    }
                )
                
            except SQLAlchemyError as e:
                # Other SQLAlchemy errors
                await db_service.rollback()
                raise DatabaseError(
                    message="Database operation failed",
                    operation="transaction",
                    original_error=e,
                    details={
                        "error_type": type(e).__name__,
                        "attempt": attempt + 1
                    }
                )
                
            except Exception as e:
                # Unexpected errors
                try:
                    await db_service.rollback()
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback transaction: {rollback_error}")
                
                raise DatabaseError(
                    message="Unexpected error during transaction",
                    operation="transaction",
                    original_error=e,
                    details={
                        "error_type": type(e).__name__,
                        "attempt": attempt + 1
                    }
                )
        
        # If we get here, all retries failed
        raise DatabaseError(
            message=f"Transaction failed after {self.max_retries + 1} attempts",
            operation="transaction",
            original_error=last_error,
            details={
                "max_retries": self.max_retries,
                "final_attempt": attempt
            }
        )
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt.
        
        Args:
            attempt: Current attempt number (1-based)
            
        Returns:
            Delay in seconds
        """
        if self.exponential_backoff:
            return self.retry_delay * (2 ** (attempt - 1))
        return self.retry_delay


# Global transaction manager instance
transaction_manager = TransactionManager()


@asynccontextmanager
async def database_transaction(
    isolation_level: Optional[str] = None,
    max_retries: int = 3
) -> AsyncGenerator[DatabaseService, None]:
    """Context manager for database transactions with error handling.
    
    Args:
        isolation_level: Transaction isolation level
        max_retries: Maximum number of retry attempts
        
    Yields:
        Database service instance
        
    Example:
        async def create_ticket_with_message():
            async with database_transaction() as db:
                ticket = await db.tickets.create(...)
                message = await db.messages.create(...)
                return ticket
    """
    async with get_database_service() as db_service:
        tx_manager = TransactionManager(max_retries=max_retries)
        async with tx_manager.transaction(db_service, isolation_level) as db:
            yield db


def transactional(
    isolation_level: Optional[str] = None,
    max_retries: int = 3,
    auto_commit: bool = True
):
    """Decorator to wrap functions in database transactions.
    
    Args:
        isolation_level: Transaction isolation level
        max_retries: Maximum number of retry attempts
        auto_commit: Whether to auto-commit the transaction
        
    Returns:
        Decorator function
        
    Example:
        @transactional()
        async def create_ticket_with_message(ticket_data, message_data):
            async with get_database_service() as db:
                ticket = await db.tickets.create(ticket_data)
                message = await db.messages.create(message_data)
                return ticket
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if auto_commit:
                async with database_transaction(isolation_level, max_retries) as db:
                    # Inject db service if function expects it
                    if 'db' in func.__code__.co_varnames:
                        kwargs['db'] = db
                    return await func(*args, **kwargs)
            else:
                # Just handle errors without auto-commit
                try:
                    return await func(*args, **kwargs)
                except SQLAlchemyError as e:
                    raise DatabaseError(
                        message="Database operation failed",
                        operation=func.__name__,
                        original_error=e
                    )
        return wrapper
    return decorator


class BatchOperationManager:
    """Manager for batch database operations with error handling."""
    
    def __init__(self, batch_size: int = 100, continue_on_error: bool = False):
        """Initialize batch operation manager.
        
        Args:
            batch_size: Number of operations per batch
            continue_on_error: Whether to continue processing after errors
        """
        self.batch_size = batch_size
        self.continue_on_error = continue_on_error
    
    async def execute_batch(
        self,
        operations: list,
        db_service: DatabaseService,
        operation_name: str = "batch_operation"
    ) -> Dict[str, Any]:
        """Execute a batch of database operations.
        
        Args:
            operations: List of async functions to execute
            db_service: Database service instance
            operation_name: Name for logging and error reporting
            
        Returns:
            Dictionary with results and error information
        """
        results = []
        errors = []
        processed = 0
        
        # Process operations in batches
        for i in range(0, len(operations), self.batch_size):
            batch = operations[i:i + self.batch_size]
            batch_results = []
            batch_errors = []
            
            async with transaction_manager.transaction(db_service) as db:
                for j, operation in enumerate(batch):
                    try:
                        result = await operation(db)
                        batch_results.append({
                            "index": i + j,
                            "result": result,
                            "status": "success"
                        })
                        processed += 1
                        
                    except Exception as e:
                        error_info = {
                            "index": i + j,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "status": "error"
                        }
                        batch_errors.append(error_info)
                        
                        if not self.continue_on_error:
                            # Rollback will happen automatically
                            raise DatabaseError(
                                message=f"Batch operation failed at index {i + j}",
                                operation=operation_name,
                                original_error=e,
                                details={
                                    "batch_index": i // self.batch_size,
                                    "operation_index": j,
                                    "processed_count": processed
                                }
                            )
                        
                        logger.warning(
                            f"Error in batch operation {operation_name} at index {i + j}: {e}"
                        )
            
            results.extend(batch_results)
            errors.extend(batch_errors)
            
            logger.info(
                f"Processed batch {i // self.batch_size + 1} of {operation_name}: "
                f"{len(batch_results)} successful, {len(batch_errors)} errors"
            )
        
        return {
            "total_operations": len(operations),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
            "operation_name": operation_name
        }


# Utility functions for common transaction patterns

async def safe_create_with_conflict_check(
    create_func: Callable,
    check_func: Callable,
    conflict_message: str,
    *args,
    **kwargs
) -> Any:
    """Safely create a resource with conflict checking.
    
    Args:
        create_func: Function to create the resource
        check_func: Function to check if resource already exists
        conflict_message: Message for conflict error
        *args: Arguments for create function
        **kwargs: Keyword arguments for create function
        
    Returns:
        Created resource
        
    Raises:
        ConflictError: If resource already exists
    """
    async with database_transaction() as db:
        # Check if resource already exists
        existing = await check_func(db, *args, **kwargs)
        if existing:
            raise ConflictError(message=conflict_message)
        
        # Create the resource
        return await create_func(db, *args, **kwargs)


async def safe_update_with_version_check(
    get_func: Callable,
    update_func: Callable,
    resource_id: Any,
    expected_version: Optional[int] = None,
    *args,
    **kwargs
) -> Any:
    """Safely update a resource with optimistic locking.
    
    Args:
        get_func: Function to get the current resource
        update_func: Function to update the resource
        resource_id: ID of the resource to update
        expected_version: Expected version for optimistic locking
        *args: Arguments for update function
        **kwargs: Keyword arguments for update function
        
    Returns:
        Updated resource
        
    Raises:
        NotFoundError: If resource doesn't exist
        ConflictError: If version mismatch occurs
    """
    async with database_transaction() as db:
        # Get current resource
        current = await get_func(db, resource_id)
        if not current:
            from backend.exceptions import NotFoundError
            raise NotFoundError("Resource", resource_id)
        
        # Check version if provided
        if expected_version is not None:
            current_version = getattr(current, 'version', None)
            if current_version != expected_version:
                raise ConflictError(
                    message="Resource has been modified by another process",
                    details={
                        "expected_version": expected_version,
                        "current_version": current_version
                    }
                )
        
        # Update the resource
        return await update_func(db, resource_id, *args, **kwargs)