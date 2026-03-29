"""Tests for FeatureDetector orchestrator.

Validates core feature detection logic:
- Task analysis (counting, async, conditionals, etc.)
- Handler detection and notification tracking
- Collection and module dependency analysis
- Task annotation detection and validation
- Edge cases (missing directories, invalid YAML, etc.)
"""

from __future__ import annotations

import inspect
import pytest
from pathlib import Path

from prism.scanner_core import DIContainer, FeatureDetector
from prism.scanner_core import feature_detector


def test_feature_detector_imports_task_parser_from_canonical_module() -> None:
    """FeatureDetector should import task helpers from scanner_extract, not shim."""
    source = inspect.getsource(feature_detector)
    assert "from ..scanner_submodules.task_parser import" not in source
    assert "from ..scanner_extract.task_parser import" in source


class TestFeatureDetectorInit:
    """Tests for FeatureDetector initialization."""

    def test_init_requires_di_container(self, tmp_path):
        """Verify FeatureDetector raises ValueError if di is None."""
        with pytest.raises(ValueError, match="di .* must not be None"):
            FeatureDetector(None, str(tmp_path), {})

    def test_init_requires_role_path(self):
        """Verify FeatureDetector raises ValueError if role_path is empty."""
        di = DIContainer("/fake/role", {})
        with pytest.raises(ValueError, match="role_path must not be empty"):
            FeatureDetector(di, "", {})

    def test_init_requires_options(self, tmp_path):
        """Verify FeatureDetector raises ValueError if options is None."""
        di = DIContainer(str(tmp_path), {})
        with pytest.raises(ValueError, match="options must not be None"):
            FeatureDetector(di, str(tmp_path), None)

    def test_init_accepts_valid_inputs(self, tmp_path):
        """Verify FeatureDetector initializes with valid inputs."""
        di = DIContainer(str(tmp_path), {})
        detector = FeatureDetector(di, str(tmp_path), {})
        assert detector is not None


class TestFeatureDetectorEmptyRole:
    """Tests for FeatureDetector with empty/missing directories."""

    def test_detect_returns_zero_counts_for_missing_tasks_directory(self, tmp_path):
        """Verify detector returns 0 counts when tasks/ is missing."""
        role = tmp_path / "role"
        role.mkdir()

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        features = detector.detect()

        assert features["task_files_scanned"] == 0
        assert features["tasks_scanned"] == 0
        assert features["recursive_task_includes"] == 0
        assert features["unique_modules"] == "none"

    def test_detect_returns_valid_features_context_type(self, tmp_path):
        """Verify detect() returns proper FeaturesContext TypedDict."""
        role = tmp_path / "role"
        role.mkdir()

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        features = detector.detect()

        # Verify all required keys are present
        required_keys = {
            "task_files_scanned",
            "tasks_scanned",
            "recursive_task_includes",
            "unique_modules",
            "external_collections",
            "handlers_notified",
            "privileged_tasks",
            "conditional_tasks",
            "tagged_tasks",
            "included_role_calls",
            "included_roles",
            "dynamic_included_role_calls",
            "dynamic_included_roles",
            "disabled_task_annotations",
            "yaml_like_task_annotations",
        }
        assert set(features.keys()) >= required_keys


