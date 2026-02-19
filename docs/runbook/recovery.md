# Recovery Runbook

## 1. PostgreSQL Recovery

### Full Backup Recovery
```bash
# Stop the application
docker compose down backend celery-worker celery-beat

# Restore from latest backup
docker exec -i sns-solution-postgres-1 psql -U postgres sns_solution < backup_YYYYMMDD.sql

# Verify data integrity
docker exec sns-solution-postgres-1 psql -U postgres sns_solution -c "SELECT count(*) FROM users;"

# Restart application
docker compose up -d
```

### WAL Recovery (Point-in-Time)
```bash
# Configure recovery.conf in PostgreSQL
# Set recovery_target_time = 'YYYY-MM-DD HH:MM:SS'
# Restart PostgreSQL
docker compose restart postgres
```

### Partial Table Recovery
```bash
# Extract specific table from backup
pg_restore -t <table_name> -d sns_solution backup_YYYYMMDD.dump

# Or from SQL backup using sed to extract specific table
sed -n '/^-- Data for.*<table_name>/,/^-- Data for/p' backup_YYYYMMDD.sql | \
  docker exec -i sns-solution-postgres-1 psql -U postgres sns_solution
```

### Verify Database Consistency
```bash
# Check for corrupted indexes
docker exec sns-solution-postgres-1 psql -U postgres sns_solution -c "REINDEX DATABASE sns_solution;"

# Check table health
docker exec sns-solution-postgres-1 psql -U postgres sns_solution -c "
  SELECT schemaname, relname, n_dead_tup, last_vacuum, last_autovacuum
  FROM pg_stat_user_tables ORDER BY n_dead_tup DESC;
"
```

## 2. Redis Recovery

### Restore from AOF
```bash
docker compose stop redis
# Redis AOF file is in redis_data volume
docker compose start redis
# Redis will replay AOF on startup
```

### Restore from RDB Snapshot
```bash
docker compose stop redis
# Copy RDB file to the Redis data volume
docker cp dump.rdb sns-solution-redis-1:/data/dump.rdb
docker compose start redis
```

### Flush and Rebuild
```bash
docker exec sns-solution-redis-1 redis-cli FLUSHALL
# Restart application to rebuild caches
docker compose restart backend
```

### Flush Only Cache Keys (Preserve Sessions)
```bash
# Delete cache keys only, keep session and queue data
docker exec sns-solution-redis-1 redis-cli --scan --pattern "cache:*" | \
  xargs -r docker exec -i sns-solution-redis-1 redis-cli DEL

# Verify sessions are intact
docker exec sns-solution-redis-1 redis-cli --scan --pattern "session:*" | wc -l
```

## 3. MinIO/S3 Recovery

### Restore Bucket
```bash
# Restore from backup using mc (MinIO client)
mc mirror backup/sns-media local/sns-media
```

### Verify Bucket Integrity
```bash
# List all objects and check count
mc ls --recursive local/sns-media | wc -l

# Compare with backup
mc diff backup/sns-media local/sns-media
```

### Recreate Bucket and Policies
```bash
# Create bucket if missing
mc mb local/sns-media

# Set policy for presigned URL access
mc policy set download local/sns-media/public/
```

## 4. Application Recovery

### Full Stack Restart
```bash
docker compose down
docker compose up -d
# Wait for health checks
docker compose ps

# Verify all services are healthy
curl -f http://localhost:8000/health
curl -f http://localhost:3000
```

### Single Service Restart
```bash
docker compose restart backend
docker compose restart celery-worker
docker compose restart celery-beat
```

### Rolling Restart (Zero Downtime)
```bash
# Scale up first, then remove old containers
docker compose up -d --scale backend=2 --no-recreate
sleep 10
docker compose up -d --scale backend=1
```

### Rebuild and Restart
```bash
# When code changes require rebuild
docker compose build backend
docker compose up -d backend

# For frontend changes
docker compose build frontend
docker compose up -d frontend
```

## 5. Common Issues

### Database Connection Pool Exhausted
```bash
# Check active connections
docker exec sns-solution-postgres-1 psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Identify long-running queries
docker exec sns-solution-postgres-1 psql -U postgres -c "
  SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
  FROM pg_stat_activity
  WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
  AND state != 'idle'
  ORDER BY duration DESC;
"

# Terminate stuck connections
docker exec sns-solution-postgres-1 psql -U postgres -c "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE (now() - pg_stat_activity.query_start) > interval '10 minutes'
  AND state != 'idle';
"

# Restart backend to reset pool
docker compose restart backend
```

