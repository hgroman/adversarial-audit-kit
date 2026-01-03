"""
Compliance Test Suite Template

This template shows the structure for generated compliance tests.
Each test class corresponds to one auditor domain.
Each test method verifies one or more findings.

USAGE:
  The compliance-test-orchestrator reads audit findings and generates
  a test file following this structure, with tests specific to the
  violations found.

CONVENTIONS:
  - Class names: Test{Domain}Compliance
  - Method names: test_{what}_{expectation}
  - Docstrings: Must cite LAW and FINDING
  - Assertions: Must include actionable error message
"""

import ast
import re
from pathlib import Path
from typing import List, Set
import pytest


# =============================================================================
# STRUCTURAL COMPLIANCE (ARCH-*)
# =============================================================================

class TestArchitecturalCompliance:
    """
    Tests for structural integrity violations found by the Architect auditor.

    Covers:
    - Import chain violations
    - Layer separation
    - Naming conventions
    - Schema-model synchronization
    """

    def test_example_layer_violation(self):
        """
        LAW: SESSION-AND-TENANT-LAW.md §Layer Separation
        FINDING: ARCH-XXX - Services must not import routers

        Services are layer 4, routers are layer 3.
        Higher layers may not depend on lower layers.
        """
        violations: List[str] = []
        services_dir = Path("src/services")

        if not services_dir.exists():
            pytest.skip("src/services directory not found")

        for py_file in services_dir.rglob("*.py"):
            content = py_file.read_text()
            if "from src.routers" in content:
                violations.append(str(py_file))

        assert violations == [], (
            f"Layer violation - services importing routers:\n"
            f"  {chr(10).join(f'  - {v}' for v in violations)}\n\n"
            f"LAW: Services (L4) must not import routers (L3).\n"
            f"FIX: Move shared logic to a lower layer or use dependency injection."
        )


# =============================================================================
# SECURITY COMPLIANCE (SEC-*)
# =============================================================================

class TestSecurityCompliance:
    """
    Tests for security violations found by the Data Assassin auditor.

    Covers:
    - RLS policy compliance
    - Tenant isolation
    - Role management (SET/RESET)
    - Hardcoded credentials/IDs
    """

    def test_example_role_management(self):
        """
        LAW: SESSION-AND-TENANT-LAW.md §Rule 4
        FINDING: SEC-XXX - Every SET ROLE must have RESET ROLE

        Role leak vulnerability: If SET ROLE is called without
        RESET ROLE in a finally block, subsequent queries may
        run with wrong permissions.
        """
        violations: List[str] = []

        for py_file in Path("src").rglob("*.py"):
            content = py_file.read_text()

            set_role_count = len(re.findall(r"SET ROLE", content))
            reset_role_count = len(re.findall(r"RESET ROLE", content))

            if set_role_count > 0 and set_role_count > reset_role_count:
                violations.append(
                    f"{py_file}: {set_role_count} SET ROLE, {reset_role_count} RESET ROLE"
                )

        assert violations == [], (
            f"Role leak vulnerability:\n"
            f"  {chr(10).join(f'  - {v}' for v in violations)}\n\n"
            f"LAW: Every SET ROLE must have RESET ROLE in finally block.\n"
            f"FIX: Wrap SET ROLE in try/finally with RESET ROLE in finally."
        )


# =============================================================================
# BUILD COMPLIANCE (DEVOPS-*)
# =============================================================================

class TestBuildCompliance:
    """
    Tests for build/deploy violations found by the DevOps auditor.

    Covers:
    - Dependency management
    - Router registration
    - Environment variables
    - Docker build requirements
    """

    def test_example_router_registration(self):
        """
        LAW: FastAPI router registration protocol
        FINDING: DEVOPS-XXX - All routers must be registered in main.py

        Unregistered routers return 404 for all their endpoints.
        """
        main_file = Path("src/main.py")
        if not main_file.exists():
            pytest.skip("src/main.py not found")

        main_content = main_file.read_text()
        routers_dir = Path("src/routers")

        violations: List[str] = []

        for py_file in routers_dir.glob("wf*.py"):
            router_module = py_file.stem
            if router_module not in main_content:
                violations.append(router_module)

        assert violations == [], (
            f"Unregistered routers (will return 404):\n"
            f"  {chr(10).join(f'  - {v}' for v in violations)}\n\n"
            f"LAW: All workflow routers must be registered in main.py.\n"
            f"FIX: Add 'from src.routers.{'{router}'} import router' and include_router()."
        )


# =============================================================================
# CONCURRENCY COMPLIANCE (KRAKEN-*)
# =============================================================================

