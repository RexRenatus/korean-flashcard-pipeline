#!/usr/bin/env python3
"""
Database Integrity Checker for the Korean Flashcard Pipeline.
Performs comprehensive schema and data integrity checks.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.python.flashcard_pipeline.utils import get_logger

logger = get_logger("db_integrity_check")


class DatabaseIntegrityChecker:
    """Comprehensive database integrity checker."""
    
    def __init__(self, db_path: str):
        """
        Initialize integrity checker.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = Path(db_path)
        self.issues = []
        self.warnings = []
        self.stats = {}
    
    def check_database_exists(self) -> bool:
        """Check if database file exists."""
        if not self.db_path.exists():
            self.issues.append(f"Database file not found: {self.db_path}")
            return False
        
        if self.db_path.stat().st_size == 0:
            self.issues.append("Database file is empty")
            return False
        
        return True
    
    def check_sqlite_integrity(self) -> bool:
        """Run SQLite built-in integrity check."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                
                if result[0] != "ok":
                    self.issues.append(f"SQLite integrity check failed: {result}")
                    return False
                
                logger.info("SQLite integrity check passed")
                return True
                
        except Exception as e:
            self.issues.append(f"Failed to run integrity check: {e}")
            return False
    
    def check_foreign_keys(self) -> bool:
        """Check foreign key constraints."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Enable foreign keys
                cursor.execute("PRAGMA foreign_keys = ON")
                
                # Check for violations
                cursor.execute("PRAGMA foreign_key_check")
                violations = cursor.fetchall()
                
                if violations:
                    for violation in violations:
                        self.issues.append(f"Foreign key violation: {violation}")
                    return False
                
                logger.info("Foreign key check passed")
                return True
                
        except Exception as e:
            self.issues.append(f"Failed to check foreign keys: {e}")
            return False
    
    def check_schema_structure(self) -> bool:
        """Verify expected tables and columns exist."""
        expected_schema = {
            'vocabulary_master': [
                'id', 'term', 'ipa', 'pos', 'definition', 
                'difficulty_level', 'frequency', 'created_at', 'updated_at'
            ],
            'import_operations': [
                'id', 'batch_id', 'file_name', 'import_type',
                'total_items', 'successful_items', 'failed_items',
                'started_at', 'completed_at', 'status', 'error_details'
            ],
            'processing_tasks': [
                'id', 'vocabulary_id', 'stage', 'status', 'priority',
                'created_at', 'started_at', 'completed_at', 'retry_count',
                'error_message', 'processing_time_ms'
            ],
            'flashcards': [
                'id', 'vocabulary_id', 'task_id', 'card_number',
                'deck_name', 'front_content', 'back_content',
                'pronunciation_guide', 'tags', 'honorific_level',
                'position', 'primer', 'tab_name', 'is_published',
                'created_at', 'updated_at'
            ],
            'cache_entries': [
                'id', 'cache_key', 'created_at', 'accessed_at',
                'access_count', 'cache_size', 'is_compressed'
            ],
            'cache_responses': [
                'cache_id', 'stage', 'tokens_used', 'response_data',
                'response_metadata'
            ]
        }
        
        all_valid = True
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Check each table
                for table_name, expected_columns in expected_schema.items():
                    # Check if table exists
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name=?
                    """, (table_name,))
                    
                    if not cursor.fetchone():
                        self.issues.append(f"Missing table: {table_name}")
                        all_valid = False
                        continue
                    
                    # Get actual columns
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    actual_columns = {row[1] for row in cursor.fetchall()}
                    
                    # Check for missing columns
                    missing_columns = set(expected_columns) - actual_columns
                    if missing_columns:
                        self.issues.append(
                            f"Table {table_name} missing columns: {missing_columns}"
                        )
                        all_valid = False
                    
                    # Warn about extra columns
                    extra_columns = actual_columns - set(expected_columns)
                    if extra_columns:
                        self.warnings.append(
                            f"Table {table_name} has extra columns: {extra_columns}"
                        )
                
                return all_valid
                
        except Exception as e:
            self.issues.append(f"Failed to check schema structure: {e}")
            return False
    
    def check_indexes(self) -> bool:
        """Verify expected indexes exist."""
        expected_indexes = [
            'idx_vocabulary_term',
            'idx_vocabulary_pos',
            'idx_import_batch_id',
            'idx_tasks_vocabulary_id',
            'idx_tasks_status',
            'idx_flashcards_vocabulary_id',
            'idx_flashcards_position',
            'idx_cache_key',
            'idx_cache_accessed'
        ]
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Get all indexes
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name NOT LIKE 'sqlite_%'
                """)
                
                actual_indexes = {row[0] for row in cursor.fetchall()}
                
                # Check for missing indexes
                missing_indexes = set(expected_indexes) - actual_indexes
                if missing_indexes:
                    for idx in missing_indexes:
                        self.warnings.append(f"Missing index: {idx}")
                
                # Report index count
                self.stats['index_count'] = len(actual_indexes)
                logger.info(f"Found {len(actual_indexes)} indexes")
                
                return True
                
        except Exception as e:
            self.issues.append(f"Failed to check indexes: {e}")
            return False
    
    def check_data_consistency(self) -> bool:
        """Check data consistency across tables."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Check orphaned flashcards
                cursor.execute("""
                    SELECT COUNT(*) FROM flashcards f
                    LEFT JOIN vocabulary_master v ON f.vocabulary_id = v.id
                    WHERE v.id IS NULL
                """)
                orphaned_flashcards = cursor.fetchone()[0]
                
                if orphaned_flashcards > 0:
                    self.issues.append(
                        f"Found {orphaned_flashcards} orphaned flashcards"
                    )
                
                # Check orphaned tasks
                cursor.execute("""
                    SELECT COUNT(*) FROM processing_tasks t
                    LEFT JOIN vocabulary_master v ON t.vocabulary_id = v.id
                    WHERE v.id IS NULL
                """)
                orphaned_tasks = cursor.fetchone()[0]
                
                if orphaned_tasks > 0:
                    self.issues.append(
                        f"Found {orphaned_tasks} orphaned processing tasks"
                    )
                
                # Check duplicate vocabulary terms
                cursor.execute("""
                    SELECT term, COUNT(*) as cnt
                    FROM vocabulary_master
                    GROUP BY term
                    HAVING cnt > 1
                """)
                duplicates = cursor.fetchall()
                
                if duplicates:
                    for term, count in duplicates:
                        self.warnings.append(
                            f"Duplicate vocabulary term '{term}' ({count} occurrences)"
                        )
                
                return True
                
        except Exception as e:
            self.issues.append(f"Failed to check data consistency: {e}")
            return False
    
    def collect_statistics(self) -> Dict[str, Any]:
        """Collect database statistics."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Database size
                cursor.execute("""
                    SELECT page_count * page_size 
                    FROM pragma_page_count(), pragma_page_size()
                """)
                self.stats['db_size_bytes'] = cursor.fetchone()[0]
                
                # Table row counts
                tables = [
                    'vocabulary_master', 'import_operations', 'vocabulary_imports',
                    'processing_tasks', 'processing_results', 'flashcards',
                    'cache_entries', 'api_usage_metrics'
                ]
                
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        self.stats[f"{table}_count"] = cursor.fetchone()[0]
                    except:
                        self.stats[f"{table}_count"] = 0
                
                # Cache statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_entries,
                        SUM(cache_size) as total_size,
                        AVG(access_count) as avg_access_count
                    FROM cache_entries
                """)
                cache_stats = cursor.fetchone()
                
                self.stats['cache_entries'] = cache_stats[0] or 0
                self.stats['cache_total_size'] = cache_stats[1] or 0
                self.stats['cache_avg_access'] = cache_stats[2] or 0
                
                # Processing statistics
                cursor.execute("""
                    SELECT 
                        status,
                        COUNT(*) as count,
                        AVG(processing_time_ms) as avg_time
                    FROM processing_tasks
                    GROUP BY status
                """)
                
                self.stats['task_status_breakdown'] = {
                    row[0]: {'count': row[1], 'avg_time_ms': row[2]}
                    for row in cursor.fetchall()
                }
                
                return self.stats
                
        except Exception as e:
            self.issues.append(f"Failed to collect statistics: {e}")
            return self.stats
    
    def generate_report(self) -> str:
        """Generate comprehensive integrity report."""
        report = []
        report.append("=== Database Integrity Check Report ===")
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append(f"Database: {self.db_path}")
        report.append("")
        
        # Summary
        issue_count = len(self.issues)
        warning_count = len(self.warnings)
        
        if issue_count == 0:
            report.append(" Database integrity check PASSED")
        else:
            report.append(f" Database integrity check FAILED ({issue_count} issues)")
        
        report.append(f"Warnings: {warning_count}")
        report.append("")
        
        # Issues
        if self.issues:
            report.append("Critical Issues:")
            for issue in self.issues:
                report.append(f"   {issue}")
            report.append("")
        
        # Warnings
        if self.warnings:
            report.append("Warnings:")
            for warning in self.warnings:
                report.append(f"    {warning}")
            report.append("")
        
        # Statistics
        report.append("Database Statistics:")
        report.append(f"  Size: {self.stats.get('db_size_bytes', 0):,} bytes")
        report.append(f"  Indexes: {self.stats.get('index_count', 0)}")
        report.append("")
        
        report.append("Table Row Counts:")
        for key, value in self.stats.items():
            if key.endswith('_count') and not key.startswith('cache_'):
                table_name = key.replace('_count', '')
                report.append(f"  {table_name}: {value:,}")
        
        report.append("")
        report.append("Cache Statistics:")
        report.append(f"  Entries: {self.stats.get('cache_entries', 0):,}")
        report.append(f"  Total Size: {self.stats.get('cache_total_size', 0):,} bytes")
        report.append(f"  Avg Access Count: {self.stats.get('cache_avg_access', 0):.2f}")
        
        # Task status
        if 'task_status_breakdown' in self.stats:
            report.append("")
            report.append("Task Status Breakdown:")
            for status, info in self.stats['task_status_breakdown'].items():
                avg_time = info['avg_time_ms'] or 0
                report.append(
                    f"  {status}: {info['count']:,} tasks "
                    f"(avg time: {avg_time:.2f}ms)"
                )
        
        return "\n".join(report)
    
    def run_all_checks(self) -> bool:
        """
        Run all integrity checks.
        
        Returns:
            True if all critical checks pass, False otherwise
        """
        checks = [
            ("Database exists", self.check_database_exists),
            ("SQLite integrity", self.check_sqlite_integrity),
            ("Foreign keys", self.check_foreign_keys),
            ("Schema structure", self.check_schema_structure),
            ("Indexes", self.check_indexes),
            ("Data consistency", self.check_data_consistency)
        ]
        
        all_passed = True
        
        for check_name, check_func in checks:
            logger.info(f"Running check: {check_name}")
            
            try:
                if not check_func():
                    all_passed = False
                    logger.error(f"Check failed: {check_name}")
                else:
                    logger.info(f"Check passed: {check_name}")
            except Exception as e:
                logger.error(f"Check {check_name} raised exception: {e}")
                self.issues.append(f"Check {check_name} failed with exception: {e}")
                all_passed = False
        
        # Collect statistics regardless of check results
        self.collect_statistics()
        
        return all_passed and len(self.issues) == 0


def main():
    """Main entry point for integrity checker."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Check database integrity for Korean Flashcard Pipeline"
    )
    parser.add_argument(
        "--db-path",
        default="pipeline.db",
        help="Path to the database file"
    )
    parser.add_argument(
        "--output",
        help="Output file for report (default: print to console)"
    )
    
    args = parser.parse_args()
    
    # Initialize checker
    checker = DatabaseIntegrityChecker(args.db_path)
    
    # Run checks
    logger.info("Starting database integrity check...")
    success = checker.run_all_checks()
    
    # Generate report
    report = checker.generate_report()
    
    # Output report
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        logger.info(f"Report saved to: {args.output}")
    else:
        print("\n" + report)
    
    # Exit with appropriate code
    if success:
        logger.info("All integrity checks passed")
        sys.exit(0)
    else:
        logger.error("Integrity check failed")
        sys.exit(1)


if __name__ == "__main__":
    main()