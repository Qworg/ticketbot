"""
Simple performance tests that can run independently.
Tests basic performance metrics without complex dependencies.
"""
import pytest
import asyncio
import time
import statistics
import sqlite3
import tempfile
import os
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import random
import string


class SimplePerformanceMetrics:
    """Helper class to collect performance metrics."""
    
    def __init__(self):
        self.operation_times = []
        self.successful_operations = 0
        self.failed_operations = 0
        self.start_time = None
        self.end_time = None
    
    def start_timer(self):
        """Start timing the test."""
        self.start_time = time.time()
    
    def end_timer(self):
        """End timing the test."""
        self.end_time = time.time()
    
    def add_operation(self, operation_time: float, success: bool):
        """Add operation measurement."""
        self.operation_times.append(operation_time)
        if success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.operation_times:
            return {"error": "No operation times recorded"}
        
        total_time = self.end_time - self.start_time if self.end_time and self.start_time else 0
        total_operations = len(self.operation_times)
        
        return {
            "total_operations": total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "success_rate": self.successful_operations / total_operations * 100,
            "total_time_seconds": total_time,
            "operations_per_second": total_operations / total_time if total_time > 0 else 0,
            "avg_operation_time_ms": statistics.mean(self.operation_times) * 1000,
            "median_operation_time_ms": statistics.median(self.operation_times) * 1000,
            "min_operation_time_ms": min(self.operation_times) * 1000,
            "max_operation_time_ms": max(self.operation_times) * 1000,
            "p95_operation_time_ms": statistics.quantiles(self.operation_times, n=20)[18] * 1000,
            "p99_operation_time_ms": statistics.quantiles(self.operation_times, n=100)[98] * 1000
        }


