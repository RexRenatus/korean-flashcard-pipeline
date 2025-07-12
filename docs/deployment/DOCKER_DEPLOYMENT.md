# 🐳 Docker Deployment Guide

This guide covers production-quality Docker deployment for personal use of the Korean Flashcard Pipeline.

## 📋 Prerequisites

- Docker Engine 20.10+ 
- Docker Compose 2.0+
- At least 4GB RAM available
- 10GB free disk space
- OpenRouter API key

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/korean-flashcard-pipeline.git
cd korean-flashcard-pipeline

# Copy environment template
cp .env.production.template .env.production

# Edit .env.production with your API key
nano .env.production
```

### 2. Build Production Image

```bash
# Build the optimized production image
docker build -f Dockerfile.production -t korean-flashcard-pipeline:production .

# Verify the build
docker images | grep korean-flashcard-pipeline
```

### 3. Start Services

```bash
# Start core services (pipeline, redis, monitor, backup)
docker-compose -f docker-compose.personal.yml up -d

# Check service status
docker-compose -f docker-compose.personal.yml ps

# View logs
docker-compose -f docker-compose.personal.yml logs -f flashcard-pipeline
```

## 📦 Service Architecture

### Core Services (Always Running)

1. **flashcard-pipeline**: Main application service
   - Handles all CLI commands
   - Manages database operations
   - Processes vocabulary files

2. **redis**: High-performance cache
   - Reduces API calls
   - Improves response times
   - Persistent data storage

3. **monitor**: Real-time monitoring
   - Tracks processing metrics
   - Exports statistics
   - Performance monitoring

4. **backup**: Automated backup service
   - Daily database backups
   - Cache exports
   - 7-day retention

### Optional Services (Profiles)

Enable with: `docker-compose -f docker-compose.personal.yml --profile <profile> up -d`

- **automation**: Directory watcher and scheduler
- **maintenance**: Database optimization
- **monitoring**: Advanced health monitoring

## 🎯 Common Usage Patterns

### Process Vocabulary Files

```bash
# Single file processing
docker-compose -f docker-compose.personal.yml run --rm flashcard-pipeline \
  python -m flashcard_pipeline process /app/data/input/vocabulary.csv \
  --concurrent 20 --output /app/data/output/results.tsv

# Batch processing with resume support
docker-compose -f docker-compose.personal.yml run --rm flashcard-pipeline \
  python -m flashcard_pipeline process /app/data/input/large_vocab.csv \
  --concurrent 50 --batch-id "korean_5000_words" --resume
```

### Import and Export

```bash
# Import CSV data
docker-compose -f docker-compose.personal.yml run --rm flashcard-pipeline \
  python -m flashcard_pipeline import csv /app/data/input/new_words.csv

# Export to Anki
docker-compose -f docker-compose.personal.yml run --rm flashcard-pipeline \
  python -m flashcard_pipeline export anki /app/exports/korean_deck.apkg \
  --filter "confidence >= 0.85"
```

### Database Operations

```bash
# Check database stats
docker-compose -f docker-compose.personal.yml run --rm flashcard-pipeline \
  python -m flashcard_pipeline db stats

# Manual backup
docker-compose -f docker-compose.personal.yml run --rm flashcard-pipeline \
  python -m flashcard_pipeline db backup /app/backup/manual_backup.db
```

### Cache Management

```bash
# View cache statistics
docker-compose -f docker-compose.personal.yml run --rm flashcard-pipeline \
  python -m flashcard_pipeline cache stats

# Clear cache if needed
docker-compose -f docker-compose.personal.yml run --rm flashcard-pipeline \
  python -m flashcard_pipeline cache clear --yes
```

## 🔧 Advanced Configuration

### Resource Limits

Edit `docker-compose.personal.yml` to adjust resources:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'      # Increase for faster processing
      memory: 4G     # Increase for larger batches
```

### Volume Mounts

