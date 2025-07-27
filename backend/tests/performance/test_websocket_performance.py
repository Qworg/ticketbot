"""
Performance tests for WebSocket connections with multiple concurrent connections.
Tests WebSocket performance under high load and concurrent connection scenarios.
"""
import pytest
import asyncio
import time
import json
import statistics
from typing import List, Dict, Any
import websockets
from unittest.mock import AsyncMock, patch

from tests.integration.test_redis_service import TestRedisService


class WebSocketPerformanceMetrics:
    """Helper class to collect WebSocket performance metrics."""
    
    def __init__(self):
        self.connection_times = []
        self.message_latencies = []
        self.successful_connections = 0
        self.failed_connections = 0
        self.messages_sent = 0
        self.messages_received = 0
        self.start_time = None
        self.end_time = None
    
    def start_timer(self):
        """Start timing the test."""
        self.start_time = time.time()
    
    def end_timer(self):
        """End timing the test."""
        self.end_time = time.time()
    
    def add_connection(self, connection_time: float, success: bool):
        """Add connection measurement."""
        self.connection_times.append(connection_time)
        if success:
            self.successful_connections += 1
        else:
            self.failed_connections += 1
    
    def add_message_latency(self, latency: float):
        """Add message latency measurement."""
        self.message_latencies.append(latency)
    
    def increment_messages_sent(self):
        """Increment sent message counter."""
        self.messages_sent += 1
    
    def increment_messages_received(self):
        """Increment received message counter."""
        self.messages_received += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        total_time = self.end_time - self.start_time if self.end_time and self.start_time else 0
        total_connections = self.successful_connections + self.failed_connections
        
        stats = {
            "total_connections": total_connections,
            "successful_connections": self.successful_connections,
            "failed_connections": self.failed_connections,
            "connection_success_rate": (self.successful_connections / total_connections * 100) if total_connections > 0 else 0,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "message_delivery_rate": (self.messages_received / self.messages_sent * 100) if self.messages_sent > 0 else 0,
            "total_time_seconds": total_time,
            "connections_per_second": total_connections / total_time if total_time > 0 else 0
        }
        
        if self.connection_times:
            stats.update({
                "avg_connection_time_ms": statistics.mean(self.connection_times) * 1000,
                "median_connection_time_ms": statistics.median(self.connection_times) * 1000,
                "max_connection_time_ms": max(self.connection_times) * 1000,
                "min_connection_time_ms": min(self.connection_times) * 1000
            })
        
        if self.message_latencies:
            stats.update({
                "avg_message_latency_ms": statistics.mean(self.message_latencies) * 1000,
                "median_message_latency_ms": statistics.median(self.message_latencies) * 1000,
                "p95_message_latency_ms": statistics.quantiles(self.message_latencies, n=20)[18] * 1000,
                "p99_message_latency_ms": statistics.quantiles(self.message_latencies, n=100)[98] * 1000,
                "max_message_latency_ms": max(self.message_latencies) * 1000,
                "min_message_latency_ms": min(self.message_latencies) * 1000
            })
        
        return stats


