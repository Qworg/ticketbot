"""Logging configuration for the Discord Ticket Bot backend."""

import logging
import logging.config
import os
import sys
from typing import Dict, Any
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info'
            }:
                log_entry[key] = value
        
        return json.dumps(log_entry)


class RequestContextFilter(logging.Filter):
    """Filter to add request context to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to log record."""
        # Try to get request context from contextvars or thread local
        # This would be set by middleware
        record.request_id = getattr(record, 'request_id', 'N/A')
        record.user_id = getattr(record, 'user_id', 'N/A')
        record.service = 'backend'
        return True


def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration based on environment."""
    environment = os.getenv("ENVIRONMENT", "development")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Base configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "simple": {
                "format": "%(levelname)s - %(name)s - %(message)s",
            },
        },
        "filters": {
            "request_context": {
                "()": RequestContextFilter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "json" if environment == "production" else "detailed",
                "filters": ["request_context"],
                "stream": sys.stdout,
            },
        },
        "loggers": {
            # Application loggers
            "backend": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "discord_bot": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            # Third-party loggers
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "redis": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
    }
    
    # Add file logging for production
    if environment == "production":
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "json",
            "filters": ["request_context"],
            "filename": "/var/log/backend/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        }
        
        # Add file handler to all loggers
        for logger_config in config["loggers"].values():
            if "handlers" in logger_config:
                logger_config["handlers"].append("file")
        config["root"]["handlers"].append("file")
    
    return config


def setup_logging():
    """Set up logging configuration."""
    config = get_logging_config()
    logging.config.dictConfig(config)
    
    # Set up uvicorn logging
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    
    # Disable uvicorn default formatting
    for handler in uvicorn_logger.handlers:
        handler.setFormatter(logging.Formatter())
    for handler in uvicorn_access_logger.handlers:
        handler.setFormatter(logging.Formatter())


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)


# Metrics collection helpers
class MetricsCollector:
    """Simple metrics collector for monitoring."""
    
    def __init__(self):
        self.metrics = {
            "requests_total": 0,
            "requests_by_status": {},
            "response_times": [],
            "active_connections": 0,
            "database_queries": 0,
            "redis_operations": 0,
            "errors_total": 0,
        }
    
    def increment_requests(self, status_code: int = None):
        """Increment request counter."""
        self.metrics["requests_total"] += 1
        if status_code:
            self.metrics["requests_by_status"][status_code] = (
                self.metrics["requests_by_status"].get(status_code, 0) + 1
            )
    
    def record_response_time(self, time_ms: float):
        """Record response time."""
        self.metrics["response_times"].append(time_ms)
        # Keep only last 1000 response times
        if len(self.metrics["response_times"]) > 1000:
            self.metrics["response_times"] = self.metrics["response_times"][-1000:]
    
    def increment_connections(self, delta: int = 1):
        """Increment active connections."""
        self.metrics["active_connections"] += delta
    
    def increment_db_queries(self):
        """Increment database query counter."""
        self.metrics["database_queries"] += 1
    
    def increment_redis_operations(self):
        """Increment Redis operation counter."""
        self.metrics["redis_operations"] += 1
    
    def increment_errors(self):
        """Increment error counter."""
        self.metrics["errors_total"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        metrics = self.metrics.copy()
        
        # Calculate response time statistics
        if metrics["response_times"]:
            response_times = metrics["response_times"]
            metrics["avg_response_time"] = sum(response_times) / len(response_times)
            metrics["min_response_time"] = min(response_times)
            metrics["max_response_time"] = max(response_times)
        else:
            metrics["avg_response_time"] = 0
            metrics["min_response_time"] = 0
            metrics["max_response_time"] = 0
        
        # Remove raw response times from output
        del metrics["response_times"]
        
        return metrics


# Global metrics collector instance
metrics_collector = MetricsCollector()