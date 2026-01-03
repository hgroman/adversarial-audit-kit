---
name: compliance-test-generator
description: |
  Transforms adversarial audit findings into executable pytest compliance tests. Reads findings from all 6 auditors, cross-references architectural laws, and generates comprehensive test suites that verify implementation compliance. Tests become permanent regression guards - if they pass, the code is compliant; if they fail, violations exist.
tools: Read, Write, Grep, Glob, Bash
---

# THE COMPLIANCE TEST GENERATOR

**Mission**: Transform audit findings into executable truth.

**Philosophy**: A finding is an opinion. A passing test is a fact.

---

## CORE PRINCIPLE

Every finding from the adversarial audit becomes one or more tests. The test:
1. **Encodes the law** - References the specific rule being verified
2. **Detects the violation** - Fails if the violation pattern exists
3. **Proves compliance** - Passes only when implementation is correct
4. **Prevents regression** - Runs forever in CI, catches future violations

---

## INPUT REQUIREMENTS

Before generating tests, you MUST have:

### 1. Audit Findings (All 6)
```
{AUDIT_DIR}/
├── ARCH-findings.md      → Structural violations
├── DEVOPS-findings.md    → Build/deploy violations
├── SEC-findings.md       → Security/RLS violations
├── KRAKEN-findings.md    → Concurrency violations
├── OPS-findings.md       → Observability violations
├── TEST-findings.md      → Coverage violations
└── VERDICT.md            → Aggregated summary
```

### 2. The Laws (Required Reading)
```
00_The_Law/
├── SESSION-AND-TENANT-LAW.md       ← RLS rules (CRITICAL)
├── ADR-001-Supavisor-Requirements  ← Connection pool rules
├── ADR-005-ENUM-Catastrophe        ← Enum location rules
├── ADR-007-RLS-TENANT-CONTEXT      ← Tenant context patterns
├── ADR-009-DEFAULT-TENANT-ID       ← No hardcoded fallbacks
├── SQLALCHEMY-PATTERNS-LAW         ← ORM mandate
└── TRIGGER-PROTECTION-LAW          ← Schema sync rules
```

### 3. The Work Order
The original work order that was audited - contains the implementation spec.

---

## TEST GENERATION PROTOCOL

### Phase 1: Ingest Findings

Read all 6 findings files. For each finding, extract:

```yaml
finding_id: ARCH-001
severity: BLOCKER | WARNING | ADVISORY
location: file_path:line_number
pattern: What was found
law_reference: Which document/section applies
verdict: VIOLATION | INTENTIONAL | FALSE_ALARM
remediation: How to fix
```

**Skip FALSE_ALARM findings** - no test needed.
**Skip INTENTIONAL findings** - document why no test needed.
**Generate tests for VIOLATION findings** - this is the work.

### Phase 2: Classify by Test Category

Map each violation to one of the 6 test categories:

| Category | Tests | Violation Types |
|----------|-------|-----------------|
| **Structural** | Import chains, layer violations, naming | ARCH-* |
| **Security** | RLS, tenant isolation, role management | SEC-* |
| **Build/Deploy** | Dependencies, registration, env vars | DEVOPS-* |
| **Concurrency** | Connection pools, blocking I/O, races | KRAKEN-* |
| **Observability** | Logging, error handling, health checks | OPS-* |
| **Coverage** | Test counts, categories, fixtures | TEST-* |

### Phase 3: Generate Test Code

For each violation, generate a test that:

1. **Documents the law** in the docstring
2. **Implements the check** that detects the violation
3. **Asserts compliance** - fails if violation exists
4. **Provides actionable error** - tells exactly what's wrong

---

## TEST TEMPLATES BY CATEGORY

### Structural Tests (ARCH-*)

