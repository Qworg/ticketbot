"""Monitoring middleware for FastAPI backend."""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.logging_config import metrics_collector, get_logger

logger = get_logger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring requests and collecting metrics."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = get_logger("backend.monitoring")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect monitoring data."""
        start_time = time.time()
        
        # Log request start
        self.logger.info(
            "Request started",
            extra={
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "request_id": getattr(request.state, "request_id", "unknown"),
            }
        )
        
        # Increment request counter
        metrics_collector.increment_requests()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            process_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Record metrics
            metrics_collector.increment_requests(response.status_code)
            metrics_collector.record_response_time(process_time)
            
            # Add response headers
            response.headers["X-Process-Time"] = str(process_time)
            
            # Log request completion
            self.logger.info(
                "Request completed",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "process_time_ms": process_time,
                    "request_id": getattr(request.state, "request_id", "unknown"),
                }
            )
            
            return response
            
        except Exception as e:
            # Calculate response time for errors
            process_time = (time.time() - start_time) * 1000
            
            # Record error metrics
            metrics_collector.increment_errors()
            metrics_collector.record_response_time(process_time)
            
            # Log error
            self.logger.error(
                "Request failed",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "process_time_ms": process_time,
                    "error": str(e),
                    "request_id": getattr(request.state, "request_id", "unknown"),
                },
                exc_info=True
            )
            
            # Re-raise the exception
            raise


class DatabaseMonitoringMixin:
    """Mixin for monitoring database operations."""
    
    def __init__(self):
        self.logger = get_logger("backend.database")
    
    def log_query(self, query: str, params: dict = None, execution_time: float = None):
        """Log database query execution."""
        metrics_collector.increment_db_queries()
        
        self.logger.debug(
            "Database query executed",
            extra={
                "query": query[:200] + "..." if len(query) > 200 else query,
                "params": params,
                "execution_time_ms": execution_time * 1000 if execution_time else None,
            }
        )
    
    def log_error(self, error: Exception, query: str = None):
        """Log database error."""
        self.logger.error(
            "Database operation failed",
            extra={
                "error": str(error),
                "query": query[:200] + "..." if query and len(query) > 200 else query,
            },
            exc_info=True
        )


class RedisMonitoringMixin:
    """Mixin for monitoring Redis operations."""
    
    def __init__(self):
        self.logger = get_logger("backend.redis")
    
    def log_operation(self, operation: str, key: str = None, execution_time: float = None):
        """Log Redis operation."""
        metrics_collector.increment_redis_operations()
        
        self.logger.debug(
            "Redis operation executed",
            extra={
                "operation": operation,
                "key": key,
                "execution_time_ms": execution_time * 1000 if execution_time else None,
            }
        )
    
    def log_error(self, error: Exception, operation: str = None, key: str = None):
        """Log Redis error."""
        self.logger.error(
            "Redis operation failed",
            extra={
                "error": str(error),
                "operation": operation,
                "key": key,
            },
            exc_info=True
        )


class WebSocketMonitoringMixin:
    """Mixin for monitoring WebSocket connections."""
    
    def __init__(self):
        self.logger = get_logger("backend.websocket")
    
    def log_connection(self, user_id: int, action: str):
        """Log WebSocket connection events."""
        if action == "connect":
            metrics_collector.increment_connections(1)
        elif action == "disconnect":
            metrics_collector.increment_connections(-1)
        
        self.logger.info(
            f"WebSocket {action}",
            extra={
                "user_id": user_id,
                "action": action,
                "active_connections": metrics_collector.metrics["active_connections"],
            }
        )
    
    def log_message(self, user_id: int, message_type: str, size: int = None):
        """Log WebSocket message."""
        self.logger.debug(
            "WebSocket message",
            extra={
                "user_id": user_id,
                "message_type": message_type,
                "size_bytes": size,
            }
        )
    
    def log_error(self, error: Exception, user_id: int = None):
        """Log WebSocket error."""
        self.logger.error(
            "WebSocket error",
            extra={
                "error": str(error),
                "user_id": user_id,
            },
            exc_info=True
        )