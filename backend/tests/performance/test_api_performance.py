"""
Performance tests for API endpoints under high volume.
Tests API performance with concurrent requests and high load scenarios.
"""
import pytest
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
import httpx
from fastapi.testclient import TestClient
from unittest.mock import patch

# Patch the database modules before importing app
with patch("backend.db.get_db_session"), \
     patch("backend.db.create_async_engine"), \
     patch("backend.db.create_engine"), \
     patch("backend.db.check_db_connection"):
    from backend.main import app

from tests.integration.test_database_service import get_test_database_service
from tests.integration.test_redis_service import TestRedisService
from tests.integration.mock_services import MockAuthService


@pytest.fixture
def performance_client():
    """Create test client for performance testing."""
    return TestClient(app)


@pytest.fixture
async def performance_setup():
    """Set up performance test environment."""
    async with get_test_database_service() as db_service:
        redis_service = TestRedisService()
        auth_service = MockAuthService(db_service)
        
        await db_service.create_tables()
        
        # Create test staff for authentication
        staff_data = {
            "discord_id": 123456789,
            "username": "perf_test_staff",
            "role": "admin",
            "permissions": {"can_close_tickets": True, "can_assign_tickets": True}
        }
        staff = await db_service.create_staff(staff_data)
        token = await auth_service.create_access_token(staff.discord_id)
        
        yield {
            "db_service": db_service,
            "redis_service": redis_service,
            "staff": staff,
            "token": token
        }
        
        await db_service.cleanup()
        await redis_service.cleanup()


class PerformanceMetrics:
    """Helper class to collect and analyze performance metrics."""
    
    def __init__(self):
        self.response_times = []
        self.success_count = 0
        self.error_count = 0
        self.start_time = None
        self.end_time = None
    
    def start_timer(self):
        """Start timing the test."""
        self.start_time = time.time()
    
    def end_timer(self):
        """End timing the test."""
        self.end_time = time.time()
    
    def add_response(self, response_time: float, success: bool):
        """Add a response measurement."""
        self.response_times.append(response_time)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.response_times:
            return {"error": "No response times recorded"}
        
        total_time = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        return {
            "total_requests": len(self.response_times),
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / len(self.response_times) * 100,
            "total_time_seconds": total_time,
            "requests_per_second": len(self.response_times) / total_time if total_time > 0 else 0,
            "avg_response_time_ms": statistics.mean(self.response_times) * 1000,
            "median_response_time_ms": statistics.median(self.response_times) * 1000,
            "min_response_time_ms": min(self.response_times) * 1000,
            "max_response_time_ms": max(self.response_times) * 1000,
            "p95_response_time_ms": statistics.quantiles(self.response_times, n=20)[18] * 1000,
            "p99_response_time_ms": statistics.quantiles(self.response_times, n=100)[98] * 1000
        }