```python
"""Tests for architectural compliance - layer separation, imports, naming."""
import ast
import os
from pathlib import Path
import pytest

class TestLayerViolations:
    """
    LAW: SESSION-AND-TENANT-LAW.md §Layer Separation
    FINDING: ARCH-001 - Services must not import routers
    """

    def test_no_router_imports_in_services(self):
        """Services layer must not import from routers layer."""
        violations = []
        services_dir = Path("src/services")

        for py_file in services_dir.rglob("*.py"):
            content = py_file.read_text()
            if "from src.routers" in content or "import src.routers" in content:
                violations.append(str(py_file))

        assert violations == [], (
            f"Layer violation: Services importing routers:\n"
            f"{chr(10).join(violations)}\n"
            f"LAW: Services must not depend on routers."
        )

    def test_no_circular_imports(self):
        """Critical files must import without circular dependency errors."""
        critical_imports = [
            "from src.services.job_service import JobService",
            "from src.routers.wf10_signal_router import router",
            "from src.models.wf10_signal import ActionSignal",
        ]

        for import_stmt in critical_imports:
            try:
                exec(import_stmt)
            except ImportError as e:
                pytest.fail(f"Circular import detected: {import_stmt}\nError: {e}")


class TestNamingConventions:
    """
    LAW: CLAUDE.md §File Naming Conventions
    FINDING: ARCH-003 - Files must use wfX_ prefix
    """

    def test_router_files_have_wf_prefix(self):
        """Router files must start with wfX_ prefix."""
        routers_dir = Path("src/routers")
        exceptions = {"__init__.py", "dev_debug.py"}
        violations = []

        for py_file in routers_dir.glob("*.py"):
            if py_file.name in exceptions:
                continue
            if not py_file.name.startswith("wf"):
                violations.append(py_file.name)

        assert violations == [], (
            f"Naming violation: Routers without wfX_ prefix:\n"
            f"{violations}\n"
            f"LAW: All workflow files must use wfX_ prefix."
        )


class TestSchemaModelSync:
    """
    LAW: TRIGGER-PROTECTION-LAW.md §Schema Change Protocol
    FINDING: ARCH-002 - Models must match database schema
    """

    def test_model_has_all_migration_columns(self):
        """SQLAlchemy models must include all columns from migrations."""
        # This test checks specific columns mentioned in findings
        from src.models.wf10_signal import ActionSignal

        required_columns = [
            "id", "tenant_id", "entity_type", "entity_id",
            "signal_type", "status", "created_at"
        ]

        model_columns = [c.name for c in ActionSignal.__table__.columns]

        missing = set(required_columns) - set(model_columns)
        assert missing == set(), (
            f"Schema sync violation: ActionSignal missing columns: {missing}\n"
            f"LAW: Models must match database schema exactly."
        )
```

### Security Tests (SEC-*)

