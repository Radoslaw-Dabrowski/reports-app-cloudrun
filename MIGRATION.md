# Migration Guide: From K8s to Cloud Run

## Architectural Differences

### Original K8s Version
```
┌─────────────────────────────────────────┐
│           K8s Cluster (K3s)             │
│  ┌────────────────────────────────────┐ │
│  │  Reports App Pod (Stateful)        │ │
│  │  - Flask App                        │ │
│  │  - Data loaded at startup          │ │
│  │  - Always running (1-2 replicas)   │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  PostgreSQL StatefulSet            │ │
│  │  - Persistent data                 │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
         │              │
         ▼              ▼
    Longhorn PV    AWS S3 Bucket
```

### Cloud Run Version
```
┌─────────────────────────────────────────┐
│        Google Cloud Run                 │
│  ┌────────────────────────────────────┐ │
│  │  Container Instances (0-10)        │ │
│  │  - Stateless                        │ │
│  │  - Lazy initialization             │ │
│  │  - Auto-scale on demand            │ │
│  │  - Scale to ZERO when idle! 💰     │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
         │        │         │
         ▼        ▼         ▼
    Cloud SQL  Redis    AWS S3
   (Managed)  (Cache)  (Storage)
```

## Key Differences

| Feature | K8s Version | Cloud Run Version |
|---------|-------------|-------------------|
| **State** | Stateful pods | Stateless containers |
| **Scaling** | Manual HPA | Automatic (0-10) |
| **Idle Cost** | Always running | **Zero!** 💰 |
| **Cold Start** | Always warm | 1-3 seconds |
| **Data Loading** | At startup | Lazy/Cached |
| **Database** | Self-hosted PostgreSQL | Cloud SQL (managed) |
| **Caching** | In-memory only | Redis (Memorystore) |
| **Deployment** | ArgoCD + Git | gcloud CLI / Cloud Build |
| **HA** | Pod anti-affinity | Built-in (multi-zone) |
| **Monitoring** | Prometheus + Grafana | Cloud Monitoring |

## Code Changes

### 1. Application Initialization

**K8s Version** (eager loading):
```python
# Load ALL data at startup
app.config['reports_df'] = read_from_database('report')
app.config['frequencies_df'] = read_from_database('frequencies')
# ... more data loaded immediately
```

**Cloud Run Version** (lazy loading):
```python
# Lazy initialization - only when needed
@app.before_first_request
def setup_database():
    db_manager.init_engine(database_url)

# Data loaded on-demand with caching
@cached(timeout=3600)
def get_reports():
    return db_manager.read_table('report')
```

### 2. Database Connections

**K8s Version**:
```python
# Direct connection, always available
DATABASE_URL = "postgresql://user:pass@postgres-service:5432/db"
engine = create_engine(DATABASE_URL)
```

**Cloud Run Version**:
```python
# Supports both TCP and Unix Socket (Cloud SQL)
if DB_UNIX_SOCKET:
    # Cloud SQL Unix Socket
    url = f"postgresql://user:pass@/db?host={DB_UNIX_SOCKET}"
else:
    # Standard TCP
    url = f"postgresql://user:pass@host:5432/db"

# Connection pooling optimized for serverless
engine = create_engine(
    url,
    pool_size=5,  # Smaller pool for Cloud Run
    pool_recycle=1800,  # Recycle connections
    pool_pre_ping=True  # Verify before use
)
```

### 3. Caching Strategy

**K8s Version**:
```python
# Simple in-memory cache (lost on pod restart)
app.config['cached_data'] = expensive_operation()
```

**Cloud Run Version**:
```python
# Redis-backed cache (survives container restarts)
from flask_caching import Cache
cache = Cache(config={'CACHE_TYPE': 'redis'})

@cached(timeout=3600, key_prefix="report")
def expensive_operation():
    return compute_data()
```

### 4. Secrets Management

**K8s Version**:
```yaml
# Kubernetes Secret + External Secrets Operator
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: app-secrets
spec:
  secretStoreRef:
    name: vault-store
```

**Cloud Run Version**:
```yaml
# Google Secret Manager
env:
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: reports-app-db-password
      key: latest
```

## Migration Steps

### Phase 1: Setup GCP Infrastructure

1. **Create Cloud SQL instance**
   ```bash
   gcloud sql instances create reports-db \
       --database-version=POSTGRES_14 \
       --region=europe-west1
   ```

2. **Create Redis instance**
   ```bash
   gcloud redis instances create reports-cache \
       --region=europe-west1
   ```