class TestConcurrencyCompliance:
    """
    Tests for concurrency violations found by the Kraken auditor.

    Covers:
    - Blocking I/O patterns
    - Connection pool management
    - Rate limiting
    - Thread safety
    """

    def test_example_blocking_init(self):
        """
        LAW: L4_Service_Guardian §Lazy Initialization
        FINDING: KRAKEN-XXX - No blocking I/O in __init__

        Blocking calls in __init__ block the event loop during
        service instantiation, causing timeouts at load.
        """
        blocking_patterns = [
            "requests.get(", "requests.post(",
            "httpx.get(", "httpx.post(",
            "ChatOpenAI(", "OpenAI(",
        ]

        violations: List[str] = []

        for py_file in Path("src/services").rglob("*.py"):
            try:
                content = py_file.read_text()
                tree = ast.parse(content)
            except (SyntaxError, FileNotFoundError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                    init_source = ast.unparse(node)
                    for pattern in blocking_patterns:
                        if pattern in init_source:
                            violations.append(f"{py_file}: {pattern}")

        assert violations == [], (
            f"Blocking I/O in __init__ (blocks event loop):\n"
            f"  {chr(10).join(f'  - {v}' for v in violations)}\n\n"
            f"LAW: External clients must use lazy initialization.\n"
            f"FIX: Use @property with _client = None pattern."
        )


# =============================================================================
# OBSERVABILITY COMPLIANCE (OPS-*)
# =============================================================================

class TestObservabilityCompliance:
    """
    Tests for observability violations found by the Operator auditor.

    Covers:
    - Logging standards
    - Error handling
    - Health checks
    - Metrics exposure
    """

    def test_example_tenant_in_logs(self):
        """
        LAW: OBSERVABILITY-REQUIREMENTS.md §Structured Logging
        FINDING: OPS-XXX - All logs must include tenant_id

        Without tenant_id in logs, debugging multi-tenant issues
        at 2 AM is impossible.
        """
        # This is a heuristic check - services should have tenant context
        services_with_logging: List[str] = []
        services_with_tenant_logging: List[str] = []

        for py_file in Path("src/services").rglob("*.py"):
            content = py_file.read_text()

            has_logging = "logger." in content
            has_tenant = "tenant_id" in content

            if has_logging:
                services_with_logging.append(str(py_file))
                if has_tenant:
                    services_with_tenant_logging.append(str(py_file))

        # At least 50% of services with logging should have tenant context
        if len(services_with_logging) > 0:
            ratio = len(services_with_tenant_logging) / len(services_with_logging)
            assert ratio >= 0.5, (
                f"Low tenant context in logs ({ratio:.0%}):\n"
                f"  Services with logging: {len(services_with_logging)}\n"
                f"  Services with tenant_id: {len(services_with_tenant_logging)}\n\n"
                f"LAW: Service logs must include tenant_id for isolation.\n"
                f"FIX: Add extra={{'tenant_id': tenant_id}} to log calls."
            )


# =============================================================================
# COVERAGE COMPLIANCE (TEST-*)
# =============================================================================

class TestCoverageCompliance:
    """
    Tests for coverage violations found by the Test Sentinel auditor.

    Covers:
    - Minimum test counts
    - Required test categories
    - Fixture availability
    - RLS test coverage
    """

    def test_example_minimum_test_files(self):
        """
        LAW: WO-INTEGRATION-TEST-STANDARDIZATION.md §Acceptance Criteria
        FINDING: TEST-XXX - Minimum 20 tests per workflow

        Each workflow needs comprehensive test coverage across
        6 categories: happy path, errors, RLS, edge cases,
        fallback, concurrency.
        """
        tests_dir = Path("tests/integration")
        if not tests_dir.exists():
            pytest.skip("tests/integration directory not found")

        workflows = ["wf1", "wf4", "wf5", "wf7", "wf8", "wf10"]
        low_coverage: dict = {}

        for wf in workflows:
            test_files = list(tests_dir.glob(f"test_{wf}_*.py"))
            if len(test_files) < 3:  # Minimum 3 test files per workflow
                low_coverage[wf] = len(test_files)

        assert len(low_coverage) < len(workflows) // 2, (
            f"Workflows with insufficient test coverage:\n"
            f"  {low_coverage}\n\n"
            f"LAW: Each workflow needs minimum 3 integration test files.\n"
            f"FIX: Add test files for: happy path, errors, RLS isolation."
        )


# =============================================================================
# CUSTOM COMPLIANCE (Specific to this audit)
# =============================================================================

class TestCustomCompliance:
    """
    Tests for work-order-specific violations that don't fit other categories.

    These tests are generated based on unique findings in the audit
    that require custom detection logic.
    """

    def test_example_custom_check(self):
        """
        LAW: [Specific document]
        FINDING: [Specific finding ID]

        [Description of what this checks]
        """
        # Custom implementation based on finding
        pass


# =============================================================================
# TEST UTILITIES
# =============================================================================

def find_pattern_in_files(
    directory: Path,
    pattern: str,
    glob: str = "*.py"
) -> List[str]:
    """
    Utility to find regex pattern in files.

    Returns list of "file:line" for each match.
    """
    matches: List[str] = []

    for py_file in directory.rglob(glob):
        try:
            content = py_file.read_text()
            for i, line in enumerate(content.split("\n"), 1):
                if re.search(pattern, line):
                    matches.append(f"{py_file}:{i}")
        except (OSError, UnicodeDecodeError):
            continue

    return matches


def get_python_imports(file_path: Path) -> Set[str]:
    """
    Extract all imports from a Python file.

    Returns set of imported module names.
    """
    imports: Set[str] = set()

    try:
        tree = ast.parse(file_path.read_text())
    except (SyntaxError, FileNotFoundError):
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    return imports
