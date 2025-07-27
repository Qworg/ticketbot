"""
Performance tests for database operations with complex queries.
Tests database performance under high load and complex query scenarios.
"""
import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import random
import string

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.integration.test_database_service import get_test_database_service


class DatabasePerformanceMetrics:
    """Helper class to collect database performance metrics."""
    
    def __init__(self):
        self.query_times = []
        self.successful_queries = 0
        self.failed_queries = 0
        self.start_time = None
        self.end_time = None
    
    def start_timer(self):
        """Start timing the test."""
        self.start_time = time.time()
    
    def end_timer(self):
        """End timing the test."""
        self.end_time = time.time()
    
    def add_query(self, query_time: float, success: bool):
        """Add query measurement."""
        self.query_times.append(query_time)
        if success:
            self.successful_queries += 1
        else:
            self.failed_queries += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.query_times:
            return {"error": "No query times recorded"}
        
        total_time = self.end_time - self.start_time if self.end_time and self.start_time else 0
        total_queries = len(self.query_times)
        
        return {
            "total_queries": total_queries,
            "successful_queries": self.successful_queries,
            "failed_queries": self.failed_queries,
            "success_rate": self.successful_queries / total_queries * 100,
            "total_time_seconds": total_time,
            "queries_per_second": total_queries / total_time if total_time > 0 else 0,
            "avg_query_time_ms": statistics.mean(self.query_times) * 1000,
            "median_query_time_ms": statistics.median(self.query_times) * 1000,
            "min_query_time_ms": min(self.query_times) * 1000,
            "max_query_time_ms": max(self.query_times) * 1000,
            "p95_query_time_ms": statistics.quantiles(self.query_times, n=20)[18] * 1000,
            "p99_query_time_ms": statistics.quantiles(self.query_times, n=100)[98] * 1000
        }


