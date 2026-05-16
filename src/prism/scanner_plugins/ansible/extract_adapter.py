"""Ansible extract adapter seam — facade over scanner_extract internals.

Purpose: Provides explicit contract for Ansible plugin access to extract layer.
This adapter consolidates 30+ direct imports into 5 adapter methods, making
the layer boundary explicit and testable for layer boundary rule LB-1002.

Contract:
- Adapter is IMMUTABLE (read-only access to extract layer)
- All extract functions accessible ONLY through adapter methods
- DI injection ensures single point of access control
- No behavior changes (transparent delegation)
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from prism.scanner_data.contracts_request import (
    DIContainer,
    TaskAnnotation,
    TaskMapping,
)
from prism.scanner_data.policy_constants import PolicyConstants


class AnsibleExtractAdapter:
    """Facade adapter providing controlled access to scanner_extract internals.

    Consolidates Ansible plugin coupling to extract layer through explicit
    contract methods. This prevents direct imports and enables:
    - Layer boundary enforcement (LB-1002)
    - Independent testing of Ansible plugin (can mock adapter)
    - Future extract layer refactoring without breaking plugin
    """

    ADAPTER_IS_IMMUTABLE = True

    def __init__(self, di: DIContainer | None = None) -> None:
        """Initialize adapter with optional DI context."""
        self._di = di

    # ──────────────────────────────────────────────────────────────
    # Task File & Traversal Adapters
    # ──────────────────────────────────────────────────────────────

    def collect_task_files(
        self,
        role_root: Path,
        *,
        exclude_paths: list[str] | None = None,
        policy_constants: PolicyConstants | None = None,
    ) -> list[Path]:
        """Collect task files from role directory.

        Adapts: scanner_extract.task_file_traversal.collect_task_files
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.collect_task_files(
            role_root,
            exclude_paths=exclude_paths,
            di=self._di,
            policy_constants=policy_constants,
        )

    def load_task_yaml_file(
        self,
        path: Path,
        *,
        yaml_failure_collector: list[Any] | None = None,
        role_root: Path | None = None,
    ) -> object:
        """Load and parse a task YAML file.

        Adapts: scanner_extract.task_file_traversal.load_yaml_file
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.load_task_yaml_file(
            path,
            yaml_failure_collector=yaml_failure_collector,
            role_root=role_root,
            di=self._di,
        )

    def is_path_excluded(
        self,
        path: Path,
        role_root: Path,
        exclude_paths: list[str] | None,
    ) -> bool:
        """Check if path matches exclude patterns.

        Adapts: scanner_extract.task_file_traversal.is_path_excluded
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.is_path_excluded(path, role_root, exclude_paths)

    # ──────────────────────────────────────────────────────────────
    # Task Iteration & Mapping Adapters
    # ──────────────────────────────────────────────────────────────

    def iter_task_mappings(
        self,
        task: object,
    ) -> Iterable[TaskMapping]:
        """Iterate task mappings from task object.

        Adapts: scanner_extract.task_file_traversal.iter_task_mappings
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.iter_task_mappings(task, di=self._di)

    def iter_task_include_targets(
        self,
        data: object,
    ) -> list[str]:
        """Iterate task include targets.

        Adapts: scanner_extract.task_file_traversal.iter_task_include_targets
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.iter_task_include_targets(data, di=self._di)

    def iter_role_include_targets(
        self,
        task: TaskMapping,
    ) -> list[str]:
        """Iterate role include targets.

        Adapts: scanner_extract.task_file_traversal.iter_role_include_targets
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.iter_role_include_targets(task, di=self._di)

    def iter_dynamic_role_include_targets(
        self,
        task: TaskMapping,
    ) -> list[str]:
        """Iterate dynamic role include targets (templated includes).

        Adapts: scanner_extract.task_file_traversal.iter_dynamic_role_include_targets
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.iter_dynamic_role_include_targets(task, di=self._di)

    def collect_unconstrained_dynamic_role_includes(
        self,
        role_path: str,
        exclude_paths: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """Collect unconstrained dynamic role includes.

        Adapts: scanner_extract.task_file_traversal.collect_unconstrained_dynamic_role_includes
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.collect_unconstrained_dynamic_role_includes(
            role_path,
            exclude_paths=exclude_paths,
            di=self._di,
        )

    def collect_unconstrained_dynamic_task_includes(
        self,
        role_path: str,
        exclude_paths: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """Collect unconstrained dynamic task includes.

        Adapts: scanner_extract.task_file_traversal.collect_unconstrained_dynamic_task_includes
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.collect_unconstrained_dynamic_task_includes(
            role_path,
            exclude_paths=exclude_paths,
            di=self._di,
        )

    # ──────────────────────────────────────────────────────────────
    # Task Annotation & Catalog Adapters
    # ──────────────────────────────────────────────────────────────

    def extract_task_annotations_for_file(
        self,
        lines: list[str],
        marker_prefix: str,
        include_task_index: bool = False,
        *,
        policy_constants: PolicyConstants | None = None,
    ) -> tuple[list[TaskAnnotation], dict[str, list[TaskAnnotation]]]:
        """Extract task annotations from file lines.

        Adapts: scanner_extract.task_annotation_parsing.extract_task_annotations_for_file
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.extract_task_annotations_for_file(
            lines,
            marker_prefix,
            include_task_index,
            di=self._di,
            policy_constants=policy_constants,
        )

    def detect_task_module(
        self,
        task: dict[Any, Any],
        *,
        policy_constants: PolicyConstants | None = None,
    ) -> str | None:
        """Detect module name from task.

        Adapts: scanner_extract.task_catalog_assembly.detect_task_module
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.detect_task_module(
            task, di=self._di, policy_constants=policy_constants
        )

    def extract_collection_from_module_name(
        self,
        module_name: str,
        builtin_collection_prefixes: frozenset[str] = frozenset(),
    ) -> str | None:
        """Extract collection name from module name.

        Adapts: scanner_extract.task_catalog_assembly.extract_collection_from_module_name
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.extract_collection_from_module_name(
            module_name, builtin_collection_prefixes=builtin_collection_prefixes
        )

    def collect_molecule_scenarios(
        self,
        role_path: str,
        exclude_paths: list[str] | None = None,
    ) -> list[dict[str, object]]:
        """Collect Molecule test scenarios.

        Adapts: scanner_extract.task_catalog_assembly.collect_molecule_scenarios
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.collect_molecule_scenarios(
            role_path, exclude_paths=exclude_paths, di=self._di
        )

    # ──────────────────────────────────────────────────────────────
    # Variable Helper Adapters
    # ──────────────────────────────────────────────────────────────

    def format_inline_yaml(self, value: object) -> str:
        """Format inline YAML value.

        Adapts: scanner_extract.variable_helpers.format_inline_yaml
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.format_inline_yaml(value)

    def find_variable_line_in_yaml(
        self,
        path: Path | None,
        name: str,
    ) -> int | None:
        """Find line number of variable in YAML file.

        Adapts: scanner_extract.variable_helpers.find_variable_line_in_yaml
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.find_variable_line_in_yaml(path, name)

    def infer_variable_type(self, value: object) -> str:
        """Infer variable type from value.

        Adapts: scanner_extract.variable_helpers.infer_variable_type
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.infer_variable_type(value)

    def is_sensitive_variable(self, name: str, value: Any) -> bool:
        """Check if variable is sensitive.

        Adapts: scanner_extract.variable_helpers.is_sensitive_variable
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.is_sensitive_variable(name, value)

    # ──────────────────────────────────────────────────────────────
    # Requirements & Discovery Adapters
    # ──────────────────────────────────────────────────────────────

    def normalize_requirements(self, requirements: list[Any]) -> list[str]:
        """Normalize requirements list.

        Adapts: scanner_extract.requirements.normalize_requirements
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.normalize_requirements(requirements)

    def iter_role_variable_map_candidates(
        self,
        role_root: Path,
        subdir: str,
    ) -> list[Path]:
        """Iterate candidate variable map files in role.

        Adapts: scanner_extract.discovery.iter_role_variable_map_candidates
        """
        from prism.scanner_plugins.ansible import extract_utils as _utils

        return _utils.iter_role_variable_map_candidates(role_root, subdir)


__all__ = ["AnsibleExtractAdapter"]
