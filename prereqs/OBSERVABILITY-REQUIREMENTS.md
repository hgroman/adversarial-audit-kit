# Observability Requirements

**Audience**: Operator Auditor (audit-05-operator)
**Purpose**: Define what production observability looks like for ScraperSky

---

## 1. Current Observability State

### Health Endpoints

| Endpoint | Location | What It Checks |
|----------|----------|----------------|
| `/health` | `src/main.py:438` | Basic liveness (returns `{"status": "ok"}`) |
| `/health/database` | `src/main.py:444` | Database connection via `check_database_connection()` |
| `/api/v3/google-maps-api/health` | `wf1_google_maps_api_router.py:486` | WF1 service health |
| `/api/v3/page-scraper-batch/health` | `wf7_page_batch_scraper_router.py:452` | WF7 batch scraper health |
| `/api/v3/n8n-webhook/health` | `wf8_n8n_webhook_router.py:311` | WF8 n8n integration health |
| `/api/v3/db-portal/health` | `db_portal.py:236` | Database portal health |

**Gap**: No aggregated health endpoint that checks ALL services at once.

### Logging Configuration

Location: `src/config/logging_config.py`

```python
# Current format (MISSING tenant_id)
format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

**Critical Gap**: `tenant_id` is NOT in the log format. This means:
- During an incident, you cannot filter logs by tenant
- Multi-tenant issues are nearly impossible to debug
- RLS violations leave no tenant trail

### Service Logging Pattern

Services use standard Python logging:
```python
logger = logging.getLogger("src.services.jobs")
logger.warning(f"Job not found for status update: {job_id}")
```

**What's Logged**:
- Job IDs, status changes
- Errors and warnings
- Some operational events

**What's NOT Logged**:
- Tenant ID (critical gap)
- Request correlation IDs
- RLS context changes (SET ROLE / RESET ROLE)
- Scheduler job start/end times

---

## 2. What the Operator Must Verify

### Logging Requirements Checklist

For ANY refactor or new feature, verify:

- [ ] **Tenant Context Preserved**: Does `tenant_id` appear in logs after this change?
- [ ] **Exception Stack Traces**: Are exceptions logged with full stack traces (not rewrapped)?
- [ ] **Scheduler Logging**: Do background jobs log start, end, and tenant processed?
- [ ] **RLS Context Logging**: Can you trace when `SET ROLE` and `RESET ROLE` happen?

### Health Check Requirements

For ANY new service or workflow:

- [ ] **Health Endpoint Exists**: New service has `/health` endpoint
- [ ] **Database Check**: If service uses DB, health checks connection
- [ ] **External Service Check**: If service calls external API, health checks connectivity
- [ ] **Aggregation**: Main `/health` should eventually aggregate all service health

### Rollback Observability

Before ANY deployment:

- [ ] **Schema Compatibility**: Can old code read new schema? Can new code read old schema?
- [ ] **Log Format Unchanged**: Will existing log parsing/alerting still work?
- [ ] **Metric Names Stable**: Will dashboards break if we rollback?

---

## 3. Anti-Patterns the Operator Hunts

### 3.1 Silent Shims

**Pattern**: Facade that catches exceptions and returns generic error
```python
# BAD - swallows the real error
class ServiceFacade:
    async def do_work(self):
        try:
            return await self.real_service.work()
        except Exception:
            return {"error": "Something went wrong"}  # SILENT DEATH
```

**What to Look For**:
- `except Exception:` without `logger.exception()`
- Generic error messages that hide root cause
- Return values instead of re-raising exceptions

### 3.2 Ghost Metrics

**Pattern**: Metrics/decorators on code that was moved or renamed
```python
# OLD: metrics attached to OldService.process()
# NEW: code moved to NewService.handle()
# RESULT: metric stops reporting, dashboard shows zero
```

**What to Look For**:
- `@instrument` or `@metrics` decorators on methods that no longer exist
- Dashboard metrics that suddenly go to zero after refactor
- Prometheus queries referencing old class/method names

### 3.3 Context Black Holes

**Pattern**: Logging middleware loses tenant_id during refactor
```python
# BEFORE: tenant_id injected via middleware
# AFTER: new code path bypasses middleware
# RESULT: logs have no tenant context for new code path
```

**What to Look For**:
- New code paths that don't go through the standard request pipeline
- Background tasks that create their own logging context
- Services called directly without going through routers

### 3.4 Telemetry Drift

**Pattern**: New services not registered with health checks
```python
# New WF10 service added
# Health check still only checks WF1-WF9
# Production: WF10 silently fails, main health shows "ok"
```

**What to Look For**:
- New routers/services not included in health aggregation
- External dependencies without health checks
- Scheduler jobs that don't report status anywhere

---

## 4. Required Logging for Multi-Tenant

### Minimum Viable Logging

Every log statement in a tenant-scoped operation SHOULD include:

```python
logger.info(
    f"Processing domain {domain_id}",
    extra={
        "tenant_id": tenant_id,
        "operation": "domain_scan",
        "domain_id": str(domain_id)
    }
)
```

### Scheduler Logging Pattern

Background schedulers MUST log:

```python
logger.info(f"[SCHEDULER] Starting {scheduler_name}")
logger.info(f"[SCHEDULER] Found {count} items for tenant {tenant_id}")
logger.info(f"[SCHEDULER] Completed {scheduler_name} in {elapsed}s")
```

### Error Logging Pattern

Errors MUST include tenant context:

```python
logger.exception(
    f"Failed to process {operation} for tenant {tenant_id}",
    extra={"tenant_id": tenant_id, "operation": operation}
)
```

---

## 5. Incident Response Questions

When auditing, imagine the 2 AM incident:

1. **"Which tenant is affected?"** - Can you filter logs by `tenant_id`?
2. **"When did it start?"** - Are timestamps in logs accurate and consistent?
3. **"What was the last successful operation?"** - Is success logged, not just errors?
4. **"Is the database connection the problem?"** - Does `/health/database` work?
5. **"Is it just one workflow?"** - Can you isolate by workflow prefix in logs?

---

## 6. Reference Files

| File | Purpose | Operator Focus |
|------|---------|----------------|
| `src/config/logging_config.py` | Logging format setup | Check tenant_id in format |
| `src/main.py:438-455` | Health endpoints | Check what's monitored |
| `src/services/*` | Business logic | Check logger usage patterns |
| `src/db/tenant_context.py` | RLS context manager | Check if context changes logged |

---

## 7. Future State (What Good Looks Like)

**Ideal Logging Configuration**:
```python
format="%(asctime)s - %(name)s - %(levelname)s - [tenant:%(tenant_id)s] %(message)s"
```

**Ideal Health Aggregation**:
```json
{
  "status": "ok",
  "services": {
    "database": "ok",
    "wf1_google_maps": "ok",
    "wf5_sitemap": "ok",
    "wf7_page_scraper": "ok",
    "wf8_crm": "ok",
    "scheduler": "ok"
  }
}
```

**Ideal Metrics**:
- `scrapersky_jobs_per_minute{workflow="wf1", tenant="xxx"}`
- `scrapersky_scheduler_run_seconds{scheduler="domain_scheduler"}`
- `scrapersky_rls_context_switches_total{role="app_worker"}`

---

## Summary

The Operator auditor should verify that:

1. **Tenant context flows through ALL log statements**
2. **Health checks exist for ALL services**
3. **Exceptions are logged, not swallowed**
4. **Metrics survive refactors**
5. **Rollback won't break observability**

Without these, "the code works, but you're flying blind in production."
