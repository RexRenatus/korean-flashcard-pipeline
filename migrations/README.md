# Database Migrations

This directory contains SQL migration scripts for evolving the database schema of the flashcard pipeline system.

## Overview

Migrations are versioned SQL scripts that modify the database schema. They allow us to:
- Track schema changes over time
- Deploy updates safely
- Roll back if needed
- Keep all environments in sync

## Migration Files

Current migrations:
- `001_initial_schema.sql` - Initial database setup
- `002_add_ingress_tables.sql` - Import operation tracking
- `003_database_reorganization_phase1.sql` - Schema optimization
- `004_database_reorganization_phase2.sql` - Additional indexes
- `005_database_reorganization_phase3_data_migration.sql` - Data migration
- `006_stage_output_schema_update.sql` - Stage output improvements

## Migration Format

Each migration file follows this structure:

```sql
-- Migration: 001_initial_schema
-- Description: Create initial database schema
-- Author: System
-- Date: 2024-01-01

-- Up Migration (Apply)
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS vocabulary_master (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    korean TEXT NOT NULL,
    english TEXT,
    -- ... more fields
);

-- Add indexes, constraints, etc.

COMMIT;

-- Down Migration (Rollback)
-- BEGIN TRANSACTION;
-- DROP TABLE vocabulary_master;
-- COMMIT;
```

## Running Migrations

### Automatic Migration
```bash
# Run all pending migrations
python scripts/migration_runner.py

# Check migration status
python scripts/migration_runner.py --status
```

### Manual Migration
```bash
# Apply specific migration
sqlite3 pipeline.db < migrations/001_initial_schema.sql

# With transaction safety
sqlite3 pipeline.db "BEGIN; .read migrations/001_initial_schema.sql; COMMIT;"
```

### Migration with Backup
```bash
# Always recommended for production
cp pipeline.db pipeline.db.backup
python scripts/migration_runner.py --backup
```

## Creating New Migrations

### 1. Generate Migration File
```bash
# Use the helper script
python scripts/create_migration.py "Add user preferences table"

# Or create manually
touch migrations/007_add_user_preferences.sql
```

### 2. Write Migration Script
```sql
-- Migration: 007_add_user_preferences
-- Description: Add table for user preferences
-- Author: Your Name
-- Date: 2024-01-10

-- Up Migration
BEGIN TRANSACTION;

CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL UNIQUE,
    theme TEXT DEFAULT 'light',
    language TEXT DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);

COMMIT;

-- Down Migration (commented out for safety)
-- BEGIN TRANSACTION;
-- DROP TABLE user_preferences;
-- COMMIT;
```

### 3. Test Migration
```bash
# Test on copy of database
cp pipeline.db test.db
sqlite3 test.db < migrations/007_add_user_preferences.sql

# Verify schema
sqlite3 test.db ".schema user_preferences"
```

### 4. Document Changes
Update schema documentation and add migration notes.

## Best Practices

### Writing Migrations

1. **Always use transactions** - Ensure atomicity
2. **Make migrations idempotent** - Use `IF NOT EXISTS`
3. **Include rollback scripts** - But comment them out
4. **One change per migration** - Keep them focused
5. **Test thoroughly** - On copy of production data

### Schema Changes

1. **Add columns as nullable** - Then populate, then add constraints
2. **Create indexes after data** - Faster for large tables
3. **Avoid renaming** - Add new, migrate data, drop old
4. **Consider data size** - Large tables need special handling

### Safety Rules

1. **Never modify past migrations** - Create new ones
2. **Always backup first** - Especially in production
3. **Test on real data copy** - Not just empty database
4. **Review before applying** - Have someone check
5. **Monitor after deployment** - Watch for issues

## Migration Strategy

### For New Columns
```sql
-- Step 1: Add nullable column
ALTER TABLE vocabulary_master ADD COLUMN new_field TEXT;

-- Step 2: Populate with default data (separate migration)
UPDATE vocabulary_master SET new_field = 'default' WHERE new_field IS NULL;

-- Step 3: Add constraints (separate migration)
-- SQLite doesn't support adding NOT NULL after creation
```

### For Table Restructuring
```sql
-- Step 1: Create new table
CREATE TABLE vocabulary_master_new (...);

-- Step 2: Copy data
INSERT INTO vocabulary_master_new SELECT ... FROM vocabulary_master;

-- Step 3: Swap tables
ALTER TABLE vocabulary_master RENAME TO vocabulary_master_old;
ALTER TABLE vocabulary_master_new RENAME TO vocabulary_master;

-- Step 4: Drop old table (separate migration after verification)
DROP TABLE vocabulary_master_old;
```

## Troubleshooting

### Migration Failed
1. Check error message
2. Verify database is not locked
3. Ensure migration is idempotent
4. Try running manually to see full error

### Rollback Needed
1. Restore from backup (preferred)
2. Or run down migration if available
3. Fix issue in migration
4. Reapply

### Schema Conflicts
1. Check current schema: `sqlite3 pipeline.db .schema`
2. Compare with expected state
3. Create corrective migration
4. Document the discrepancy

## Migration History

Track applied migrations:
```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Query history:
```sql
SELECT * FROM schema_migrations ORDER BY version;
```

## Related Documentation

- [Database Schema](../docs/architecture/DATABASE_SCHEMA.md)
- [Database Design](../Phase1_Design/DATABASE_DESIGN.md)
- [Migration Runner Script](../scripts/migration_runner.py)