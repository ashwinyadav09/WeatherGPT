# Operator Runbook

This runbook documents operational procedures for WeatherGPT administrators, operators, and site reliability engineers.

---

## 1. Service Restarts & Zero-Downtime Reloads

### Quick Restart (Local Compose Stack)
```bash
# Restart API and Web services without dropping Postgres or Redis
docker compose restart api worker web
```

### Full Stack Up / Down
```bash
python scripts/dev.py down
python scripts/dev.py up
```

### Production Zero-Downtime Reload (Kubernetes)
```bash
# Perform rolling restart of API deployment
kubectl rollout restart deployment/weathergpt-api -n weathergpt
kubectl rollout status deployment/weathergpt-api -n weathergpt
```

---

## 2. External Source Outages & Fallback Ladder

WeatherGPT is designed with resilient degradation. If an upstream source fails, the system automatically falls back and explicitly labels the active source in answers.

### Scenario A: IMD API is Unreachable / 5xx Errors
- **Behavior**: System automatically falls back to Open-Meteo.
- **Answer Banner**: The conversation agent states: *"Official IMD forecast is temporarily unavailable; using Open-Meteo model guidance (CC BY 4.0)."*
- **Action**: Check `https://api.imd.gov.in/public/api_reference.html` status. If persistent, verify JWT renewal.

### Scenario B: Open-Meteo Rate Limited (429)
- **Behavior**: Caches serve previous hourly forecast for the requested place grid.
- **Action**: Verify daily quota usage (10,000 requests/day). Ensure cache TTL (`ttl_seconds: 900`) is active in Redis.

### Scenario C: SACHET RSS Feed Down
- **Behavior**: Stored active alerts remain in database until their `expires` timestamp. No expired alert is relayed.
- **Action**: Check `https://sachet.ndma.gov.in`. Fall back to WMO Alert Hub mirror if necessary.

---

## 3. API Key Rotation

Keys must **NEVER** be committed to Git or printed in chat logs.

### Groq / OpenRouter LLM Keys
1. Generate new API key in provider console.
2. In production VM or Kubernetes:
   ```bash
   kubectl create secret generic weathergpt-secrets \
     --from-literal=GROQ_API_KEY="new-key" \
     --from-literal=OPENROUTER_API_KEY="new-key" \
     --dry-run=client -o yaml | kubectl apply -f -
   ```
3. Trigger rolling restart: `kubectl rollout restart deployment/weathergpt-api -n weathergpt`.
4. Test chat endpoint with `python scripts/dev.py test`.
5. Revoke old key in provider dashboard.

### Admin Token (`ADMIN_TOKEN`) Rotation
1. Update `ADMIN_TOKEN` in `.env` / Kubernetes secret.
2. Verify unauthorized requests to `/v1/admin/glossary/hi` receive HTTP 401.

---

## 4. Backups and Disaster Recovery
See [infra/backup-runbook.md](file:///d:/Projects/WeatherGPT/infra/backup-runbook.md) for full database snapshot, WAL archiving, and restore procedures.