3. **Setup secrets**
   ```bash
   ./scripts/setup-secrets.sh ${PROJECT_ID}
   ```

### Phase 2: Migrate Data

1. **Export data from K8s PostgreSQL**
   ```bash
   kubectl exec -it postgres-0 -- pg_dump -U user reports_db > dump.sql
   ```

2. **Import to Cloud SQL**
   ```bash
   gcloud sql import sql reports-db gs://bucket/dump.sql \
       --database=reports_db
   ```

3. **Verify S3 access**
   ```bash
   # Cloud Run will access same S3 bucket
   # No migration needed!
   ```

### Phase 3: Deploy to Cloud Run

1. **Deploy application**
   ```bash
   ./scripts/deploy.sh ${PROJECT_ID} europe-west1
   ```

2. **Test endpoints**
   ```bash
   SERVICE_URL=$(gcloud run services describe reports-app \
       --region=europe-west1 --format='value(status.url)')
   
   curl ${SERVICE_URL}/health
   curl ${SERVICE_URL}
   ```

3. **Load cache**
   ```bash
   curl -X POST ${SERVICE_URL}/refresh_cache
   ```

### Phase 4: Traffic Migration

1. **Run both systems in parallel** (recommended)
   - Keep K8s version running
   - Test Cloud Run version with subset of users
   - Compare performance and costs

2. **Update DNS** (when ready)
   ```bash
   # Point DNS to Cloud Run URL
   # Or use Cloud Load Balancer
   ```

3. **Monitor** (first 48 hours)
   - Watch Cloud Run logs
   - Check error rates
   - Monitor cold start times
   - Verify cache hit rates

4. **Decommission K8s** (when confident)
   - Scale down K8s deployment
   - Stop ArgoCD sync
   - Archive data

## Performance Comparison

### Response Times

| Scenario | K8s | Cloud Run (warm) | Cloud Run (cold) |
|----------|-----|------------------|------------------|
| Simple page | 50ms | 40ms | 1200ms |
| Report query | 200ms | 150ms | 1500ms |
| Cache hit | 10ms | 15ms | 20ms |

### Cost Comparison (monthly estimate)

**K8s** (always running):
- 2 app replicas: $30
- PostgreSQL: $20
- Longhorn storage: $5
- **Total: ~$55/month**

**Cloud Run** (100k requests/month):
- Compute (only when active): $8
- Cloud SQL: $25
- Redis: $10
- Requests: $0.04
- **Total: ~$43/month**

**Cloud Run wins by ~22%!** 💰

Plus: Scale to zero means $0 during nights/weekends!

## Best Practices for Cloud Run

### 1. Optimize Cold Starts

```python
# ✅ Good: Lazy initialization
@app.before_first_request
def init():
    setup_database()

# ❌ Bad: Eager loading
db_manager.init_engine()  # At module level
```

### 2. Use Caching Aggressively

```python
# Cache expensive operations
@cached(timeout=3600)
def get_vmware_versions():
    return scrape_vmware_website()
```

### 3. Set Appropriate Timeouts

```yaml
# For long-running reports
spec:
  timeoutSeconds: 300  # 5 minutes max
```

### 4. Monitor and Optimize

```bash
# Watch cold start metrics
gcloud run services describe reports-app \
    --region=europe-west1 \
    --format="value(status.latestCreatedRevisionName)"
```

## Rollback Plan

If Cloud Run doesn't work out:

1. **K8s is still running** (during migration)
2. **Switch DNS back** to K8s service
3. **Data is in Cloud SQL** but can be dumped back
4. **S3 unchanged** - no impact

## Common Issues

### Issue: Cold starts too slow

**Solution:**
```bash
# Keep 1 instance always warm (costs more)
gcloud run services update reports-app --min-instances=1
```

### Issue: Database connection pool exhausted

**Solution:**
```python
# Reduce pool size in config.py
pool_size=3  # Instead of 5
```

### Issue: Redis connection timeout

**Solution:**
```python
# Add retry logic
CACHE_REDIS_OPTIONS = {
    'socket_connect_timeout': 5,
    'socket_timeout': 5,
    'retry_on_timeout': True
}
```

## Summary

**Cloud Run is ideal if:**
- ✅ Traffic is bursty/irregular
- ✅ You want to minimize costs
- ✅ You can tolerate 1-3s cold starts
- ✅ Application can be stateless

**Stick with K8s if:**
- ❌ Need sub-100ms response times always
- ❌ Have constant high traffic (>1M req/month)
- ❌ Require complex networking
- ❌ Need full control over infrastructure

For this Reports App: **Cloud Run is perfect!** 🎯
