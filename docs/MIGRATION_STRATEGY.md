# Migration Strategy: CSV to Database-Based Processing

## Overview

This document outlines the strategy for migrating from CSV-based vocabulary processing to the new database-driven ingress system. The migration is designed to be non-disruptive and allows for gradual transition.

## Migration Phases

### Phase 1: Parallel Operation (Weeks 1-2)
**Goal**: Run both systems side-by-side to validate the new approach

1. **Keep existing CSV workflow operational**
   - Continue using: `flashcard-pipeline process vocabulary.csv`
   - No changes to existing scripts or automation

2. **Test database ingress in parallel**
   ```bash
   # Import test batches
   flashcard-pipeline ingress import test_vocabulary.csv --batch-id test_batch_001
   
   # Process test batches
   flashcard-pipeline process --source database --db-batch-id test_batch_001
   ```

3. **Compare outputs**
   - Verify identical flashcard generation
   - Check performance metrics
   - Validate cache behavior

### Phase 2: Gradual Migration (Weeks 3-4)
**Goal**: Start migrating production workloads

1. **Import historical CSV files**
   ```bash
   # Script to import all existing CSV files
   for csv in data/input/*.csv; do
     flashcard-pipeline ingress import "$csv" --batch-id "import_$(basename $csv .csv)"
   done
   ```

2. **Update automation scripts**
   ```bash
   # Old script
   flashcard-pipeline process $INPUT_CSV --output $OUTPUT_TSV
   
   # New script
   flashcard-pipeline ingress import $INPUT_CSV
   flashcard-pipeline process --source database --output $OUTPUT_TSV
   ```

3. **Monitor and validate**
   - Track processing success rates
   - Monitor performance improvements
   - Collect user feedback

### Phase 3: Full Migration (Week 5)
**Goal**: Complete transition to database-based processing

1. **Update all documentation**
   - README.md examples
   - User guides
   - API documentation

2. **Deprecate CSV direct processing**
   - Add deprecation warnings
   - Update help text
   - Plan removal timeline

3. **Optimize database operations**
   - Add indexes for common queries
   - Implement cleanup jobs
   - Set up monitoring

## Migration Scripts

### 1. Bulk CSV Import Script
```bash
#!/bin/bash
# bulk_import.sh - Import all CSV files to database

IMPORT_DIR="${1:-data/input}"
LOG_FILE="migration_$(date +%Y%m%d_%H%M%S).log"

echo "Starting bulk import from $IMPORT_DIR" | tee -a $LOG_FILE

for csv_file in "$IMPORT_DIR"/*.csv; do
    if [[ -f "$csv_file" ]]; then
        echo "Importing: $csv_file" | tee -a $LOG_FILE
        
        batch_id="migrate_$(basename "$csv_file" .csv)_$(date +%Y%m%d)"
        
        if flashcard-pipeline ingress import "$csv_file" --batch-id "$batch_id" >> $LOG_FILE 2>&1; then
            echo "✓ Success: $csv_file" | tee -a $LOG_FILE
        else
            echo "✗ Failed: $csv_file" | tee -a $LOG_FILE
        fi
    fi
done

echo "Import complete. Check $LOG_FILE for details."
```

### 2. Processing Status Monitor
```bash
#!/bin/bash
# monitor_batches.sh - Monitor batch processing status

while true; do
    clear
    echo "=== Batch Processing Status ==="
    echo "Time: $(date)"
    echo ""
    
    flashcard-pipeline ingress list-batches --limit 10
    
    echo ""
    echo "=== Recent Activity ==="
    tail -n 20 logs/pipeline.log | grep -E "(Imported|Processing|Completed)"
    
    sleep 30
done
```

### 3. Database Maintenance Script
```python
#!/usr/bin/env python3
# maintain_database.py - Database cleanup and optimization

import sqlite3
import os
from datetime import datetime, timedelta

def cleanup_old_batches(db_path, days=30):
    """Remove completed batches older than specified days"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Find old completed batches
    cursor.execute("""
        SELECT id, source_file, completed_at 
        FROM import_batches 
        WHERE status = 'completed' 
        AND completed_at < ?
    """, (cutoff_date.isoformat(),))
    
    old_batches = cursor.fetchall()
    
    for batch_id, source_file, completed_at in old_batches:
        print(f"Removing batch {batch_id} ({source_file}) completed on {completed_at}")
        
        # Delete vocabulary items
        cursor.execute("""
            DELETE FROM vocabulary_items 
            WHERE import_batch_id = ? 
            AND status = 'completed'
        """, (batch_id,))
        
        # Delete batch record
        cursor.execute("DELETE FROM import_batches WHERE id = ?", (batch_id,))
    
    conn.commit()
    
    # Vacuum database
    cursor.execute("VACUUM")
    
    conn.close()
    print(f"Cleanup complete. Removed {len(old_batches)} old batches.")

if __name__ == "__main__":
    db_path = os.getenv("DATABASE_PATH", "pipeline.db")
    cleanup_old_batches(db_path)
```

## Configuration Updates

### Environment Variables
```env
# Add to .env during migration
MIGRATION_MODE=true
ENABLE_CSV_DEPRECATION_WARNING=true
DATABASE_BACKUP_PATH=./backups/pipeline_backup.db
```

### Docker Compose Updates
```yaml
# Add migration service to docker-compose.yml
migration:
  image: korean-flashcard-pipeline:latest
  container_name: flashcard-migration
  volumes:
    - ./data:/app/data
    - ./scripts:/app/scripts
    - ./.env:/app/.env:ro
  command: /app/scripts/bulk_import.sh
  profiles:
    - migration
```

## Rollback Plan

If issues arise during migration:

1. **Immediate Rollback**
   ```bash
   # Stop using database source
   flashcard-pipeline process vocabulary.csv  # Revert to CSV processing
   ```

2. **Data Recovery**
   ```bash
   # Restore database backup
   cp backups/pipeline_backup.db pipeline.db
   
   # Re-import specific batches if needed
   flashcard-pipeline ingress import problem_file.csv --batch-id recovery_batch
   ```

3. **Cache Preservation**
   - Cache remains compatible between both approaches
   - No cache clearing required during rollback

## Success Metrics

Track these metrics to validate migration success:

1. **Performance Metrics**
   - Processing speed (items/second)
   - API call reduction from cache hits
   - Database query performance

2. **Reliability Metrics**
   - Success rate comparison (CSV vs Database)
   - Error recovery effectiveness
   - Batch completion rates

3. **Operational Metrics**
   - Time to process new vocabulary sets
   - Ease of retry for failed items
   - Storage requirements

## Timeline

| Week | Phase | Activities |
|------|-------|-----------|
| 1-2 | Testing | Parallel operation, validation |
| 3-4 | Migration | Gradual workload transition |
| 5 | Completion | Full migration, deprecation |
| 6+ | Optimization | Performance tuning, cleanup |

## FAQ

**Q: Will existing cache still work?**
A: Yes, the cache system remains unchanged and will work with both approaches.

**Q: Can I still use CSV files after migration?**
A: Yes, but they must be imported to the database first using the ingress command.

**Q: What happens to in-progress CSV processing?**
A: Complete any running CSV processes before switching to database mode.

**Q: How do I handle custom CSV formats?**
A: Update the IngressService.import_csv() method to handle your specific format.

## Support

For migration assistance:
1. Check logs in `logs/pipeline.log`
2. Use `flashcard-pipeline ingress status` for batch details
3. Run database integrity checks with SQLite tools
4. Create GitHub issues for migration problems