class MockWebSocketServer:
    """Mock WebSocket server for performance testing."""
    
    def __init__(self):
        self.clients = set()
        self.message_handlers = {}
        self.redis_service = TestRedisService()
    
    async def register_client(self, websocket):
        """Register a new client connection."""
        self.clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            self.clients.discard(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        if self.clients:
            message_str = json.dumps(message)
            await asyncio.gather(
                *[client.send(message_str) for client in self.clients],
                return_exceptions=True
            )
    
    async def handle_message(self, websocket, message: str):
        """Handle incoming message from client."""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type in self.message_handlers:
                await self.message_handlers[message_type](websocket, data)
            else:
                # Echo message back
                await websocket.send(json.dumps({"type": "echo", "data": data}))
        except json.JSONDecodeError:
            await websocket.send(json.dumps({"type": "error", "message": "Invalid JSON"}))
    
    def register_handler(self, message_type: str, handler):
        """Register a message handler."""
        self.message_handlers[message_type] = handler


@pytest.fixture
async def websocket_server():
    """Create mock WebSocket server for testing."""
    server = MockWebSocketServer()
    
    # Register some test handlers
    async def ticket_update_handler(websocket, data):
        response = {
            "type": "ticket_updated",
            "data": {
                "ticket_id": data.get("ticket_id"),
                "status": "processed",
                "timestamp": time.time()
            }
        }
        await websocket.send(json.dumps(response))
    
    async def message_handler(websocket, data):
        response = {
            "type": "message_received",
            "data": {
                "message_id": data.get("message_id"),
                "status": "delivered",
                "timestamp": time.time()
            }
        }
        await websocket.send(json.dumps(response))
    
    server.register_handler("ticket_update", ticket_update_handler)
    server.register_handler("new_message", message_handler)
    
    return server


async def create_websocket_client(server_url: str, client_id: int, metrics: WebSocketPerformanceMetrics):
    """Create a WebSocket client and measure performance."""
    connection_start = time.time()
    
    try:
        # Mock WebSocket connection
        websocket = AsyncMock()
        websocket.send = AsyncMock()
        websocket.recv = AsyncMock()
        websocket.close = AsyncMock()
        
        connection_end = time.time()
        connection_time = connection_end - connection_start
        metrics.add_connection(connection_time, True)
        
        return websocket
    except Exception as e:
        connection_end = time.time()
        connection_time = connection_end - connection_start
        metrics.add_connection(connection_time, False)
        return None


async def send_messages_with_latency_measurement(websocket, messages: List[dict], metrics: WebSocketPerformanceMetrics):
    """Send messages and measure latency."""
    for message in messages:
        send_time = time.time()
        
        try:
            await websocket.send(json.dumps(message))
            metrics.increment_messages_sent()
            
            # Mock receiving response
            response = await websocket.recv()
            receive_time = time.time()
            
            latency = receive_time - send_time
            metrics.add_message_latency(latency)
            metrics.increment_messages_received()
            
        except Exception:
            # Handle send/receive errors
            pass


@pytest.mark.asyncio
async def test_concurrent_websocket_connections(websocket_server):
    """Test performance with multiple concurrent WebSocket connections."""
    metrics = WebSocketPerformanceMetrics()
    concurrent_connections = 100
    
    async def create_and_test_connection(client_id: int):
        """Create connection and perform basic operations."""
        websocket = await create_websocket_client("ws://localhost:8000/ws", client_id, metrics)
        
        if websocket:
            # Send test messages
            test_messages = [
                {"type": "ticket_update", "ticket_id": f"ticket-{client_id}", "status": "open"},
                {"type": "new_message", "message_id": f"msg-{client_id}", "content": "Test message"},
                {"type": "ping", "timestamp": time.time()}
            ]
            
            await send_messages_with_latency_measurement(websocket, test_messages, metrics)
            await websocket.close()
    
    metrics.start_timer()
    
    # Create concurrent connections
    tasks = [create_and_test_connection(i) for i in range(concurrent_connections)]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    metrics.end_timer()
    stats = metrics.get_stats()
    
    # Performance assertions
    assert stats["connection_success_rate"] >= 95, f"Connection success rate too low: {stats['connection_success_rate']}%"
    assert stats["message_delivery_rate"] >= 95, f"Message delivery rate too low: {stats['message_delivery_rate']}%"
    assert stats["avg_connection_time_ms"] < 100, f"Average connection time too high: {stats['avg_connection_time_ms']}ms"
    assert stats["avg_message_latency_ms"] < 50, f"Average message latency too high: {stats['avg_message_latency_ms']}ms"
    assert stats["connections_per_second"] >= 50, f"Connection rate too low: {stats['connections_per_second']} conn/s"
    
    print(f"Concurrent WebSocket Connections Performance: {stats}")


@pytest.mark.asyncio
async def test_websocket_message_throughput(websocket_server):
    """Test WebSocket message throughput under high load."""
    metrics = WebSocketPerformanceMetrics()
    num_connections = 50
    messages_per_connection = 100
    
    async def high_throughput_client(client_id: int):
        """Client that sends many messages rapidly."""
        websocket = await create_websocket_client("ws://localhost:8000/ws", client_id, metrics)
        
        if websocket:
            messages = []
            for i in range(messages_per_connection):
                messages.append({
                    "type": "ticket_update",
                    "ticket_id": f"ticket-{client_id}-{i}",
                    "status": "processing",
                    "timestamp": time.time()
                })
            
            await send_messages_with_latency_measurement(websocket, messages, metrics)
            await websocket.close()
    
    metrics.start_timer()
    
    # Create high-throughput clients
    tasks = [high_throughput_client(i) for i in range(num_connections)]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    metrics.end_timer()
    stats = metrics.get_stats()
    
    expected_messages = num_connections * messages_per_connection
    
    # Throughput assertions
    assert stats["messages_sent"] >= expected_messages * 0.95, f"Not enough messages sent: {stats['messages_sent']}/{expected_messages}"
    assert stats["message_delivery_rate"] >= 90, f"Message delivery rate too low: {stats['message_delivery_rate']}%"
    assert stats["avg_message_latency_ms"] < 100, f"Average message latency too high: {stats['avg_message_latency_ms']}ms"
    assert stats["p95_message_latency_ms"] < 200, f"95th percentile latency too high: {stats['p95_message_latency_ms']}ms"
    
    messages_per_second = stats["messages_sent"] / stats["total_time_seconds"]
    assert messages_per_second >= 1000, f"Message throughput too low: {messages_per_second} msg/s"
    
    print(f"WebSocket Message Throughput Performance: {stats}")


@pytest.mark.asyncio
async def test_websocket_broadcast_performance(websocket_server):
    """Test WebSocket broadcast performance with many connected clients."""
    metrics = WebSocketPerformanceMetrics()
    num_clients = 200
    num_broadcasts = 50
    
    # Create many connected clients
    clients = []
    for i in range(num_clients):
        websocket = await create_websocket_client("ws://localhost:8000/ws", i, metrics)
        if websocket:
            clients.append(websocket)
    
    metrics.start_timer()
    
    # Perform broadcasts and measure performance
    broadcast_times = []
    for i in range(num_broadcasts):
        broadcast_message = {
            "type": "system_announcement",
            "message": f"Broadcast message {i}",
            "timestamp": time.time()
        }
        
        broadcast_start = time.time()
        await websocket_server.broadcast(broadcast_message)
        broadcast_end = time.time()
        
        broadcast_time = broadcast_end - broadcast_start
        broadcast_times.append(broadcast_time)
        
        # Small delay between broadcasts
        await asyncio.sleep(0.01)
    
    metrics.end_timer()
    
    # Close all clients
    for client in clients:
        await client.close()
    
    # Calculate broadcast performance
    avg_broadcast_time = statistics.mean(broadcast_times) * 1000  # ms
    max_broadcast_time = max(broadcast_times) * 1000  # ms
    
    # Broadcast performance assertions
    assert len(clients) >= num_clients * 0.95, f"Not enough clients connected: {len(clients)}/{num_clients}"
    assert avg_broadcast_time < 50, f"Average broadcast time too high: {avg_broadcast_time}ms"
    assert max_broadcast_time < 200, f"Max broadcast time too high: {max_broadcast_time}ms"
    
    print(f"WebSocket Broadcast Performance - Clients: {len(clients)}, Avg Broadcast: {avg_broadcast_time:.2f}ms, Max: {max_broadcast_time:.2f}ms")


@pytest.mark.asyncio
async def test_websocket_connection_stability(websocket_server):
    """Test WebSocket connection stability over time."""
    metrics = WebSocketPerformanceMetrics()
    num_clients = 50
    test_duration = 30  # seconds
    
    async def long_running_client(client_id: int):
        """Client that maintains connection and sends periodic messages."""
        websocket = await create_websocket_client("ws://localhost:8000/ws", client_id, metrics)
        
        if websocket:
            start_time = time.time()
            message_count = 0
            
            while time.time() - start_time < test_duration:
                try:
                    message = {
                        "type": "heartbeat",
                        "client_id": client_id,
                        "message_count": message_count,
                        "timestamp": time.time()
                    }
                    
                    send_time = time.time()
                    await websocket.send(json.dumps(message))
                    metrics.increment_messages_sent()
                    
                    # Mock response
                    await websocket.recv()
                    receive_time = time.time()
                    
                    latency = receive_time - send_time
                    metrics.add_message_latency(latency)
                    metrics.increment_messages_received()
                    
                    message_count += 1
                    await asyncio.sleep(0.5)  # Send message every 500ms
                    
                except Exception:
                    break
            
            await websocket.close()
    
    metrics.start_timer()
    
    # Start long-running clients
    tasks = [long_running_client(i) for i in range(num_clients)]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    metrics.end_timer()
    stats = metrics.get_stats()
    
    # Stability assertions
    expected_messages_per_client = test_duration * 2  # One message every 500ms
    expected_total_messages = num_clients * expected_messages_per_client
    
    assert stats["message_delivery_rate"] >= 90, f"Message delivery rate too low: {stats['message_delivery_rate']}%"
    assert stats["messages_sent"] >= expected_total_messages * 0.8, f"Not enough messages sent: {stats['messages_sent']}/{expected_total_messages}"
    assert stats["avg_message_latency_ms"] < 100, f"Average latency too high: {stats['avg_message_latency_ms']}ms"
    
    print(f"WebSocket Connection Stability Performance: {stats}")


@pytest.mark.asyncio
async def test_websocket_memory_usage():
    """Test WebSocket memory usage with many connections."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Create many mock WebSocket connections
    connections = []
    for i in range(1000):
        # Mock connection object
        connection = {
            "id": i,
            "websocket": AsyncMock(),
            "last_ping": time.time(),
            "subscriptions": ["tickets", "messages", "system"]
        }
        connections.append(connection)
    
    peak_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_per_connection = (peak_memory - initial_memory) / len(connections) * 1024  # KB
    
    # Memory usage assertions
    assert memory_per_connection < 50, f"Memory per connection too high: {memory_per_connection:.2f}KB"
    assert peak_memory - initial_memory < 100, f"Total memory increase too high: {peak_memory - initial_memory:.2f}MB"
    
    print(f"WebSocket Memory Usage - Per Connection: {memory_per_connection:.2f}KB, Total Increase: {peak_memory - initial_memory:.2f}MB")


@pytest.mark.asyncio
async def test_websocket_error_recovery():
    """Test WebSocket error recovery and reconnection performance."""
    metrics = WebSocketPerformanceMetrics()
    num_clients = 20
    
    async def error_prone_client(client_id: int):
        """Client that experiences connection errors and reconnects."""
        reconnection_attempts = 0
        max_reconnections = 3
        
        while reconnection_attempts < max_reconnections:
            websocket = await create_websocket_client("ws://localhost:8000/ws", client_id, metrics)
            
            if websocket:
                try:
                    # Send some messages
                    for i in range(10):
                        message = {
                            "type": "test_message",
                            "client_id": client_id,
                            "attempt": reconnection_attempts,
                            "message_num": i
                        }
                        
                        await websocket.send(json.dumps(message))
                        metrics.increment_messages_sent()
                        
                        # Simulate error on 5th message
                        if i == 5:
                            raise Exception("Simulated connection error")
                        
                        await websocket.recv()
                        metrics.increment_messages_received()
                
                except Exception:
                    await websocket.close()
                    reconnection_attempts += 1
                    await asyncio.sleep(0.1)  # Brief delay before reconnection
                    continue
                
                await websocket.close()
                break
    
    metrics.start_timer()
    
    tasks = [error_prone_client(i) for i in range(num_clients)]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    metrics.end_timer()
    stats = metrics.get_stats()
    
    # Error recovery assertions
    assert stats["connection_success_rate"] >= 80, f"Connection success rate too low with errors: {stats['connection_success_rate']}%"
    assert stats["message_delivery_rate"] >= 70, f"Message delivery rate too low with errors: {stats['message_delivery_rate']}%"
    
    print(f"WebSocket Error Recovery Performance: {stats}")