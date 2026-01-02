# Scheduler Intervals Reference
**Last Updated:** 2025-12-21
**Purpose:** Production intervals for all background schedulers
**Critical:** When debugging slow/stuck workflows, check these intervals first

> **ENUM UPDATE (2025-12-21)**: All schedulers now use `WorkflowProcessingStatus` for processing status.
> See [ADR-010](../00_The_Law/ADR-010-ENUM-FREEZE-POLICY.md) for the enum freeze policy.

---

## Production Scheduler Intervals

| Scheduler | Interval | Batch Size | Max Instances | File |
|-----------|----------|------------|---------------|------|
| **WF2 Deep Scan** | 1 min | 10 | 1 | `wf2_deep_scan_scheduler.py` |
| **WF3 Domain Extraction** | 2 min | 20 | 1 | `wf3_domain_extraction_scheduler.py` |
| **WF4 Domain Monitor** | 1 min | 50 | 3 | `wf4_domain_monitor_scheduler.py` |
| **WF4 Sitemap Discovery** | 1 min | 10 | 1 | `wf4_sitemap_discovery_scheduler.py` |
| **WF5 Sitemap Import** | 1 min | 20 | 1 | `wf5_sitemap_import_scheduler.py` |
| **WF7 Page Curation** | 1 min | 10 | 1 | `wf7_page_curation_scheduler.py` |
| **WF8 Brevo CRM Sync** | 1 min | 10 | 1 | `wf8_crm_brevo_sync_scheduler.py` |
| **WF8 HubSpot CRM Sync** | 1 min | 10 | 1 | `wf8_crm_hubspot_sync_scheduler.py` |
| **WF8 n8n Webhook Sync** | 1 min | 10 | 1 | `wf8_crm_n8n_sync_scheduler.py` |
| **WF8 DeBounce Validation** | 1 min | 50 | 1 | `wf8_crm_debounce_scheduler.py` |

---

## Throughput Calculations

### Per-Scheduler Throughput

**Standard Workflow (1 min interval, batch 10):**
```
10 records/min × 60 min = 600 records/hour
600 records/hour × 24 hours = 14,400 records/day
```

**DeBounce Validation (1 min interval, batch 50):**
```
50 records/min × 60 min = 3,000 records/hour
3,000 records/hour × 24 hours = 72,000 records/day
```

### Total System Throughput

**All Schedulers Combined (Theoretical Max):**
```
Workflows (5 × 10) = 50 records/min
CRM Syncs (3 × 10) = 30 records/min
Validation (1 × 50) = 50 records/min
---
Total: 130 records/min = 7,800 records/hour = 187,200 records/day
```

**Actual Throughput:**
- Depends on queue size and API response times
- Retry logic slows down failed records
- Conservative batch sizes prevent API rate limiting

---

## Scheduler Configuration

### Environment Variables

**Interval Configuration:**
```bash
# Workflow Schedulers (settings.py defaults shown)
DEEP_SCAN_SCHEDULER_INTERVAL_MINUTES=1
DOMAIN_EXTRACTION_SCHEDULER_INTERVAL_MINUTES=2
DOMAIN_SCHEDULER_INTERVAL_MINUTES=1          # WF4 Domain Monitor
DOMAIN_SITEMAP_SCHEDULER_INTERVAL_MINUTES=1  # WF4 Sitemap Discovery
SITEMAP_IMPORT_SCHEDULER_INTERVAL_MINUTES=1
PAGE_CURATION_SCHEDULER_INTERVAL_MINUTES=1

# CRM Schedulers
BREVO_SYNC_SCHEDULER_INTERVAL_MINUTES=1
HUBSPOT_SYNC_SCHEDULER_INTERVAL_MINUTES=1
N8N_SYNC_SCHEDULER_INTERVAL_MINUTES=1
DEBOUNCE_VALIDATION_SCHEDULER_INTERVAL_MINUTES=1
```

**Batch Size Configuration:**
```bash
# Workflow Schedulers (settings.py defaults shown)
DEEP_SCAN_SCHEDULER_BATCH_SIZE=10
DOMAIN_EXTRACTION_SCHEDULER_BATCH_SIZE=20
DOMAIN_SCHEDULER_BATCH_SIZE=50               # WF4 Domain Monitor
DOMAIN_SITEMAP_SCHEDULER_BATCH_SIZE=10       # WF4 Sitemap Discovery
SITEMAP_IMPORT_SCHEDULER_BATCH_SIZE=20
PAGE_CURATION_SCHEDULER_BATCH_SIZE=10

# CRM Schedulers
BREVO_SYNC_SCHEDULER_BATCH_SIZE=10
HUBSPOT_SYNC_SCHEDULER_BATCH_SIZE=10
N8N_SYNC_SCHEDULER_BATCH_SIZE=10
DEBOUNCE_VALIDATION_SCHEDULER_BATCH_SIZE=50  # Higher for validation
```

---

## Scheduler Architecture

> **RLS Pattern Reference:** For Chicken-and-Egg pattern implementation details (how schedulers bypass RLS for discovery then apply it for processing), see **SESSION-AND-TENANT-LAW.md §Chicken-and-Egg Implementation Registry**.

### SDK Pattern (`run_job_loop`)

**Most schedulers use the SDK pattern:**

```python
from src.common.curation_sdk.scheduler_loop import run_job_loop

async def process_my_queue():
    await run_job_loop(
        model=MyModel,
        status_enum=ProcessingStatus,
        queued_status=ProcessingStatus.Queued,
        processing_status=ProcessingStatus.Processing,
        completed_status=ProcessingStatus.Complete,
        failed_status=ProcessingStatus.Error,
        processing_function=MyService.process_record,
        batch_size=settings.MY_SCHEDULER_BATCH_SIZE,
        status_field_name="my_processing_status",
        error_field_name="my_processing_error",
    )
```

