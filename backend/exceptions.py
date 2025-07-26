"""Custom exceptions for the Discord Ticket Bot backend.

This module defines custom exception classes that provide structured
error handling throughout the application.
"""

from typing import Any, Dict, Optional, Union
from fastapi import status


class TicketBotException(Exception):
    """Base exception class for all Discord Ticket Bot errors.
    
    Attributes:
        message: Human-readable error message
        error_code: Application-specific error code
        details: Additional error details
        status_code: HTTP status code for API responses
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "GENERIC_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(TicketBotException):
    """Exception raised for data validation errors."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field
        if value is not None:
            error_details["value"] = value
            
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=error_details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class NotFoundError(TicketBotException):
    """Exception raised when a requested resource is not found."""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: Union[str, int],
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"{resource_type} with ID {resource_id} not found"
        error_details = details or {}
        error_details.update({
            "resource_type": resource_type,
            "resource_id": str(resource_id)
        })
        
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            details=error_details,
            status_code=status.HTTP_404_NOT_FOUND
        )


class ConflictError(TicketBotException):
    """Exception raised when a resource conflict occurs."""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[Union[str, int]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if resource_type:
            error_details["resource_type"] = resource_type
        if resource_id:
            error_details["resource_id"] = str(resource_id)
            
        super().__init__(
            message=message,
            error_code="RESOURCE_CONFLICT",
            details=error_details,
            status_code=status.HTTP_409_CONFLICT
        )


class AuthenticationError(TicketBotException):
    """Exception raised for authentication failures."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationError(TicketBotException):
    """Exception raised for authorization failures."""
    
    def __init__(
        self,
        message: str = "Access denied",
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if resource_type:
            error_details["resource_type"] = resource_type
        if action:
            error_details["action"] = action
            
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=error_details,
            status_code=status.HTTP_403_FORBIDDEN
        )


class DatabaseError(TicketBotException):
    """Exception raised for database operation errors."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if operation:
            error_details["operation"] = operation
        if table:
            error_details["table"] = table
        if original_error:
            error_details["original_error"] = str(original_error)
            error_details["error_type"] = type(original_error).__name__
            
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details=error_details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class ExternalServiceError(TicketBotException):
    """Exception raised for external service errors (Discord API, Redis, etc.)."""
    
    def __init__(
        self,
        message: str,
        service: str,
        operation: Optional[str] = None,
        status_code: Optional[int] = None,
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        error_details["service"] = service
        if operation:
            error_details["operation"] = operation
        if status_code:
            error_details["service_status_code"] = status_code
        if original_error:
            error_details["original_error"] = str(original_error)
            error_details["error_type"] = type(original_error).__name__
            
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=error_details,
            status_code=status.HTTP_502_BAD_GATEWAY
        )


class RateLimitError(TicketBotException):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        service: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if service:
            error_details["service"] = service
        if retry_after:
            error_details["retry_after"] = retry_after
            
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            details=error_details,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )


class BusinessLogicError(TicketBotException):
    """Exception raised for business logic violations."""
    
    def __init__(
        self,
        message: str,
        rule: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if rule:
            error_details["business_rule"] = rule
            
        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            details=error_details,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class ConfigurationError(TicketBotException):
    """Exception raised for configuration errors."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if config_key:
            error_details["config_key"] = config_key
            
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=error_details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )