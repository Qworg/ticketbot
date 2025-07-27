"""
Simple API performance tests that can run independently.
Tests API performance without complex dependencies.
"""
import pytest
import asyncio
import time
import statistics
import json
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, MagicMock
import random
import string


class APIPerformanceMetrics:
    """Helper class to collect API performance metrics."""
    
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


class MockAPIClient:
    """Mock API client for performance testing."""
    
    def __init__(self, base_delay: float = 0.01):
        self.base_delay = base_delay
        self.request_count = 0
        self.tickets = {}
        self.messages = {}
        self.staff = {}
    
    async def get(self, endpoint: str, params: dict = None):
        """Simulate GET request."""
        await asyncio.sleep(self.base_delay + random.uniform(0, 0.005))
        self.request_count += 1
        
        if "/tickets" in endpoint:
            if endpoint.endswith("/tickets"):
                # List tickets
                return {
                    "status_code": 200,
                    "data": list(self.tickets.values())[:20]  # Simulate pagination
                }
            else:
                # Get specific ticket
                ticket_id = endpoint.split("/")[-1]
                if ticket_id in self.tickets:
                    return {
                        "status_code": 200,
                        "data": self.tickets[ticket_id]
                    }
                else:
                    return {"status_code": 404, "error": "Ticket not found"}
        
        elif "/search" in endpoint:
            # Simulate search
            return {
                "status_code": 200,
                "data": {"results": list(self.tickets.values())[:10]}
            }
        
        return {"status_code": 200, "data": {}}
    
    async def post(self, endpoint: str, data: dict):
        """Simulate POST request."""
        await asyncio.sleep(self.base_delay + random.uniform(0, 0.01))
        self.request_count += 1
        
        if "/tickets" in endpoint:
            if endpoint.endswith("/tickets"):
                # Create ticket
                ticket_id = str(len(self.tickets) + 1)
                ticket = {
                    "id": ticket_id,
                    "title": data.get("title", "Test Ticket"),
                    "status": "open",
                    "created_at": time.time()
                }
                self.tickets[ticket_id] = ticket
                return {"status_code": 201, "data": ticket}
            
            elif "/messages" in endpoint:
                # Add message to ticket
                ticket_id = endpoint.split("/")[-2]
                message_id = str(len(self.messages) + 1)
                message = {
                    "id": message_id,
                    "ticket_id": ticket_id,
                    "content": data.get("content", "Test message"),
                    "created_at": time.time()
                }
                self.messages[message_id] = message
                return {"status_code": 201, "data": message}
        
        return {"status_code": 201, "data": {}}
    
    async def put(self, endpoint: str, data: dict):
        """Simulate PUT request."""
        await asyncio.sleep(self.base_delay + random.uniform(0, 0.008))
        self.request_count += 1
        
        if "/tickets/" in endpoint:
            ticket_id = endpoint.split("/")[-1]
            if ticket_id in self.tickets:
                self.tickets[ticket_id].update(data)
                return {"status_code": 200, "data": self.tickets[ticket_id]}
            else:
                return {"status_code": 404, "error": "Ticket not found"}
        
        return {"status_code": 200, "data": {}}
    
    async def delete(self, endpoint: str):
        """Simulate DELETE request."""
        await asyncio.sleep(self.base_delay + random.uniform(0, 0.005))
        self.request_count += 1
        
        if "/tickets/" in endpoint:
            ticket_id = endpoint.split("/")[-1]
            if ticket_id in self.tickets:
                del self.tickets[ticket_id]
                return {"status_code": 204, "data": None}
            else:
                return {"status_code": 404, "error": "Ticket not found"}
        
        return {"status_code": 204, "data": None}


def generate_random_string(length: int = 10) -> str:
    """Generate random string for test data."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


async def make_concurrent_api_requests(client: MockAPIClient, requests: List[dict], concurrent_users: int = 10) -> APIPerformanceMetrics:
    """Make concurrent API requests and measure performance."""
    metrics = APIPerformanceMetrics()
    
    async def make_request(request_info: dict):
        """Make a single API request and measure performance."""
        start_time = time.time()
        try:
            method = request_info["method"].upper()
            endpoint = request_info["endpoint"]
            data = request_info.get("data")
            params = request_info.get("params")
            
            if method == "GET":
                response = await client.get(endpoint, params)
            elif method == "POST":
                response = await client.post(endpoint, data)
            elif method == "PUT":
                response = await client.put(endpoint, data)
            elif method == "DELETE":
                response = await client.delete(endpoint)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            end_time = time.time()
            response_time = end_time - start_time
            success = 200 <= response.get("status_code", 500) < 300
            
            return response_time, success
        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            return response_time, False
    
    metrics.start_timer()
    
    # Create semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(concurrent_users)
    
    async def limited_request(request_info):
        async with semaphore:
            return await make_request(request_info)
    
    # Execute all requests
    tasks = [limited_request(req) for req in requests]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect results
    for result in results:
        if isinstance(result, tuple):
            response_time, success = result
            metrics.add_response(response_time, success)
        else:
            metrics.add_response(1.0, False)  # Error case
    
    metrics.end_timer()
    return metrics


@pytest.mark.asyncio
async def test_ticket_crud_performance():
    """Test CRUD operations performance for tickets."""
    client = MockAPIClient(base_delay=0.005)
    
    # Generate test requests
    requests = []
    
    # Create tickets
    for i in range(100):
        requests.append({
            "method": "POST",
            "endpoint": "/api/tickets",
            "data": {
                "title": f"Performance Test Ticket {i}",
                "description": f"Description for ticket {i}",
                "priority": random.choice(["low", "medium", "high", "urgent"])
            }
        })
    
    # Read tickets
    for i in range(50):
        requests.append({
            "method": "GET",
            "endpoint": "/api/tickets",
            "params": {"page": i % 5 + 1, "limit": 20}
        })
    
    # Update tickets
    for i in range(30):
        requests.append({
            "method": "PUT",
            "endpoint": f"/api/tickets/{i + 1}",
            "data": {
                "status": random.choice(["open", "in_progress", "closed"]),
                "priority": random.choice(["low", "medium", "high"])
            }
        })
    
    # Delete tickets
    for i in range(20):
        requests.append({
            "method": "DELETE",
            "endpoint": f"/api/tickets/{i + 1}"
        })
    
    # Execute requests with 20 concurrent users
    metrics = await make_concurrent_api_requests(client, requests, concurrent_users=20)
    stats = metrics.get_stats()
    
    # Performance assertions
    assert stats["success_rate"] >= 95, f"Success rate too low: {stats['success_rate']}%"
    assert stats["avg_response_time_ms"] < 50, f"Average response time too high: {stats['avg_response_time_ms']}ms"
    assert stats["p95_response_time_ms"] < 100, f"95th percentile response time too high: {stats['p95_response_time_ms']}ms"
    assert stats["requests_per_second"] >= 100, f"Throughput too low: {stats['requests_per_second']} req/s"
    
    print(f"Ticket CRUD Performance: {stats}")


@pytest.mark.asyncio
async def test_high_load_ticket_creation():
    """Test ticket creation under high load."""
    client = MockAPIClient(base_delay=0.003)
    
    # Generate many ticket creation requests
    requests = []
    for i in range(500):
        requests.append({
            "method": "POST",
            "endpoint": "/api/tickets",
            "data": {
                "title": f"High Load Test Ticket {i}",
                "description": f"Load test description {i} - {generate_random_string(100)}",
                "priority": random.choice(["low", "medium", "high", "urgent"]),
                "creator_discord_id": 111222333 + (i % 100)
            }
        })
    
    # Execute with high concurrency
    metrics = await make_concurrent_api_requests(client, requests, concurrent_users=50)
    stats = metrics.get_stats()
    
    # High load assertions
    assert stats["success_rate"] >= 90, f"Success rate too low under high load: {stats['success_rate']}%"
    assert stats["avg_response_time_ms"] < 100, f"Average response time too high: {stats['avg_response_time_ms']}ms"
    assert stats["p99_response_time_ms"] < 500, f"99th percentile response time too high: {stats['p99_response_time_ms']}ms"
    assert stats["requests_per_second"] >= 200, f"Throughput too low: {stats['requests_per_second']} req/s"
    
    print(f"High Load Ticket Creation Performance: {stats}")


@pytest.mark.asyncio
async def test_message_api_performance():
    """Test message API performance."""
    client = MockAPIClient(base_delay=0.004)
    
    # First create some tickets
    ticket_requests = []
    for i in range(50):
        ticket_requests.append({
            "method": "POST",
            "endpoint": "/api/tickets",
            "data": {
                "title": f"Message Test Ticket {i}",
                "description": f"Ticket for message testing {i}"
            }
        })
    
    await make_concurrent_api_requests(client, ticket_requests, concurrent_users=10)
    
    # Now test message creation
    message_requests = []
    for i in range(300):
        ticket_id = (i % 50) + 1  # Distribute messages across tickets
        message_requests.append({
            "method": "POST",
            "endpoint": f"/api/tickets/{ticket_id}/messages",
            "data": {
                "content": f"Performance test message {i} - {generate_random_string(150)}",
                "author_discord_id": 111222333 + (i % 20),
                "message_type": random.choice(["user_message", "staff_message", "system_message"])
            }
        })
    
    # Execute message requests
    metrics = await make_concurrent_api_requests(client, message_requests, concurrent_users=30)
    stats = metrics.get_stats()
    
    # Message API assertions
    assert stats["success_rate"] >= 95, f"Message API success rate too low: {stats['success_rate']}%"
    assert stats["avg_response_time_ms"] < 80, f"Average message response time too high: {stats['avg_response_time_ms']}ms"
    assert stats["p95_response_time_ms"] < 150, f"95th percentile message response time too high: {stats['p95_response_time_ms']}ms"
    assert stats["requests_per_second"] >= 150, f"Message API throughput too low: {stats['requests_per_second']} req/s"
    
    print(f"Message API Performance: {stats}")


@pytest.mark.asyncio
async def test_search_api_performance():
    """Test search API performance."""
    client = MockAPIClient(base_delay=0.008)  # Search is typically slower
    
    # Create test data first
    setup_requests = []
    for i in range(200):
        setup_requests.append({
            "method": "POST",
            "endpoint": "/api/tickets",
            "data": {
                "title": f"Search Test Ticket {i}",
                "description": f"Searchable content for ticket {i} about billing and support issues"
            }
        })
    
    await make_concurrent_api_requests(client, setup_requests, concurrent_users=20)
    
    # Test search requests
    search_requests = []
    search_terms = ["billing", "support", "issue", "test", "ticket", "problem", "help", "urgent"]
    
    for i in range(100):
        search_term = random.choice(search_terms)
        search_requests.append({
            "method": "GET",
            "endpoint": "/api/search/transcripts",
            "params": {
                "query": search_term,
                "limit": 20,
                "page": (i % 5) + 1
            }
        })
    
    # Execute search requests
    metrics = await make_concurrent_api_requests(client, search_requests, concurrent_users=15)
    stats = metrics.get_stats()
    
    # Search API assertions
    assert stats["success_rate"] >= 95, f"Search API success rate too low: {stats['success_rate']}%"
    assert stats["avg_response_time_ms"] < 200, f"Average search response time too high: {stats['avg_response_time_ms']}ms"
    assert stats["p95_response_time_ms"] < 400, f"95th percentile search response time too high: {stats['p95_response_time_ms']}ms"
    assert stats["requests_per_second"] >= 50, f"Search API throughput too low: {stats['requests_per_second']} req/s"
    
    print(f"Search API Performance: {stats}")


@pytest.mark.asyncio
async def test_mixed_workload_performance():
    """Test mixed API workload performance."""
    client = MockAPIClient(base_delay=0.005)
    
    # Create mixed workload requests
    requests = []
    
    # 40% ticket operations
    for i in range(80):
        if i % 4 == 0:
            # Create ticket
            requests.append({
                "method": "POST",
                "endpoint": "/api/tickets",
                "data": {
                    "title": f"Mixed Workload Ticket {i}",
                    "description": f"Mixed workload test {i}"
                }
            })
        elif i % 4 == 1:
            # List tickets
            requests.append({
                "method": "GET",
                "endpoint": "/api/tickets",
                "params": {"page": (i % 5) + 1, "limit": 20}
            })
        elif i % 4 == 2:
            # Update ticket
            requests.append({
                "method": "PUT",
                "endpoint": f"/api/tickets/{(i % 20) + 1}",
                "data": {"status": random.choice(["open", "in_progress", "closed"])}
            })
        else:
            # Get specific ticket
            requests.append({
                "method": "GET",
                "endpoint": f"/api/tickets/{(i % 20) + 1}"
            })
    
    # 30% message operations
    for i in range(60):
        requests.append({
            "method": "POST",
            "endpoint": f"/api/tickets/{(i % 20) + 1}/messages",
            "data": {
                "content": f"Mixed workload message {i}",
                "author_discord_id": 111222333 + (i % 10)
            }
        })
    
    # 20% search operations
    for i in range(40):
        requests.append({
            "method": "GET",
            "endpoint": "/api/search/transcripts",
            "params": {"query": random.choice(["test", "workload", "mixed"])}
        })
    
    # 10% other operations
    for i in range(20):
        requests.append({
            "method": "DELETE",
            "endpoint": f"/api/tickets/{(i % 10) + 1}"
        })
    
    # Shuffle requests to simulate real mixed workload
    random.shuffle(requests)
    
    # Execute mixed workload
    metrics = await make_concurrent_api_requests(client, requests, concurrent_users=25)
    stats = metrics.get_stats()
    
    # Mixed workload assertions
    assert stats["success_rate"] >= 70, f"Mixed workload success rate too low: {stats['success_rate']}%"
    assert stats["avg_response_time_ms"] < 100, f"Average mixed workload response time too high: {stats['avg_response_time_ms']}ms"
    assert stats["requests_per_second"] >= 80, f"Mixed workload throughput too low: {stats['requests_per_second']} req/s"
    
    print(f"Mixed Workload Performance: {stats}")


@pytest.mark.asyncio
async def test_api_scalability():
    """Test API scalability with increasing concurrent users."""
    client = MockAPIClient(base_delay=0.005)
    
    # Test with different concurrency levels
    concurrency_levels = [1, 5, 10, 20, 50, 100]
    results = []
    
    for concurrency in concurrency_levels:
        # Create test requests
        requests = []
        for i in range(100):  # Fixed number of requests
            requests.append({
                "method": "POST",
                "endpoint": "/api/tickets",
                "data": {
                    "title": f"Scalability Test Ticket {i}",
                    "description": f"Testing with {concurrency} concurrent users"
                }
            })
        
        # Execute with current concurrency level
        metrics = await make_concurrent_api_requests(client, requests, concurrent_users=concurrency)
        stats = metrics.get_stats()
        
        results.append({
            "concurrency": concurrency,
            "success_rate": stats["success_rate"],
            "avg_response_time_ms": stats["avg_response_time_ms"],
            "requests_per_second": stats["requests_per_second"]
        })
        
        # Clear client state for next test
        client.tickets.clear()
    
    # Scalability assertions
    for result in results:
        assert result["success_rate"] >= 90, f"Success rate degraded at {result['concurrency']} concurrent users: {result['success_rate']}%"
        assert result["avg_response_time_ms"] < 200, f"Response time too high at {result['concurrency']} concurrent users: {result['avg_response_time_ms']}ms"
    
    print("API Scalability Results:")
    for result in results:
        print(f"  {result['concurrency']} users: {result['success_rate']:.1f}% success, {result['avg_response_time_ms']:.2f}ms avg, {result['requests_per_second']:.1f} req/s")


@pytest.mark.asyncio
async def test_api_memory_usage():
    """Test API memory usage during high load."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    client = MockAPIClient(base_delay=0.002)
    
    # Create high load to test memory usage
    requests = []
    for i in range(1000):
        requests.append({
            "method": "POST",
            "endpoint": "/api/tickets",
            "data": {
                "title": f"Memory Test Ticket {i}",
                "description": f"Memory test description {i} - {generate_random_string(200)}",
                "priority": random.choice(["low", "medium", "high", "urgent"])
            }
        })
    
    # Execute requests
    await make_concurrent_api_requests(client, requests, concurrent_users=50)
    
    peak_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = peak_memory - initial_memory
    
    # Memory usage assertions
    assert memory_increase < 100, f"API memory usage increased too much: {memory_increase:.2f}MB"
    
    print(f"API Memory Usage - Initial: {initial_memory:.2f}MB, Peak: {peak_memory:.2f}MB, Increase: {memory_increase:.2f}MB")


@pytest.mark.asyncio
async def test_api_error_handling_performance():
    """Test API performance under error conditions."""
    client = MockAPIClient(base_delay=0.005)
    
    # Mix of valid and invalid requests
    requests = []
    
    # Valid requests
    for i in range(50):
        requests.append({
            "method": "POST",
            "endpoint": "/api/tickets",
            "data": {
                "title": f"Valid Ticket {i}",
                "description": f"Valid description {i}"
            }
        })
    
    # Invalid requests (non-existent tickets)
    for i in range(50):
        requests.append({
            "method": "GET",
            "endpoint": f"/api/tickets/{i + 1000}"  # Non-existent ticket IDs
        })
    
    # Invalid updates
    for i in range(30):
        requests.append({
            "method": "PUT",
            "endpoint": f"/api/tickets/{i + 2000}",  # Non-existent ticket IDs
            "data": {"status": "closed"}
        })
    
    # Invalid deletes
    for i in range(20):
        requests.append({
            "method": "DELETE",
            "endpoint": f"/api/tickets/{i + 3000}"  # Non-existent ticket IDs
        })
    
    # Execute mixed valid/invalid requests
    metrics = await make_concurrent_api_requests(client, requests, concurrent_users=20)
    stats = metrics.get_stats()
    
    # Error handling performance assertions
    # We expect some failures due to invalid requests, but system should handle them efficiently
    assert stats["success_rate"] >= 30, f"Success rate too low (should handle valid requests): {stats['success_rate']}%"
    assert stats["avg_response_time_ms"] < 100, f"Average response time too high with errors: {stats['avg_response_time_ms']}ms"
    assert stats["requests_per_second"] >= 50, f"Throughput too low with error handling: {stats['requests_per_second']} req/s"
    
    print(f"API Error Handling Performance: {stats}")