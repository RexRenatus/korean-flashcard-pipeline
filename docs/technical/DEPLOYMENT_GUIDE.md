# Deployment Guide - Korean Language Flashcard Pipeline

## Table of Contents
1. [Overview](#overview)
2. [Docker Deployment](#docker-deployment)
3. [Production Configuration](#production-configuration)
4. [Environment Variables](#environment-variables)
5. [Database Management](#database-management)
6. [Backup Procedures](#backup-procedures)
7. [Monitoring Setup](#monitoring-setup)
8. [Security Considerations](#security-considerations)
9. [Scaling Strategies](#scaling-strategies)
10. [Troubleshooting](#troubleshooting)

## Overview

This guide covers deploying the Korean Language Flashcard Pipeline in production environments using Docker containers, with comprehensive monitoring, backup, and scaling strategies.

### Deployment Architecture

```
┌─────────────────────┐     ┌─────────────────────┐
│   Load Balancer     │────▶│   Nginx Reverse     │
│   (AWS ALB/NLB)     │     │      Proxy          │
└─────────────────────┘     └──────────┬──────────┘
                                       │
                            ┌──────────┴──────────┐
                            │                     │
                    ┌───────▼────────┐   ┌───────▼────────┐
                    │  App Instance 1 │   │  App Instance 2 │
                    │   (Container)   │   │   (Container)   │
                    └───────┬────────┘   └───────┬────────┘
                            │                     │
                            └──────────┬──────────┘
                                       │
                            ┌──────────▼──────────┐
                            │   Shared Volume    │
                            │  (Database + Cache) │
                            └─────────────────────┘
```

## Docker Deployment

### Docker Configuration

The project includes a comprehensive `docker-compose.yml` for production deployment:

```yaml
version: '3.8'

services:
  app:
    build: .
    image: korean-flashcard-pipeline:latest
    container_name: flashcard-app
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - DATABASE_PATH=/data/pipeline.db
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - WORKERS=${WORKERS:-4}
    volumes:
      - ./data:/data
      - ./logs:/logs
      - ./config:/config
    ports:
      - "8000:8000"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-m", "flashcard_pipeline.cli", "status"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - flashcard-network

  nginx:
    image: nginx:alpine
    container_name: flashcard-nginx
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - flashcard-network

  prometheus:
    image: prom/prometheus:latest
    container_name: flashcard-prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    restart: unless-stopped
    networks:
      - flashcard-network

  grafana:
    image: grafana/grafana:latest
    container_name: flashcard-grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
    restart: unless-stopped
    networks:
      - flashcard-network

volumes:
  prometheus-data:
  grafana-data:

networks:
  flashcard-network:
    driver: bridge
```

### Building and Running

1. **Build Docker Image**
   ```bash
   docker build -t korean-flashcard-pipeline:latest .
   ```

2. **Run with Docker Compose**
   ```bash
   # Production mode
   docker-compose up -d
   
   # With custom environment file
   docker-compose --env-file .env.production up -d
   
   # Scale app instances
   docker-compose up -d --scale app=3
   ```

3. **View Logs**
   ```bash
   # All services
   docker-compose logs -f
   
   # Specific service
   docker-compose logs -f app
   
   # Last 100 lines
   docker-compose logs --tail=100 app
   ```

### Dockerfile

Production-optimized Dockerfile:

```dockerfile
# Multi-stage build for smaller image
FROM python:3.11-slim as builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim

# Security: Run as non-root user
RUN useradd -m -u 1000 flashcard && \
    mkdir -p /data /logs /config && \
    chown -R flashcard:flashcard /data /logs /config

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /home/flashcard/.local
ENV PATH=/home/flashcard/.local/bin:$PATH

# Copy application code
COPY --chown=flashcard:flashcard . .

USER flashcard

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -m flashcard_pipeline.cli status || exit 1

# Default command
CMD ["python", "-m", "flashcard_pipeline.cli", "serve", "--host", "0.0.0.0", "--port", "8000"]
```

## Production Configuration

### Nginx Configuration

`nginx.conf` for reverse proxy and SSL:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream flashcard_app {
        least_conn;
        server app:8000 max_fails=3 fail_timeout=30s;
        # Add more servers for load balancing
        # server app2:8000 max_fails=3 fail_timeout=30s;
    }

    server {
        listen 80;
        server_name flashcards.example.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name flashcards.example.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        client_max_body_size 10M;

        location / {
            proxy_pass http://flashcard_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }

        location /health {
            proxy_pass http://flashcard_app/health;
            access_log off;
        }

        location /metrics {
            proxy_pass http://flashcard_app/metrics;
            allow 10.0.0.0/8;
            deny all;
        }
    }
}
```

### Application Configuration

Production `config.yaml`:

```yaml
# Production configuration
environment: production

api:
  base_url: "https://openrouter.ai/api/v1"
  timeout: 30
  max_retries: 3
  backoff_factor: 2

models:
  flashcard_creator: "anthropic/claude-3-sonnet"
  nuance_creator: "anthropic/claude-3-sonnet"

processing:
  batch_size: 50
  max_concurrent: 10
  rate_limit: 600  # per minute
  
cache:
  enabled: true
  backend: redis  # or filesystem
  ttl: 604800  # 7 days
  max_size: 10000
  
database:
  path: "/data/pipeline.db"
  pool_size: 20
  timeout: 30
  journal_mode: "WAL"
  
logging:
  level: INFO
  format: json
  output: "/logs/app.log"
  max_size: "100MB"
  max_files: 10
  
monitoring:
  enabled: true
  metrics_port: 9100
  health_check_interval: 30
  
security:
  api_key_header: "X-API-Key"
  rate_limit_header: "X-RateLimit-Limit"
  allowed_origins:
    - "https://flashcards.example.com"
    - "https://app.example.com"
```

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | OpenRouter API key | `sk-or-v1-xxxxx` |
| `DATABASE_PATH` | Path to SQLite database | `/data/pipeline.db` |
| `SECRET_KEY` | Application secret key | `generate-strong-key` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level | `INFO` |
| `WORKERS` | Number of worker processes | `4` |
| `PORT` | Application port | `8000` |
| `CACHE_BACKEND` | Cache backend (redis/filesystem) | `filesystem` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `SENTRY_DSN` | Sentry error tracking DSN | None |
| `PROMETHEUS_ENABLED` | Enable Prometheus metrics | `true` |
| `BACKUP_SCHEDULE` | Backup cron schedule | `0 2 * * *` |

### Setting Environment Variables

1. **Using .env file**
   ```bash
   # .env.production
   OPENROUTER_API_KEY=sk-or-v1-xxxxx
   DATABASE_PATH=/data/pipeline.db
   LOG_LEVEL=INFO
   WORKERS=4
   ```

2. **Docker Compose Override**
   ```yaml
   # docker-compose.override.yml
   version: '3.8'
   services:
     app:
       environment:
         - OPENROUTER_API_KEY=sk-or-v1-xxxxx
         - LOG_LEVEL=DEBUG
   ```

3. **System Environment**
   ```bash
   export OPENROUTER_API_KEY=sk-or-v1-xxxxx
   export DATABASE_PATH=/data/pipeline.db
   ```

## Database Management

### Database Configuration

1. **WAL Mode for Concurrency**
   ```sql
   PRAGMA journal_mode=WAL;
   PRAGMA synchronous=NORMAL;
   PRAGMA cache_size=10000;
   PRAGMA temp_store=MEMORY;
   ```

2. **Connection Pool Settings**
   ```python
   # In production config
   database:
     pool_size: 20
     max_overflow: 10
     pool_timeout: 30
     pool_recycle: 3600
   ```

### Migration Management

1. **Run Migrations**
   ```bash
   docker exec flashcard-app python -m flashcard_pipeline.cli db migrate
   ```

2. **Create Migration**
   ```bash
   docker exec flashcard-app python -m flashcard_pipeline.cli db create-migration "add_index"
   ```

3. **Rollback Migration**
   ```bash
   docker exec flashcard-app python -m flashcard_pipeline.cli db rollback --steps 1
   ```

### Database Optimization

1. **Regular Maintenance**
   ```bash
   # Vacuum database
   docker exec flashcard-app python -m flashcard_pipeline.cli db vacuum
   
   # Analyze tables
   docker exec flashcard-app python -m flashcard_pipeline.cli db analyze
   
   # Reindex
   docker exec flashcard-app python -m flashcard_pipeline.cli db reindex
   ```

2. **Performance Monitoring**
   ```sql
   -- Check database size
   SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();
   
   -- Check table statistics
   SELECT name, stat FROM sqlite_stat1;
   
   -- Check slow queries
   SELECT * FROM query_log WHERE duration > 1000 ORDER BY duration DESC;
   ```

## Backup Procedures

### Automated Backups

1. **Backup Script** (`scripts/backup.sh`):
   ```bash
   #!/bin/bash
   BACKUP_DIR="/backups"
   TIMESTAMP=$(date +%Y%m%d_%H%M%S)
   DB_PATH="/data/pipeline.db"
   
   # Create backup directory
   mkdir -p $BACKUP_DIR
   
   # Backup database
   sqlite3 $DB_PATH ".backup $BACKUP_DIR/pipeline_$TIMESTAMP.db"
   
   # Compress backup
   gzip $BACKUP_DIR/pipeline_$TIMESTAMP.db
   
   # Upload to S3 (optional)
   aws s3 cp $BACKUP_DIR/pipeline_$TIMESTAMP.db.gz s3://backup-bucket/flashcards/
   
   # Clean old backups (keep 30 days)
   find $BACKUP_DIR -name "pipeline_*.db.gz" -mtime +30 -delete
   ```

2. **Scheduled Backups**
   ```yaml
   # In docker-compose.yml
   backup:
     image: korean-flashcard-pipeline:latest
     volumes:
       - ./data:/data
       - ./backups:/backups
     environment:
       - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
       - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
     command: /scripts/backup.sh
     labels:
       - "ofelia.enabled=true"
       - "ofelia.job-exec.backup.schedule=0 2 * * *"
   ```

### Manual Backup

```bash
# Quick backup
docker exec flashcard-app python -m flashcard_pipeline.cli db backup --output /backups/manual_backup.db

# Full backup with verification
docker exec flashcard-app python -m flashcard_pipeline.cli db backup \
  --output /backups/full_backup.db \
  --verify \
  --compress
```

### Restore Procedures

1. **From Local Backup**
   ```bash
   # Stop application
   docker-compose stop app
   
   # Restore database
   docker exec flashcard-app python -m flashcard_pipeline.cli db restore \
     --input /backups/pipeline_20240109.db.gz \
     --verify
   
   # Restart application
   docker-compose start app
   ```

2. **From S3 Backup**
   ```bash
   # Download backup
   aws s3 cp s3://backup-bucket/flashcards/pipeline_20240109.db.gz /backups/
   
   # Restore
   docker exec flashcard-app python -m flashcard_pipeline.cli db restore \
     --input /backups/pipeline_20240109.db.gz
   ```

## Monitoring Setup

### Prometheus Configuration

`prometheus.yml`:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'flashcard-app'
    static_configs:
      - targets: ['app:9100']
    metrics_path: '/metrics'
    
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
      
  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx-exporter:9113']
```

### Application Metrics

Key metrics exposed:
```python
# Request metrics
flashcard_requests_total
flashcard_request_duration_seconds
flashcard_requests_in_progress

# API metrics
api_calls_total
api_call_duration_seconds
api_errors_total

# Cache metrics
cache_hits_total
cache_misses_total
cache_evictions_total

# Database metrics
db_connections_active
db_queries_total
db_query_duration_seconds

# Business metrics
flashcards_created_total
words_processed_total
batch_processing_duration_seconds
```

### Grafana Dashboards

1. **Application Dashboard**
   - Request rate and latency
   - Error rate
   - API usage
   - Cache hit rate

2. **System Dashboard**
   - CPU and memory usage
   - Disk I/O
   - Network traffic
   - Container health

3. **Business Dashboard**
   - Flashcards created over time
   - Popular words
   - User activity
   - API costs estimation

### Alerting Rules

```yaml
# alerting_rules.yml
groups:
  - name: flashcard_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(flashcard_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          
      - alert: APIRateLimitNear
        expr: rate(api_calls_total[1m]) > 50
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Approaching API rate limit"
          
      - alert: DatabaseConnectionsHigh
        expr: db_connections_active > 15
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High database connection count"
```

### Health Checks

1. **Application Health Endpoint**
   ```python
   # GET /health
   {
     "status": "healthy",
     "version": "1.0.0",
     "checks": {
       "database": "ok",
       "cache": "ok",
       "api": "ok"
     },
     "timestamp": "2024-01-09T12:00:00Z"
   }
   ```

2. **Docker Health Check**
   ```dockerfile
   HEALTHCHECK --interval=30s --timeout=10s \
     CMD curl -f http://localhost:8000/health || exit 1
   ```

## Security Considerations

### API Security

1. **API Key Management**
   - Store keys in environment variables
   - Rotate keys regularly
   - Use separate keys for dev/prod

2. **Request Authentication**
   ```python
   # Implement API key validation
   @require_api_key
   async def protected_endpoint(request):
       # Endpoint logic
   ```

3. **Rate Limiting**
   ```python
   # Per-IP rate limiting
   rate_limiter = RateLimiter(
       rate=100,  # requests
       period=60  # seconds
   )
   ```

### Network Security

1. **Firewall Rules**
   ```bash
   # Allow only necessary ports
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw allow 22/tcp
   ufw enable
   ```

2. **SSL/TLS Configuration**
   - Use Let's Encrypt for certificates
   - Enable HSTS
   - Disable weak ciphers

### Data Security

1. **Database Encryption**
   ```bash
   # Encrypt database at rest
   sqlcipher pipeline.db
   ```

2. **Backup Encryption**
   ```bash
   # Encrypt backups
   gpg --encrypt --recipient backup@example.com backup.db
   ```

3. **Log Sanitization**
   - Remove sensitive data from logs
   - Rotate logs regularly
   - Secure log storage

## Scaling Strategies

### Horizontal Scaling

1. **Application Scaling**
   ```bash
   # Scale to 5 instances
   docker-compose up -d --scale app=5
   ```

2. **Load Balancing**
   - Use nginx upstream configuration
   - Implement health checks
   - Session affinity if needed

### Vertical Scaling

1. **Resource Limits**
   ```yaml
   # In docker-compose.yml
   app:
     deploy:
       resources:
         limits:
           cpus: '2.0'
           memory: 4G
         reservations:
           cpus: '1.0'
           memory: 2G
   ```

### Database Scaling

1. **Read Replicas**
   - Use SQLite read-only connections
   - Implement read/write splitting

2. **Sharding**
   - Partition by word prefix
   - Separate cache database

### Caching Strategy

1. **Multi-tier Caching**
   - In-memory (application)
   - Redis (shared)
   - CDN (static assets)

2. **Cache Warming**
   ```bash
   # Pre-populate cache
   docker exec flashcard-app python -m flashcard_pipeline.cli cache warm \
     --words common_words.txt
   ```

## Troubleshooting

### Common Issues

1. **Database Locked**
   ```bash
   # Check for locks
   docker exec flashcard-app lsof | grep pipeline.db
   
   # Force unlock
   docker exec flashcard-app python -m flashcard_pipeline.cli db unlock
   ```

2. **High Memory Usage**
   ```bash
   # Check memory usage
   docker stats flashcard-app
   
   # Analyze memory
   docker exec flashcard-app python -m memory_profiler app.py
   ```

3. **Slow Performance**
   ```bash
   # Enable profiling
   docker exec flashcard-app python -m flashcard_pipeline.cli \
     --profile process-word "test"
   
   # Check slow queries
   docker exec flashcard-app python -m flashcard_pipeline.cli db analyze-queries
   ```

### Debug Mode

1. **Enable Debug Logging**
   ```yaml
   # In docker-compose.yml
   environment:
     - LOG_LEVEL=DEBUG
     - DEBUG=true
   ```

2. **Interactive Debugging**
   ```bash
   # Attach to container
   docker exec -it flashcard-app /bin/bash
   
   # Run Python debugger
   python -m pdb -m flashcard_pipeline.cli process-word "test"
   ```

### Log Analysis

1. **Aggregate Logs**
   ```bash
   # View all logs
   docker-compose logs -f
   
   # Search for errors
   docker-compose logs | grep ERROR
   
   # Export logs
   docker-compose logs > logs_$(date +%Y%m%d).txt
   ```

2. **Log Parsing**
   ```bash
   # Parse JSON logs
   docker logs flashcard-app | jq '.level == "ERROR"'
   
   # Count errors by type
   docker logs flashcard-app | jq -r '.error_type' | sort | uniq -c
   ```

## Production Checklist

Before deploying to production:

- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Backup schedule configured
- [ ] Monitoring dashboards created
- [ ] Alerts configured
- [ ] Rate limiting enabled
- [ ] Security headers configured
- [ ] Database optimized
- [ ] Logs rotation configured
- [ ] Health checks working
- [ ] Documentation updated
- [ ] Disaster recovery plan tested

## Support

For production support:
- Emergency: ops@flashcardpipeline.com
- Documentation: [docs.flashcardpipeline.com](https://docs.flashcardpipeline.com)
- Status Page: [status.flashcardpipeline.com](https://status.flashcardpipeline.com)