#!/usr/bin/env python3
"""
Database health check utility.
Provides command-line access to database health and performance metrics.
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flashcard_pipeline.database import (
    EnhancedDatabaseManager,
    DatabaseHealthEndpoint,
    PoolConfig,
    PerformanceThresholds
)


def format_health_status(health: dict) -> str:
    """Format health status for display"""
    output = []
    
    # Overall status
    status_emoji = "✅" if health['healthy'] else "❌"
    output.append(f"\n{status_emoji} Database Health Status")
    output.append(f"Timestamp: {health['timestamp']}")
    output.append("")
    
    # Checks
    output.append("Health Checks:")
    for check, status in health['checks'].items():
        emoji = "✅" if status == "OK" else "⚠️" if status == "WARNING" else "❌"
        output.append(f"  {emoji} {check}: {status}")
    
    # Pool health
    if 'pool_health' in health:
        output.append("\nConnection Pool:")
        pool = health['pool_health']
        output.append(f"  Total: {pool['total_connections']}")
        output.append(f"  Active: {pool['active_connections']}")
        output.append(f"  Available: {pool['available_connections']}")
    
    # Database info
    if 'database_info' in health:
        output.append("\nDatabase Info:")
        db_info = health['database_info']
        output.append(f"  Size: {db_info['size_mb']:.2f} MB")
        output.append(f"  Modified: {db_info['modified']}")
    
    # Performance summary
    if 'performance_summary' in health:
        output.append("\nPerformance Summary:")
        perf = health['performance_summary']
        output.append(f"  Total Queries: {perf['total_queries']:,}")
        output.append(f"  Error Rate: {perf['error_rate']:.2%}")
        output.append(f"  Avg Duration: {perf['avg_duration_ms']:.2f} ms")
        output.append(f"  Slow Queries: {perf['slow_queries']}")
    
    # Warnings
    if health.get('warnings'):
        output.append("\n⚠️  Warnings:")
        for warning in health['warnings']:
            output.append(f"  - {warning}")
    
    # Errors
    if health.get('errors'):
        output.append("\n❌ Errors:")
        for error in health['errors']:
            output.append(f"  - {error}")
    
    return "\n".join(output)


def format_metrics(metrics: dict) -> str:
    """Format metrics for display"""
    output = []
    
    output.append(f"\n📊 Database Metrics")
    output.append(f"Timestamp: {metrics['timestamp']}")
    output.append("")
    
    # Pool stats
    if 'pool_stats' in metrics:
        pool = metrics['pool_stats']
        output.append("Connection Pool Statistics:")
        output.append(f"  Connections: {pool['total_connections']}")
        output.append(f"  Active: {pool['active_connections']}")
        output.append(f"  Idle: {pool['idle_connections']}")
        
        pool_metrics = pool['metrics']
        output.append(f"\n  Lifetime Metrics:")
        output.append(f"    Created: {pool_metrics['connections_created']}")
        output.append(f"    Destroyed: {pool_metrics['connections_destroyed']}")
        output.append(f"    Reused: {pool_metrics['connections_reused']}")
        output.append(f"    Errors: {pool_metrics['connection_errors']}")
        
        # Connection details table
        if pool['connection_stats']:
            output.append("\n  Connection Details:")
            headers = ['ID', 'In Use', 'Age (s)', 'Idle (s)', 'Queries', 'Errors', 'Avg Time (ms)']
            rows = []
            for conn in pool['connection_stats']:
                rows.append([
                    conn['id'],
                    '✓' if conn['in_use'] else '',
                    f"{conn['age_seconds']:.1f}",
                    f"{conn['idle_seconds']:.1f}",
                    conn['total_queries'],
                    conn['total_errors'],
                    f"{conn['avg_query_time_ms']:.2f}"
                ])
            output.append(tabulate(rows, headers=headers, tablefmt='simple'))
    
    # Performance stats
    if 'performance_stats' in metrics:
        perf = metrics['performance_stats']
        output.append(f"\nPerformance Statistics:")
        output.append(f"  Uptime: {perf['uptime_seconds']:.1f} seconds")
        output.append(f"  Total Queries: {perf['total_queries']:,}")
        output.append(f"  Queries/Second: {perf['queries_per_second']:.2f}")
        output.append(f"  Error Rate: {perf['error_rate']:.2%}")
        output.append(f"  Avg Duration: {perf['avg_duration_ms']:.2f} ms")
        
        # Query type breakdown
        if perf['metrics_by_type']:
            output.append("\n  Query Type Breakdown:")
            headers = ['Type', 'Count', 'Avg Time (ms)', 'Errors']
            rows = []
            for qtype, stats in perf['metrics_by_type'].items():
                avg_time = stats['total_duration_ms'] / stats['count'] if stats['count'] > 0 else 0
                rows.append([
                    qtype,
                    stats['count'],
                    f"{avg_time:.2f}",
                    stats['errors']
                ])
            output.append(tabulate(rows, headers=headers, tablefmt='simple'))
    
    # Slow queries
    if 'slow_queries' in metrics and metrics['slow_queries']:
        output.append("\n🐌 Recent Slow Queries:")
        for i, query in enumerate(metrics['slow_queries'], 1):
            output.append(f"\n  {i}. [{query['severity'].upper()}] {query['duration_ms']:.2f} ms")
            output.append(f"     Type: {query['query_type']}, Table: {query['table_name'] or 'N/A'}")
            output.append(f"     Query: {query['query'][:80]}...")
            output.append(f"     Time: {query['timestamp']}")
    
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Database health check and monitoring tool")
    parser.add_argument('--db', default='pipeline.db', help='Database file path')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Health check command
    health_parser = subparsers.add_parser('health', help='Check database health')
    
    # Metrics command
    metrics_parser = subparsers.add_parser('metrics', help='Show performance metrics')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate performance report')
    
    # Optimize command
    optimize_parser = subparsers.add_parser('optimize', help='Optimize database')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Live monitoring mode')
    monitor_parser.add_argument('--interval', type=int, default=5, help='Update interval in seconds')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Check if database exists
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)
    
    # Create enhanced database manager
    try:
        db_manager = EnhancedDatabaseManager(
            db_path=str(db_path),
            pool_config=PoolConfig(min_connections=1, max_connections=3),
            performance_thresholds=PerformanceThresholds(slow_query_ms=100)
        )
        endpoint = DatabaseHealthEndpoint(db_manager)
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)
    
    try:
        if args.command == 'health':
            # Get health status
            status_code, health = endpoint.get_health()
            
            if args.json:
                print(json.dumps(health, indent=2))
            else:
                print(format_health_status(health))
            
            # Exit with appropriate code
            sys.exit(0 if status_code == 200 else 1)
        
        elif args.command == 'metrics':
            # Get metrics
            status_code, metrics = endpoint.get_metrics()
            
            if args.json:
                print(json.dumps(metrics, indent=2, default=str))
            else:
                print(format_metrics(metrics))
        
        elif args.command == 'report':
            # Generate performance report
            report = db_manager.generate_performance_report()
            print(report)
        
        elif args.command == 'optimize':
            # Run optimization
            print("🔧 Running database optimization...")
            results = db_manager.optimize_database()
            
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                print(f"\nOptimization completed at {results['timestamp']}")
                for op in results['operations']:
                    status = "✅" if op['status'] == 'success' else "❌"
                    print(f"{status} {op['operation']}: {op['status']}")
                    if 'deleted_entries' in op:
                        print(f"   Deleted {op['deleted_entries']} expired cache entries")
                    if 'error' in op:
                        print(f"   Error: {op['error']}")
        
        elif args.command == 'monitor':
            # Live monitoring mode
            import time
            import os
            
            print("📊 Live Database Monitoring (Press Ctrl+C to exit)")
            print("=" * 60)
            
            try:
                while True:
                    # Clear screen
                    os.system('clear' if os.name == 'posix' else 'cls')
                    
                    # Get current metrics
                    _, metrics = endpoint.get_metrics()
                    
                    # Display
                    print(format_metrics(metrics))
                    print(f"\nRefreshing in {args.interval} seconds...")
                    
                    time.sleep(args.interval)
                    
            except KeyboardInterrupt:
                print("\n\nMonitoring stopped.")
    
    finally:
        # Cleanup
        db_manager.close()


if __name__ == "__main__":
    main()