def generate_random_string(length: int = 10) -> str:
    """Generate random string for test data."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


@pytest.fixture
def temp_database():
    """Create temporary SQLite database for testing."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_file.close()
    
    # Create database schema
    conn = sqlite3.connect(temp_file.name)
    cursor = conn.cursor()
    
    # Create tables similar to our application
    cursor.execute("""
        CREATE TABLE tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_channel_id INTEGER UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            priority TEXT DEFAULT 'medium',
            creator_discord_id INTEGER NOT NULL,
            assigned_staff_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER REFERENCES tickets(id),
            discord_message_id INTEGER UNIQUE,
            author_discord_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            message_type TEXT DEFAULT 'user_message',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id INTEGER UNIQUE NOT NULL,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            permissions TEXT DEFAULT '{}',
            active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes for performance
    cursor.execute("CREATE INDEX idx_tickets_status ON tickets(status)")
    cursor.execute("CREATE INDEX idx_tickets_priority ON tickets(priority)")
    cursor.execute("CREATE INDEX idx_tickets_created_at ON tickets(created_at)")
    cursor.execute("CREATE INDEX idx_messages_ticket_id ON messages(ticket_id)")
    cursor.execute("CREATE INDEX idx_messages_created_at ON messages(created_at)")
    
    conn.commit()
    conn.close()
    
    yield temp_file.name
    
    # Cleanup
    os.unlink(temp_file.name)


def create_test_data(db_path: str, num_tickets: int = 1000, messages_per_ticket: int = 10):
    """Create test data in the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create staff members
    staff_members = []
    for i in range(10):
        cursor.execute("""
            INSERT INTO staff (discord_id, username, role, permissions)
            VALUES (?, ?, ?, ?)
        """, (123456789 + i, f"staff_user_{i}", "support", "{}"))
        staff_members.append(123456789 + i)
    
    # Create tickets
    ticket_ids = []
    for i in range(num_tickets):
        assigned_staff = random.choice(staff_members) if random.random() > 0.3 else None
        status = random.choice(["open", "in_progress", "closed"])
        priority = random.choice(["low", "medium", "high", "urgent"])
        
        cursor.execute("""
            INSERT INTO tickets (discord_channel_id, title, description, creator_discord_id, 
                               status, priority, assigned_staff_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            987654321 + i,
            f"Test Ticket {i}",
            f"Description for ticket {i} - {generate_random_string(50)}",
            111222333 + (i % 100),
            status,
            priority,
            assigned_staff
        ))
        ticket_ids.append(cursor.lastrowid)
    
    # Create messages
    for ticket_id in ticket_ids[:min(100, len(ticket_ids))]:  # Limit messages for performance
        for j in range(messages_per_ticket):
            cursor.execute("""
                INSERT INTO messages (ticket_id, discord_message_id, author_discord_id, 
                                    content, message_type)
                VALUES (?, ?, ?, ?, ?)
            """, (
                ticket_id,
                123456789 + (ticket_id * 100) + j,
                111222333 + (j % 50),
                f"Message {j} for ticket {ticket_id} - {generate_random_string(100)}",
                random.choice(["user_message", "staff_message", "system_message"])
            ))
    
    conn.commit()
    conn.close()


@pytest.mark.asyncio
async def test_database_query_performance(temp_database):
    """Test database query performance with complex queries."""
    db_path = temp_database
    create_test_data(db_path, 2000, 15)
    
    metrics = SimplePerformanceMetrics()
    
    # Complex queries to test
    complex_queries = [
        # Query 1: Tickets with message counts
        """
        SELECT t.id, t.title, t.status, t.priority, t.created_at,
               COUNT(m.id) as message_count,
               MAX(m.created_at) as last_message_time
        FROM tickets t
        LEFT JOIN messages m ON t.id = m.ticket_id
        WHERE t.status IN ('open', 'in_progress')
        GROUP BY t.id, t.title, t.status, t.priority, t.created_at
        ORDER BY last_message_time DESC
        LIMIT 50
        """,
        
        # Query 2: Staff workload analysis
        """
        SELECT s.username, s.role,
               COUNT(DISTINCT t.id) as assigned_tickets,
               COUNT(DISTINCT CASE WHEN t.status = 'open' THEN t.id END) as open_tickets,
               COUNT(DISTINCT CASE WHEN t.status = 'in_progress' THEN t.id END) as in_progress_tickets,
               COUNT(DISTINCT CASE WHEN t.status = 'closed' THEN t.id END) as closed_tickets
        FROM staff s
        LEFT JOIN tickets t ON s.discord_id = t.assigned_staff_id
        GROUP BY s.id, s.username, s.role
        ORDER BY assigned_tickets DESC
        """,
        
        # Query 3: Message search
        """
        SELECT t.id, t.title, m.content, m.created_at, m.author_discord_id
        FROM messages m
        JOIN tickets t ON m.ticket_id = t.id
        WHERE m.content LIKE '%test%' OR m.content LIKE '%message%'
        ORDER BY m.created_at DESC
        LIMIT 100
        """,
        
        # Query 4: Priority distribution
        """
        SELECT t.priority,
               COUNT(*) as total_tickets,
               COUNT(CASE WHEN t.status = 'open' THEN 1 END) as open_count,
               COUNT(CASE WHEN t.status = 'in_progress' THEN 1 END) as in_progress_count,
               COUNT(CASE WHEN t.status = 'closed' THEN 1 END) as closed_count,
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
    
    # Execute each query multiple times
    for query in complex_queries:
        for _ in range(10):  # Run each query 10 times
            query_start = time.time()
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(query)
                results = cursor.fetchall()
                conn.close()
                
                query_end = time.time()
                query_time = query_end - query_start
                metrics.add_operation(query_time, True)
                
            except Exception as e:
                query_end = time.time()
                query_time = query_end - query_start
                metrics.add_operation(query_time, False)
                print(f"Query failed: {e}")
    
    metrics.end_timer()
    stats = metrics.get_stats()
    
    # Performance assertions
    assert stats["success_rate"] >= 95, f"Query success rate too low: {stats['success_rate']}%"
    assert stats["avg_operation_time_ms"] < 100, f"Average query time too high: {stats['avg_operation_time_ms']}ms"
    assert stats["p95_operation_time_ms"] < 200, f"95th percentile query time too high: {stats['p95_operation_time_ms']}ms"
    assert stats["operations_per_second"] >= 50, f"Query throughput too low: {stats['operations_per_second']} queries/s"
    
    print(f"Database Query Performance: {stats}")


@pytest.mark.asyncio
async def test_concurrent_database_operations(temp_database):
    """Test database performance under concurrent operations."""
    db_path = temp_database
    create_test_data(db_path, 1000, 10)
    
    metrics = SimplePerformanceMetrics()
    
    def database_worker(worker_id: int):
        """Worker that performs database operations."""
        worker_operations = []
        
        for i in range(20):  # 20 operations per worker
            operation_start = time.time()
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                if i % 4 == 0:
                    # Create ticket
                    cursor.execute("""
                        INSERT INTO tickets (discord_channel_id, title, description, creator_discord_id, 
                                           status, priority)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        987654321 + worker_id * 1000 + i,
                        f"Concurrent Test Ticket {worker_id}-{i}",
                        f"Description for concurrent test {worker_id}-{i}",
                        111222333 + worker_id,
                        "open",
                        "medium"
                    ))
                
                elif i % 4 == 1:
                    # Read tickets
                    cursor.execute("""
                        SELECT t.*, s.username 
                        FROM tickets t 
                        LEFT JOIN staff s ON t.assigned_staff_id = s.discord_id 
                        WHERE t.status = 'open' 
                        LIMIT 10
                    """)
                    cursor.fetchall()
                
                elif i % 4 == 2:
                    # Update ticket
                    cursor.execute("""
                        UPDATE tickets 
                        SET status = 'in_progress', updated_at = CURRENT_TIMESTAMP
                        WHERE discord_channel_id = ?
                    """, (987654321 + worker_id * 1000 + i - 2,))
                
                else:
                    # Aggregation query
                    cursor.execute("""
                        SELECT status, COUNT(*) as count
                        FROM tickets 
                        GROUP BY status
                    """)
                    cursor.fetchall()
                
                conn.commit()
                conn.close()
                
                operation_end = time.time()
                operation_time = operation_end - operation_start
                worker_operations.append((operation_time, True))
                
            except Exception as e:
                if 'conn' in locals():
                    conn.close()
                operation_end = time.time()
                operation_time = operation_end - operation_start
                worker_operations.append((operation_time, False))
        
        return worker_operations
    
    metrics.start_timer()
    
    # Run 20 concurrent workers
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(database_worker, i) for i in range(20)]
        results = [future.result() for future in futures]
    
    # Collect metrics from all workers
    for worker_results in results:
        for operation_time, success in worker_results:
            metrics.add_operation(operation_time, success)
    
    metrics.end_timer()
    stats = metrics.get_stats()
    
    # Concurrent operations assertions
    assert stats["success_rate"] >= 85, f"Concurrent operations success rate too low: {stats['success_rate']}%"
    assert stats["avg_operation_time_ms"] < 100, f"Average operation time too high: {stats['avg_operation_time_ms']}ms"
    assert stats["operations_per_second"] >= 100, f"Concurrent throughput too low: {stats['operations_per_second']} ops/s"
    
    print(f"Concurrent Database Operations Performance: {stats}")


@pytest.mark.asyncio
async def test_large_dataset_performance(temp_database):
    """Test performance with large datasets."""
    db_path = temp_database
    
    print("Creating large dataset for performance testing...")
    create_test_data(db_path, 10000, 5)  # 10,000 tickets with 5 messages each
    
    metrics = SimplePerformanceMetrics()
    
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
            AVG(LENGTH(m.content)) as avg_message_length
        FROM tickets t
        LEFT JOIN messages m ON t.id = m.ticket_id
        GROUP BY t.priority, t.status
        HAVING ticket_count > 5
        ORDER BY ticket_count DESC
        """,
        
        # Subquery with large result set
        """
        SELECT t.id, t.title, t.status,
               (SELECT COUNT(*) FROM messages WHERE ticket_id = t.id) as msg_count
        FROM tickets t
        WHERE t.id IN (
            SELECT DISTINCT ticket_id 
            FROM messages 
            WHERE LENGTH(content) > 50
        )
        ORDER BY msg_count DESC
        LIMIT 100
        """
    ]
    
    metrics.start_timer()
    
    # Execute large dataset queries
    for query in large_queries:
        for _ in range(3):  # Run each query 3 times
            query_start = time.time()
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(query)
                results = cursor.fetchall()
                conn.close()
                
                query_end = time.time()
                query_time = query_end - query_start
                metrics.add_operation(query_time, True)
                
            except Exception as e:
                if 'conn' in locals():
                    conn.close()
                query_end = time.time()
                query_time = query_end - query_start
                metrics.add_operation(query_time, False)
                print(f"Large dataset query failed: {e}")
    
    metrics.end_timer()
    stats = metrics.get_stats()
    
    # Large dataset performance assertions
    assert stats["success_rate"] >= 90, f"Large dataset query success rate too low: {stats['success_rate']}%"
    assert stats["avg_operation_time_ms"] < 1000, f"Average large query time too high: {stats['avg_operation_time_ms']}ms"
    assert stats["max_operation_time_ms"] < 3000, f"Max query time too high: {stats['max_operation_time_ms']}ms"
    
    print(f"Large Dataset Query Performance: {stats}")


@pytest.mark.asyncio
async def test_memory_usage_performance():
    """Test memory usage during performance operations."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Create large data structures to simulate memory usage
    large_data = []
    for i in range(10000):
        ticket_data = {
            "id": i,
            "title": f"Memory Test Ticket {i}",
            "description": generate_random_string(200),
            "messages": [
                {
                    "id": j,
                    "content": generate_random_string(150),
                    "author": f"user_{j % 100}",
                    "timestamp": time.time()
                }
                for j in range(10)
            ]
        }
        large_data.append(ticket_data)
    
    peak_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = peak_memory - initial_memory
    
    # Memory usage assertions
    assert memory_increase < 100, f"Memory usage increased too much: {memory_increase:.2f}MB"
    
    print(f"Memory Usage - Initial: {initial_memory:.2f}MB, Peak: {peak_memory:.2f}MB, Increase: {memory_increase:.2f}MB")


@pytest.mark.asyncio
async def test_index_performance_comparison(temp_database):
    """Test the impact of database indexes on query performance."""
    db_path = temp_database
    create_test_data(db_path, 5000, 3)
    
    # Test query performance with indexes
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    test_query = """
        SELECT t.*, COUNT(m.id) as message_count
        FROM tickets t
        LEFT JOIN messages m ON t.id = m.ticket_id
        WHERE t.status = 'open' AND t.priority = 'high'
        GROUP BY t.id
        ORDER BY t.created_at DESC
        LIMIT 50
    """
    
    # Measure with indexes
    with_index_times = []
    for _ in range(10):
        start_time = time.time()
        cursor.execute(test_query)
        cursor.fetchall()
        end_time = time.time()
        with_index_times.append(end_time - start_time)
    
    # Drop indexes
    cursor.execute("DROP INDEX IF EXISTS idx_tickets_status")
    cursor.execute("DROP INDEX IF EXISTS idx_tickets_priority")
    cursor.execute("DROP INDEX IF EXISTS idx_tickets_created_at")
    cursor.execute("DROP INDEX IF EXISTS idx_messages_ticket_id")
    
    # Measure without indexes
    without_index_times = []
    for _ in range(10):
        start_time = time.time()
        cursor.execute(test_query)
        cursor.fetchall()
        end_time = time.time()
        without_index_times.append(end_time - start_time)
    
    conn.close()
    
    avg_with_index = statistics.mean(with_index_times) * 1000  # ms
    avg_without_index = statistics.mean(without_index_times) * 1000  # ms
    
    performance_improvement = ((avg_without_index - avg_with_index) / avg_without_index) * 100
    
    # Index performance assertions
    assert performance_improvement > 0, f"Indexes should improve performance: {performance_improvement:.1f}%"
    assert avg_with_index < avg_without_index, f"Indexed queries should be faster: {avg_with_index:.2f}ms vs {avg_without_index:.2f}ms"
    
    print(f"Index Performance Impact - Without: {avg_without_index:.2f}ms, With: {avg_with_index:.2f}ms, Improvement: {performance_improvement:.1f}%")