async def make_concurrent_requests(client: TestClient, endpoint: str, method: str = "GET", 
                                 data: dict = None, headers: dict = None, 
                                 concurrent_users: int = 10, requests_per_user: int = 10) -> PerformanceMetrics:
    """Make concurrent requests to test endpoint performance."""
    metrics = PerformanceMetrics()
    
    def make_request():
        """Make a single request and measure performance."""
        start_time = time.time()
        try:
            if method.upper() == "GET":
                response = client.get(endpoint, headers=headers)
            elif method.upper() == "POST":
                response = client.post(endpoint, json=data, headers=headers)
            elif method.upper() == "PUT":
                response = client.put(endpoint, json=data, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            end_time = time.time()
            response_time = end_time - start_time
            success = 200 <= response.status_code < 300
            
            return response_time, success
        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            return response_time, False
    
    # Create thread pool for concurrent requests
    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        metrics.start_timer()
        
        # Submit all requests
        futures = []
        for user in range(concurrent_users):
            for request in range(requests_per_user):
                future = executor.submit(make_request)
                futures.append(future)
        
        # Collect results
        for future in futures:
            response_time, success = future.result()
            metrics.add_response(response_time, success)
        
        metrics.end_timer()
    
    return metrics


@pytest.mark.asyncio
async def test_ticket_creation_performance(performance_client, performance_setup):
    """Test ticket creation API performance under high load."""
    setup = performance_setup
    headers = {"Authorization": f"Bearer {setup['token']}"}
    
    ticket_data = {
        "discord_channel_id": 987654321,
        "title": "Performance Test Ticket",
        "description": "Testing API performance",
        "creator_discord_id": 111222333,
        "priority": "medium"
    }
    
    # Test with 50 concurrent users making 5 requests each (250 total requests)
    metrics = await make_concurrent_requests(
        performance_client,
        "/api/tickets",
        method="POST",
        data=ticket_data,
        headers=headers,
        concurrent_users=50,
        requests_per_user=5
    )
    
    stats = metrics.get_stats()
    
    # Performance assertions
    assert stats["success_rate"] >= 95, f"Success rate too low: {stats['success_rate']}%"
    assert stats["avg_response_time_ms"] < 1000, f"Average response time too high: {stats['avg_response_time_ms']}ms"
    assert stats["p95_response_time_ms"] < 2000, f"95th percentile response time too high: {stats['p95_response_time_ms']}ms"
    assert stats["requests_per_second"] >= 50, f"Throughput too low: {stats['requests_per_second']} req/s"
    
    print(f"Ticket Creation Performance Stats: {stats}")


@pytest.mark.asyncio
async def test_ticket_list_performance(performance_client, performance_setup):
    """Test ticket list API performance under high load."""
    setup = performance_setup
    headers = {"Authorization": f"Bearer {setup['token']}"}
    
    # Pre-create some tickets for realistic testing
    ticket_data = {
        "discord_channel_id": 987654322,
        "title": "Test Ticket",
        "description": "Test description",
        "creator_discord_id": 111222333
    }
    
    # Create 100 tickets first
    for i in range(100):
        ticket_data["discord_channel_id"] = 987654322 + i
        ticket_data["title"] = f"Test Ticket {i}"
        performance_client.post("/api/tickets", json=ticket_data, headers=headers)
    
    # Test listing performance with 100 concurrent users making 10 requests each
    metrics = await make_concurrent_requests(
        performance_client,
        "/api/tickets?page=1&limit=20",
        method="GET",
        headers=headers,
        concurrent_users=100,
        requests_per_user=10
    )
    
    stats = metrics.get_stats()
    
    # Performance assertions
    assert stats["success_rate"] >= 98, f"Success rate too low: {stats['success_rate']}%"
    assert stats["avg_response_time_ms"] < 500, f"Average response time too high: {stats['avg_response_time_ms']}ms"
    assert stats["p95_response_time_ms"] < 1000, f"95th percentile response time too high: {stats['p95_response_time_ms']}ms"
    assert stats["requests_per_second"] >= 100, f"Throughput too low: {stats['requests_per_second']} req/s"
    
    print(f"Ticket List Performance Stats: {stats}")


@pytest.mark.asyncio
async def test_message_creation_performance(performance_client, performance_setup):
    """Test message creation API performance under high load."""
    setup = performance_setup
    headers = {"Authorization": f"Bearer {setup['token']}"}
    
    # Create a ticket first
    ticket_data = {
        "discord_channel_id": 987654323,
        "title": "Message Performance Test",
        "description": "Testing message API performance",
        "creator_discord_id": 111222333
    }
    
    response = performance_client.post("/api/tickets", json=ticket_data, headers=headers)
    ticket_id = response.json()["id"]
    
    message_data = {
        "author_discord_id": 111222333,
        "content": "Performance test message",
        "message_type": "user_message"
    }
    
    # Test with 30 concurrent users making 10 messages each (300 total messages)
    metrics = await make_concurrent_requests(
        performance_client,
        f"/api/tickets/{ticket_id}/messages",
        method="POST",
        data=message_data,
        headers=headers,
        concurrent_users=30,
        requests_per_user=10
    )
    
    stats = metrics.get_stats()
    
    # Performance assertions
    assert stats["success_rate"] >= 95, f"Success rate too low: {stats['success_rate']}%"
    assert stats["avg_response_time_ms"] < 800, f"Average response time too high: {stats['avg_response_time_ms']}ms"
    assert stats["p95_response_time_ms"] < 1500, f"95th percentile response time too high: {stats['p95_response_time_ms']}ms"
    assert stats["requests_per_second"] >= 30, f"Throughput too low: {stats['requests_per_second']} req/s"
    
    print(f"Message Creation Performance Stats: {stats}")


@pytest.mark.asyncio
async def test_transcript_search_performance(performance_client, performance_setup):
    """Test transcript search API performance under high load."""
    setup = performance_setup
    headers = {"Authorization": f"Bearer {setup['token']}"}
    
    # Pre-create tickets and messages for realistic search testing
    for i in range(50):
        ticket_data = {
            "discord_channel_id": 987654400 + i,
            "title": f"Search Test Ticket {i}",
            "description": f"Testing search functionality with ticket {i}",
            "creator_discord_id": 111222333
        }
        
        response = performance_client.post("/api/tickets", json=ticket_data, headers=headers)
        ticket_id = response.json()["id"]
        
        # Add messages to each ticket
        for j in range(5):
            message_data = {
                "author_discord_id": 111222333,
                "content": f"Search test message {j} for ticket {i} about billing issues",
                "message_type": "user_message"
            }
            performance_client.post(f"/api/tickets/{ticket_id}/messages", json=message_data, headers=headers)
    
    # Test search performance with 20 concurrent users making 15 searches each
    metrics = await make_concurrent_requests(
        performance_client,
        "/api/search/transcripts?query=billing",
        method="GET",
        headers=headers,
        concurrent_users=20,
        requests_per_user=15
    )
    
    stats = metrics.get_stats()
    
    # Performance assertions
    assert stats["success_rate"] >= 95, f"Success rate too low: {stats['success_rate']}%"
    assert stats["avg_response_time_ms"] < 1500, f"Average response time too high: {stats['avg_response_time_ms']}ms"
    assert stats["p95_response_time_ms"] < 3000, f"95th percentile response time too high: {stats['p95_response_time_ms']}ms"
    assert stats["requests_per_second"] >= 10, f"Throughput too low: {stats['requests_per_second']} req/s"
    
    print(f"Transcript Search Performance Stats: {stats}")


@pytest.mark.asyncio
async def test_mixed_workload_performance(performance_client, performance_setup):
    """Test mixed API workload performance simulating real usage patterns."""
    setup = performance_setup
    headers = {"Authorization": f"Bearer {setup['token']}"}
    
    async def mixed_workload_user():
        """Simulate a user performing mixed operations."""
        user_metrics = PerformanceMetrics()
        
        operations = [
            ("GET", "/api/tickets", None),  # List tickets
            ("POST", "/api/tickets", {
                "discord_channel_id": 987654500 + int(time.time() * 1000) % 10000,
                "title": "Mixed Workload Test",
                "description": "Testing mixed operations",
                "creator_discord_id": 111222333
            }),  # Create ticket
            ("GET", "/api/tickets", None),  # List tickets again
        ]
        
        for method, endpoint, data in operations:
            start_time = time.time()
            try:
                if method == "GET":
                    response = performance_client.get(endpoint, headers=headers)
                else:
                    response = performance_client.post(endpoint, json=data, headers=headers)
                
                end_time = time.time()
                response_time = end_time - start_time
                success = 200 <= response.status_code < 300
                user_metrics.add_response(response_time, success)
                
            except Exception:
                end_time = time.time()
                response_time = end_time - start_time
                user_metrics.add_response(response_time, False)
        
        return user_metrics
    
    # Run mixed workload with 25 concurrent users
    all_metrics = PerformanceMetrics()
    all_metrics.start_timer()
    
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = [executor.submit(lambda: asyncio.run(mixed_workload_user())) for _ in range(25)]
        
        for future in futures:
            user_metrics = future.result()
            all_metrics.response_times.extend(user_metrics.response_times)
            all_metrics.success_count += user_metrics.success_count
            all_metrics.error_count += user_metrics.error_count
    
    all_metrics.end_timer()
    stats = all_metrics.get_stats()
    
    # Performance assertions for mixed workload
    assert stats["success_rate"] >= 90, f"Success rate too low: {stats['success_rate']}%"
    assert stats["avg_response_time_ms"] < 1200, f"Average response time too high: {stats['avg_response_time_ms']}ms"
    assert stats["requests_per_second"] >= 20, f"Throughput too low: {stats['requests_per_second']} req/s"
    
    print(f"Mixed Workload Performance Stats: {stats}")


@pytest.mark.asyncio
async def test_database_connection_pool_performance(performance_setup):
    """Test database connection pool performance under high concurrency."""
    setup = performance_setup
    db_service = setup["db_service"]
    
    async def database_operation():
        """Perform a database operation."""
        start_time = time.time()
        try:
            # Simulate database query
            await db_service.execute_query("SELECT 1")
            end_time = time.time()
            return end_time - start_time, True
        except Exception:
            end_time = time.time()
            return end_time - start_time, False
    
    # Test with high concurrency
    metrics = PerformanceMetrics()
    metrics.start_timer()
    
    tasks = [database_operation() for _ in range(200)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, tuple):
            response_time, success = result
            metrics.add_response(response_time, success)
        else:
            metrics.add_response(1.0, False)  # Error case
    
    metrics.end_timer()
    stats = metrics.get_stats()
    
    # Database performance assertions
    assert stats["success_rate"] >= 95, f"Database success rate too low: {stats['success_rate']}%"
    assert stats["avg_response_time_ms"] < 100, f"Database response time too high: {stats['avg_response_time_ms']}ms"
    
    print(f"Database Connection Pool Performance Stats: {stats}")


@pytest.mark.asyncio
async def test_memory_usage_under_load(performance_client, performance_setup):
    """Test memory usage during high load scenarios."""
    import psutil
    import os
    
    setup = performance_setup
    headers = {"Authorization": f"Bearer {setup['token']}"}
    
    # Get initial memory usage
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Create load
    ticket_data = {
        "discord_channel_id": 987654600,
        "title": "Memory Test Ticket",
        "description": "Testing memory usage",
        "creator_discord_id": 111222333
    }
    
    # Create 500 tickets to test memory usage
    for i in range(500):
        ticket_data["discord_channel_id"] = 987654600 + i
        ticket_data["title"] = f"Memory Test Ticket {i}"
        performance_client.post("/api/tickets", json=ticket_data, headers=headers)
    
    # Get peak memory usage
    peak_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = peak_memory - initial_memory
    
    # Memory usage assertions
    assert memory_increase < 500, f"Memory usage increased too much: {memory_increase}MB"
    
    print(f"Memory Usage - Initial: {initial_memory:.2f}MB, Peak: {peak_memory:.2f}MB, Increase: {memory_increase:.2f}MB")