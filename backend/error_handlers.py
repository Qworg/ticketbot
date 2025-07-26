"""Global error handlers for the FastAPI application.

This module provides comprehensive error handling for the Discord Ticket Bot
backend, including custom exception handlers, database error handling,
and structured error responses.
"""

import logging
import traceback
from typing import Dict, Any, Union, List
from datetime import datetime

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import (
    SQLAlchemyError, 
    IntegrityError, 
    DataError, 
    OperationalError,
    TimeoutError as SQLTimeoutError,
    DisconnectionError
)
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from backend.exceptions import (
    TicketBotException,
    ValidationError,
    NotFoundError,
    ConflictError,
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
    ExternalServiceError,
    RateLimitError,
    BusinessLogicError,
    ConfigurationError
)

# Configure logger
logger = logging.getLogger(__name__)


class ErrorResponse:
    """Structured error response builder."""
    
    @staticmethod
    def build_error_response(
        error_code: str,
        message: str,
        details: Dict[str, Any] = None,
        request_id: str = None,
        timestamp: datetime = None
    ) -> Dict[str, Any]:
        """Build a structured error response.
        
        Args:
            error_code: Application-specific error code
            message: Human-readable error message
            details: Additional error details
            request_id: Request identifier for tracing
            timestamp: Error timestamp
            
        Returns:
            Structured error response dictionary
        """
        response = {
            "error": {
                "code": error_code,
                "message": message,
                "timestamp": (timestamp or datetime.utcnow()).isoformat() + "Z"
            }
        }
        
        if details:
            response["error"]["details"] = details
            
        if request_id:
            response["error"]["request_id"] = request_id
            
        return response


