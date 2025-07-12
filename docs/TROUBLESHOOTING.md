# Troubleshooting Guide - Korean Language Flashcard Pipeline

## Table of Contents
1. [Common Errors](#common-errors)
2. [Installation Issues](#installation-issues)
3. [API Errors](#api-errors)
4. [Database Issues](#database-issues)
5. [Performance Problems](#performance-problems)
6. [Export Issues](#export-issues)
7. [Debug Techniques](#debug-techniques)
8. [Log Analysis](#log-analysis)
9. [Performance Optimization](#performance-optimization)
10. [Support Channels](#support-channels)

## Common Errors

### Error: "OpenRouter API key not found"

**Symptoms:**
```
Error: OpenRouter API key not found. Please set OPENROUTER_API_KEY environment variable.
```

**Solutions:**

1. **Check .env file exists:**
   ```bash
   ls -la | grep .env
   # Should show: .env
   ```

2. **Verify .env content:**
   ```bash
   cat .env
   # Should contain: OPENROUTER_API_KEY=sk-or-v1-xxxxx
   ```

3. **Check for spaces:**
   ```bash
   # Bad: OPENROUTER_API_KEY = sk-or-v1-xxxxx
   # Good: OPENROUTER_API_KEY=sk-or-v1-xxxxx
   ```

4. **Reload environment:**
   ```bash
   # Deactivate and reactivate virtual environment
   deactivate
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```

5. **Set directly in terminal:**
   ```bash
   export OPENROUTER_API_KEY=sk-or-v1-xxxxx
   python -m flashcard_pipeline.cli process-word "test"
   ```

### Error: "Database is locked"

**Symptoms:**
```
sqlite3.OperationalError: database is locked
```

**Solutions:**

1. **Check for other processes:**
   ```bash
   # Linux/Mac
   lsof | grep pipeline.db
   
   # Windows
   handle pipeline.db
   ```

2. **Kill stuck processes:**
   ```bash
   # Find process ID from above command
   kill -9 <PID>
   ```

3. **Use database unlock command:**
   ```bash
   python -m flashcard_pipeline.cli db unlock
   ```

4. **Enable WAL mode:**
   ```bash
   sqlite3 pipeline.db "PRAGMA journal_mode=WAL;"
   ```

5. **Increase timeout:**
   ```python
   # In config.yaml
   database:
     timeout: 30  # Increase from default 5
   ```

### Error: "Rate limit exceeded"

**Symptoms:**
```
RateLimitError: Rate limit exceeded. Please retry after 60 seconds.
```

**Solutions:**

1. **Check current rate limit:**
   ```bash
   python -m flashcard_pipeline.cli status --rate-limit
   ```

2. **Reduce request rate:**
   ```yaml
   # In config.yaml
   processing:
     rate_limit: 30  # Reduce from 60
     batch_size: 5   # Reduce from 10
   ```

3. **Enable caching:**
   ```bash
   # Check cache is enabled
   python -m flashcard_pipeline.cli cache status
   ```

4. **Use batch processing with delays:**
   ```python
   # Custom script with delays
   import time
   from flashcard_pipeline import Pipeline
   
   pipeline = Pipeline()
   for word in words:
       pipeline.process_word(word)
       time.sleep(2)  # 2 second delay
   ```

### Error: "Connection timeout"

**Symptoms:**
```
TimeoutError: API request timed out after 30 seconds
```

**Solutions:**

1. **Increase timeout:**
   ```yaml
   # In config.yaml
   api:
     timeout: 60  # Increase from 30
   ```

2. **Check internet connection:**
   ```bash
   # Test API connectivity
   curl -I https://openrouter.ai/api/v1
   ```

3. **Use retry logic:**
   ```bash
   python -m flashcard_pipeline.cli process-word "test" --retries 5
   ```

4. **Check proxy settings:**
   ```bash
   # If behind proxy
   export HTTP_PROXY=http://proxy.company.com:8080
   export HTTPS_PROXY=http://proxy.company.com:8080
   ```

## Installation Issues

### Python Version Errors

**Problem:** `This version of flashcard-pipeline requires Python >=3.8`

**Solution:**
```bash
# Check Python version
python --version

# Install Python 3.8+ if needed
# Ubuntu/Debian
sudo apt update
sudo apt install python3.8

# macOS (with Homebrew)
brew install python@3.8

# Windows
# Download from python.org
```

### Dependency Conflicts

**Problem:** `ERROR: pip's dependency resolver does not currently take into account all the packages that are installed`

**Solution:**
```bash
# Create fresh virtual environment
python -m venv venv_fresh
source venv_fresh/bin/activate  # or venv_fresh\Scripts\activate

# Install with no cache
pip install --no-cache-dir -r requirements.txt

# Or use constraints file
pip install -c constraints.txt -r requirements.txt
```

### Missing System Dependencies

**Problem:** `error: Microsoft Visual C++ 14.0 is required` (Windows)

**Solution:**
1. Install Visual Studio Build Tools
2. Or install pre-compiled wheels:
   ```bash
   pip install --only-binary :all: -r requirements.txt
   ```

**Problem:** `fatal error: Python.h: No such file or directory` (Linux)

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev

# CentOS/RHEL
sudo yum install python3-devel
```

## API Errors

### Invalid API Key

**Symptoms:**
```json
{
  "error": {
    "code": "INVALID_API_KEY",
    "message": "Invalid or expired API key"
  }
}
```

**Debug Steps:**

1. **Verify API key format:**
   ```python
   # Should start with sk-or-v1-
   print(os.environ.get('OPENROUTER_API_KEY'))
   ```

2. **Test API key directly:**
   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" \
        https://openrouter.ai/api/v1/models
   ```

3. **Check key permissions:**
   - Log into OpenRouter dashboard
   - Verify key is active
   - Check rate limits

### Model Not Available

**Symptoms:**
```
Error: Model 'claude-3-sonnet' is not available
```

**Solutions:**

1. **List available models:**
   ```bash
   python -m flashcard_pipeline.cli models list
   ```

2. **Update model configuration:**
   ```yaml
   # In config.yaml
   models:
     flashcard_creator: "anthropic/claude-2"  # Use available model
     nuance_creator: "anthropic/claude-2"
   ```

3. **Check model permissions:**
   - Some models require special access
   - Contact OpenRouter support

### Malformed Response

**Symptoms:**
```
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Debug Steps:**

1. **Enable debug logging:**
   ```bash
   export LOG_LEVEL=DEBUG
   python -m flashcard_pipeline.cli process-word "test" --debug
   ```

2. **Check raw response:**
   ```python
   # Add to debug script
   import logging
   logging.basicConfig(level=logging.DEBUG)
   
   # Will show raw API responses
   ```

3. **Verify API endpoint:**
   ```yaml
   # In config.yaml
   api:
     base_url: "https://openrouter.ai/api/v1"  # Ensure correct
   ```

## Database Issues

### Corrupted Database

**Symptoms:**
```
DatabaseError: database disk image is malformed
```

**Recovery Steps:**

1. **Attempt repair:**
   ```bash
   # Backup first
   cp pipeline.db pipeline.db.backup
   
   # Try to recover
   sqlite3 pipeline.db ".recover" | sqlite3 pipeline_recovered.db
   ```

2. **Export what's readable:**
   ```bash
   sqlite3 pipeline.db .dump > dump.sql
   sqlite3 pipeline_new.db < dump.sql
   ```

3. **Use integrity check:**
   ```bash
   python -m flashcard_pipeline.cli db check --repair
   ```

4. **Restore from backup:**
   ```bash
   python -m flashcard_pipeline.cli db restore --input backups/latest.db
   ```

### Migration Failures

**Problem:** `Migration 003_add_indexes.sql failed`

**Solution:**

1. **Check current schema:**
   ```bash
   sqlite3 pipeline.db .schema
   ```

2. **Run migrations manually:**
   ```bash
   sqlite3 pipeline.db < migrations/003_add_indexes.sql
   ```

3. **Skip failed migration:**
   ```bash
   python -m flashcard_pipeline.cli db migrate --skip 003
   ```

4. **Reset migrations:**
   ```bash
   python -m flashcard_pipeline.cli db reset-migrations
   ```

### Query Performance

**Problem:** Slow database queries

**Optimization:**

1. **Add indexes:**
   ```sql
   CREATE INDEX idx_flashcards_created ON flashcards(created_at);
   CREATE INDEX idx_flashcards_word ON flashcards(word);
   ```

2. **Vacuum database:**
   ```bash
   python -m flashcard_pipeline.cli db vacuum
   ```

3. **Analyze tables:**
   ```bash
   python -m flashcard_pipeline.cli db analyze
   ```

4. **Check query plan:**
   ```sql
   EXPLAIN QUERY PLAN SELECT * FROM flashcards WHERE word = '안녕';
   ```

## Performance Problems

### High Memory Usage

**Symptoms:**
- Process using >1GB RAM
- System becomes unresponsive
- `MemoryError` exceptions

**Solutions:**

1. **Process in smaller batches:**
   ```python
   # Instead of loading all at once
   for chunk in read_csv_chunks('large.csv', chunk_size=100):
       process_chunk(chunk)
   ```

2. **Enable streaming mode:**
   ```bash
   python -m flashcard_pipeline.cli process-csv large.csv --stream
   ```

3. **Clear cache periodically:**
   ```python
   # In processing loop
   if processed_count % 1000 == 0:
       cache.clear_old_entries()
   ```

4. **Monitor memory usage:**
   ```bash
   # Linux/Mac
   python -m memory_profiler flashcard_pipeline.cli process-csv large.csv
   
   # Or use built-in monitoring
   python -m flashcard_pipeline.cli process-csv large.csv --monitor-memory
   ```

### Slow Processing

**Symptoms:**
- Processing takes >5 seconds per word
- Batch processing extremely slow

**Optimization:**

1. **Enable parallel processing:**
   ```bash
   python -m flashcard_pipeline.cli process-csv words.csv --parallel --workers 4
   ```

2. **Optimize API calls:**
   ```yaml
   # In config.yaml
   processing:
     batch_size: 20      # Process more at once
     prefetch: true      # Prefetch next batch
     compression: true   # Compress API payloads
   ```

3. **Use connection pooling:**
   ```yaml
   database:
     pool_size: 10
     pool_pre_ping: true
   ```

4. **Profile performance:**
   ```bash
   python -m cProfile -s cumulative flashcard_pipeline.cli process-word "test"
   ```

### Cache Misses

**Problem:** Cache not improving performance

**Debug:**

1. **Check cache statistics:**
   ```bash
   python -m flashcard_pipeline.cli cache stats
   ```

2. **Verify cache is working:**
   ```bash
   # Process same word twice
   time python -m flashcard_pipeline.cli process-word "안녕"
   time python -m flashcard_pipeline.cli process-word "안녕"
   # Second should be much faster
   ```

3. **Increase cache size:**
   ```yaml
   cache:
     max_size: 10000  # Increase from default
     ttl: 2592000     # 30 days
   ```

## Export Issues

### Anki Import Failures

**Problem:** "Invalid file format" when importing to Anki

**Solutions:**

1. **Verify export format:**
   ```bash
   # Check file is valid zip
   file flashcards.apkg
   
   # Extract and check contents
   unzip -l flashcards.apkg
   ```

2. **Use compatible note type:**
   ```bash
   python -m flashcard_pipeline.cli export anki \
     --note-type "Basic" \
     --deck-name "Korean Vocab"
   ```

3. **Check for special characters:**
   ```python
   # Remove problematic characters
   def clean_for_anki(text):
       return text.replace('\x00', '').replace('\x1f', '')
   ```

### CSV Encoding Issues

**Problem:** Korean characters appear as ??? in CSV

**Solutions:**

1. **Specify UTF-8 encoding:**
   ```bash
   python -m flashcard_pipeline.cli export csv \
     --output flashcards.csv \
     --encoding utf-8-sig  # For Excel compatibility
   ```

2. **Open correctly in Excel:**
   - Don't double-click CSV
   - Use Data > From Text
   - Select UTF-8 encoding

3. **Convert encoding if needed:**
   ```bash
   iconv -f UTF-8 -t UTF-16LE flashcards.csv > flashcards_utf16.csv
   ```

## Debug Techniques

### Enable Verbose Logging

```bash
# Maximum verbosity
export LOG_LEVEL=DEBUG
export FLASHCARD_DEBUG=1

python -m flashcard_pipeline.cli process-word "test" -vvv
```

### API Request Debugging

```python
# debug_api.py
import logging
import http.client as http_client

# Enable HTTP debugging
http_client.HTTPConnection.debuglevel = 1

# Configure logging
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

# Now run your code
from flashcard_pipeline import FlashcardClient
client = FlashcardClient(api_key="YOUR_KEY")
client.process_word("test")
```

### Database Query Logging

```python
# Enable SQL logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Or in config
database:
  echo: true  # Log all SQL
```

### Memory Profiling

```bash
# Install memory profiler
pip install memory_profiler

# Run with profiling
python -m memory_profiler example.py

# Or use decorator
@profile
def process_large_batch():
    # Your code
```

### Performance Profiling

```bash
# CPU profiling
python -m cProfile -o profile.stats script.py
python -m pstats profile.stats

# Line-by-line profiling
pip install line_profiler
kernprof -l -v script.py
```

## Log Analysis

### Log Locations

```
logs/
├── app.log          # Main application log
├── api.log          # API requests/responses
├── error.log        # Errors only
└── performance.log  # Performance metrics
```

### Common Log Patterns

1. **Find all errors:**
   ```bash
   grep ERROR logs/app.log | less
   ```

2. **Count errors by type:**
   ```bash
   grep ERROR logs/app.log | cut -d' ' -f5- | sort | uniq -c | sort -nr
   ```

3. **Find slow queries:**
   ```bash
   grep "duration:" logs/performance.log | awk '$NF > 1000' 
   ```

4. **Track request rate:**
   ```bash
   grep "POST /api/v1/flashcards" logs/api.log | \
     awk '{print $1}' | \
     cut -d'T' -f1 | \
     uniq -c
   ```

### Log Parsing Script

```python
#!/usr/bin/env python
# parse_logs.py
import re
from collections import Counter
from datetime import datetime

def analyze_logs(log_file):
    errors = Counter()
    response_times = []
    
    with open(log_file, 'r') as f:
        for line in f:
            # Count errors
            if 'ERROR' in line:
                match = re.search(r'ERROR - (.+?):', line)
                if match:
                    errors[match.group(1)] += 1
            
            # Extract response times
            match = re.search(r'duration: (\d+)ms', line)
            if match:
                response_times.append(int(match.group(1)))
    
    # Report
    print("Top Errors:")
    for error, count in errors.most_common(10):
        print(f"  {error}: {count}")
    
    if response_times:
        print(f"\nResponse Times:")
        print(f"  Average: {sum(response_times)/len(response_times):.2f}ms")
        print(f"  Max: {max(response_times)}ms")
        print(f"  Min: {min(response_times)}ms")

if __name__ == "__main__":
    analyze_logs('logs/app.log')
```

## Performance Optimization

### Database Optimization

1. **Enable Write-Ahead Logging:**
   ```sql
   PRAGMA journal_mode=WAL;
   PRAGMA synchronous=NORMAL;
   ```

2. **Optimize indexes:**
   ```sql
   -- Check unused indexes
   SELECT name FROM sqlite_master 
   WHERE type='index' 
   AND name NOT IN (
     SELECT DISTINCT idx FROM sqlite_stat1
   );
   ```

3. **Batch operations:**
   ```python
   # Instead of individual inserts
   with db.transaction():
       for flashcard in flashcards:
           db.insert(flashcard)
   ```

### API Optimization

1. **Request compression:**
   ```python
   # Enable gzip compression
   headers = {'Content-Encoding': 'gzip'}
   compressed_data = gzip.compress(json_data.encode())
   ```

2. **Connection pooling:**
   ```python
   # Reuse connections
   session = requests.Session()
   adapter = HTTPAdapter(
       pool_connections=10,
       pool_maxsize=10,
       max_retries=3
   )
   session.mount('https://', adapter)
   ```

3. **Async processing:**
   ```python
   import asyncio
   import aiohttp
   
   async def process_words_async(words):
       async with aiohttp.ClientSession() as session:
           tasks = [process_word(session, word) for word in words]
           return await asyncio.gather(*tasks)
   ```

### Caching Optimization

1. **Warm cache on startup:**
   ```bash
   python -m flashcard_pipeline.cli cache warm --common-words
   ```

2. **Use tiered caching:**
   ```python
   # L1: In-memory (fast, small)
   memory_cache = LRUCache(maxsize=100)
   
   # L2: Redis (medium, larger)
   redis_cache = RedisCache(ttl=3600)
   
   # L3: Database (slow, permanent)
   db_cache = DatabaseCache()
   ```

3. **Cache preloading:**
   ```python
   # Preload frequently used words
   common_words = load_common_words()
   for word in common_words:
       cache.preload(word)
   ```

## Support Channels

### Self-Service Resources

1. **Documentation:**
   - User Guide: [/docs/USER_GUIDE.md](USER_GUIDE.md)
   - API Reference: [/docs/API_REFERENCE.md](API_REFERENCE.md)
   - FAQ: [/docs/FAQ.md](FAQ.md)

2. **Community:**
   - Discord: [discord.gg/flashcards](https://discord.gg/flashcards)
   - Reddit: [r/KoreanFlashcards](https://reddit.com/r/KoreanFlashcards)
   - Stack Overflow: Tag `korean-flashcard-pipeline`

### Getting Help

1. **Before asking for help:**
   - Search existing issues
   - Check documentation
   - Try debug techniques
   - Prepare minimal example

2. **Information to provide:**
   ```markdown
   ## Environment
   - OS: [e.g., Ubuntu 20.04]
   - Python version: [e.g., 3.8.10]
   - Package version: [e.g., 1.0.0]
   
   ## Issue Description
   [Clear description of the problem]
   
   ## Steps to Reproduce
   1. [First step]
   2. [Second step]
   
   ## Expected Behavior
   [What should happen]
   
   ## Actual Behavior
   [What actually happens]
   
   ## Error Output
   ```
   [Full error message]
   ```
   
   ## Debug Information
   - Log level: DEBUG
   - Config file: [attached]
   - Sample data: [attached]
   ```

### Professional Support

- **Email:** support@flashcardpipeline.com
- **Response time:** 24-48 hours
- **Priority support:** Available for Pro/Enterprise plans

### Bug Reports

File issues at: [github.com/yourusername/korean-flashcard-pipeline/issues](https://github.com/yourusername/korean-flashcard-pipeline/issues)

Template:
```markdown
**Bug Description**
A clear description of the bug

**Version**
- flashcard-pipeline version: X.Y.Z
- Python version: X.Y.Z
- OS: [e.g. Ubuntu 20.04]

**Reproduction Steps**
1. Step one
2. Step two
3. ...

**Expected vs Actual**
- Expected: [what should happen]
- Actual: [what happens]

**Logs**
```
[Relevant log output]
```

**Additional Context**
Any other relevant information
```

Remember: The more information you provide, the faster we can help!