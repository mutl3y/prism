"""Task and handler catalog assembly, feature extraction, and role analysis.

This module builds detailed task/handler catalogs from parsed role structures,
extracts role-level features, and collects molecule scenario metadata.

Functions exported:
  _detect_task_module, _extract_collection_from_module_name, _compact_task_parameters,
  _extract_role_notes_from_comments, _collect_task_handler_catalog,
  _collect_molecule_scenarios, extract_role_features
"""

from __future__ import annotations

from pathlib import Path
from collections import defaultdict

from . import task_line_parsing as tlp
from . import task_file_traversal as tft
from . import task_annotation_parsing as tap

# ---------------------------------------------------------------------------
# Task module detection
# ---------------------------------------------------------------------------


def _detect_task_module(task: dict) -> str | None:
    """Detect the task module key from an Ansible task mapping."""
    # Check for explicit include/import tasks first
    for include_key in tlp.TASK_INCLUDE_KEYS:
        if include_key in task:
            # Normalize to short form for readability
            if "import_tasks" in include_key:
                return "import_tasks"
            return "include_tasks"

    for include_key in tlp.ROLE_INCLUDE_KEYS:
        if include_key in task:
            if "import_role" in include_key:
                return "import_role"
            return "include_role"

    # Then look for regular modules
    for key in task:
        if key in tlp.TASK_META_KEYS or key in tlp.TASK_BLOCK_KEYS:
            continue
        if key.startswith("with_"):
            continue
        return key
    return None


def _extract_collection_from_module_name(module_name: str) -> str | None:
    """Return collection prefix from a fully-qualified module name."""
    parts = module_name.split(".")
    if len(parts) < 3:
        return None
    collection = ".".join(parts[:2]).strip()
    if not collection or collection.startswith("ansible."):
        return None
    return collection


# ---------------------------------------------------------------------------
# Compact parameter rendering
# ---------------------------------------------------------------------------


def _compact_task_parameters(task: dict, module_name: str) -> str:
    """Render a compact and bounded summary of key task parameters."""
    if module_name in {"include_role", "import_role"}:
        role_target = ""
        role_payload = None
        if module_name in task:
            role_payload = task.get(module_name)
        else:
            for include_key in tlp.ROLE_INCLUDE_KEYS:
                if include_key in task and include_key.endswith(module_name):
                    role_payload = task.get(include_key)
                    break
        if isinstance(role_payload, str):
            role_target = role_payload.strip()
        elif isinstance(role_payload, dict):
            candidate = role_payload.get("name") or role_payload.get("_raw_params")
            if isinstance(candidate, str):
                role_target = candidate.strip()
        if role_target:
            return f"name={role_target}"

    value = task.get(module_name)
    if isinstance(value, dict):
        pairs = [
            f"{key}={tft._format_inline_yaml(val)}"
            for key, val in value.items()
            if key not in {"src", "dest", "name"}
        ]
        if pairs:
            rendered = ", ".join(pairs[:3])
            if len(pairs) > 3:
                rendered += ", ..."
            return rendered
    if isinstance(value, str):
        compact = value.strip().replace("\n", " ")
        return compact[:80] + ("..." if len(compact) > 80 else "")
    return ""


# ---------------------------------------------------------------------------
# Role notes extraction from comments
# ---------------------------------------------------------------------------


def _extract_role_notes_from_comments(
    role_path: str,
    exclude_paths: list[str] | None = None,
    marker_prefix: str = tlp.DEFAULT_DOC_MARKER_PREFIX,
) -> dict[str, list[str]]:
    """Extract comment-driven role notes from YAML files.

    Supported syntax:
        # prism~warning: text
        # prism~deprecated: text
        # prism~note: text
        # prism~notes: text
        # prism~additional: text
    """
    marker_line_re = tlp.get_marker_line_re(marker_prefix)
    role_root = Path(role_path).resolve()
    categories: dict[str, list[str]] = {
        "warnings": [],
        "deprecations": [],
        "notes": [],
        "additionals": [],
    }
    files: list[Path] = []
    files.extend(tft._collect_task_files(role_root, exclude_paths=exclude_paths))
    for rel in ("defaults/main.yml", "vars/main.yml", "handlers/main.yml"):
        candidate = role_root / rel
        if candidate.is_file() and not tft._is_path_excluded(
            candidate, role_root, exclude_paths
        ):
            files.append(candidate)

    for file_path in files:
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        i = 0
        while i < len(lines):
            line = lines[i]
            match = marker_line_re.match(line)
            if not match:
                i += 1
                continue

            label = (match.group("label") or "").strip().lower()
            note_type = "note"
            if label == "warning":
                note_type = "warning"
            elif label == "deprecated":
                note_type = "deprecated"
            elif label in {"additional", "additionals"}:
                note_type = "additional"
            elif label in {"note", "notes"}:
                note_type = "note"
            else:
                i += 1
                continue

            text = (match.group("body") or "").strip()
            continuation: list[str] = []
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if marker_line_re.match(next_line):
                    break
                cont_match = tlp.COMMENT_CONTINUATION_RE.match(next_line)
                if not cont_match:
                    break
                continuation.append((cont_match.group(1) or "").strip())
                j += 1
            if continuation:
                text = " ".join(part for part in [text, *continuation] if part)
            if text:
                if note_type == "warning":
                    categories["warnings"].append(text)
                elif note_type == "deprecated":
                    categories["deprecations"].append(text)
                elif note_type in {"additional", "additionals"}:
                    categories["additionals"].append(text)
                else:
                    categories["notes"].append(text)
            i = j if j > i + 1 else i + 1

    return categories