Default volume structure:
```
./data/          # Input/output files
./logs/          # Application logs
./cache/         # Local cache (in addition to Redis)
./backup/        # Automated backups
./exports/       # Export files
./templates/     # Custom templates
```

### Networking

The setup uses a custom bridge network for service isolation:
- Subnet: 172.20.0.0/16
- Services communicate internally by name
- Only required ports exposed to host

## 🔍 Monitoring and Logs

### Real-time Monitoring

```bash
# View live metrics
docker-compose -f docker-compose.personal.yml logs -f monitor

# Access metrics file
cat logs/metrics.jsonl | jq '.'
```

### Health Checks

```bash
# Check all services health
docker-compose -f docker-compose.personal.yml ps

# Test specific service
docker exec flashcard-pipeline python -m flashcard_pipeline test all
```

### Log Management

Logs are automatically rotated:
- Max size: 10MB per file
- Keep 3 recent files
- JSON format for easy parsing

## 🛡️ Security Best Practices

1. **API Key Protection**
   - Never commit `.env.production` to git
   - Use read-only mount for env file
   - Rotate keys regularly

2. **Network Isolation**
   - Services run in isolated network
   - Only necessary ports exposed
   - Internal communication encrypted

3. **Non-root User**
   - Application runs as unprivileged user
   - Write access only to designated directories
   - Follows principle of least privilege

4. **Regular Updates**
   ```bash
   # Update base images
   docker-compose -f docker-compose.personal.yml pull
   docker-compose -f docker-compose.personal.yml build --no-cache
   ```

## 🔄 Backup and Recovery

### Automated Backups

Backups run daily at 2 AM and include:
- SQLite database
- Cache exports
- 7-day retention policy

### Manual Backup

```bash
# Full backup
./scripts/backup.sh

# Restore from backup
docker-compose -f docker-compose.personal.yml run --rm flashcard-pipeline \
  python -m flashcard_pipeline db restore /app/backup/pipeline_20240107_020000.db
```

## 🚨 Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose -f docker-compose.personal.yml logs flashcard-pipeline

# Verify environment
docker-compose -f docker-compose.personal.yml config

# Reset and rebuild
docker-compose -f docker-compose.personal.yml down -v
docker-compose -f docker-compose.personal.yml build --no-cache
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Increase Redis memory
docker-compose -f docker-compose.personal.yml exec redis redis-cli CONFIG SET maxmemory 2gb

# Optimize database
docker-compose -f docker-compose.personal.yml run --rm flashcard-pipeline \
  python -m flashcard_pipeline optimize --component all
```

### API Connection Errors

```bash
# Test connection
docker-compose -f docker-compose.personal.yml run --rm flashcard-pipeline \
  python -m flashcard_pipeline test connection

# Check API key
docker-compose -f docker-compose.personal.yml run --rm flashcard-pipeline \
  python -m flashcard_pipeline config --validate
```

## 📊 Performance Tips

1. **Concurrent Processing**: Use `--concurrent 20-50` for optimal speed
2. **Batch Size**: Adjust based on available memory (default: 100)
3. **Cache Warming**: Pre-load cache for frequently used vocabulary
4. **Redis Tuning**: Increase memory limit for larger datasets
5. **Volume Performance**: Use SSD for data volumes

## 🎯 Production Checklist

- [ ] Set strong Redis password in `.env.production`
- [ ] Configure appropriate resource limits
- [ ] Set up automated backups
- [ ] Enable monitoring services
- [ ] Configure log retention
- [ ] Test disaster recovery procedure
- [ ] Document custom configurations
- [ ] Set up health check alerts

## 📚 Additional Resources

- [CLI User Guide](docs/user/CLI_GUIDE.md)
- [API Documentation](docs/API_REFERENCE.md)
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- [Performance Tuning](docs/PERFORMANCE_GUIDE.md)

---

For support or questions, please check the [project documentation](README.md) or file an issue.