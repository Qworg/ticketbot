"""Metrics endpoints for monitoring and observability."""

import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer

from backend.logging_config import metrics_collector, get_logger
from backend.services.redis_service import RedisService, get_redis
from backend.db import get_db_session
from backend.models import Ticket

router = APIRouter(prefix="/metrics", tags=["metrics"])
security = HTTPBearer()
logger = get_logger(__name__)


@router.get("/health")
async def detailed_health_check(
    redis: RedisService = Depends(get_redis),
    db = Depends(get_db_session)
):
    """Detailed health check with component status."""
    start_time = time.time()
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "discord-ticket-bot-backend",
        "version": "1.0.0",
        "uptime_seconds": time.time() - start_time,
        "components": {}
    }
    
    # Check database
    try:
        # Simple query to test database connection
        result = await db.execute("SELECT 1")
        await result.fetchone()
        health_status["components"]["database"] = {
            "status": "healthy",
            "type": "postgresql",
            "response_time_ms": (time.time() - start_time) * 1000
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "type": "postgresql",
            "error": str(e)
        }
    
    # Check Redis
    redis_start = time.time()
    try:
        await redis.ping()
        health_status["components"]["redis"] = {
            "status": "healthy",
            "type": "redis",
            "response_time_ms": (time.time() - redis_start) * 1000
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "type": "redis",
            "error": str(e)
        }
    
    # Check system resources
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        health_status["components"]["system"] = {
            "status": "healthy" if cpu_percent < 90 and memory.percent < 90 else "degraded",
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "available_memory_mb": memory.available // 1024 // 1024,
            "available_disk_gb": disk.free // 1024 // 1024 // 1024
        }
        
        if cpu_percent > 90 or memory.percent > 90:
            health_status["status"] = "degraded"
            
    except Exception as e:
        health_status["components"]["system"] = {
            "status": "unknown",
            "error": str(e)
        }
    
    return health_status


@router.get("/application")
async def application_metrics():
    """Get application-specific metrics."""
    metrics = metrics_collector.get_metrics()
    
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "discord-ticket-bot-backend",
        "metrics": metrics
    }