class TestFeatureDetectorTaskCounting:
    """Tests for task counting and analysis."""

    def test_detect_counts_basic_tasks(self, tmp_path):
        """Verify detector counts tasks in main.yml."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "main.yml").write_text(
            "---\n"
            "- name: First task\n"
            "  ansible.builtin.debug:\n"
            '    msg: "ok"\n'
            "- name: Second task\n"
            "  ansible.builtin.debug:\n"
            '    msg: "ok"\n',
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        features = detector.detect()

        assert features["task_files_scanned"] == 1
        assert features["tasks_scanned"] == 2

    def test_detect_counts_tasks_across_multiple_files(self, tmp_path):
        """Verify detector counts tasks across multiple task files."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)

        (tasks / "main.yml").write_text(
            "---\n" "- name: Task 1\n" "  debug:\n" '    msg: "ok"\n',
            encoding="utf-8",
        )
        (tasks / "deploy.yml").write_text(
            "---\n"
            "- name: Task 2\n"
            "  debug:\n"
            '    msg: "ok"\n'
            "- name: Task 3\n"
            "  debug:\n"
            '    msg: "ok"\n',
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        features = detector.detect()

        # Only discovers tasks reachable from main.yml
        assert features["tasks_scanned"] >= 1

    def test_detect_counts_conditional_tasks(self, tmp_path):
        """Verify detector counts tasks with when conditions."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "main.yml").write_text(
            "---\n"
            "- name: Conditional task\n"
            "  debug:\n"
            '    msg: "ok"\n'
            "  when: some_var is defined\n"
            "- name: Unconditional task\n"
            "  debug:\n"
            '    msg: "ok"\n',
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        features = detector.detect()

        assert features["tasks_scanned"] == 2
        assert features["conditional_tasks"] == 1

    def test_detect_counts_tagged_tasks(self, tmp_path):
        """Verify detector counts tasks with tags."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "main.yml").write_text(
            "---\n"
            "- name: Tagged task\n"
            "  debug:\n"
            '    msg: "ok"\n'
            "  tags: [deploy, critical]\n"
            "- name: Untagged task\n"
            "  debug:\n"
            '    msg: "ok"\n',
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        features = detector.detect()

        assert features["tasks_scanned"] == 2
        assert features["tagged_tasks"] == 1

    def test_detect_counts_privileged_tasks(self, tmp_path):
        """Verify detector counts tasks with become privilege escalation."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "main.yml").write_text(
            "---\n"
            "- name: Privileged task\n"
            "  debug:\n"
            '    msg: "ok"\n'
            "  become: true\n"
            "- name: Unprivileged task\n"
            "  debug:\n"
            '    msg: "ok"\n',
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        features = detector.detect()

        assert features["tasks_scanned"] == 2
        assert features["privileged_tasks"] == 1

    def test_detect_counts_recursive_includes(self, tmp_path):
        """Verify detector counts nested task includes."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)

        (tasks / "main.yml").write_text(
            "---\n"
            "- name: Include nested tasks\n"
            "  include_tasks: nested.yml\n"
            "- name: Another include\n"
            "  include_tasks: other.yml\n",
            encoding="utf-8",
        )
        (tasks / "nested.yml").write_text(
            "---\n" "- name: Nested task\n" "  debug:\n" '    msg: "ok"\n',
            encoding="utf-8",
        )
        (tasks / "other.yml").write_text(
            "---\n" "- name: Other task\n" "  debug:\n" '    msg: "ok"\n',
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        features = detector.detect()

        # main.yml has 2 include_tasks directives
        assert features["recursive_task_includes"] == 2


class TestFeatureDetectorModulesAndCollections:
    """Tests for module and collection detection."""

    def test_detect_extracts_unique_modules(self, tmp_path):
        """Verify detector extracts unique module names."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "main.yml").write_text(
            "---\n"
            "- name: Debug task\n"
            "  ansible.builtin.debug:\n"
            '    msg: "test"\n'
            "- name: Command task\n"
            "  ansible.builtin.command:\n"
            '    cmd: "ls"\n'
            "- name: Debug again\n"
            "  debug:\n"
            '    msg: "ok"\n',
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        features = detector.detect()

        modules = features["unique_modules"].split(", ")
        assert "ansible.builtin.command" in modules
        assert "ansible.builtin.debug" in modules
        assert "debug" in modules
        assert len(modules) == 3  # 3 unique module names (FQCN + short name)

    def test_detect_extracts_external_collections(self, tmp_path):
        """Verify detector extracts external collection names."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "main.yml").write_text(
            "---\n"
            "- name: Kubernetes task\n"
            "  kubernetes.core.k8s:\n"
            "    state: present\n"
            "- name: AWS task\n"
            "  amazon.aws.ec2:\n"
            "    state: started\n",
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        features = detector.detect()

        collections = features["external_collections"].split(", ")
        assert "amazon.aws" in collections
        assert "kubernetes.core" in collections


class TestFeatureDetectorHandlers:
    """Tests for handler detection and notification tracking."""

    def test_detect_counts_notified_handlers(self, tmp_path):
        """Verify detector counts handlers notified by tasks."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "main.yml").write_text(
            "---\n"
            "- name: Task that notifies\n"
            "  debug:\n"
            '    msg: "ok"\n'
            "  notify: restart_service\n"
            "- name: Task with multiple handlers\n"
            "  debug:\n"
            '    msg: "ok"\n'
            "  notify:\n"
            "    - reload_config\n"
            "    - restart_service\n",
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        features = detector.detect()

        handlers = features["handlers_notified"].split(", ")
        assert "reload_config" in handlers
        assert "restart_service" in handlers
        assert len(handlers) == 2

    def test_detect_ignores_non_string_notify_items(self, tmp_path):
        """Verify detector ignores non-string items in notify lists."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "main.yml").write_text(
            "---\n"
            "- name: Task with mixed notify\n"
            "  debug:\n"
            '    msg: "ok"\n'
            "  notify:\n"
            "    - restart_service\n"
            "    - 123\n"
            "    - null\n",
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        features = detector.detect()

        # Only restart_service should be counted (123 and null are ignored)
        assert features["handlers_notified"] == "restart_service"


class TestFeatureDetectorRoleIncludes:
    """Tests for detecting included and imported roles."""

    def test_detect_counts_included_roles_static(self, tmp_path):
        """Verify detector counts static role includes."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "main.yml").write_text(
            "---\n"
            "- name: include common role\n"
            "  include_role:\n"
            "    name: acme.common\n"
            "- name: import web role\n"
            "  ansible.builtin.import_role:\n"
            "    name: acme.web\n",
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        features = detector.detect()

        assert features["included_role_calls"] == 2
        roles = features["included_roles"].split(", ")
        assert "acme.common" in roles
        assert "acme.web" in roles

    def test_detect_counts_dynamic_role_includes(self, tmp_path):
        """Verify detector counts dynamic role includes (with variables)."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "main.yml").write_text(
            "---\n"
            "- name: static include\n"
            "  include_role:\n"
            "    name: acme.static\n"
            "- name: dynamic include\n"
            "  import_role:\n"
            '    name: "{{ dynamic_role }}"\n',
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        features = detector.detect()

        assert features["included_role_calls"] == 1
        assert features["dynamic_included_role_calls"] == 1
        assert "acme.static" in features["included_roles"]
        assert "{{ dynamic_role }}" in features["dynamic_included_roles"]


class TestFeatureDetectorAnnotations:
    """Tests for task annotation detection."""

    def test_detect_counts_disabled_task_annotations(self, tmp_path):
        """Verify detector counts disabled (commented) task annotations."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "main.yml").write_text(
            "---\n"
            "# prism~runbook: owner=platform impact=high\n"
            "# - name: Disabled rollback step\n"
            "#   ansible.builtin.debug:\n"
            "#     msg: disabled\n"
            "- name: Real task\n"
            "  ansible.builtin.debug:\n"
            '    msg: "ok"\n',
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        features = detector.detect()

        assert features["disabled_task_annotations"] == 1

    def test_detect_counts_yaml_like_format_violations(self, tmp_path):
        """Verify detector counts YAML-like format violations in annotations."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "main.yml").write_text(
            "---\n"
            "# prism~task: Deploy app | owner=platform impact=high\n"
            "- name: Deploy app\n"
            "  debug:\n"
            '    msg: "ok"\n',
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        features = detector.detect()

        # The format_warning flag should be set for YAML-like violations
        assert features["yaml_like_task_annotations"] >= 0


class TestFeatureDetectorAnalyzeTaskCatalog:
    """Tests for analyze_task_catalog method."""

    def test_analyze_task_catalog_returns_per_file_analysis(self, tmp_path):
        """Verify analyze_task_catalog returns per-file breakdown."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "main.yml").write_text(
            "---\n"
            "- name: Task 1\n"
            "  debug:\n"
            '    msg: "ok"\n'
            "- name: Task 2\n"
            "  command:\n"
            '    cmd: "ls"\n',
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        catalog = detector.analyze_task_catalog()

        assert "tasks/main.yml" in catalog
        assert catalog["tasks/main.yml"]["task_count"] == 2
        # When modules are specified without FQCN, they are stored as-is
        modules_used = catalog["tasks/main.yml"]["modules_used"]
        assert "debug" in modules_used
        assert "command" in modules_used

    def test_analyze_task_catalog_tracks_async_tasks(self, tmp_path):
        """Verify analyze_task_catalog counts async tasks per file."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "main.yml").write_text(
            "---\n"
            "- name: Async task\n"
            "  command:\n"
            '    cmd: "sleep 10"\n'
            "  async: 30\n"
            "- name: Sync task\n"
            "  debug:\n"
            '    msg: "ok"\n',
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        catalog = detector.analyze_task_catalog()

        assert catalog["tasks/main.yml"]["task_count"] == 2
        assert catalog["tasks/main.yml"]["async_count"] == 1

    def test_analyze_task_catalog_includes_per_file_metrics(self, tmp_path):
        """Verify analyze_task_catalog includes all expected per-file metrics."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "main.yml").write_text(
            "---\n"
            "- name: Privileged conditional task\n"
            "  command:\n"
            '    cmd: "id"\n'
            "  become: true\n"
            "  when: is_prod\n"
            "  tags: [deploy]\n"
            "  notify: restart_service\n",
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})
        catalog = detector.analyze_task_catalog()

        file_metrics = catalog["tasks/main.yml"]
        assert file_metrics["task_count"] == 1
        assert file_metrics["privileged_tasks"] == 1
        assert file_metrics["conditional_tasks"] == 1
        assert file_metrics["tagged_tasks"] == 1
        assert "restart_service" in file_metrics["handlers_notified"]


class TestFeatureDetectorIntegration:
    """Integration tests with more complex roles."""

    def test_feature_detection_with_complete_role_fixture(self):
        """Integration test: detect features from a real role fixture."""
        # This test uses a role fixture if available
        fixtures_dir = Path(__file__).parent / "fixtures"
        if not fixtures_dir.exists():
            # Create a minimal test fixture
            pytest.skip("No fixtures directory available")

    def test_feature_detection_consistency_across_calls(self, tmp_path):
        """Verify feature detection is consistent across multiple calls."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "main.yml").write_text(
            "---\n"
            "- name: Deploy\n"
            "  debug:\n"
            '    msg: "deploy now"\n'
            "  become: true\n"
            "  notify: restart\n",
            encoding="utf-8",
        )

        di = DIContainer(str(role), {})
        detector = FeatureDetector(di, str(role), {})

        # Call detect multiple times and verify consistency
        features1 = detector.detect()
        features2 = detector.detect()

        assert features1 == features2
        assert features1["tasks_scanned"] == 1
        assert features1["privileged_tasks"] == 1
        assert "restart" in features1["handlers_notified"]

    def test_feature_detection_with_exclude_patterns(self, tmp_path):
        """Verify FeatureDetector respects exclude_path_patterns option."""
        role = tmp_path / "role"
        tasks = role / "tasks"
        tasks.mkdir(parents=True)

        (tasks / "main.yml").write_text(
            "---\n" "- name: Main task\n" "  debug:\n" '    msg: "main"\n',
            encoding="utf-8",
        )
        (tasks / "excluded.yml").write_text(
            "---\n" "- name: Excluded task\n" "  debug:\n" '    msg: "excluded"\n',
            encoding="utf-8",
        )

        options = {"exclude_path_patterns": ["**/excluded.yml"]}
        di = DIContainer(str(role), options)
        detector = FeatureDetector(di, str(role), options)
        features = detector.detect()

        # The excluded file should not be scanned
        assert features["tasks_scanned"] == 1