### Celery Worker Stuck
```bash
# Check worker status
docker exec sns-solution-celery-worker-1 celery -A app.tasks.celery_app inspect active

# Check queue lengths
docker exec sns-solution-redis-1 redis-cli LLEN celery
docker exec sns-solution-redis-1 redis-cli LLEN critical
docker exec sns-solution-redis-1 redis-cli LLEN high
docker exec sns-solution-redis-1 redis-cli LLEN medium
docker exec sns-solution-redis-1 redis-cli LLEN low

# Purge all queues
docker exec sns-solution-celery-worker-1 celery -A app.tasks.celery_app purge -f

# Restart worker
docker compose restart celery-worker
```

### Celery Beat Scheduler Issues
```bash
# Check beat schedule
docker exec sns-solution-celery-beat-1 celery -A app.tasks.celery_app inspect scheduled

# Reset beat schedule (remove the schedule file)
docker exec sns-solution-celery-beat-1 rm -f /app/celerybeat-schedule

# Restart beat
docker compose restart celery-beat
```

### Redis Memory Full
```bash
# Check memory usage
docker exec sns-solution-redis-1 redis-cli INFO memory

# Check key distribution
docker exec sns-solution-redis-1 redis-cli INFO keyspace

# Flush non-critical caches
docker exec sns-solution-redis-1 redis-cli --scan --pattern "cache:*" | \
  xargs -r docker exec -i sns-solution-redis-1 redis-cli DEL

# Check memory after cleanup
docker exec sns-solution-redis-1 redis-cli INFO memory | grep used_memory_human
```

### Alembic Migration Failures
```bash
# Check current migration version
cd backend && alembic current

# Show migration history
alembic history --verbose

# Downgrade one step if last migration failed
alembic downgrade -1

# Re-run migration
alembic upgrade head

# If migration state is inconsistent, stamp to a known version
alembic stamp <revision_id>
```

### WebSocket Connection Issues
```bash
# Check WebSocket endpoint health
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: test" \
  http://localhost:8000/ws?token=test

# Check nginx WebSocket proxy config
docker exec sns-solution-nginx-1 nginx -t

# Restart nginx if WebSocket proxy is misconfigured
docker compose restart nginx
```

### Disk Space Issues
```bash
# Check disk usage by service
docker system df

# Clean unused Docker resources
docker system prune -f

# Clean old logs
docker compose logs --tail=0 > /dev/null  # Truncate logs
find /var/lib/docker/containers -name "*.log" -size +100M -exec truncate -s 0 {} \;

# Archive old analytics data (if applicable)
docker exec sns-solution-postgres-1 psql -U postgres sns_solution -c "
  DELETE FROM analytics_metrics
  WHERE collected_at < NOW() - INTERVAL '90 days';
"
```

## 6. Monitoring Alerts

| Alert | Severity | Action |
|-------|----------|--------|
| High CPU (>80%) | Warning | Scale workers or optimize queries |
| Memory >90% | Critical | Check for leaks, restart affected service |
| DB connections >80 | Warning | Optimize pool size, check for connection leaks |
| 5xx rate >1% | Critical | Check logs, restart if needed, investigate root cause |
| Celery queue >100 | Warning | Scale workers, check for stuck tasks |
| Disk >85% | Warning | Clean logs, archive old data, extend storage |
| Redis memory >80% | Warning | Flush non-critical caches, check for key leaks |
| WebSocket connections >1000 | Warning | Scale backend instances, check for connection leaks |
| Response time P95 >500ms | Warning | Check slow queries, optimize endpoints, add caching |
| SSL certificate expiry <14d | Critical | Renew certificate immediately |

## 7. Emergency Contacts

| Role | Responsibility | Escalation Time |
|------|---------------|-----------------|
| On-call Engineer | First response, service restarts | Immediate |
| Backend Lead | Database recovery, API issues | 15 minutes |
| DevOps Lead | Infrastructure, Docker, networking | 15 minutes |
| Project Manager | Client communication, priority decisions | 30 minutes |

## 8. Post-Incident Checklist

- [ ] Verify all services are running: `docker compose ps`
- [ ] Verify health endpoint: `curl http://localhost:8000/health`
- [ ] Check error rates in Sentry
- [ ] Verify database connectivity and query performance
- [ ] Check Redis connectivity and memory usage
- [ ] Verify Celery workers are processing tasks
- [ ] Test WebSocket connections
- [ ] Check for any data loss or inconsistency
- [ ] Update incident timeline documentation
- [ ] Schedule post-mortem if severity was Critical
