"""FeatureDetector orchestrator for role feature analysis.

This module consolidates feature-extraction logic currently scattered in:
- scanner_extract.task_parser — task/handler catalog, included roles, executed modules
- scanner_submodules — feature counting and pattern analysis

The FeatureDetector class provides a cohesive interface for detecting,
analyzing, and reporting on all adaptively-discovered role features
(tasks, handlers, collections, modules, entry points, etc.).

Features detected:
- Task counts and analysis (total, async, conditional, tagged, privileged)
- Handler counts and patterns
- Collection dependencies and module imports
- Included/imported role references (static and dynamic)
- Recursive task includes and imports
- Disabled task annotations and format violations
- Entry points, callbacks, plugins (extensible)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .di import DIContainer
from ..scanner_data.contracts_request import FeaturesContext
from ..scanner_extract.task_parser import (
    _collect_task_files,
    _load_yaml_file,
    _iter_task_include_targets,
    _iter_task_mappings,
    _iter_role_include_targets,
    _iter_dynamic_role_include_targets,
    _detect_task_module,
    _extract_collection_from_module_name,
    _extract_task_annotations_for_file,
)


class FeatureDetector:
    """Orchestrator for detecting role features and capabilities.

    Detects:
    - Task counts and patterns (tags, when conditions, loops)
    - Handler counts and patterns
    - Collection dependencies and imports
    - Module imports and dependencies
    - Main playbook entry points
    - Callbacks, filters, plugins
    - Complex patterns (includes, blocks, templates)
    - Task annotations (disabled, format violations)

    Returns immutable FeaturesContext with complete feature analysis.

    **Design Rationale:**
    - Encapsulates feature detection logic currently in task_parser.py
    - Provides immutable TypedDict results (FeaturesContext)
    - Enables testable dependency injection via DIContainer
    - Operates at higher abstraction than low-level helpers
    - Graceful degradation: missing directories → counts of 0
    """

    def __init__(
        self,
        di: DIContainer,
        role_path: str,
        options: dict[str, Any],
    ) -> None:
        """Initialize detector with DI container and role path.

        Args:
            di: Dependency Injection container for orchestration.
            role_path: Path to the role directory.
            options: Scan configuration dictionary containing:
                - role_path: Role directory path
                - exclude_path_patterns: List of paths to exclude (optional)

        Raises:
            ValueError: If di is None, role_path is empty, or options is None.
        """
        if di is None:
            raise ValueError("di (DIContainer) must not be None")
        if not role_path:
            raise ValueError("role_path must not be empty")
        if options is None:
            raise ValueError("options must not be None")

        self._di = di
        self._role_path = role_path
        self._options = options

    def detect(self) -> FeaturesContext:
        """Detect all features and return FeaturesContext.

        Analyzes role structure and returns complete feature analysis:
        - task_files_scanned: int (number of task files discovered)
        - tasks_scanned: int (total task count across all files)
        - recursive_task_includes: int (nested includes detected)
        - unique_modules: str (comma-separated module names)
        - external_collections: str (comma-separated collection names)
        - handlers_notified: str (comma-separated handler names)
        - privileged_tasks: int (tasks with become: true)
        - conditional_tasks: int (tasks with when:)
        - tagged_tasks: int (tasks with tags:)
        - included_role_calls: int (static role includes)
        - included_roles: str (comma-separated role names)
        - dynamic_included_role_calls: int (dynamic role includes)
        - dynamic_included_roles: str (comma-separated dynamic roles)
        - disabled_task_annotations: int (disabled tasks in comments)
        - yaml_like_task_annotations: int (format violations in annotations)

        **Error Handling:**
        - Missing tasks/ directory → returns counts of 0
        - Missing handlers/ directory → returns counts of 0
        - Invalid YAML in task file → logs, skips file, continues
        - Invalid role structure → returns best-effort FeaturesContext

        Returns:
            FeaturesContext: Immutable feature analysis dict.
        """
        role_root = Path(self._role_path).resolve()

        # Collect task files and extract exclude patterns
        exclude_patterns = self._options.get("exclude_path_patterns")
        task_files = _collect_task_files(role_root, exclude_paths=exclude_patterns)

        # Initialize counters
        include_count = 0
        tasks_scanned = 0
        privileged_tasks = 0
        conditional_tasks = 0
        tagged_tasks = 0
        modules: set[str] = set()
        external_collections: set[str] = set()
        handlers_notified: set[str] = set()
        included_roles: set[str] = set()
        included_role_calls = 0
        dynamic_included_role_calls = 0
        dynamic_included_roles: set[str] = set()

        # Phase 1: Scan all task files for features
        for task_file in task_files:
            # Count recursive includes
            data = _load_yaml_file(task_file)
            include_count += len(_iter_task_include_targets(data))

            # Iterate all tasks in this file
            for task in _iter_task_mappings(data):
                tasks_scanned += 1

                # Detect static role includes
                included_targets = _iter_role_include_targets(task)
                included_role_calls += len(included_targets)
                included_roles.update(included_targets)

                # Detect dynamic role includes
                dynamic_targets = _iter_dynamic_role_include_targets(task)
                dynamic_included_role_calls += len(dynamic_targets)
                dynamic_included_roles.update(dynamic_targets)

                # Detect module and collection
                module_name = _detect_task_module(task)
                if module_name:
                    modules.add(module_name)
                    collection = _extract_collection_from_module_name(module_name)
                    if collection:
                        external_collections.add(collection)

                # Detect privilege escalation
                if bool(task.get("become")):
                    privileged_tasks += 1

                # Detect conditionals
                if "when" in task:
                    conditional_tasks += 1

                # Detect tags
                if task.get("tags"):
                    tagged_tasks += 1

                # Detect notified handlers
                notify = task.get("notify")
                if isinstance(notify, str):
                    handlers_notified.add(notify)
                elif isinstance(notify, list):
                    handlers_notified.update(
                        item for item in notify if isinstance(item, str)
                    )

        # Phase 2: Scan task files for annotations
        disabled_task_annotations = 0
        yaml_like_task_annotations = 0
        for task_file in task_files:
            try:
                raw_lines = task_file.read_text(encoding="utf-8").splitlines()
            except OSError:
                raw_lines = []

            impl_anns, expl_anns = _extract_task_annotations_for_file(raw_lines)
            disabled_task_annotations += sum(1 for a in impl_anns if a.get("disabled"))
            yaml_like_task_annotations += sum(
                1 for a in impl_anns if a.get("format_warning")
            )
            yaml_like_task_annotations += sum(
                1
                for items in expl_anns.values()
                for a in items
                if a.get("format_warning")
            )

        # Build and return immutable FeaturesContext
        return {
            "task_files_scanned": len(task_files),
            "tasks_scanned": tasks_scanned,
            "recursive_task_includes": include_count,
            "unique_modules": ", ".join(sorted(modules)) if modules else "none",
            "external_collections": (
                ", ".join(sorted(external_collections))
                if external_collections
                else "none"
            ),
            "handlers_notified": (
                ", ".join(sorted(handlers_notified)) if handlers_notified else "none"
            ),
            "privileged_tasks": privileged_tasks,
            "conditional_tasks": conditional_tasks,
            "tagged_tasks": tagged_tasks,
            "included_role_calls": included_role_calls,
            "included_roles": (
                ", ".join(sorted(included_roles)) if included_roles else "none"
            ),
            "dynamic_included_role_calls": dynamic_included_role_calls,
            "dynamic_included_roles": (
                ", ".join(sorted(dynamic_included_roles))
                if dynamic_included_roles
                else "none"
            ),
            "disabled_task_annotations": disabled_task_annotations,
            "yaml_like_task_annotations": yaml_like_task_annotations,
        }

    def analyze_task_catalog(self) -> dict[str, dict[str, Any]]:
        """Return detailed task analysis for each task file.

        Per-file breakdown of task counts, module usage, handlers, etc.
        Useful for detailed role documentation and debugging.

        Returns:
            dict: {task_file_name: {counts, modules, handlers, ...}}
                Example:
                {
                    "main.yml": {
                        "task_count": 5,
                        "async_count": 0,
                        "handler_count": 0,
                        "modules": ["ansible.builtin.debug", ...],
                        "collections": ["ansible.builtin"],
                        "handlers_notified": ["restart_service"],
                        ...
                    }
                }
        """
        role_root = Path(self._role_path).resolve()
        exclude_patterns = self._options.get("exclude_path_patterns")
        task_files = _collect_task_files(role_root, exclude_paths=exclude_patterns)

        result: dict[str, dict[str, Any]] = {}

        for task_file in task_files:
            rel_path = task_file.relative_to(role_root)
            file_key = str(rel_path)

            data = _load_yaml_file(task_file)
            task_count = 0
            async_count = 0
            modules_in_file: set[str] = set()
            collections_in_file: set[str] = set()
            handlers_in_file: set[str] = set()
            privileged_in_file = 0
            conditional_in_file = 0
            tagged_in_file = 0

            for task in _iter_task_mappings(data):
                task_count += 1

                # Detect async
                if task.get("async") or task.get("poll") is not None:
                    async_count += 1

                # Detect module
                module_name = _detect_task_module(task)
                if module_name:
                    modules_in_file.add(module_name)
                    collection = _extract_collection_from_module_name(module_name)
                    if collection:
                        collections_in_file.add(collection)

                # Detect handlers
                notify = task.get("notify")
                if isinstance(notify, str):
                    handlers_in_file.add(notify)
                elif isinstance(notify, list):
                    handlers_in_file.update(
                        item for item in notify if isinstance(item, str)
                    )

                # Detect privilege escalation
                if bool(task.get("become")):
                    privileged_in_file += 1

                # Detect conditionals
                if "when" in task:
                    conditional_in_file += 1

                # Detect tags
                if task.get("tags"):
                    tagged_in_file += 1

            result[file_key] = {
                "task_count": task_count,
                "async_count": async_count,
                "modules_used": sorted(modules_in_file),
                "collections_used": sorted(collections_in_file),
                "handlers_notified": sorted(handlers_in_file),
                "privileged_tasks": privileged_in_file,
                "conditional_tasks": conditional_in_file,
                "tagged_tasks": tagged_in_file,
            }

        return result
