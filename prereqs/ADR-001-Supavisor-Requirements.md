# ADR-001: Supavisor Connection Requirements

**Status:** Active
**Date:** 2025-11-16
**Decision Makers:** System Architecture
**Related Files:** `src/db/session.py`

---

## Context

ScraperSky uses Supabase for PostgreSQL database hosting. Supabase provides Supavisor, a connection pooler that sits between the application and the database to manage connection efficiency at scale.

**The Challenge:** Supavisor has specific requirements for how applications connect to it. Using standard PostgreSQL connection parameters causes connection failures, query errors, and unpredictable behavior.

---

## Decision

**We exclusively use Supavisor with the following mandatory connection parameters:**

```python
# Port
SUPABASE_POOLER_PORT = 6543  # Must use Supavisor port, NOT 5432

# Connection String Parameters (MANDATORY)
postgresql+asyncpg://user:password@host:6543/database?raw_sql=true&no_prepare=true&statement_cache_size=0
```

**These three parameters are REQUIRED and IMMUTABLE:**

1. **`raw_sql=true`** - Use raw SQL instead of ORM-prepared statements
2. **`no_prepare=true`** - Disable prepared statements for Supavisor compatibility
3. **`statement_cache_size=0`** - Disable statement caching

---

## Rationale

### Why Port 6543?
- Port 5432 connects directly to PostgreSQL (bypasses Supavisor)
- Port 6543 connects through Supavisor (connection pooling enabled)
- Direct connections (5432) don't scale and can exhaust database connections
- Supavisor (6543) manages connection pooling, allowing thousands of app connections to share a smaller pool of database connections

### Why `raw_sql=true`?
- Supavisor requires raw SQL for proper query routing
- ORM-prepared statements can cause routing failures
- Ensures queries are processed correctly through the pooler

### Why `no_prepare=true`?
- Prepared statements don't work reliably with Supavisor's connection pooling
- Each pooled connection may go to a different backend
- Prepared statements are session-specific and break when connections are pooled
- Disabling prevents "prepared statement does not exist" errors

### Why `statement_cache_size=0`?
- Prevents caching of prepared statements
- Works in conjunction with `no_prepare=true`
- Ensures consistent behavior across pooled connections
- Eliminates cache-related errors in pooled environment

---

## Consequences

### Positive
✅ **Reliable database connections** - No mysterious connection failures
✅ **Proper connection pooling** - Application scales without exhausting database connections
✅ **No prepared statement errors** - Queries work consistently
✅ **Supabase best practices** - Following official Supavisor requirements

### Negative
⚠️ **Cannot use standard PostgreSQL drivers** - Must use these exact parameters
⚠️ **Slightly reduced query performance** - Prepared statements would be faster, but don't work with Supavisor
⚠️ **Cannot change parameters** - These are immutable requirements, not preferences

### Trade-offs
- **Sacrificed:** Minor query performance optimization from prepared statements
- **Gained:** Reliable connection pooling and scalability

---

## Implementation

**Location:** `src/db/session.py` (connection configuration)

```python
# Connection string construction
connection_string = (
    f"postgresql+asyncpg://{settings.supabase_pooler_user}:{password}@"
    f"{settings.supabase_pooler_host}:{settings.supabase_pooler_port}/"
    f"{settings.supabase_pooler_database}"
    f"?raw_sql=true&no_prepare=true&statement_cache_size=0"
)

# CRITICAL: DO NOT MODIFY THESE PARAMETERS
# They are required for Supavisor compatibility
```

**Code Comments:**
- Marked with `# CRITICAL: DO NOT MODIFY` warnings
- Documented in CLAUDE.md
- Referenced in architecture documentation

---

## Enforcement

**This decision is enforced through:**

1. **Code Comments** - `DO NOT MODIFY` warnings in `async_session.py`
2. **Documentation** - CLAUDE.md explicitly states these are mandatory
3. **This ADR** - Explains WHY they cannot be changed
4. **Code Review** - Any PR attempting to modify these parameters should be rejected

**If you see these parameters and think "I could optimize this":**
- **STOP**
- Read this ADR
- Understand they are Supavisor requirements, not preferences
- Do not modify

---

## Related Decisions

- **ADR-004:** Transaction Boundaries (uses these connections)
- **Configuration:** `src/config/settings.py` defines Supavisor connection variables

---

## References

- **Supabase Supavisor Documentation:** https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler
- **Implementation:** `src/db/session.py`

---

## Revision History

- **2025-11-16:** Initial ADR created from codebase analysis and audit findings