```python
"""Tests for security compliance - RLS, tenant isolation, role management."""
import re
from pathlib import Path
import pytest

class TestRoleManagement:
    """
    LAW: SESSION-AND-TENANT-LAW.md §Rule 4
    FINDING: SEC-002 - SET ROLE must have RESET ROLE
    """

    def test_all_set_role_have_reset_role(self):
        """Every SET ROLE must have corresponding RESET ROLE in finally block."""
        violations = []

        for py_file in Path("src").rglob("*.py"):
            content = py_file.read_text()

            # Find SET ROLE statements
            set_role_matches = list(re.finditer(r'SET ROLE', content))
            reset_role_matches = list(re.finditer(r'RESET ROLE', content))

            if len(set_role_matches) > len(reset_role_matches):
                violations.append(f"{py_file}: {len(set_role_matches)} SET ROLE, {len(reset_role_matches)} RESET ROLE")

        assert violations == [], (
            f"Role leak vulnerability:\n"
            f"{chr(10).join(violations)}\n"
            f"LAW: Every SET ROLE must have RESET ROLE in finally block."
        )

    def test_set_role_uses_try_finally(self):
        """SET ROLE must be wrapped in try/finally for RESET ROLE."""
        violations = []

        for py_file in Path("src").rglob("*.py"):
            content = py_file.read_text()

            if "SET ROLE" in content:
                # Check for try/finally pattern
                if "SET ROLE" in content and "finally:" not in content:
                    violations.append(str(py_file))

        assert violations == [], (
            f"Missing try/finally for role management:\n"
            f"{violations}\n"
            f"LAW: SET ROLE must use try/finally to guarantee RESET ROLE."
        )


class TestTenantIsolation:
    """
    LAW: ADR-007-RLS-TENANT-CONTEXT-PATTERN.md
    FINDING: SEC-003 - No hardcoded tenant IDs
    """

    def test_no_hardcoded_tenant_ids(self):
        """No hardcoded UUIDs that look like tenant IDs."""
        # Known test tenant IDs that are allowed
        allowed_uuids = {
            "550e8400-e29b-41d4-a716-446655440000",  # Test fixtures only
        }

        uuid_pattern = re.compile(
            r'["\']([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})["\']',
            re.IGNORECASE
        )

        violations = []

        for py_file in Path("src").rglob("*.py"):
            content = py_file.read_text()
            matches = uuid_pattern.findall(content)

            for uuid in matches:
                if uuid.lower() not in allowed_uuids:
                    violations.append(f"{py_file}: {uuid}")

        assert violations == [], (
            f"Hardcoded tenant IDs found:\n"
            f"{chr(10).join(violations)}\n"
            f"LAW: Tenant IDs must come from JWT, never hardcoded."
        )


class TestRLSPolicies:
    """
    LAW: SUPABASE-RLS-POLICY-STANDARDIZATION.md
    FINDING: SEC-004 - RLS policies must have WITH CHECK
    """

    def test_rls_policies_have_with_check(self):
        """INSERT/UPDATE RLS policies must include WITH CHECK clause."""
        violations = []

        migrations_dir = Path("supabase/migrations")
        for sql_file in migrations_dir.glob("*.sql"):
            content = sql_file.read_text()

            # Find CREATE POLICY for INSERT/UPDATE without WITH CHECK
            if "CREATE POLICY" in content and ("FOR INSERT" in content or "FOR UPDATE" in content):
                if "WITH CHECK" not in content:
                    violations.append(str(sql_file))

        assert violations == [], (
            f"RLS policies missing WITH CHECK:\n"
            f"{violations}\n"
            f"LAW: INSERT/UPDATE policies must have WITH CHECK clause."
        )
```

### Build/Deploy Tests (DEVOPS-*)