async def ticket_bot_exception_handler(request: Request, exc: TicketBotException) -> JSONResponse:
    """Handle custom TicketBot exceptions.
    
    Args:
        request: FastAPI request object
        exc: TicketBot exception instance
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", None)
    
    # Log the error
    logger.error(
        f"TicketBot exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    response = ErrorResponse.build_error_response(
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions.
    
    Args:
        request: FastAPI request object
        exc: HTTP exception instance
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", None)
    
    # Map HTTP status codes to error codes
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT"
    }
    
    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")
    
    # Log the error
    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    response = ErrorResponse.build_error_response(
        error_code=error_code,
        message=str(exc.detail),
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors.
    
    Args:
        request: FastAPI request object
        exc: Request validation error instance
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", None)
    
    # Format validation errors
    validation_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        validation_errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    # Log the error
    logger.warning(
        f"Validation error: {len(validation_errors)} field(s) failed validation",
        extra={
            "validation_errors": validation_errors,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    response = ErrorResponse.build_error_response(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"validation_errors": validation_errors},
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database errors.
    
    Args:
        request: FastAPI request object
        exc: SQLAlchemy exception instance
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", None)
    
    # Determine error type and appropriate response
    if isinstance(exc, IntegrityError):
        error_code = "DATABASE_INTEGRITY_ERROR"
        message = "Database integrity constraint violation"
        status_code = status.HTTP_409_CONFLICT
        
        # Extract constraint information if available
        details = {"constraint_type": "integrity"}
        if hasattr(exc, "orig") and exc.orig:
            details["database_error"] = str(exc.orig)
            
    elif isinstance(exc, DataError):
        error_code = "DATABASE_DATA_ERROR"
        message = "Invalid data provided for database operation"
        status_code = status.HTTP_400_BAD_REQUEST
        details = {"error_type": "data_error"}
        
    elif isinstance(exc, OperationalError):
        error_code = "DATABASE_OPERATIONAL_ERROR"
        message = "Database operational error"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        details = {"error_type": "operational"}
        
    elif isinstance(exc, SQLTimeoutError):
        error_code = "DATABASE_TIMEOUT_ERROR"
        message = "Database operation timed out"
        status_code = status.HTTP_504_GATEWAY_TIMEOUT
        details = {"error_type": "timeout"}
        
    elif isinstance(exc, DisconnectionError):
        error_code = "DATABASE_CONNECTION_ERROR"
        message = "Database connection lost"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        details = {"error_type": "disconnection"}
        
    else:
        error_code = "DATABASE_ERROR"
        message = "Database operation failed"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        details = {"error_type": "generic"}
    
    # Add original error information for debugging
    if hasattr(exc, "statement"):
        details["statement"] = str(exc.statement)
    if hasattr(exc, "params"):
        details["params"] = str(exc.params)
    
    # Log the error
    logger.error(
        f"Database error: {error_code} - {message}",
        extra={
            "error_code": error_code,
            "exception_type": type(exc).__name__,
            "details": details,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        },
        exc_info=True
    )
    
    response = ErrorResponse.build_error_response(
        error_code=error_code,
        message=message,
        details=details,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status_code,
        content=response
    )


async def redis_exception_handler(request: Request, exc: RedisError) -> JSONResponse:
    """Handle Redis errors.
    
    Args:
        request: FastAPI request object
        exc: Redis exception instance
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", None)
    
    # Determine error type
    if isinstance(exc, RedisConnectionError):
        error_code = "REDIS_CONNECTION_ERROR"
        message = "Redis connection failed"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        error_code = "REDIS_ERROR"
        message = "Redis operation failed"
        status_code = status.HTTP_502_BAD_GATEWAY
    
    details = {
        "service": "redis",
        "error_type": type(exc).__name__,
        "original_error": str(exc)
    }
    
    # Log the error
    logger.error(
        f"Redis error: {error_code} - {message}",
        extra={
            "error_code": error_code,
            "exception_type": type(exc).__name__,
            "details": details,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        },
        exc_info=True
    )
    
    response = ErrorResponse.build_error_response(
        error_code=error_code,
        message=message,
        details=details,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status_code,
        content=response
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions.
    
    Args:
        request: FastAPI request object
        exc: Generic exception instance
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", None)
    
    # Log the full traceback for debugging
    logger.error(
        f"Unexpected error: {type(exc).__name__} - {str(exc)}",
        extra={
            "exception_type": type(exc).__name__,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc()
        },
        exc_info=True
    )
    
    response = ErrorResponse.build_error_response(
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
        details={
            "error_type": type(exc).__name__,
            "error_message": str(exc)
        },
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response
    )


def setup_error_handlers(app):
    """Set up all error handlers for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Custom exception handlers
    app.add_exception_handler(TicketBotException, ticket_bot_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Database error handlers
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    
    # External service error handlers
    app.add_exception_handler(RedisError, redis_exception_handler)
    
    # Generic exception handler (catch-all)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Error handlers configured successfully")


# Utility functions for error handling in services

def handle_database_error(operation: str, table: str = None) -> callable:
    """Decorator to handle database errors in service methods.
    
    Args:
        operation: Description of the database operation
        table: Database table name (optional)
        
    Returns:
        Decorator function
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except SQLAlchemyError as e:
                raise DatabaseError(
                    message=f"Database {operation} failed",
                    operation=operation,
                    table=table,
                    original_error=e
                )
            except Exception as e:
                if isinstance(e, TicketBotException):
                    raise
                raise DatabaseError(
                    message=f"Unexpected error during {operation}",
                    operation=operation,
                    table=table,
                    original_error=e
                )
        return wrapper
    return decorator


def handle_external_service_error(service: str, operation: str = None) -> callable:
    """Decorator to handle external service errors.
    
    Args:
        service: Name of the external service
        operation: Description of the operation (optional)
        
    Returns:
        Decorator function
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except (RedisError, RedisConnectionError) as e:
                raise ExternalServiceError(
                    message=f"{service} operation failed",
                    service=service,
                    operation=operation,
                    original_error=e
                )
            except Exception as e:
                if isinstance(e, TicketBotException):
                    raise
                raise ExternalServiceError(
                    message=f"Unexpected error in {service}",
                    service=service,
                    operation=operation,
                    original_error=e
                )
        return wrapper
    return decorator