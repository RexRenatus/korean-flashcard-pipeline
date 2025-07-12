#!/usr/bin/env python3
"""
Example usage of DatabaseCircuitBreaker with persistent state and intelligent pattern analysis
"""

import asyncio
import random
import sqlite3
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "python"))

from flashcard_pipeline.circuit_breaker import (
    DatabaseCircuitBreaker, 
    MultiServiceDatabaseCircuitBreaker,
    CircuitBreakerError
)


# Example async function that simulates API calls
async def simulated_api_call(service_name: str, fail_rate: float = 0.3):
    """Simulate an API call that might fail"""
    await asyncio.sleep(random.uniform(0.1, 0.3))  # Simulate network delay
    
    if random.random() < fail_rate:
        # Simulate different types of errors
        error_types = [
            (ConnectionError, "Connection timeout"),
            (ValueError, "Invalid API response"),
            (RuntimeError, "Service unavailable"),
        ]
        error_class, message = random.choice(error_types)
        raise error_class(f"{service_name}: {message}")
    
    return {"status": "success", "data": f"Response from {service_name}"}


# Alert callback function
def alert_handler(alert_data):
    """Handle circuit breaker alerts"""
    print(f"\n🚨 ALERT [{alert_data['severity'].upper()}]: {alert_data['message']}")
    if alert_data.get('details'):
        for key, value in alert_data['details'].items():
            print(f"   {key}: {value}")


async def example_single_service():
    """Example using DatabaseCircuitBreaker for a single service"""
    print("\n=== Single Service Circuit Breaker Example ===\n")
    
    # Create database-backed circuit breaker
    breaker = DatabaseCircuitBreaker(
        db_path="example_circuit_breaker.db",
        service_name="payment_api",
        failure_threshold=3,
        recovery_timeout=30,
        enable_alerts=True,
        alert_callback=alert_handler
    )
    
    # Simulate API calls with varying failure patterns
    print("Simulating normal operations...")
    for i in range(5):
        try:
            result = await breaker.call(simulated_api_call, "payment_api", 0.1)
            print(f"Call {i+1}: Success - {result}")
        except CircuitBreakerError as e:
            print(f"Call {i+1}: Circuit breaker OPEN - {e}")
        except Exception as e:
            print(f"Call {i+1}: Failed - {type(e).__name__}: {e}")
        
        await asyncio.sleep(0.5)
    
    print("\nSimulating burst failures...")
    for i in range(10):
        try:
            result = await breaker.call(simulated_api_call, "payment_api", 0.8)
            print(f"Call {i+1}: Success - {result}")
        except CircuitBreakerError as e:
            print(f"Call {i+1}: Circuit breaker OPEN - {e}")
        except Exception as e:
            print(f"Call {i+1}: Failed - {type(e).__name__}: {e}")
        
        await asyncio.sleep(0.2)
    
    # Get statistics and recommendations
    stats = breaker.get_stats()
    print(f"\n📊 Circuit Breaker Statistics:")
    print(f"   State: {stats['state']}")
    print(f"   Success rate: {stats['success_rate']:.1f}%")
    print(f"   Failure count: {stats['failure_count']}")
    print(f"   Unacknowledged alerts: {stats['unacknowledged_alerts']}")
    
    if 'latest_pattern' in stats:
        print(f"\n   Latest Pattern Detected:")
        print(f"   - Type: {stats['latest_pattern']['type']}")
        print(f"   - Confidence: {stats['latest_pattern']['confidence']:.2f}")
    
    recommendations = breaker.get_recommendations()
    if recommendations['has_recommendations']:
        print(f"\n💡 Recommendations:")
        print(f"   {recommendations['message']}")
        print(f"   Based on {recommendations['based_on_patterns']} patterns")
        print(f"   Confidence: {recommendations['confidence']:.2f}")