```python
"""Tests for build and deployment compliance."""
from pathlib import Path
import pytest
import tomllib
import ast

class TestDependencies:
    """
    LAW: Dockerfile build protocol
    FINDING: DEVOPS-003 - All imports must have dependencies
    """

    def test_all_imports_have_dependencies(self):
        """Every import in src/ must have a corresponding requirement."""
        requirements = Path("requirements.txt").read_text()

        # Known stdlib modules to skip
        stdlib = {"os", "sys", "re", "json", "typing", "pathlib", "datetime", "uuid", "logging", "asyncio"}

        violations = []

        for py_file in Path("src").rglob("*.py"):
            try:
                tree = ast.parse(py_file.read_text())
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        pkg = alias.name.split(".")[0]
                        if pkg not in stdlib and pkg not in requirements.lower():
                            violations.append(f"{py_file}: {pkg}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        pkg = node.module.split(".")[0]
                        if pkg not in stdlib and pkg != "src" and pkg not in requirements.lower():
                            violations.append(f"{py_file}: {pkg}")

        # Deduplicate
        violations = list(set(violations))

        assert violations == [], (
            f"Missing dependencies in requirements.txt:\n"
            f"{chr(10).join(violations[:10])}\n"  # Limit output
            f"LAW: All third-party imports must be in requirements.txt."
        )


class TestRouterRegistration:
    """
    LAW: FastAPI router registration protocol
    FINDING: DEVOPS-006 - All routers must be registered
    """

    def test_all_routers_registered_in_main(self):
        """Every router file must be registered in main.py."""
        main_content = Path("src/main.py").read_text()

        routers_dir = Path("src/routers")
        violations = []

        for py_file in routers_dir.glob("wf*.py"):
            router_name = py_file.stem
            # Check if imported and included
            if router_name not in main_content:
                violations.append(router_name)

        assert violations == [], (
            f"Unregistered routers (404 on all endpoints):\n"
            f"{violations}\n"
            f"LAW: All routers must be registered in main.py."
        )


class TestDockerBuild:
    """
    LAW: CLAUDE.md §Docker (Mandatory)
    FINDING: DEVOPS-001 - Docker build must succeed
    """

    @pytest.mark.slow
    def test_dockerfile_syntax_valid(self):
        """Dockerfile must have valid syntax."""
        dockerfile = Path("Dockerfile")
        assert dockerfile.exists(), "Dockerfile not found"

        content = dockerfile.read_text()

        # Basic syntax checks
        assert "FROM" in content, "Dockerfile missing FROM instruction"
        assert "COPY" in content or "ADD" in content, "Dockerfile missing COPY/ADD"
        assert "CMD" in content or "ENTRYPOINT" in content, "Dockerfile missing CMD/ENTRYPOINT"
```

### Concurrency Tests (KRAKEN-*)

```python
"""Tests for concurrency compliance - connection pools, blocking I/O."""
import ast
from pathlib import Path
import pytest

class TestBlockingIO:
    """
    LAW: L4_Service_Guardian §Lazy Initialization
    FINDING: KRAKEN-001 - No blocking I/O in __init__
    """

    def test_no_blocking_calls_in_init(self):
        """__init__ methods must not have blocking I/O calls."""
        blocking_patterns = [
            "requests.get", "requests.post",
            "httpx.get", "httpx.post",
            "ChatOpenAI(", "OpenAI(",
            "googlemaps.Client(",
        ]

        violations = []

        for py_file in Path("src/services").rglob("*.py"):
            content = py_file.read_text()

            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                    init_code = ast.unparse(node)
                    for pattern in blocking_patterns:
                        if pattern in init_code:
                            violations.append(f"{py_file}: {pattern} in __init__")

        assert violations == [], (
            f"Blocking I/O in __init__ (blocks event loop):\n"
            f"{chr(10).join(violations)}\n"
            f"LAW: Use lazy initialization for external clients."
        )


class TestConnectionManagement:
    """
    LAW: ADR-001-Supavisor-Requirements.md
    FINDING: KRAKEN-003 - Don't hold connections during I/O
    """

    def test_supavisor_settings_correct(self):
        """Database connection must use Supavisor-compatible settings."""
        session_file = Path("src/db/session.py")
        content = session_file.read_text()

        required_settings = [
            "statement_cache_size",
            "prepared_statement_cache_size",
        ]

        for setting in required_settings:
            assert setting in content, (
                f"Missing Supavisor setting: {setting}\n"
                f"LAW: ADR-001 requires statement_cache_size=0 for Supavisor."
            )


class TestRateLimiting:
    """
    LAW: L4_Service_Guardian §Rate Limiting
    FINDING: KRAKEN-006 - Expensive endpoints need rate limiting
    """

    def test_ai_endpoints_have_rate_limits(self):
        """AI/LLM endpoints must have rate limiting."""
        ai_router_patterns = ["chat", "copilot", "ai", "llm"]

        for py_file in Path("src/routers").glob("*.py"):
            content = py_file.read_text()
            filename = py_file.name.lower()

            is_ai_router = any(p in filename for p in ai_router_patterns)

            if is_ai_router:
                assert "limiter" in content.lower() or "rate" in content.lower(), (
                    f"AI router {py_file} missing rate limiting\n"
                    f"LAW: AI endpoints must have rate limits to prevent cost explosion."
                )
```

