#!/usr/bin/env python3
"""
Unified Database Health Check Tool
Combines functionality from db_health_check.py and db_integrity_check.py
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
import sqlite3
import json
from datetime import datetime, timedelta
from tabulate import tabulate

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.python.flashcard_pipeline.database import DatabaseManager
from src.python.flashcard_pipeline.utils import setup_logging, get_logger

logger = get_logger(__name__)


class DatabaseHealthChecker:
    """Comprehensive database health and integrity checker"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_manager = DatabaseManager(db_path)
        self.issues = []
    
    def check_all(self) -> Dict[str, Any]:
        """Run all health checks"""
        logger.info("Starting comprehensive database health check...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "database": str(self.db_path),
            "checks": {}
        }
        
        # Run all checks
        results["checks"]["connection"] = self._check_connection()
        results["checks"]["schema"] = self._check_schema()
        results["checks"]["integrity"] = self._check_integrity()
        results["checks"]["performance"] = self._check_performance()
        results["checks"]["statistics"] = self._get_statistics()
        results["checks"]["data_quality"] = self._check_data_quality()
        
        # Overall health status
        results["overall_status"] = "healthy" if not self.issues else "unhealthy"
        results["issues"] = self.issues
        
        return results
    
    def _check_connection(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("SELECT sqlite_version()")
                version = cursor.fetchone()[0]
                return {
                    "status": "ok",
                    "sqlite_version": version,
                    "file_size": self.db_path.stat().st_size
                }
        except Exception as e:
            self.issues.append(f"Connection check failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _check_schema(self) -> Dict[str, Any]:
        """Verify database schema integrity"""
        expected_tables = [
            "vocabulary",
            "processing_tasks",
            "flashcards",
            "stage_outputs",
            "processing_results",
            "ingress_batches",
            "ingress_items"
        ]
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """)
                actual_tables = [row[0] for row in cursor]
                
                missing_tables = set(expected_tables) - set(actual_tables)
                extra_tables = set(actual_tables) - set(expected_tables)
                
                if missing_tables:
                    self.issues.append(f"Missing tables: {missing_tables}")
                
                return {
                    "status": "ok" if not missing_tables else "warning",
                    "expected_tables": len(expected_tables),
                    "actual_tables": len(actual_tables),
                    "missing": list(missing_tables),
                    "extra": list(extra_tables)
                }
        except Exception as e:
            self.issues.append(f"Schema check failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _check_integrity(self) -> Dict[str, Any]:
        """Check referential integrity and constraints"""
        integrity_checks = {
            "foreign_keys": self._check_foreign_keys(),
            "orphaned_records": self._check_orphaned_records(),
            "duplicate_checks": self._check_duplicates()
        }
        
        return integrity_checks
    
    def _check_foreign_keys(self) -> Dict[str, Any]:
        """Verify foreign key constraints"""
        try:
            with self.db_manager.get_connection() as conn:
                # Check foreign key setting
                cursor = conn.execute("PRAGMA foreign_keys")
                fk_enabled = cursor.fetchone()[0]
                
                # Run foreign key check
                cursor = conn.execute("PRAGMA foreign_key_check")
                violations = cursor.fetchall()
                
                if violations:
                    self.issues.append(f"Foreign key violations: {len(violations)}")
                
                return {
                    "enabled": bool(fk_enabled),
                    "violations": len(violations),
                    "status": "ok" if not violations else "error"
                }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _check_orphaned_records(self) -> Dict[str, Any]:
        """Check for orphaned records"""
        orphans = {}
        
        try:
            with self.db_manager.get_connection() as conn:
                # Check orphaned processing tasks
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM processing_tasks pt
                    LEFT JOIN vocabulary v ON pt.vocabulary_id = v.id
                    WHERE v.id IS NULL
                """)
                orphans["processing_tasks"] = cursor.fetchone()[0]
                
                # Check orphaned flashcards
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM flashcards f
                    LEFT JOIN vocabulary v ON f.vocabulary_id = v.id
                    WHERE v.id IS NULL
                """)
                orphans["flashcards"] = cursor.fetchone()[0]
                
                total_orphans = sum(orphans.values())
                if total_orphans > 0:
                    self.issues.append(f"Found {total_orphans} orphaned records")
                
                return {
                    "status": "ok" if total_orphans == 0 else "warning",
                    "orphaned_records": orphans,
                    "total": total_orphans
                }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _check_duplicates(self) -> Dict[str, Any]:
        """Check for duplicate records"""
        duplicates = {}
        
        try:
            with self.db_manager.get_connection() as conn:
                # Check duplicate vocabulary terms
                cursor = conn.execute("""
                    SELECT term, COUNT(*) as count
                    FROM vocabulary
                    GROUP BY term
                    HAVING count > 1
                """)
                dup_terms = cursor.fetchall()
                duplicates["vocabulary_terms"] = len(dup_terms)
                
                if dup_terms:
                    self.issues.append(f"Found {len(dup_terms)} duplicate vocabulary terms")
                
                return {
                    "status": "ok" if not dup_terms else "warning",
                    "duplicates": duplicates
                }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _check_performance(self) -> Dict[str, Any]:
        """Check database performance metrics"""
        metrics = {}
        
        try:
            with self.db_manager.get_connection() as conn:
                # Check page stats
                cursor = conn.execute("PRAGMA page_count")
                metrics["page_count"] = cursor.fetchone()[0]
                
                cursor = conn.execute("PRAGMA page_size")
                metrics["page_size"] = cursor.fetchone()[0]
                
                # Check cache stats
                cursor = conn.execute("PRAGMA cache_size")
                metrics["cache_size"] = cursor.fetchone()[0]
                
                # Check auto vacuum
                cursor = conn.execute("PRAGMA auto_vacuum")
                metrics["auto_vacuum"] = cursor.fetchone()[0]
                
                # Calculate database size
                metrics["total_size_mb"] = (metrics["page_count"] * metrics["page_size"]) / (1024 * 1024)
                
                return {
                    "status": "ok",
                    "metrics": metrics
                }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _check_data_quality(self) -> Dict[str, Any]:
        """Check data quality issues"""
        quality_checks = {}
        
        try:
            with self.db_manager.get_connection() as conn:
                # Check for null/empty critical fields
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM vocabulary
                    WHERE term IS NULL OR term = ''
                """)
                quality_checks["empty_terms"] = cursor.fetchone()[0]
                
                # Check for stuck processing tasks
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM processing_tasks
                    WHERE status = 'processing'
                    AND updated_at < datetime('now', '-1 hour')
                """)
                quality_checks["stuck_tasks"] = cursor.fetchone()[0]
                
                # Check for old pending tasks
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM processing_tasks
                    WHERE status = 'pending'
                    AND created_at < datetime('now', '-7 days')
                """)
                quality_checks["old_pending_tasks"] = cursor.fetchone()[0]
                
                issues_found = sum(1 for v in quality_checks.values() if v > 0)
                if issues_found > 0:
                    self.issues.append(f"Data quality issues found: {issues_found}")
                
                return {
                    "status": "ok" if issues_found == 0 else "warning",
                    "checks": quality_checks
                }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}
        
        try:
            with self.db_manager.get_connection() as conn:
                # Table row counts
                for table in ["vocabulary", "processing_tasks", "flashcards"]:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = cursor.fetchone()[0]
                
                # Task statistics
                cursor = conn.execute("""
                    SELECT status, COUNT(*) as count
                    FROM processing_tasks
                    GROUP BY status
                """)
                stats["task_status"] = {row[0]: row[1] for row in cursor}
                
                # Recent activity
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM vocabulary
                    WHERE created_at > datetime('now', '-24 hours')
                """)
                stats["new_vocabulary_24h"] = cursor.fetchone()[0]
                
                return {
                    "status": "ok",
                    "statistics": stats
                }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def print_report(self, results: Dict[str, Any], format: str = "table"):
        """Print health check report"""
        if format == "json":
            print(json.dumps(results, indent=2))
            return
        
        # Print header
        print("\n" + "="*60)
        print(f"DATABASE HEALTH REPORT")
        print(f"Database: {results['database']}")
        print(f"Timestamp: {results['timestamp']}")
        print(f"Overall Status: {results['overall_status'].upper()}")
        print("="*60 + "\n")
        
        # Print check results
        for check_name, check_result in results["checks"].items():
            print(f"\n{check_name.upper().replace('_', ' ')}:")
            print("-" * 40)
            
            if isinstance(check_result, dict):
                self._print_dict_as_table(check_result)
            else:
                print(check_result)
        
        # Print issues if any
        if results["issues"]:
            print("\n\nISSUES FOUND:")
            print("-" * 40)
            for i, issue in enumerate(results["issues"], 1):
                print(f"{i}. {issue}")
    
    def _print_dict_as_table(self, data: Dict[str, Any], indent: int = 0):
        """Print dictionary as formatted table"""
        items = []
        for key, value in data.items():
            if isinstance(value, dict):
                items.append([key, ""])
                for sub_key, sub_value in value.items():
                    items.append([f"  {sub_key}", str(sub_value)])
            else:
                items.append([key, str(value)])
        
        if items:
            print(tabulate(items, headers=["Property", "Value"], tablefmt="simple"))


def main():
    parser = argparse.ArgumentParser(
        description="Database Health Check Tool - Comprehensive database analysis"
    )
    parser.add_argument(
        "database",
        nargs="?",
        default="flashcard_pipeline.db",
        help="Path to database file (default: flashcard_pipeline.db)"
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)"
    )
    parser.add_argument(
        "--check",
        choices=["all", "connection", "schema", "integrity", "performance", "quality"],
        default="all",
        help="Specific check to run (default: all)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix issues found (use with caution)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(verbose=args.verbose)
    
    # Run health check
    db_path = Path(args.database)
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return 1
    
    checker = DatabaseHealthChecker(db_path)
    
    try:
        if args.check == "all":
            results = checker.check_all()
        else:
            # Run specific check
            check_method = getattr(checker, f"_check_{args.check}")
            results = {
                "timestamp": datetime.now().isoformat(),
                "database": str(db_path),
                "checks": {args.check: check_method()},
                "overall_status": "healthy" if not checker.issues else "unhealthy",
                "issues": checker.issues
            }
        
        # Print report
        checker.print_report(results, format=args.format)
        
        # Return appropriate exit code
        return 0 if results["overall_status"] == "healthy" else 1
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())