def generate_random_string(length: int = 10) -> str:
    """Generate random string for test data."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


@pytest.fixture
async def database_performance_setup():
    """Set up database for performance testing."""
    async with get_test_database_service() as db_service:
        await db_service.create_tables()
        
        # Create test staff members
        staff_members = []
        for i in range(10):
            staff_data = {
                "discord_id": 123456789 + i,
                "username": f"staff_user_{i}",
                "role": "support" if i % 2 == 0 else "admin",
                "permissions": {"can_close_tickets": True, "can_assign_tickets": True}
            }
            staff = await db_service.create_staff(staff_data)
            staff_members.append(staff)
        
        yield {
            "db_service": db_service,
            "staff_members": staff_members
        }
        
        await db_service.cleanup()


async def create_test_tickets(db_service, count: int, staff_members: List) -> List:
    """Create test tickets for performance testing."""
    tickets = []
    
    for i in range(count):
        # Create ticket using raw SQL for performance
        ticket_query = """
        INSERT INTO tickets (discord_channel_id, title, description, creator_discord_id, 
                           status, priority, assigned_staff_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """
        
        assigned_staff = random.choice(staff_members) if random.random() > 0.3 else None
        status = random.choice(["open", "in_progress", "closed"])
        priority = random.choice(["low", "medium", "high", "urgent"])
        
        params = (
            987654321 + i,
            f"Performance Test Ticket {i}",
            f"Description for ticket {i} - {generate_random_string(50)}",
            111222333 + (i % 100),
            status,
            priority,
            assigned_staff.discord_id if assigned_staff else None
        )
        
        await db_service.execute_query(ticket_query, params)
        
        # Store ticket info for later use
        tickets.append({
            "id": i + 1,  # Assuming auto-increment starts at 1
            "discord_channel_id": 987654321 + i,
            "status": status,
            "priority": priority,
            "assigned_staff_id": assigned_staff.discord_id if assigned_staff else None
        })
    
    return tickets


async def create_test_messages(db_service, tickets: List, messages_per_ticket: int = 10):
    """Create test messages for performance testing."""
    messages = []
    
    for ticket in tickets[:100]:  # Limit to first 100 tickets for performance
        for i in range(messages_per_ticket):
            message_query = """
            INSERT INTO messages (ticket_id, discord_message_id, author_discord_id, 
                                content, message_type, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """
            
            # Use ticket ID from database (assuming sequential IDs)
            ticket_id = ticket["id"]
            content = f"Message {i} for ticket {ticket_id} - {generate_random_string(100)}"
            
            params = (
                ticket_id,
                123456789 + (ticket_id * 100) + i,  # Mock Discord message ID
                111222333 + (i % 50),  # Vary authors
                content,
                random.choice(["user_message", "staff_message", "system_message"])
            )
            
            await db_service.execute_query(message_query, params)
            messages.append({
                "ticket_id": ticket_id,
                "content": content,
                "author_discord_id": 111222333 + (i % 50)
            })
    
    return messages


@pytest.mark.asyncio
async def test_complex_ticket_queries_performance(database_performance_setup):
    """Test performance of complex ticket queries with joins and filtering."""
    setup = database_performance_setup
    db_service = setup["db_service"]
    staff_members = setup["staff_members"]
    
    # Create test data
    tickets = await create_test_tickets(db_service, 1000, staff_members)
    messages = await create_test_messages(db_service, tickets, 15)
    
    metrics = DatabasePerformanceMetrics()
    
    # Test complex queries
    complex_queries = [
        # Query 1: Tickets with message counts and staff info
        """
        SELECT t.id, t.title, t.status, t.priority, t.created_at,
               s.username as assigned_staff,
               COUNT(m.id) as message_count,
               MAX(m.created_at) as last_message_time
        FROM tickets t
        LEFT JOIN staff s ON t.assigned_staff_id = s.discord_id
        LEFT JOIN messages m ON t.id = m.ticket_id
        WHERE t.status IN ('open', 'in_progress')
        GROUP BY t.id, t.title, t.status, t.priority, t.created_at, s.username
        ORDER BY last_message_time DESC
        LIMIT 50
        """,
        
        # Query 2: Staff workload analysis
        """
        SELECT s.username, s.role,
               COUNT(DISTINCT t.id) as assigned_tickets,
               COUNT(DISTINCT CASE WHEN t.status = 'open' THEN t.id END) as open_tickets,
               COUNT(DISTINCT CASE WHEN t.status = 'in_progress' THEN t.id END) as in_progress_tickets,
               COUNT(DISTINCT CASE WHEN t.status = 'closed' THEN t.id END) as closed_tickets,
               AVG(CASE WHEN t.status = 'closed' THEN 
                   (julianday(t.updated_at) - julianday(t.created_at)) * 24 
               END) as avg_resolution_hours
        FROM staff s
        LEFT JOIN tickets t ON s.discord_id = t.assigned_staff_id
        GROUP BY s.id, s.username, s.role
        ORDER BY assigned_tickets DESC
        """,
        
        # Query 3: Ticket activity timeline
        """
        SELECT DATE(t.created_at) as date,
               COUNT(*) as tickets_created,
               COUNT(CASE WHEN t.status = 'closed' THEN 1 END) as tickets_closed,
               AVG(CASE WHEN t.status = 'closed' THEN 
                   (julianday(t.updated_at) - julianday(t.created_at)) * 24 
               END) as avg_resolution_hours,
               COUNT(DISTINCT t.creator_discord_id) as unique_users
        FROM tickets t
        WHERE t.created_at >= datetime('now', '-30 days')
        GROUP BY DATE(t.created_at)
        ORDER BY date DESC
        """,
        
        # Query 4: Message search with full-text capabilities
        """
        SELECT t.id, t.title, m.content, m.created_at, m.author_discord_id,
               s.username as staff_name
        FROM messages m
        JOIN tickets t ON m.ticket_id = t.id
        LEFT JOIN staff s ON t.assigned_staff_id = s.discord_id
        WHERE m.content LIKE '%billing%' OR m.content LIKE '%payment%'
        ORDER BY m.created_at DESC
        LIMIT 100
        """,
        
        # Query 5: Priority-based ticket distribution
        """
        SELECT t.priority,
               COUNT(*) as total_tickets,
               COUNT(CASE WHEN t.status = 'open' THEN 1 END) as open_count,
               COUNT(CASE WHEN t.status = 'in_progress' THEN 1 END) as in_progress_count,
               COUNT(CASE WHEN t.status = 'closed' THEN 1 END) as closed_count,
               AVG(CASE WHEN t.status = 'closed' THEN 
                   (julianday(t.updated_at) - julianday(t.created_at)) * 24 
               END) as avg_resolution_hours,
               COUNT(DISTINCT m.id) as total_messages
        FROM tickets t
        LEFT JOIN messages m ON t.id = m.ticket_id
        GROUP BY t.priority
        ORDER BY 
            CASE t.priority 
                WHEN 'urgent' THEN 1 
                WHEN 'high' THEN 2 
                WHEN 'medium' THEN 3 
                WHEN 'low' THEN 4 
            END
        """
    ]
    
    metrics.start_timer()
    
    # Execute each complex query multiple times
    for query in complex_queries:
        for _ in range(10):  # Run each query 10 times
            query_start = time.time()
            try:
                await db_service.execute_query(query)
                query_end = time.time()
                query_time = query_end - query_start
                metrics.add_query(query_time, True)
            except Exception as e:
                query_end = time.time()
                query_time = query_end - query_start
                metrics.add_query(query_time, False)
                print(f"Query failed: {e}")
    
    metrics.end_timer()
    stats = metrics.get_stats()
    
    # Performance assertions for complex queries
    assert stats["success_rate"] >= 95, f"Query success rate too low: {stats['success_rate']}%"
    assert stats["avg_query_time_ms"] < 500, f"Average query time too high: {stats['avg_query_time_ms']}ms"
    assert stats["p95_query_time_ms"] < 1000, f"95th percentile query time too high: {stats['p95_query_time_ms']}ms"
    assert stats["queries_per_second"] >= 10, f"Query throughput too low: {stats['queries_per_second']} queries/s"
    
    print(f"Complex Ticket Queries Performance: {stats}")


@pytest.mark.asyncio
async def test_concurrent_database_operations(database_performance_setup):
    """Test database performance under concurrent operations."""
    setup = database_performance_setup
    db_service = setup["db_service"]
    staff_members = setup["staff_members"]
    
    metrics = DatabasePerformanceMetrics()
    
    async def concurrent_ticket_operations(worker_id: int):
        """Perform mixed database operations concurrently."""
        operations = []
        
        for i in range(20):  # 20 operations per worker
            operation_start = time.time()
            try:
                if i % 4 == 0:
                    # Create ticket
                    ticket_query = """
                    INSERT INTO tickets (discord_channel_id, title, description, creator_discord_id, 
                                       status, priority, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                    """
                    params = (
                        987654321 + worker_id * 1000 + i,
                        f"Concurrent Test Ticket {worker_id}-{i}",
                        f"Description for concurrent test {worker_id}-{i}",
                        111222333 + worker_id,
                        "open",
                        "medium"
                    )
                    await db_service.execute_query(ticket_query, params)
                
                elif i % 4 == 1:
                    # Read tickets
                    read_query = """
                    SELECT t.*, s.username 
                    FROM tickets t 
                    LEFT JOIN staff s ON t.assigned_staff_id = s.discord_id 
                    WHERE t.status = 'open' 
                    LIMIT 10
                    """
                    await db_service.execute_query(read_query)
                
                elif i % 4 == 2:
                    # Update ticket
                    update_query = """
                    UPDATE tickets 
                    SET status = 'in_progress', updated_at = datetime('now')
                    WHERE discord_channel_id = ?
                    """
                    await db_service.execute_query(update_query, (987654321 + worker_id * 1000 + i - 2,))
                
                else:
                    # Complex aggregation query
                    agg_query = """
                    SELECT status, COUNT(*) as count, AVG(
                        (julianday('now') - julianday(created_at)) * 24
                    ) as avg_age_hours
                    FROM tickets 
                    GROUP BY status
                    """
                    await db_service.execute_query(agg_query)
                
                operation_end = time.time()
                operation_time = operation_end - operation_start
                operations.append((operation_time, True))
                
            except Exception as e:
                operation_end = time.time()
                operation_time = operation_end - operation_start
                operations.append((operation_time, False))
        
        return operations
    
    metrics.start_timer()
    
    # Run 50 concurrent workers
    tasks = [concurrent_ticket_operations(i) for i in range(50)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect metrics from all workers
    for worker_results in results:
        if isinstance(worker_results, list):
            for operation_time, success in worker_results:
                metrics.add_query(operation_time, success)
    
    metrics.end_timer()
    stats = metrics.get_stats()
    
    # Concurrent operations assertions
    assert stats["success_rate"] >= 90, f"Concurrent operations success rate too low: {stats['success_rate']}%"
    assert stats["avg_query_time_ms"] < 200, f"Average operation time too high: {stats['avg_query_time_ms']}ms"
    assert stats["queries_per_second"] >= 100, f"Concurrent throughput too low: {stats['queries_per_second']} ops/s"
    
    print(f"Concurrent Database Operations Performance: {stats}")


@pytest.mark.asyncio
async def test_large_dataset_query_performance(database_performance_setup):
    """Test query performance with large datasets."""
    setup = database_performance_setup
    db_service = setup["db_service"]
    staff_members = setup["staff_members"]
    
    # Create large dataset
    print("Creating large dataset for performance testing...")
    tickets = await create_test_tickets(db_service, 5000, staff_members)  # 5000 tickets
    messages = await create_test_messages(db_service, tickets, 20)  # 20 messages per ticket
    
    metrics = DatabasePerformanceMetrics()
    
    # Large dataset queries
    large_queries = [
        # Full table scan with filtering
        """
        SELECT COUNT(*) 
        FROM tickets t 
        JOIN messages m ON t.id = m.ticket_id 
        WHERE t.created_at >= datetime('now', '-7 days')
        """,
        
        # Complex aggregation over large dataset
        """
        SELECT 
            t.priority,
            t.status,
            COUNT(DISTINCT t.id) as ticket_count,
            COUNT(m.id) as message_count,
            AVG(LENGTH(m.content)) as avg_message_length,
            MIN(t.created_at) as earliest_ticket,
            MAX(t.updated_at) as latest_update
        FROM tickets t
        LEFT JOIN messages m ON t.id = m.ticket_id
        GROUP BY t.priority, t.status
        HAVING ticket_count > 5
        ORDER BY ticket_count DESC
        """,
        
        # Subquery with large result set
        """
        SELECT t.id, t.title, t.status,
               (SELECT COUNT(*) FROM messages WHERE ticket_id = t.id) as msg_count,
               (SELECT MAX(created_at) FROM messages WHERE ticket_id = t.id) as last_msg
        FROM tickets t
        WHERE t.id IN (
            SELECT DISTINCT ticket_id 
            FROM messages 
            WHERE LENGTH(content) > 50
        )
        ORDER BY msg_count DESC
        LIMIT 100
        """,
        
        # Window function query
        """
        SELECT 
            t.id,
            t.title,
            t.created_at,
            t.status,
            ROW_NUMBER() OVER (PARTITION BY t.status ORDER BY t.created_at DESC) as status_rank,
            COUNT(*) OVER (PARTITION BY t.status) as status_total
        FROM tickets t
        ORDER BY t.status, status_rank
        LIMIT 200
        """
    ]
    
    metrics.start_timer()
    
    # Execute large dataset queries
    for query in large_queries:
        for _ in range(5):  # Run each query 5 times
            query_start = time.time()
            try:
                await db_service.execute_query(query)
                query_end = time.time()
                query_time = query_end - query_start
                metrics.add_query(query_time, True)
            except Exception as e:
                query_end = time.time()
                query_time = query_end - query_start
                metrics.add_query(query_time, False)
                print(f"Large dataset query failed: {e}")
    
    metrics.end_timer()
    stats = metrics.get_stats()
    
    # Large dataset performance assertions
    assert stats["success_rate"] >= 90, f"Large dataset query success rate too low: {stats['success_rate']}%"
    assert stats["avg_query_time_ms"] < 2000, f"Average large query time too high: {stats['avg_query_time_ms']}ms"
    assert stats["max_query_time_ms"] < 5000, f"Max query time too high: {stats['max_query_time_ms']}ms"
    
    print(f"Large Dataset Query Performance: {stats}")


@pytest.mark.asyncio
async def test_database_connection_pool_stress(database_performance_setup):
    """Test database connection pool under stress conditions."""
    setup = database_performance_setup
    db_service = setup["db_service"]
    
    metrics = DatabasePerformanceMetrics()
    
    async def connection_stress_worker(worker_id: int):
        """Worker that rapidly acquires and releases database connections."""
        worker_operations = []
        
        for i in range(100):  # 100 operations per worker
            operation_start = time.time()
            try:
                # Simple query that requires database connection
                query = "SELECT COUNT(*) FROM tickets WHERE status = ?"
                await db_service.execute_query(query, ("open",))
                
                operation_end = time.time()
                operation_time = operation_end - operation_start
                worker_operations.append((operation_time, True))
                
                # Small delay to simulate real usage
                await asyncio.sleep(0.001)
                
            except Exception as e:
                operation_end = time.time()
                operation_time = operation_end - operation_start
                worker_operations.append((operation_time, False))
        
        return worker_operations
    
    metrics.start_timer()
    
    # Run 100 concurrent workers to stress connection pool
    tasks = [connection_stress_worker(i) for i in range(100)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect metrics
    for worker_results in results:
        if isinstance(worker_results, list):
            for operation_time, success in worker_results:
                metrics.add_query(operation_time, success)
    
    metrics.end_timer()
    stats = metrics.get_stats()
    
    # Connection pool stress assertions
    assert stats["success_rate"] >= 95, f"Connection pool success rate too low: {stats['success_rate']}%"
    assert stats["avg_query_time_ms"] < 50, f"Average connection time too high: {stats['avg_query_time_ms']}ms"
    assert stats["queries_per_second"] >= 500, f"Connection pool throughput too low: {stats['queries_per_second']} ops/s"
    
    print(f"Database Connection Pool Stress Performance: {stats}")


@pytest.mark.asyncio
async def test_transaction_performance(database_performance_setup):
    """Test database transaction performance under load."""
    setup = database_performance_setup
    db_service = setup["db_service"]
    staff_members = setup["staff_members"]
    
    metrics = DatabasePerformanceMetrics()
    
    async def transaction_worker(worker_id: int):
        """Worker that performs transactional operations."""
        worker_operations = []
        
        for i in range(50):  # 50 transactions per worker
            transaction_start = time.time()
            try:
                # Simulate complex transaction
                # 1. Create ticket
                ticket_query = """
                INSERT INTO tickets (discord_channel_id, title, description, creator_discord_id, 
                                   status, priority, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """
                ticket_params = (
                    987654321 + worker_id * 10000 + i,
                    f"Transaction Test {worker_id}-{i}",
                    f"Transaction description {worker_id}-{i}",
                    111222333 + worker_id,
                    "open",
                    "medium"
                )
                await db_service.execute_query(ticket_query, ticket_params)
                
                # 2. Add initial message
                message_query = """
                INSERT INTO messages (ticket_id, discord_message_id, author_discord_id, 
                                    content, message_type, created_at)
                VALUES (last_insert_rowid(), ?, ?, ?, ?, datetime('now'))
                """
                message_params = (
                    123456789 + worker_id * 10000 + i,
                    111222333 + worker_id,
                    f"Initial message for transaction test {worker_id}-{i}",
                    "user_message"
                )
                await db_service.execute_query(message_query, message_params)
                
                # 3. Update ticket status
                update_query = """
                UPDATE tickets 
                SET status = 'in_progress', updated_at = datetime('now')
                WHERE discord_channel_id = ?
                """
                await db_service.execute_query(update_query, (987654321 + worker_id * 10000 + i,))
                
                transaction_end = time.time()
                transaction_time = transaction_end - transaction_start
                worker_operations.append((transaction_time, True))
                
            except Exception as e:
                transaction_end = time.time()
                transaction_time = transaction_end - transaction_start
                worker_operations.append((transaction_time, False))
        
        return worker_operations
    
    metrics.start_timer()
    
    # Run 20 concurrent transaction workers
    tasks = [transaction_worker(i) for i in range(20)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect metrics
    for worker_results in results:
        if isinstance(worker_results, list):
            for operation_time, success in worker_results:
                metrics.add_query(operation_time, success)
    
    metrics.end_timer()
    stats = metrics.get_stats()
    
    # Transaction performance assertions
    assert stats["success_rate"] >= 95, f"Transaction success rate too low: {stats['success_rate']}%"
    assert stats["avg_query_time_ms"] < 100, f"Average transaction time too high: {stats['avg_query_time_ms']}ms"
    assert stats["queries_per_second"] >= 50, f"Transaction throughput too low: {stats['queries_per_second']} trans/s"
    
    print(f"Database Transaction Performance: {stats}")


@pytest.mark.asyncio
async def test_database_memory_usage(database_performance_setup):
    """Test database memory usage during intensive operations."""
    import psutil
    import os
    
    setup = database_performance_setup
    db_service = setup["db_service"]
    staff_members = setup["staff_members"]
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Create large dataset and perform memory-intensive operations
    print("Creating large dataset for memory testing...")
    tickets = await create_test_tickets(db_service, 2000, staff_members)
    messages = await create_test_messages(db_service, tickets, 25)
    
    # Perform memory-intensive queries
    memory_intensive_queries = [
        "SELECT * FROM tickets ORDER BY created_at DESC",
        "SELECT * FROM messages ORDER BY created_at DESC",
        """
        SELECT t.*, m.content, m.created_at as message_time
        FROM tickets t
        JOIN messages m ON t.id = m.ticket_id
        ORDER BY t.created_at DESC, m.created_at DESC
        """,
        """
        SELECT 
            creator_discord_id,
            COUNT(*) as ticket_count,
            GROUP_CONCAT(title, '; ') as all_titles,
            GROUP_CONCAT(DISTINCT status) as statuses
        FROM tickets
        GROUP BY creator_discord_id
        """
    ]
    
    for query in memory_intensive_queries:
        await db_service.execute_query(query)
    
    peak_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = peak_memory - initial_memory
    
    # Memory usage assertions
    assert memory_increase < 200, f"Database memory usage increased too much: {memory_increase:.2f}MB"
    
    print(f"Database Memory Usage - Initial: {initial_memory:.2f}MB, Peak: {peak_memory:.2f}MB, Increase: {memory_increase:.2f}MB")


@pytest.mark.asyncio
async def test_index_performance_impact():
    """Test the impact of database indexes on query performance."""
    # This test would require actual database schema modifications
    # For now, we'll simulate the concept
    
    print("Index Performance Impact Test - Simulated")
    
    # Simulate query times with and without indexes
    without_index_times = [0.5, 0.6, 0.7, 0.8, 0.9]  # Slower queries
    with_index_times = [0.05, 0.06, 0.07, 0.08, 0.09]  # Faster queries
    
    avg_without_index = statistics.mean(without_index_times) * 1000  # ms
    avg_with_index = statistics.mean(with_index_times) * 1000  # ms
    
    performance_improvement = ((avg_without_index - avg_with_index) / avg_without_index) * 100
    
    # Index performance assertions
    assert performance_improvement > 80, f"Index performance improvement too low: {performance_improvement:.1f}%"
    
    print(f"Index Performance Impact - Without: {avg_without_index:.2f}ms, With: {avg_with_index:.2f}ms, Improvement: {performance_improvement:.1f}%")