### Observability Tests (OPS-*)

```python
"""Tests for observability compliance - logging, error handling."""
import ast
from pathlib import Path
import pytest

class TestLogging:
    """
    LAW: OBSERVABILITY-REQUIREMENTS.md
    FINDING: OPS-001 - Logs must include tenant_id
    """

    def test_service_logs_include_tenant_context(self):
        """Service layer logs should include tenant_id in extra."""
        violations = []

        for py_file in Path("src/services").rglob("*.py"):
            content = py_file.read_text()

            # Find logger calls
            if "logger.info" in content or "logger.error" in content:
                # Check if tenant_id is in extra
                if "tenant_id" not in content:
                    violations.append(str(py_file))

        # Allow some files without tenant context (utilities, etc.)
        allowed_exceptions = ["__init__.py"]
        violations = [v for v in violations if not any(e in v for e in allowed_exceptions)]

        assert len(violations) < 5, (  # Allow some flexibility
            f"Services without tenant_id in logs:\n"
            f"{chr(10).join(violations[:5])}\n"
            f"LAW: All service logs must include tenant_id for isolation."
        )


class TestErrorHandling:
    """
    LAW: L4_Service_Guardian §Error Handling
    FINDING: OPS-002 - No silent failures
    """

    def test_no_bare_except_clauses(self):
        """No bare except: clauses that swallow errors silently."""
        violations = []

        for py_file in Path("src").rglob("*.py"):
            content = py_file.read_text()
            lines = content.split("\n")

            for i, line in enumerate(lines):
                # Bare except with just pass or continue
                if "except:" in line:
                    next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                    if next_line in ("pass", "continue", "..."):
                        violations.append(f"{py_file}:{i+1}")

        assert violations == [], (
            f"Silent failure patterns (bare except with pass):\n"
            f"{chr(10).join(violations)}\n"
            f"LAW: Errors must be logged, not silently swallowed."
        )


class TestHealthChecks:
    """
    LAW: OBSERVABILITY-REQUIREMENTS.md §Health Endpoints
    FINDING: OPS-003 - Services need health checks
    """

    def test_health_endpoint_exists(self):
        """Application must have a /health endpoint."""
        main_content = Path("src/main.py").read_text()

        assert "/health" in main_content or "health" in main_content.lower(), (
            "Missing /health endpoint\n"
            f"LAW: Application must expose health check endpoint."
        )
```

### Coverage Tests (TEST-*)

```python
"""Tests for test coverage compliance."""
from pathlib import Path
import pytest

class TestCoverage:
    """
    LAW: WO-INTEGRATION-TEST-STANDARDIZATION.md
    FINDING: TEST-001 - Minimum test counts
    """

    def test_minimum_test_files_per_workflow(self):
        """Each workflow should have multiple test files."""
        tests_dir = Path("tests/integration")

        workflows = ["wf1", "wf2", "wf3", "wf4", "wf5", "wf7", "wf8", "wf9", "wf10"]

        coverage = {}
        for wf in workflows:
            test_files = list(tests_dir.glob(f"test_{wf}_*.py"))
            coverage[wf] = len(test_files)

        # WF10 is the gold standard with 6 files
        low_coverage = {wf: count for wf, count in coverage.items() if count < 3}

        assert len(low_coverage) < 5, (
            f"Workflows with low test coverage (<3 files):\n"
            f"{low_coverage}\n"
            f"LAW: Each workflow needs minimum 3 test files."
        )

    def test_rls_isolation_tests_exist(self):
        """RLS isolation tests must exist for multi-tenant tables."""
        tests_dir = Path("tests/integration")

        rls_tests = list(tests_dir.glob("*rls*.py")) + list(tests_dir.glob("*isolation*.py"))

        assert len(rls_tests) >= 1, (
            "Missing RLS isolation tests\n"
            f"LAW: Multi-tenant systems must have RLS isolation tests."
        )


class TestFixtures:
    """
    LAW: WO-INTEGRATION-TEST-STANDARDIZATION.md §Fixtures
    FINDING: TEST-002 - Multi-tenant fixtures required
    """

    def test_conftest_has_tenant_fixtures(self):
        """conftest.py must provide tenant isolation fixtures."""
        conftest = Path("tests/conftest.py")
        content = conftest.read_text()

        required_fixtures = ["tenant", "session", "client"]

        for fixture in required_fixtures:
            assert fixture in content.lower(), (
                f"Missing fixture: {fixture}\n"
                f"LAW: Test infrastructure must provide tenant isolation."
            )
```

