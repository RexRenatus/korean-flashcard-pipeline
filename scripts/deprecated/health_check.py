#!/usr/bin/env python3
"""
Health Check Endpoint for Korean Flashcard Pipeline
Provides comprehensive system health status in JSON format
"""

import json
import os
import sys
import psutil
import sqlite3
import redis
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.python.flashcard_pipeline.database.connection_pool import DatabaseConnectionPool
from src.python.flashcard_pipeline.cache import CacheService
from src.python.flashcard_pipeline.api_client import APIClient


class HealthChecker:
    """Comprehensive health checking for all system components"""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.checks = {
            "status": "unknown",
            "timestamp": self.start_time.isoformat(),
            "checks": {},
            "metrics": {}
        }
    
    def check_database(self) -> Tuple[bool, Dict[str, Any]]:
        """Check database connectivity and health"""
        try:
            db_path = os.getenv("DATABASE_PATH", "/app/data/pipeline.db")
            
            # Check if database file exists
            if not Path(db_path).exists():
                return False, {"error": "Database file not found", "path": db_path}
            
            # Test connection
            conn = sqlite3.connect(db_path, timeout=5)
            cursor = conn.cursor()
            
            # Check tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            table_count = len(tables)
            
            # Get database size
            db_size = Path(db_path).stat().st_size / (1024 * 1024)  # MB
            
            # Check record counts
            counts = {}
            for table in ['words', 'flashcards', 'api_calls']:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cursor.fetchone()[0]
                except:
                    counts[table] = 0
            
            conn.close()
            
            return True, {
                "status": "healthy",
                "tables": table_count,
                "size_mb": round(db_size, 2),
                "record_counts": counts,
                "path": db_path
            }
            
        except Exception as e:
            return False, {"status": "unhealthy", "error": str(e)}
    
    def check_redis(self) -> Tuple[bool, Dict[str, Any]]:
        """Check Redis cache connectivity"""
        try:
            r = redis.Redis(
                host=os.getenv("REDIS_HOST", "redis"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                password=os.getenv("REDIS_PASSWORD"),
                decode_responses=True,
                socket_timeout=5
            )
            
            # Test connection
            r.ping()
            
            # Get info
            info = r.info()
            memory_used_mb = info.get('used_memory', 0) / (1024 * 1024)
            
            # Get key count
            key_count = r.dbsize()
            
            return True, {
                "status": "healthy",
                "version": info.get('redis_version', 'unknown'),
                "memory_used_mb": round(memory_used_mb, 2),
                "key_count": key_count,
                "uptime_seconds": info.get('uptime_in_seconds', 0)
            }
            
        except Exception as e:
            return False, {"status": "unhealthy", "error": str(e)}
    
    def check_api(self) -> Tuple[bool, Dict[str, Any]]:
        """Check API connectivity and rate limits"""
        try:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                return False, {"error": "API key not configured"}
            
            # Check OpenRouter API
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                rate_limit = response.headers.get('X-RateLimit-Limit', 'unknown')
                rate_remaining = response.headers.get('X-RateLimit-Remaining', 'unknown')
                
                return True, {
                    "status": "healthy",
                    "rate_limit": rate_limit,
                    "rate_remaining": rate_remaining,
                    "response_time_ms": round(response.elapsed.total_seconds() * 1000, 2)
                }
            else:
                return False, {
                    "status": "unhealthy",
                    "status_code": response.status_code,
                    "error": response.text
                }
                
        except Exception as e:
            return False, {"status": "unhealthy", "error": str(e)}
    
    def check_disk_space(self) -> Tuple[bool, Dict[str, Any]]:
        """Check available disk space"""
        try:
            disk = psutil.disk_usage('/')
            
            # Warning if less than 10% free
            is_healthy = disk.percent < 90
            
            return is_healthy, {
                "status": "healthy" if is_healthy else "warning",
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": disk.percent
            }
            
        except Exception as e:
            return False, {"status": "unhealthy", "error": str(e)}
    
    def check_memory(self) -> Tuple[bool, Dict[str, Any]]:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            
            # Warning if less than 10% available
            is_healthy = memory.percent < 90
            
            return is_healthy, {
                "status": "healthy" if is_healthy else "warning",
                "total_mb": round(memory.total / (1024**2), 2),
                "available_mb": round(memory.available / (1024**2), 2),
                "percent_used": memory.percent
            }
            
        except Exception as e:
            return False, {"status": "unhealthy", "error": str(e)}
    
    def check_cpu(self) -> Tuple[bool, Dict[str, Any]]:
        """Check CPU usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Warning if over 80% usage
            is_healthy = cpu_percent < 80
            
            return is_healthy, {
                "status": "healthy" if is_healthy else "warning",
                "cores": cpu_count,
                "percent_used": cpu_percent,
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None
            }
            
        except Exception as e:
            return False, {"status": "unhealthy", "error": str(e)}
    
    def check_application_files(self) -> Tuple[bool, Dict[str, Any]]:
        """Check critical application files exist"""
        critical_files = [
            "src/python/flashcard_pipeline/__init__.py",
            "migrations/001_initial_schema.sql",
            "requirements.txt",
            ".env"
        ]
        
        missing_files = []
        for file in critical_files:
            if not Path(file).exists():
                missing_files.append(file)
        
        is_healthy = len(missing_files) == 0
        
        return is_healthy, {
            "status": "healthy" if is_healthy else "unhealthy",
            "missing_files": missing_files,
            "checked_files": len(critical_files)
        }
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and compile results"""
        # Run individual checks
        checks = {
            "database": self.check_database(),
            "redis": self.check_redis(),
            "api": self.check_api(),
            "disk": self.check_disk_space(),
            "memory": self.check_memory(),
            "cpu": self.check_cpu(),
            "files": self.check_application_files()
        }
        
        # Compile results
        all_healthy = True
        for check_name, (is_healthy, details) in checks.items():
            self.checks["checks"][check_name] = details
            if not is_healthy:
                all_healthy = False
        
        # Calculate uptime
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        # Set overall status
        self.checks["status"] = "healthy" if all_healthy else "unhealthy"
        self.checks["metrics"]["uptime_seconds"] = uptime
        self.checks["metrics"]["checks_passed"] = sum(1 for _, (h, _) in checks.items() if h)
        self.checks["metrics"]["checks_total"] = len(checks)
        
        # Add version info
        self.checks["version"] = self._get_version()
        
        return self.checks
    
    def _get_version(self) -> str:
        """Get application version"""
        version_file = Path("VERSION.txt")
        if version_file.exists():
            return version_file.read_text().strip()
        return "unknown"


def main():
    """Main health check entry point"""
    checker = HealthChecker()
    results = checker.run_all_checks()
    
    # Output JSON
    print(json.dumps(results, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if results["status"] == "healthy" else 1)


if __name__ == "__main__":
    main()