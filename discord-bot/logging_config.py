"""Logging configuration for the Discord bot."""

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
            "service": "discord-bot",
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
                'exc_text', 'stack_info', 'service'
            }:
                log_entry[key] = value
        
        return json.dumps(log_entry)


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
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "simple": {
                "format": "%(levelname)s - %(name)s - %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "json" if environment == "production" else "detailed",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            # Application loggers
            "discord_bot": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "bot": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            # Discord.py loggers
            "discord": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "discord.client": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "discord.gateway": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "discord.http": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            # HTTP client logger
            "httpx": {
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
            "filename": "/var/log/discord-bot/app.log",
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


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)


# Metrics collection for Discord bot
class BotMetricsCollector:
    """Simple metrics collector for Discord bot monitoring."""
    
    def __init__(self):
        self.metrics = {
            "commands_executed": 0,
            "commands_by_type": {},
            "messages_processed": 0,
            "api_calls": 0,
            "errors_total": 0,
            "guilds_connected": 0,
            "users_interacted": set(),
            "uptime_start": datetime.utcnow(),
        }
    
    def increment_commands(self, command_name: str):
        """Increment command counter."""
        self.metrics["commands_executed"] += 1
        self.metrics["commands_by_type"][command_name] = (
            self.metrics["commands_by_type"].get(command_name, 0) + 1
        )
    
    def increment_messages(self):
        """Increment message counter."""
        self.metrics["messages_processed"] += 1
    
    def increment_api_calls(self):
        """Increment API call counter."""
        self.metrics["api_calls"] += 1
    
    def increment_errors(self):
        """Increment error counter."""
        self.metrics["errors_total"] += 1
    
    def add_user_interaction(self, user_id: int):
        """Add user to interaction set."""
        self.metrics["users_interacted"].add(user_id)
    
    def set_guild_count(self, count: int):
        """Set guild count."""
        self.metrics["guilds_connected"] = count
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        metrics = self.metrics.copy()
        
        # Convert set to count for JSON serialization
        metrics["unique_users_interacted"] = len(metrics["users_interacted"])
        del metrics["users_interacted"]
        
        # Calculate uptime
        uptime = datetime.utcnow() - metrics["uptime_start"]
        metrics["uptime_seconds"] = uptime.total_seconds()
        metrics["uptime_start"] = metrics["uptime_start"].isoformat() + "Z"
        
        return metrics


# Global metrics collector instance
bot_metrics_collector = BotMetricsCollector()