**Benefits:**
- ✅ Consistent error handling
- ✅ Automatic status transitions
- ✅ Built-in batch processing
- ✅ No race conditions (max_instances=1)

---

## Retry Logic

### Exponential Backoff (All Schedulers)

```
Retry 0 → 5 minutes delay
Retry 1 → 10 minutes delay
Retry 2 → 20 minutes delay
Retry 3 → Max retries exceeded (Error final state)
```

**Database Fields:**
```python
retry_count = Column(Integer, default=0)
next_retry_at = Column(DateTime(timezone=True))
last_retry_at = Column(DateTime(timezone=True))
last_failed_service = Column(String)  # Which service failed
{service}_processing_error = Column(String(500))  # Error message
```

---

## Monitoring \u0026 Debugging

### Check Scheduler Status

**View running schedulers:**
```bash
docker compose logs -f --tail=100 | grep "scheduler"
```

**Check specific scheduler:**
```bash
docker compose logs -f --tail=100 | grep "WF7"
```

### Common Issues

**Issue:** Records stuck in "Queued" status
**Check:**
1. Is the scheduler running? (Check logs)
2. Is the interval too long? (Check env vars)
3. Are there errors? (Check `{service}_processing_error` field)

**Issue:** Scheduler processing too slowly
**Check:**
1. Increase batch size (if API allows)
2. Decrease interval (if safe)
3. Check for retry backoff delays

**Issue:** Duplicate processing
**Check:**
1. Verify `max_instances=1` in scheduler config
2. Check for race conditions in dual-status adapter

---

## Performance Optimization

### Database Indexes

**Critical indexes for scheduler performance:**

```sql
-- Queued status lookup
CREATE INDEX idx_{table}_processing_status ON {table}(processing_status);

-- Retry scheduling
CREATE INDEX idx_{table}_next_retry_at ON {table}(next_retry_at)
WHERE next_retry_at IS NOT NULL;

-- Error tracking
CREATE INDEX idx_{table}_retry_count ON {table}(retry_count)
WHERE retry_count > 0;
```

### API Response Times (Expected)

**External APIs:**
- Brevo: 200-500ms per contact
- HubSpot: 300-600ms per contact
- DeBounce: 500-1000ms per email
- n8n: 100-300ms per webhook POST

**Database Operations:**
- Status updates: < 50ms
- Batch queries: < 200ms

---

## Scheduler Registration

**All schedulers are registered in `src/main.py` using APScheduler:**

Schedulers use the shared `scheduler` instance from `src/scheduler_instance.py` and are registered via the FastAPI `lifespan` context manager.

```python
# Import setup functions from each scheduler module
from src.services.background.wf2_deep_scan_scheduler import setup_deep_scan_scheduler
from src.services.background.wf3_domain_extraction_scheduler import setup_domain_extraction_scheduler
from src.services.background.wf4_domain_monitor_scheduler import setup_domain_scheduler
from src.services.background.wf4_sitemap_discovery_scheduler import setup_sitemap_discovery_scheduler
from src.services.background.wf5_sitemap_import_scheduler import setup_sitemap_import_scheduler
from src.services.background.wf7_page_curation_scheduler import setup_page_curation_scheduler
from src.services.background.wf8_crm_brevo_sync_scheduler import setup_brevo_sync_scheduler
from src.services.background.wf8_crm_hubspot_sync_scheduler import setup_hubspot_sync_scheduler
from src.services.background.wf8_crm_n8n_sync_scheduler import setup_n8n_sync_scheduler
from src.services.background.wf8_crm_debounce_scheduler import setup_debounce_validation_scheduler

# Register via lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()  # Start APScheduler

    # Add jobs to shared scheduler
    setup_domain_scheduler()           # WF4 Domain Monitor
    setup_deep_scan_scheduler()        # WF2
    setup_domain_extraction_scheduler() # WF3
    setup_sitemap_discovery_scheduler() # WF4 Sitemap
    setup_sitemap_import_scheduler()   # WF5
    setup_page_curation_scheduler()    # WF7
    setup_brevo_sync_scheduler()       # WF8 Brevo
    setup_hubspot_sync_scheduler()     # WF8 HubSpot
    setup_debounce_validation_scheduler() # WF8 DeBounce
    setup_n8n_sync_scheduler()         # WF8 n8n

    yield

    shutdown_scheduler()  # Cleanup on shutdown
```

**Each scheduler's `setup_*` function adds a job to APScheduler:**

```python
# Example from wf2_deep_scan_scheduler.py
def setup_deep_scan_scheduler():
    scheduler.add_job(
        process_deep_scan_queue,
        trigger="interval",
        minutes=settings.DEEP_SCAN_SCHEDULER_INTERVAL_MINUTES,
        id="process_deep_scan_queue",
        name="WF2 - Deep Scan Queue Processor",
        replace_existing=True,
        max_instances=settings.DEEP_SCAN_SCHEDULER_MAX_INSTANCES,
        coalesce=True,
        misfire_grace_time=60,
    )
```

---

## Future Enhancements

### Adaptive Intervals

**Concept:** Adjust interval based on queue size

```python
if queue_size > 100:
    interval = 30 seconds  # Process faster
elif queue_size > 10:
    interval = 1 minute    # Normal speed
else:
    interval = 5 minutes   # Slow down when idle
```

**Benefits:**
- ✅ Faster processing during high load
- ✅ Reduced CPU usage during idle periods

**Estimated Effort:** 4-6 hours
**Work Order:** WO-034 (to be created)

---

**Status:** 📋 Reference Complete - Use for debugging and optimization