@router.get("/system")
async def system_metrics():
    """Get system resource metrics."""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        
        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        
        # Network metrics (if available)
        try:
            network = psutil.net_io_counters()
            network_stats = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv,
                "errin": network.errin,
                "errout": network.errout,
                "dropin": network.dropin,
                "dropout": network.dropout
            }
        except:
            network_stats = None
        
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
                "load_avg_1m": load_avg[0],
                "load_avg_5m": load_avg[1],
                "load_avg_15m": load_avg[2]
            },
            "memory": {
                "total_bytes": memory.total,
                "available_bytes": memory.available,
                "used_bytes": memory.used,
                "percent": memory.percent,
                "swap_total_bytes": swap.total,
                "swap_used_bytes": swap.used,
                "swap_percent": swap.percent
            },
            "disk": {
                "total_bytes": disk.total,
                "used_bytes": disk.used,
                "free_bytes": disk.free,
                "percent": disk.percent
            },
            "network": network_stats
        }
        
    except Exception as e:
        logger.error("Failed to collect system metrics", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to collect system metrics: {str(e)}")


@router.get("/database")
async def database_metrics(db = Depends(get_db_session)):
    """Get database-specific metrics."""
    try:
        # Get ticket statistics
        total_tickets = await db.execute("SELECT COUNT(*) FROM tickets")
        total_tickets = (await total_tickets.fetchone())[0]
        
        open_tickets = await db.execute("SELECT COUNT(*) FROM tickets WHERE status = 'open'")
        open_tickets = (await open_tickets.fetchone())[0]
        
        closed_tickets = await db.execute("SELECT COUNT(*) FROM tickets WHERE status = 'closed'")
        closed_tickets = (await closed_tickets.fetchone())[0]
        
        # Get recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_tickets = await db.execute(
            "SELECT COUNT(*) FROM tickets WHERE created_at > %s",
            (yesterday,)
        )
        recent_tickets = (await recent_tickets.fetchone())[0]
        
        # Get message statistics
        total_messages = await db.execute("SELECT COUNT(*) FROM messages")
        total_messages = (await total_messages.fetchone())[0]
        
        recent_messages = await db.execute(
            "SELECT COUNT(*) FROM messages WHERE created_at > %s",
            (yesterday,)
        )
        recent_messages = (await recent_messages.fetchone())[0]
        
        # Get database size information
        db_size = await db.execute(
            "SELECT pg_size_pretty(pg_database_size(current_database()))"
        )
        db_size = (await db_size.fetchone())[0]
        
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "tickets": {
                "total": total_tickets,
                "open": open_tickets,
                "closed": closed_tickets,
                "created_last_24h": recent_tickets
            },
            "messages": {
                "total": total_messages,
                "created_last_24h": recent_messages
            },
            "database": {
                "size": db_size,
                "queries_executed": metrics_collector.metrics["database_queries"]
            }
        }
        
    except Exception as e:
        logger.error("Failed to collect database metrics", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to collect database metrics: {str(e)}")


@router.get("/redis")
async def redis_metrics(redis: RedisService = Depends(get_redis)):
    """Get Redis-specific metrics."""
    try:
        # Get Redis info
        info = await redis.info()
        
        # Extract relevant metrics
        redis_metrics = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "server": {
                "version": info.get("redis_version"),
                "uptime_seconds": info.get("uptime_in_seconds"),
                "connected_clients": info.get("connected_clients"),
                "blocked_clients": info.get("blocked_clients")
            },
            "memory": {
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
                "used_memory_peak": info.get("used_memory_peak"),
                "used_memory_peak_human": info.get("used_memory_peak_human"),
                "memory_fragmentation_ratio": info.get("mem_fragmentation_ratio")
            },
            "stats": {
                "total_connections_received": info.get("total_connections_received"),
                "total_commands_processed": info.get("total_commands_processed"),
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "expired_keys": info.get("expired_keys"),
                "evicted_keys": info.get("evicted_keys")
            },
            "persistence": {
                "rdb_changes_since_last_save": info.get("rdb_changes_since_last_save"),
                "rdb_last_save_time": info.get("rdb_last_save_time"),
                "aof_enabled": info.get("aof_enabled", 0) == 1
            },
            "application": {
                "operations_executed": metrics_collector.metrics["redis_operations"]
            }
        }
        
        return redis_metrics
        
    except Exception as e:
        logger.error("Failed to collect Redis metrics", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to collect Redis metrics: {str(e)}")


@router.get("/prometheus")
async def prometheus_metrics(
    redis: RedisService = Depends(get_redis),
    db = Depends(get_db_session)
):
    """Get metrics in Prometheus format."""
    try:
        app_metrics = metrics_collector.get_metrics()
        
        # Get additional metrics
        total_tickets = await db.execute("SELECT COUNT(*) FROM tickets")
        total_tickets = (await total_tickets.fetchone())[0]
        
        open_tickets = await db.execute("SELECT COUNT(*) FROM tickets WHERE status = 'open'")
        open_tickets = (await open_tickets.fetchone())[0]
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        # Format as Prometheus metrics
        prometheus_output = f"""# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total {app_metrics['requests_total']}

# HELP http_request_duration_seconds HTTP request duration in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_sum {sum(app_metrics.get('response_times', [])) / 1000}
http_request_duration_seconds_count {len(app_metrics.get('response_times', []))}

# HELP active_websocket_connections Number of active WebSocket connections
# TYPE active_websocket_connections gauge
active_websocket_connections {app_metrics['active_connections']}

# HELP database_queries_total Total number of database queries
# TYPE database_queries_total counter
database_queries_total {app_metrics['database_queries']}

# HELP redis_operations_total Total number of Redis operations
# TYPE redis_operations_total counter
redis_operations_total {app_metrics['redis_operations']}

# HELP tickets_total Total number of tickets
# TYPE tickets_total gauge
tickets_total {total_tickets}

# HELP tickets_open Number of open tickets
# TYPE tickets_open gauge
tickets_open {open_tickets}

# HELP system_cpu_usage_percent CPU usage percentage
# TYPE system_cpu_usage_percent gauge
system_cpu_usage_percent {cpu_percent}

# HELP system_memory_usage_percent Memory usage percentage
# TYPE system_memory_usage_percent gauge
system_memory_usage_percent {memory.percent}

# HELP errors_total Total number of errors
# TYPE errors_total counter
errors_total {app_metrics['errors_total']}
"""
        
        return prometheus_output
        
    except Exception as e:
        logger.error("Failed to generate Prometheus metrics", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate Prometheus metrics: {str(e)}")


@router.get("/")
async def metrics_overview():
    """Get overview of available metrics endpoints."""
    return {
        "service": "discord-ticket-bot-backend",
        "metrics_endpoints": {
            "/metrics/health": "Detailed health check with component status",
            "/metrics/application": "Application-specific metrics",
            "/metrics/system": "System resource metrics",
            "/metrics/database": "Database-specific metrics",
            "/metrics/redis": "Redis-specific metrics",
            "/metrics/prometheus": "Metrics in Prometheus format"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }