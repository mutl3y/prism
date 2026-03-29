"""Shared pytest fixtures for prism scanner unit tests.

Provides reusable fixtures for mock objects, test data, and test role
setup to reduce duplication across unit test modules and enable consistent
test isolation patterns.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from prism.scanner_core import DIContainer, FeatureDetector, VariableDiscovery
from prism.scanner_data.contracts import FeaturesContext, VariableRow

# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_variable_discovery() -> Mock:
    """Mock VariableDiscovery for unit tests.

    Returns a Mock with discover() returning an empty tuple by default.
    Tests can override return_value or side_effect as needed.
    """
    mock = Mock(spec=VariableDiscovery)
    mock.discover.return_value = ()
    mock.discover_static.return_value = ()
    mock.discover_referenced.return_value = ()
    return mock


@pytest.fixture
def mock_feature_detector() -> Mock:
    """Mock FeatureDetector for unit tests.

    Returns a Mock with detect() returning empty FeaturesContext by default.
    Tests can override return_value or side_effect as needed.
    """
    mock = Mock(spec=FeatureDetector)
    mock.detect.return_value = FeaturesContext()
    mock.analyze_task_catalog.return_value = {}
    return mock


@pytest.fixture
def mock_di_container() -> Mock:
    """Mock DIContainer for unit tests.

    Returns a Mock with factory methods configured to return mocks.
    Tests can override factory methods as needed.
    """
    mock = Mock(spec=DIContainer)
    mock.factory_variable_discovery.return_value = Mock(spec=VariableDiscovery)
    mock.factory_feature_detector.return_value = Mock(spec=FeatureDetector)
    return mock


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def test_variable_row() -> VariableRow:
    """Sample VariableRow for testing.

    Provides a minimal valid VariableRow with typical defaults.
    """
    return VariableRow(
        name="test_variable",
        type="string",
        documented=False,
        required=False,
        secret=False,
        default=None,
        description=None,
        confidence=0.8,
    )


@pytest.fixture
def test_variable_rows() -> tuple[VariableRow, ...]:
    """Sample collection of VariableRows for testing.

    Provides a tuple of 3 typical variables: string, list, and dict.
    """
    return (
        VariableRow(
            name="string_var",
            type="string",
            documented=True,
            required=False,
            secret=False,
            default="default_value",
            description="A string variable",
            confidence=0.9,
        ),
        VariableRow(
            name="list_var",
            type="list",
            documented=True,
            required=True,
            secret=False,
            default=None,
            description="A list variable",
            confidence=0.8,
        ),
        VariableRow(
            name="secret_var",
            type="string",
            documented=False,
            required=False,
            secret=True,
            default=None,
            description=None,
            confidence=0.6,
        ),
    )


@pytest.fixture
def test_features_context() -> FeaturesContext:
    """Sample FeaturesContext for testing.

    Provides a minimal valid FeaturesContext with typical defaults.
    """
    return FeaturesContext(
        task_files_scanned=2,
        tasks_scanned=10,
        recursive_task_includes=0,
        unique_modules="gcloud,kubernetes",
        external_collections="community.general",
        handlers_notified="restart_service",
        privileged_tasks=1,
        conditional_tasks=3,
        tagged_tasks=5,
        included_role_calls=0,
        included_roles="none",
        dynamic_included_role_calls=0,
        dynamic_included_roles="none",
        disabled_task_annotations=0,
        yaml_like_task_annotations=2,
    )


@pytest.fixture
def test_di_container() -> DIContainer:
    """Real DIContainer for testing (non-mocked).

    Creates a DIContainer with minimal config pointing to a non-existent
    role (tests should not access the filesystem).
    """
    return DIContainer(
        role_path="/tmp/test_role",
        scan_options={
            "role_path": "/tmp/test_role",
            "include_vars_main": True,
            "exclude_path_patterns": None,
            "vars_seed_paths": None,
            "ignore_unresolved_internal_underscore_references": False,
        },
    )


# ============================================================================
# Test Role Fixtures
# ============================================================================


@pytest.fixture
def empty_test_role(tmp_path: Path) -> Path:
    """Empty Ansible role for testing.

    Creates a minimal role structure with no files.

    Returns:
        Path: Path to the test role directory.
    """
    role_path = tmp_path / "test_role"
    role_path.mkdir(parents=True, exist_ok=True)
    return role_path


@pytest.fixture
def basic_test_role(tmp_path: Path) -> Path:
    """Basic Ansible role with minimal files for testing.

    Creates a role structure with:
    - defaults/main.yml: simple variables
    - tasks/main.yml: basic task list

    Returns:
        Path: Path to the test role directory.
    """
    role_path = tmp_path / "basic_role"

    # Create directory structure
    (role_path / "defaults").mkdir(parents=True, exist_ok=True)
    (role_path / "tasks").mkdir(parents=True, exist_ok=True)

    # Create defaults/main.yml
    (role_path / "defaults" / "main.yml").write_text(
        "---\ntest_variable: test_value\nenabled: true\n",
        encoding="utf-8",
    )

    # Create tasks/main.yml
    (role_path / "tasks" / "main.yml").write_text(
        "---\n" "- name: Test task\n" "  debug:\n" "    msg: '{{ test_variable }}'\n",
        encoding="utf-8",
    )

    return role_path


@pytest.fixture
def complex_test_role(tmp_path: Path) -> Path:
    """Complex Ansible role with multiple files for testing.

    Creates a role structure with:
    - defaults/main.yml: multiple variables
    - tasks/main.yml: multiple tasks with handlers
    - handlers/main.yml: handler definitions
    - templates/: example template

    Returns:
        Path: Path to the test role directory.
    """
    role_path = tmp_path / "complex_role"

    # Create directory structure
    (role_path / "defaults").mkdir(parents=True, exist_ok=True)
    (role_path / "tasks").mkdir(parents=True, exist_ok=True)
    (role_path / "handlers").mkdir(parents=True, exist_ok=True)
    (role_path / "templates").mkdir(parents=True, exist_ok=True)

    # Create defaults/main.yml
    (role_path / "defaults" / "main.yml").write_text(
        "---\n"
        "app_name: myapp\n"
        "app_version: 1.0.0\n"
        "app_port: 8080\n"
        "app_config:\n"
        "  debug: false\n"
        "  timeout: 30\n",
        encoding="utf-8",
    )

    # Create tasks/main.yml
    (role_path / "tasks" / "main.yml").write_text(
        "---\n"
        "- name: Install application\n"
        "  apt:\n"
        "    name: '{{ app_name }}'\n"
        "    state: present\n"
        "  notify: restart app\n"
        "\n"
        "- name: Configure application\n"
        "  template:\n"
        "    src: app.conf.j2\n"
        "    dest: /etc/app/config\n"
        "  notify: restart app\n",
        encoding="utf-8",
    )

    # Create handlers/main.yml
    (role_path / "handlers" / "main.yml").write_text(
        "---\n"
        "- name: restart app\n"
        "  systemd:\n"
        "    name: '{{ app_name }}'\n"
        "    state: restarted\n",
        encoding="utf-8",
    )

    # Create templates/app.conf.j2
    (role_path / "templates" / "app.conf.j2").write_text(
        "# Configuration for {{ app_name }}\n"
        "port: {{ app_port }}\n"
        "version: {{ app_version }}\n",
        encoding="utf-8",
    )

    return role_path


# ============================================================================
# Marker Fixtures
# ============================================================================


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test (may be slow, requires files)",
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as a unit test (fast, isolated, mocked)",
    )
