# Database Migration Guide

## Overview

This guide documents the database migration process for the Korean Flashcard Pipeline, including backup procedures, migration execution, and rollback strategies.

## Migration Scripts

The following migration scripts need to be executed in order:

1. **003_database_reorganization_phase1.sql** - Creates new normalized schema
2. **004_database_reorganization_phase2.sql** - Adds performance indexes and views  
3. **005_database_reorganization_phase3_data_migration.sql** - Migrates existing data
4. **006_stage_output_schema_update.sql** - Adds support for structured outputs

## Pre-Migration Checklist

- [ ] Database backup created
- [ ] All migration files present in `/migrations` directory
- [ ] Database is not currently being accessed by other processes
- [ ] Sufficient disk space for backup and temporary data
- [ ] Python environment set up with required dependencies

## Migration Process

### 1. Create Backup

```bash
# Manual backup
python scripts/automated_backup.py

# Or using backup manager directly
python -c "
from src.python.flashcard_pipeline.database import BackupManager
bm = BackupManager('pipeline.db')
backup_path = bm.create_backup('Pre-migration backup')
print(f'Backup created: {backup_path}')
"
```

### 2. Run Migrations

#### Option A: Using Enhanced Migration Runner (Recommended)

```bash
# Dry run to validate migrations
python scripts/migration_runner_v2.py --dry-run

# Execute migrations with automatic backup
python scripts/migration_runner_v2.py
```

#### Option B: Using Simple Migration Runner

```bash
python scripts/run_migrations.py
```

#### Option C: Manual Execution

```bash
# Run each migration individually
sqlite3 pipeline.db < migrations/003_database_reorganization_phase1.sql
sqlite3 pipeline.db < migrations/004_database_reorganization_phase2.sql
sqlite3 pipeline.db < migrations/005_database_reorganization_phase3_data_migration.sql
sqlite3 pipeline.db < migrations/006_stage_output_schema_update.sql
```

### 3. Verify Migration

```bash
# Run integrity check
python scripts/db_integrity_check.py

# Check specific tables
sqlite3 pipeline.db "SELECT COUNT(*) FROM vocabulary_master;"
sqlite3 pipeline.db "SELECT COUNT(*) FROM flashcards;"
sqlite3 pipeline.db "SELECT COUNT(*) FROM processing_tasks;"
```

## Rollback Procedures

### Automatic Rollback

The migration runner automatically creates backups and can restore them if migrations fail:

```python
from src.python.flashcard_pipeline.database import BackupManager

bm = BackupManager('pipeline.db')
# List available backups
backups = bm.list_backups()
for backup in backups:
    print(f"{backup['id']}: {backup['description']} ({backup['timestamp']})")

# Restore specific backup
bm.restore_backup('backup_20250108_120000')
```

### Manual Rollback

```bash
# List backups
ls -la backups/

# Restore from backup
cp backups/backup_20250108_120000.db pipeline.db
```

## Post-Migration Tasks

### 1. Update Application Code

```python
# Update imports to use new database manager
from flashcard_pipeline.database import DatabaseManager

# Initialize with connection pooling
db = DatabaseManager('pipeline.db', pool_size=10)
```

### 2. Update Ingress Service

```python
# Use new IngressServiceV2
from flashcard_pipeline.ingress_v2 import IngressServiceV2

ingress = IngressServiceV2('pipeline.db')
```

### 3. Configure Output Parsers

```python
from flashcard_pipeline.parsers import (
    NuanceOutputParser,
    FlashcardOutputParser,
    OutputValidator
)

# Initialize parsers
validator = OutputValidator()
nuance_parser = NuanceOutputParser(validator)
flashcard_parser = FlashcardOutputParser(validator)
```

## Troubleshooting

### Common Issues

1. **Foreign Key Violations**
   ```sql
   -- Check for violations
   PRAGMA foreign_key_check;
   
   -- Temporarily disable foreign keys
   PRAGMA foreign_keys = OFF;
   ```

2. **Locked Database**
   ```bash
   # Check for locks
   fuser pipeline.db
   
   # Kill processes if needed
   fuser -k pipeline.db
   ```

3. **Insufficient Space**
   ```bash
   # Check available space
   df -h .
   
   # Clean up old backups
   python -c "
   from src.python.flashcard_pipeline.database import BackupManager
   bm = BackupManager('pipeline.db')
   bm.cleanup_old_backups(keep_count=5, keep_days=7)
   "
   ```

### Migration Failed

If migration fails:

1. Check migration report: `cat migration_report.txt`
2. Review error logs
3. Restore from backup
4. Fix identified issues
5. Retry migration

### Performance Issues

After migration:

1. Run VACUUM to optimize database:
   ```sql
   sqlite3 pipeline.db "VACUUM;"
   ```

2. Update statistics:
   ```sql
   sqlite3 pipeline.db "ANALYZE;"
   ```

3. Verify indexes:
   ```bash
   python scripts/db_integrity_check.py
   ```

## Automated Backup Schedule

Set up cron job for automated backups:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /usr/bin/python3 /path/to/scripts/automated_backup.py
```

Or use environment variables:

```bash
export PIPELINE_DB_PATH="/path/to/pipeline.db"
export BACKUP_DIR="/path/to/backups"
export BACKUP_KEEP_COUNT=10
export BACKUP_KEEP_DAYS=30
```

## Migration Metrics

Expected results after successful migration:

- **Database size**: May increase 10-20% due to indexes
- **Query performance**: 5-10x improvement for common queries
- **Data integrity**: Zero foreign key violations
- **Schema version**: 6

## Security Considerations

1. **Backup Encryption**: Consider encrypting backups
2. **Access Control**: Restrict database file permissions
3. **Audit Trail**: Migration creates full audit trail
4. **Data Validation**: All data validated during migration

## Next Steps

After successful migration:

1. Update all application instances
2. Monitor performance metrics
3. Schedule regular backups
4. Plan for future migrations
5. Document any custom modifications

---

For additional support, see:
- [Database Schema V2 Documentation](./DATABASE_SCHEMA_V2.md)
- [Database Reorganization Plan](./architecture/DATABASE_REORGANIZATION_PLAN.md)
- [Implementation Roadmap](./IMPLEMENTATION_ROADMAP.md)