# ---------------------------------------------------------------------------
# Task and handler catalog
# ---------------------------------------------------------------------------


def _collect_task_handler_catalog(
    role_path: str,
    exclude_paths: list[str] | None = None,
    marker_prefix: str = tlp.DEFAULT_DOC_MARKER_PREFIX,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Build optional detailed task and handler catalogs for README rendering.

    Tasks are collected in execution order (depth-first), following includes
    as they would be encountered during Ansible playbook execution.
    """
    role_root = Path(role_path).resolve()

    def _collect_tasks_recursive(
        task_file: Path,
        task_entries: list[dict[str, object]],
        seen_files: set[Path],
    ) -> None:
        """Recursively collect tasks in execution order, following includes."""
        if task_file in seen_files or not task_file.is_file():
            return
        if tft._is_path_excluded(task_file, role_root, exclude_paths):
            return

        seen_files.add(task_file)
        data = tft._load_yaml_file(task_file)
        try:
            raw_lines = task_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            raw_lines = []
        implicit_annotations, explicit_annotations = (
            tap._extract_task_annotations_for_file(
                raw_lines,
                marker_prefix=marker_prefix,
                include_task_index=True,
            )
        )
        implicit_by_task_index: dict[int, list[dict[str, object]]] = defaultdict(list)
        implicit_fallback: list[dict[str, object]] = []
        for annotation in implicit_annotations:
            task_index = annotation.get("task_index")
            if isinstance(task_index, int):
                implicit_by_task_index[task_index].append(annotation)
            else:
                implicit_fallback.append(annotation)
        implicit_index = 0
        task_index = 0
        relpath = str(task_file.relative_to(role_root))
        # Strip "tasks/" prefix since this is a task catalog
        if relpath.startswith("tasks/"):
            relpath = relpath[6:]

        for task in tft._iter_task_mappings(data):
            # Add this task to the catalog
            module_name = _detect_task_module(task) or "unknown"
            task_name = str(task.get("name") or "(unnamed task)")
            annotations: list[dict[str, object]] = []
            if task_index in implicit_by_task_index:
                annotations.extend(
                    {key: value for key, value in item.items() if key != "task_index"}
                    for item in implicit_by_task_index[task_index]
                )
            elif implicit_index < len(implicit_fallback):
                annotations.append(implicit_fallback[implicit_index])
                implicit_index += 1
            annotations.extend(explicit_annotations.get(task_name, []))

            runbook_items = [
                note.get("text", "")
                for note in annotations
                if note.get("kind") == "runbook" and note.get("text")
            ]
            runbook = runbook_items[0] if runbook_items else ""
            anchor = tap._task_anchor(relpath, task_name, len(task_entries) + 1)
            task_entries.append(
                {
                    "file": relpath,
                    "name": task_name,
                    "module": module_name,
                    "parameters": _compact_task_parameters(task, module_name),
                    "anchor": anchor,
                    "runbook": runbook,
                    "annotations": annotations,
                }
            )

            # If this task includes/imports another file, process it inline
            for include_key in tlp.TASK_INCLUDE_KEYS:
                if include_key in task:
                    include_target = task[include_key]
                    include_paths: list[str] = []
                    if isinstance(include_target, str):
                        include_paths.extend(
                            tft._expand_include_target_candidates(task, include_target)
                        )
                    elif isinstance(include_target, dict):
                        candidate = include_target.get("file") or include_target.get(
                            "_raw_params"
                        )
                        if isinstance(candidate, str):
                            include_paths.extend(
                                tft._expand_include_target_candidates(task, candidate)
                            )

                    for include_path in include_paths:
                        included_file = tft._resolve_task_include(
                            role_root, task_file, include_path
                        )
                        if included_file:
                            _collect_tasks_recursive(
                                included_file, task_entries, seen_files
                            )

            task_index += 1

    # Start with main.yml if it exists, otherwise with any available task file
    tasks_dir = role_root / "tasks"
    task_entries: list[dict[str, object]] = []
    seen_files: set[Path] = set()

    if tasks_dir.is_dir():
        main_file = tasks_dir / "main.yml"
        if main_file.exists():
            _collect_tasks_recursive(main_file, task_entries, seen_files)
        else:
            # Fallback: process any discovered task files in order
            for task_file in sorted(
                path
                for path in tasks_dir.rglob("*")
                if path.is_file() and path.suffix in {".yml", ".yaml"}
            ):
                _collect_tasks_recursive(task_file, task_entries, seen_files)

    # Handlers are typically not nested, so collect them normally
    handler_entries: list[dict[str, object]] = []
    handlers_dir = role_root / "handlers"
    if handlers_dir.is_dir():
        for handler_file in sorted(
            path for path in handlers_dir.rglob("*.yml") if path.is_file()
        ):
            if tft._is_path_excluded(handler_file, role_root, exclude_paths):
                continue
            data = tft._load_yaml_file(handler_file)
            relpath = str(handler_file.relative_to(role_root))
            # Strip "handlers/" prefix since this is a handler catalog
            if relpath.startswith("handlers/"):
                relpath = relpath[9:]
            for task in tft._iter_task_mappings(data):
                module_name = _detect_task_module(task) or "unknown"
                task_name = str(task.get("name") or "(unnamed handler)")
                handler_entries.append(
                    {
                        "file": relpath,
                        "name": task_name,
                        "module": module_name,
                        "parameters": _compact_task_parameters(task, module_name),
                        "anchor": tap._task_anchor(
                            relpath, task_name, len(handler_entries) + 1
                        ),
                    }
                )
    return task_entries, handler_entries


# ---------------------------------------------------------------------------
# Molecule scenarios
# ---------------------------------------------------------------------------


def _collect_molecule_scenarios(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict[str, object]]:
    """Collect Molecule scenario metadata from ``molecule/*/molecule.yml``."""
    role_root = Path(role_path).resolve()
    molecule_root = role_root / "molecule"
    if not molecule_root.is_dir():
        return []

    scenarios: list[dict[str, object]] = []
    for scenario_dir in sorted(
        path for path in molecule_root.iterdir() if path.is_dir()
    ):
        molecule_file = scenario_dir / "molecule.yml"
        if not molecule_file.is_file() or tft._is_path_excluded(
            molecule_file, role_root, exclude_paths
        ):
            continue
        doc = tft._load_yaml_file(molecule_file)
        if not isinstance(doc, dict):
            continue

        driver_raw = doc.get("driver")
        verifier_raw = doc.get("verifier")
        platforms_value = doc.get("platforms")
        driver = driver_raw if isinstance(driver_raw, dict) else {}
        verifier = verifier_raw if isinstance(verifier_raw, dict) else {}
        platforms_raw = platforms_value if isinstance(platforms_value, list) else []
        platforms: list[str] = []
        for platform in platforms_raw:
            if not isinstance(platform, dict):
                continue
            platform_name = str(platform.get("name") or "").strip()
            platform_image = str(platform.get("image") or "").strip()
            if platform_name and platform_image:
                platforms.append(f"{platform_name} ({platform_image})")
            elif platform_name:
                platforms.append(platform_name)

        scenarios.append(
            {
                "name": scenario_dir.name,
                "driver": str(driver.get("name") or "unknown"),
                "verifier": str(verifier.get("name") or "unknown"),
                "platforms": platforms,
                "path": str(molecule_file.relative_to(role_root)),
            }
        )

    return scenarios


# ---------------------------------------------------------------------------
# Role feature extraction
# ---------------------------------------------------------------------------


def extract_role_features(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> dict:
    """Extract adaptive role features from tasks and role structure.

    These heuristics are intentionally lightweight and update automatically
    as task files change, providing richer documentation without manual edits.
    """
    role_root = Path(role_path).resolve()
    task_files = tft._collect_task_files(role_root, exclude_paths=exclude_paths)

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
        data = tft._load_yaml_file(task_file)
        include_count += len(tft._iter_task_include_targets(data))
        for task in tft._iter_task_mappings(data):
            tasks_scanned += 1
            included_targets = tft._iter_role_include_targets(task)
            included_role_calls += len(included_targets)
            included_roles.update(included_targets)
            dynamic_targets = tft._iter_dynamic_role_include_targets(task)
            dynamic_included_role_calls += len(dynamic_targets)
            dynamic_included_roles.update(dynamic_targets)
            module_name = _detect_task_module(task)
            if module_name:
                modules.add(module_name)
                collection = _extract_collection_from_module_name(module_name)
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
        impl_anns, expl_anns = tap._extract_task_annotations_for_file(raw_lines)
        disabled_task_annotations += sum(1 for a in impl_anns if a.get("disabled"))
        yaml_like_task_annotations += sum(
            1 for a in impl_anns if a.get("format_warning")
        )
        yaml_like_task_annotations += sum(
            1 for items in expl_anns.values() for a in items if a.get("format_warning")
        )

    return {
        "task_files_scanned": len(task_files),
        "tasks_scanned": tasks_scanned,
        "recursive_task_includes": include_count,
        "unique_modules": ", ".join(sorted(modules)) if modules else "none",
        "external_collections": (
            ", ".join(sorted(external_collections)) if external_collections else "none"
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
