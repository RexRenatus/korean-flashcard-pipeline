# Production Deployment Checklist

## Korean Language Flashcard Pipeline v1.0.0

This checklist ensures a safe and successful production deployment. Complete each section in order and verify all items before proceeding to the next section.

---

## 📋 Pre-Deployment Checks

### 1. Environment Preparation
- [ ] Production server meets minimum requirements:
  - [ ] Ubuntu 20.04 LTS or later / CentOS 8+
  - [ ] 4 CPU cores minimum
  - [ ] 8GB RAM minimum
  - [ ] 50GB available disk space
  - [ ] Docker 20.10+ installed
  - [ ] Docker Compose 1.29+ installed
  
### 2. Network Configuration
- [ ] Port 80 (HTTP) accessible
- [ ] Port 443 (HTTPS) accessible
- [ ] Port 3000 (Grafana) restricted to admin IPs
- [ ] Port 9090 (Prometheus) restricted to internal network
- [ ] Firewall rules configured
- [ ] SSL certificates obtained (Let's Encrypt recommended)

### 3. Dependencies Verification
- [ ] Python 3.9+ available
- [ ] SQLite3 installed
- [ ] Redis server accessible
- [ ] Git installed for version control
- [ ] jq installed for JSON parsing
- [ ] AWS CLI installed (if using S3 backups)

### 4. Configuration Files
- [ ] Copy `.env.production` to `.env`
- [ ] Update all environment variables in `.env`:
  - [ ] `OPENROUTER_API_KEY` set with valid key
  - [ ] `REDIS_PASSWORD` set with strong password
  - [ ] `DATABASE_PATH` configured
  - [ ] `DB_ENCRYPTION_KEY` generated (32 bytes)
  - [ ] Email settings configured (if using alerts)
  - [ ] S3 credentials set (if using cloud backups)
- [ ] Verify nginx configuration in `nginx/nginx.conf`
- [ ] Update monitoring configs in `monitoring/`

---

## 🔒 Security Verification

### 1. Credentials Security
- [ ] No hardcoded credentials in code
- [ ] All sensitive values in `.env` file only
- [ ] `.env` file permissions set to 600
- [ ] `.env` excluded from version control
- [ ] API keys have appropriate scopes/permissions
- [ ] Database encryption key is unique and secure

### 2. Network Security
- [ ] HTTPS configured with valid certificates
- [ ] HTTP-to-HTTPS redirect enabled
- [ ] Security headers configured in nginx:
  - [ ] X-Frame-Options
  - [ ] X-Content-Type-Options
  - [ ] X-XSS-Protection
  - [ ] Content-Security-Policy
- [ ] Rate limiting configured
- [ ] DDoS protection enabled (Cloudflare/AWS WAF)

### 3. Application Security
- [ ] Input validation enabled
- [ ] SQL injection protection verified
- [ ] API authentication required
- [ ] Admin interfaces protected
- [ ] Debug mode disabled
- [ ] Error messages don't leak sensitive info

### 4. Access Control
- [ ] SSH key-based authentication only
- [ ] Root login disabled
- [ ] Sudo access restricted
- [ ] Service accounts have minimal permissions
- [ ] Database access restricted to application only

---

## 🚀 Performance Validation

### 1. Resource Allocation
- [ ] Docker memory limits set appropriately
- [ ] CPU limits configured
- [ ] Swap space configured (2x RAM)
- [ ] Database connection pool sized correctly
- [ ] Worker thread count optimized

### 2. Caching Configuration
- [ ] Redis memory limit set
- [ ] Cache eviction policy configured
- [ ] Cache TTL values appropriate
- [ ] Cache keys properly namespaced

### 3. Load Testing
- [ ] API endpoints load tested
- [ ] Database queries optimized
- [ ] Response times under 2s for 95th percentile
- [ ] System handles expected concurrent users
- [ ] No memory leaks detected

### 4. Optimization Checks
- [ ] Database indexes created
- [ ] Slow queries identified and fixed
- [ ] Static assets compressed
- [ ] Docker images optimized
- [ ] Unnecessary services disabled

---

## 📊 Monitoring Setup

### 1. Metrics Collection
- [ ] Prometheus configured and running
- [ ] Application metrics exposed
- [ ] System metrics collected
- [ ] Custom business metrics defined
- [ ] Metric retention policy set

### 2. Visualization
- [ ] Grafana accessible
- [ ] Admin password changed from default
- [ ] Dashboards imported:
  - [ ] System Overview
  - [ ] Application Performance
  - [ ] API Usage
  - [ ] Error Rates
- [ ] Alert rules configured

### 3. Logging
- [ ] Centralized logging configured
- [ ] Log rotation enabled
- [ ] Log retention policy set
- [ ] Log levels appropriate for production
- [ ] Sensitive data excluded from logs

### 4. Alerting
- [ ] Alert destinations configured:
  - [ ] Email notifications
  - [ ] Slack/Discord webhooks
  - [ ] PagerDuty integration (if applicable)
- [ ] Alert thresholds set for:
  - [ ] High CPU usage (>80%)
  - [ ] High memory usage (>90%)
  - [ ] Low disk space (<10%)
  - [ ] API errors (>5%)
  - [ ] Database connection failures
  - [ ] Service health check failures

---

## 💾 Backup Verification

### 1. Backup Configuration
- [ ] Backup script executable permissions set
- [ ] Backup schedule configured (cron/systemd)
- [ ] Backup retention policy defined
- [ ] Backup storage location has sufficient space
- [ ] S3 backup configured (if applicable)

### 2. Backup Testing
- [ ] Manual backup successful
- [ ] Backup integrity verified
- [ ] Restore process tested
- [ ] Restore time documented
- [ ] Backup monitoring enabled

### 3. Disaster Recovery
- [ ] Recovery procedures documented
- [ ] RTO (Recovery Time Objective) defined
- [ ] RPO (Recovery Point Objective) defined
- [ ] Backup locations documented
- [ ] Team trained on recovery process

---

## 🚦 Go-Live Steps

### 1. Final Preparations
- [ ] All tests passing (>90% coverage)
- [ ] Documentation up to date
- [ ] Team briefed on deployment
- [ ] Rollback plan prepared
- [ ] Maintenance window scheduled

### 2. Deployment Execution
```bash
# 1. Final backup before deployment
./scripts/backup.sh

# 2. Deploy application
./scripts/deploy.sh

# 3. Verify health
./scripts/health_check.py

# 4. Run smoke tests
./scripts/smoke_tests.sh
```

### 3. Post-Deployment Verification
- [ ] All services running
- [ ] Health checks passing
- [ ] No errors in logs
- [ ] API endpoints responding
- [ ] Database accessible
- [ ] Cache working
- [ ] Monitoring active

### 4. Performance Verification
- [ ] Response times normal
- [ ] CPU usage stable
- [ ] Memory usage stable
- [ ] No error spikes
- [ ] Cache hit rates good

### 5. User Acceptance
- [ ] Test user can create flashcards
- [ ] API rate limiting working
- [ ] Error handling functional
- [ ] Data persistence verified

---

## 📝 Post-Deployment Tasks

### 1. Documentation
- [ ] Deployment notes updated
- [ ] Known issues documented
- [ ] Performance baseline recorded
- [ ] Configuration changes logged

### 2. Monitoring
- [ ] Watch metrics for 24 hours
- [ ] Check for memory leaks
- [ ] Monitor error rates
- [ ] Review user feedback

### 3. Optimization
- [ ] Analyze performance data
- [ ] Identify bottlenecks
- [ ] Plan optimizations
- [ ] Schedule improvements

### 4. Communication
- [ ] Notify stakeholders
- [ ] Update status page
- [ ] Send deployment report
- [ ] Schedule retrospective

---

## 🚨 Emergency Contacts

| Role | Name | Contact | Availability |
|------|------|---------|--------------|
| Lead Developer | [Name] | [Email/Phone] | 24/7 |
| DevOps Engineer | [Name] | [Email/Phone] | Business hours |
| Database Admin | [Name] | [Email/Phone] | On-call |
| Security Officer | [Name] | [Email/Phone] | Business hours |

---

## 🔄 Rollback Procedure

If critical issues are discovered:

1. **Immediate Actions**
   ```bash
   # Stop traffic to application
   # Execute rollback
   ./scripts/deploy.sh rollback
   ```

2. **Verification**
   - Health checks passing
   - Previous version restored
   - Data integrity verified

3. **Communication**
   - Notify team immediately
   - Update status page
   - Document issues

4. **Root Cause Analysis**
   - Collect logs
   - Analyze failures
   - Plan fixes
   - Update procedures

---

## ✅ Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Development Lead | | | |
| QA Lead | | | |
| Security Officer | | | |
| Operations Manager | | | |
| Product Owner | | | |

---

**Remember**: Take your time, double-check everything, and don't hesitate to abort if something seems wrong. A successful deployment is worth the extra caution!