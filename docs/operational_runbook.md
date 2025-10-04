# LuvHive Bot Operational Runbook

**Emergency contact info and quick fixes for production issues**  
*Based on ChatGPT's Phase-4 recommendations*

## 🚨 Emergency Response Checklist

### FloodWait Spike (Telegram rate limiting)
**Symptoms**: Bot responses delayed, "FloodWait" in logs  
**Quick Fix**:
1. Check rate limiting metrics: `grep "FloodWait" /tmp/luvhive_violations.log`
2. Temporarily reduce message frequency in `utils/rate_limiter.py`
3. Restart bot workflow: Use Replit's restart button
4. Monitor for 10-15 minutes

**Root Cause Analysis**:
- High user activity or spam wave
- Rate limit buckets need tuning
- Message debouncing not working

### Database 100% CPU
**Symptoms**: Slow responses, timeouts, high DB CPU  
**Quick Fix**:
1. Check current connections: Look for connection pool exhaustion
2. Kill long-running queries if any
3. Restart bot to reset connection pool
4. Scale up database if needed

**Prevention**:
- Monitor query performance
- Add missing database indexes
- Optimize N+1 query patterns

### Webhook 5xx Errors
**Symptoms**: Telegram webhook failing, messages not processed  
**Quick Fix**:
1. Check webhook URL in Replit
2. Verify EXTERNAL_URL environment variable
3. Switch to polling mode temporarily:
   ```bash
   export RUN_MODE=polling
   # Restart workflow
   ```
4. Check reverse proxy if using one

### High Memory Usage
**Symptoms**: Out of memory errors, slow performance  
**Quick Fix**:
1. Restart bot workflow
2. Check for memory leaks in user tracking
3. Clear in-memory caches if safe
4. Enable swap if available

### Backup System Failure
**Symptoms**: No recent backups, backup alerts  
**Quick Fix**:
1. Check backup logs: `tail -f /tmp/luvhive_backup.log`
2. Manually create backup:
   ```bash
   python3 scripts/automated_backup.py
   ```
3. Verify database connectivity
4. Check disk space in backup directory

---

## 📊 Monitoring & Health Checks

### Health Check Endpoints
- **Basic health**: Call `/healthz` - should return `{"status": "healthy"}`
- **Readiness check**: Call `/readyz` - checks DB + Telegram API
- **Database check**: Look for p95 latency > 200ms

### Key Metrics to Watch
1. **Error rate**: Should be < 1% (5min window)
2. **DB latency**: p95 < 200ms (5min window)  
3. **FloodWait rate**: < 5 per minute
4. **Queue depth**: < 100 items for 60s
5. **Memory usage**: < 85%
6. **CPU usage**: < 80%

### Log Locations
- **Main bot logs**: Replit console output
- **Violation logs**: `/tmp/luvhive_violations.log`
- **Backup logs**: `/tmp/luvhive_backup.log`
- **Cron logs**: `/tmp/logs/backup_cron.log`

---

## 🛠️ Common Maintenance Tasks

### Weekly Tasks
- [ ] Review moderation violation trends
- [ ] Check backup restoration test results
- [ ] Monitor database growth and cleanup old data
- [ ] Review error rates and investigate spikes

### Monthly Tasks  
- [ ] Rotate bot token if needed
- [ ] Review and update abuse prevention rules
- [ ] Analyze payment fraud patterns
- [ ] Database performance optimization review

### Emergency Recovery

#### Complete Database Recovery
```bash
# 1. List available backups
python3 -c "from utils.backup_system import backup_system; print(backup_system.list_backups())"

# 2. Restore from latest backup (replace DB_NAME and BACKUP_FILE)
createdb luvhive_recovery
pg_restore -d luvhive_recovery /tmp/backups/luvhive_backup_YYYYMMDD_HHMMSS.sql

# 3. Switch database URL to recovery DB
# Update DATABASE_URL in environment
```

#### Bot Token Compromise
```bash
# 1. Revoke old token in @BotFather
# 2. Generate new token  
# 3. Update BOT_TOKEN environment variable
# 4. Restart all workflows
# 5. Test basic functionality
```

---

## 🔍 Troubleshooting Common Issues

### "Database connection failed"
1. Check DATABASE_URL format
2. Verify database is running
3. Test connection manually
4. Check firewall/network issues

### "ModuleNotFoundError" 
1. Check Python path setup
2. Verify all dependencies installed
3. Check file permissions
4. Restart Python environment

### "Webhook validation failed"
1. Check SECRET_TOKEN matches
2. Verify HTTPS certificate
3. Test webhook URL directly
4. Check reverse proxy configuration

### High abuse/spam reports
1. Review recent moderation rule changes
2. Check for new spam patterns
3. Adjust rate limiting if needed
4. Temporarily increase moderation strictness

---

## 🎯 Performance Tuning Guidelines

### Rate Limiting Optimization
- **Normal load**: 1.5 msg/s per user, 15 msg/s global
- **High load**: Reduce to 1 msg/s per user, 10 msg/s global  
- **Crisis mode**: 0.5 msg/s per user, 5 msg/s global

### Database Connection Tuning
- **Standard**: 5-10 connections per worker
- **High load**: Use connection pooling (pgBouncer)
- **Emergency**: Reduce connection pool size

### Memory Management
- **Clear old user activity data** after 24 hours
- **Limit in-memory caches** to 1000 items max
- **Monitor deque sizes** in abuse prevention

---

*This runbook should be updated as new issues are discovered and resolved.*