# Database & Redis Backup Runbook

## 1. PostgreSQL (PostGIS) Backups
- **Schedule**: Full database snapshot taken nightly at 02:00 IST (20:30 UTC); continuous WAL archiving enabled.
- **Retention**: Daily backups kept for 30 days; weekly backups kept for 12 weeks.

### Create Manual Backup
```bash
pg_dump -h localhost -U weathergpt -d weathergpt -F c -b -v -f /backups/weathergpt_$(date +%Y%m%d_%H%M%S).dump
```

### Restore Database
```bash
# 1. Stop API instances
kubectl scale deployment/weathergpt-api --replicas=0 -n weathergpt

# 2. Restore database from dump
pg_restore -h localhost -U weathergpt -d weathergpt -v --clean /backups/weathergpt_20261117_020000.dump

# 3. Verify migration head
python scripts/dev.py db-heads

# 4. Resume API instances
kubectl scale deployment/weathergpt-api --replicas=3 -n weathergpt
```

## 2. Redis Cache & Push Subscriptions
- Redis RDB snapshots saved to `/data/dump.rdb` every 15 minutes if at least 10 keys changed.
- Append Only File (`appendonly yes`) enabled for durable push subscription event delivery.
