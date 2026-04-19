"""AnsibleFeatureDetectionPlugin — Ansible-specific feature detection logic."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from prism.scanner_data.contracts_request import FeaturesContext
from prism.scanner_core.task_extract_adapters import collect_task_files
from prism.scanner_core.task_extract_adapters import detect_task_module
from prism.scanner_core.task_extract_adapters import extract_collection_from_module_name
from prism.scanner_core.task_extract_adapters import extract_task_annotations_for_file
from prism.scanner_core.task_extract_adapters import iter_dynamic_role_include_targets
from prism.scanner_core.task_extract_adapters import iter_role_include_targets
from prism.scanner_core.task_extract_adapters import iter_task_include_targets
from prism.scanner_core.task_extract_adapters import iter_task_mappings
from prism.scanner_core.task_extract_adapters import load_task_yaml_file


class AnsibleFeatureDetectionPlugin:
    """Ansible-specific feature detection plugin.

    Implements the FeatureDetectionPlugin protocol, containing all
    Ansible-native detection logic previously inline in FeatureDetector.
    """

    def __init__(self, di: Any = None) -> None:
        self._di = di

    def detect_features(
        self,
        role_path: str,
        options: dict[str, Any],
    ) -> FeaturesContext:
        role_root = Path(role_path).resolve()
        exclude_patterns = options.get("exclude_path_patterns")
        task_files = collect_task_files(
            role_root,
            exclude_paths=exclude_patterns,
            di=self._di,
        )

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

        for task_file in task_files:
            data = load_task_yaml_file(task_file, di=self._di)
            include_count += len(iter_task_include_targets(data, di=self._di))

            for task in iter_task_mappings(data, di=self._di):
                tasks_scanned += 1

                included_targets = iter_role_include_targets(task, di=self._di)
                included_role_calls += len(included_targets)
                included_roles.update(included_targets)

                dynamic_targets = iter_dynamic_role_include_targets(task, di=self._di)
                dynamic_included_role_calls += len(dynamic_targets)
                dynamic_included_roles.update(dynamic_targets)

                module_name = detect_task_module(task, di=self._di)
                if module_name:
                    modules.add(module_name)
                    collection = extract_collection_from_module_name(module_name)
                    if collection:
                        external_collections.add(collection)

                if bool(task.get("become")):
                    privileged_tasks += 1
                if "when" in task:
                    conditional_tasks += 1
                if task.get("tags"):
                    tagged_tasks += 1

                notify = task.get("notify")
                if isinstance(notify, str):
                    handlers_notified.add(notify)
                elif isinstance(notify, list):
                    handlers_notified.update(
                        item for item in notify if isinstance(item, str)
                    )

        disabled_task_annotations = 0
        yaml_like_task_annotations = 0
        for task_file in task_files:
            try:
                raw_lines = task_file.read_text(encoding="utf-8").splitlines()
            except OSError:
                raw_lines = []

            impl_anns, expl_anns = extract_task_annotations_for_file(
                raw_lines,
                di=self._di,
            )
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

        return FeaturesContext(
            task_files_scanned=len(task_files),
            tasks_scanned=tasks_scanned,
            recursive_task_includes=include_count,
            unique_modules=", ".join(sorted(modules)) if modules else "none",
            external_collections=(
                ", ".join(sorted(external_collections))
                if external_collections
                else "none"
            ),
            handlers_notified=(
                ", ".join(sorted(handlers_notified)) if handlers_notified else "none"
            ),
            privileged_tasks=privileged_tasks,
            conditional_tasks=conditional_tasks,
            tagged_tasks=tagged_tasks,
            included_role_calls=included_role_calls,
            included_roles=(
                ", ".join(sorted(included_roles)) if included_roles else "none"
            ),
            dynamic_included_role_calls=dynamic_included_role_calls,
            dynamic_included_roles=(
                ", ".join(sorted(dynamic_included_roles))
                if dynamic_included_roles
                else "none"
            ),
            disabled_task_annotations=disabled_task_annotations,
            yaml_like_task_annotations=yaml_like_task_annotations,
        )

    def analyze_task_catalog(
        self,
        role_path: str,
        options: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        role_root = Path(role_path).resolve()
        exclude_patterns = options.get("exclude_path_patterns")
        task_files = collect_task_files(
            role_root,
            exclude_paths=exclude_patterns,
            di=self._di,
        )

        result: dict[str, dict[str, Any]] = {}
        for task_file in task_files:
            rel_path = str(task_file.relative_to(role_root))
            data = load_task_yaml_file(task_file, di=self._di)

            task_count = 0
            async_count = 0
            modules_in_file: set[str] = set()
            collections_in_file: set[str] = set()
            handlers_in_file: set[str] = set()
            privileged_in_file = 0
            conditional_in_file = 0
            tagged_in_file = 0

            for task in iter_task_mappings(data, di=self._di):
                task_count += 1
                if task.get("async") or task.get("poll") is not None:
                    async_count += 1

                module_name = detect_task_module(task, di=self._di)
                if module_name:
                    modules_in_file.add(module_name)
                    collection = extract_collection_from_module_name(module_name)
                    if collection:
                        collections_in_file.add(collection)

                notify = task.get("notify")
                if isinstance(notify, str):
                    handlers_in_file.add(notify)
                elif isinstance(notify, list):
                    handlers_in_file.update(
                        item for item in notify if isinstance(item, str)
                    )

                if bool(task.get("become")):
                    privileged_in_file += 1
                if "when" in task:
                    conditional_in_file += 1
                if task.get("tags"):
                    tagged_in_file += 1

            result[rel_path] = {
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