async def example_multi_service():
    """Example using MultiServiceDatabaseCircuitBreaker for multiple services"""
    print("\n\n=== Multi-Service Circuit Breaker Example ===\n")
    
    # Create multi-service manager
    manager = MultiServiceDatabaseCircuitBreaker(
        db_path="example_circuit_breaker.db",
        enable_alerts=True,
        alert_callback=alert_handler
    )
    
    # Define services with different characteristics
    services = {
        "auth_service": {"fail_rate": 0.2, "calls": 15},
        "inventory_service": {"fail_rate": 0.5, "calls": 20},
        "shipping_service": {"fail_rate": 0.1, "calls": 10},
    }
    
    # Simulate calls to multiple services
    for service_name, config in services.items():
        print(f"\nTesting {service_name}...")
        
        for i in range(config["calls"]):
            try:
                breaker = await manager.get_breaker(service_name)
                result = await breaker.call(
                    simulated_api_call, 
                    service_name, 
                    config["fail_rate"]
                )
                print(f"   Call {i+1}: Success")
            except CircuitBreakerError as e:
                print(f"   Call {i+1}: Circuit OPEN")
            except Exception as e:
                print(f"   Call {i+1}: Failed - {type(e).__name__}")
            
            await asyncio.sleep(0.1)
    
    # Get all statistics
    print("\n📊 All Services Statistics:")
    all_stats = manager.get_all_stats()
    for service, stats in all_stats.items():
        print(f"\n   {service}:")
        print(f"   - State: {stats['state']}")
        print(f"   - Success rate: {stats['success_rate']:.1f}%")
        print(f"   - Calls: {stats['call_count']}")
    
    # Get services needing attention
    attention_services = manager.get_services_needing_attention()
    if attention_services:
        print(f"\n⚠️  Services needing attention: {', '.join(attention_services)}")
    
    # Get recommendations for all services
    print("\n💡 All Service Recommendations:")
    all_recommendations = manager.get_all_recommendations()
    for service, rec in all_recommendations.items():
        if rec['has_recommendations']:
            print(f"\n   {service}: {rec['message']}")


async def example_view_alerts():
    """Example showing how to view and acknowledge alerts"""
    print("\n\n=== Viewing Circuit Breaker Alerts ===\n")
    
    # Connect to database and view alerts
    conn = sqlite3.connect("example_circuit_breaker.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get unacknowledged alerts
    cursor.execute("""
        SELECT id, service_name, alert_type, severity, message, created_at
        FROM circuit_breaker_alerts
        WHERE acknowledged = FALSE
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    alerts = cursor.fetchall()
    if alerts:
        print("📬 Unacknowledged Alerts:")
        for alert in alerts:
            timestamp = datetime.fromisoformat(alert['created_at'].replace('Z', '+00:00'))
            print(f"\n   [{alert['severity'].upper()}] {alert['service_name']} - {alert['alert_type']}")
            print(f"   {alert['message']}")
            print(f"   Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Acknowledge the alert (in real system, this would be done by user)
            cursor.execute("""
                UPDATE circuit_breaker_alerts
                SET acknowledged = TRUE, acknowledged_by = 'example_script', 
                    acknowledged_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (alert['id'],))
        
        conn.commit()
    else:
        print("No unacknowledged alerts")
    
    # View failure patterns
    cursor.execute("""
        SELECT service_name, pattern_type, error_rate, confidence_score, detected_at
        FROM circuit_breaker_failure_patterns
        ORDER BY detected_at DESC
        LIMIT 5
    """)
    
    patterns = cursor.fetchall()
    if patterns:
        print("\n\n🔍 Recent Failure Patterns:")
        for pattern in patterns:
            timestamp = datetime.fromisoformat(pattern['detected_at'].replace('Z', '+00:00'))
            print(f"\n   {pattern['service_name']} - {pattern['pattern_type']} pattern")
            print(f"   Error rate: {pattern['error_rate']:.2f} errors/sec")
            print(f"   Confidence: {pattern['confidence_score']:.2f}")
            print(f"   Detected: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    conn.close()


async def main():
    """Run all examples"""
    # Ensure database has required tables
    import subprocess
    
    # Run migration to create tables
    migration_path = Path(__file__).parent.parent / "migrations" / "008_add_circuit_breaker_tracking.sql"
    if migration_path.exists():
        conn = sqlite3.connect("example_circuit_breaker.db")
        with open(migration_path, 'r') as f:
            conn.executescript(f.read())
        conn.close()
        print("✅ Database tables created")
    
    # Run examples
    await example_single_service()
    await example_multi_service()
    await example_view_alerts()
    
    print("\n\n✅ All examples completed!")
    print("Check 'example_circuit_breaker.db' to explore the stored data.")


if __name__ == "__main__":
    asyncio.run(main())