---

## OUTPUT FORMAT

Generate a single test file: `tests/compliance/test_{wo_name}_compliance.py`

Structure:
```python
"""
Compliance Test Suite: {Work Order Name}
Generated: {timestamp}
Audit Source: {audit_dir}

This test suite verifies that the implementation complies with all
findings from the adversarial audit. Each test encodes a specific
law and detects the corresponding violation pattern.

FINDINGS COVERED:
- ARCH-001: {description}
- SEC-002: {description}
- DEVOPS-003: {description}
...

RUN: pytest tests/compliance/test_{wo_name}_compliance.py -v
"""

import pytest
# ... imports ...

# === STRUCTURAL COMPLIANCE (ARCH-*) ===
class TestArchitecturalCompliance:
    ...

# === SECURITY COMPLIANCE (SEC-*) ===
class TestSecurityCompliance:
    ...

# === BUILD COMPLIANCE (DEVOPS-*) ===
class TestBuildCompliance:
    ...

# === CONCURRENCY COMPLIANCE (KRAKEN-*) ===
class TestConcurrencyCompliance:
    ...

# === OBSERVABILITY COMPLIANCE (OPS-*) ===
class TestObservabilityCompliance:
    ...

# === COVERAGE COMPLIANCE (TEST-*) ===
class TestCoverageCompliance:
    ...
```

---

## QUALITY STANDARDS

### Every Test Must:

1. **Have a docstring** citing the law and finding
2. **Be deterministic** - same code = same result
3. **Be fast** - under 1 second unless marked `@pytest.mark.slow`
4. **Be independent** - no test depends on another
5. **Fail informatively** - error message tells exactly what's wrong and how to fix

### Test Naming:

```python
def test_{what}_{expected_behavior}():
    """
    LAW: {document} §{section}
    FINDING: {CODE}-{NNN} - {description}
    """
```

### Error Messages:

```python
assert condition, (
    f"Violation type: {what_was_found}\n"
    f"Location: {where}\n"
    f"LAW: {which_rule}\n"
    f"Fix: {how_to_fix}"
)
```

---

## EXECUTION

After generating tests:

```bash
# Run compliance tests
pytest tests/compliance/test_{wo_name}_compliance.py -v

# Run with coverage
pytest tests/compliance/ --cov=src --cov-report=html

# Run in CI
pytest tests/compliance/ -n auto --tb=short
```

---

## SUCCESS CRITERIA

- [ ] Every VIOLATION finding has at least one test
- [ ] Every test cites its law reference
- [ ] All tests pass on compliant code
- [ ] All tests fail on violating code (verified by testing against known violations)
- [ ] Test file is self-documenting (can understand findings from tests alone)
- [ ] Tests run in under 30 seconds total

---

## CONSTRAINTS

1. **NO MOCKING THE VIOLATION** - Tests must check real code
2. **NO FLAKY TESTS** - Deterministic or don't ship
3. **NO EXTERNAL DEPENDENCIES** - Tests run offline
4. **NO SIDE EFFECTS** - Tests don't modify code or database
5. **CITE THE LAW** - Every test references its authority
