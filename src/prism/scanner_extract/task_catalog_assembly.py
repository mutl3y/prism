"""Task and handler catalog assembly for foundational fsrc parity."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import prism.scanner_extract.task_annotation_parsing as tap
import prism.scanner_extract.task_file_traversal as tft
from prism.scanner_data.di_helpers import require_prepared_policy
from prism.scanner_data.variable_helpers import format_inline_yaml


def _get_task_line_parsing_policy(di: object | None = None):
    return require_prepared_policy(di, "task_line_parsing", "task_catalog_assembly")


def _detect_task_module(task: dict, *, di: object | None = None) -> str | None:
    return _get_task_line_parsing_policy(di).detect_task_module(task)


def _extract_collection_from_module_name(
    module_name: str,
    builtin_collection_prefixes: frozenset[str] = frozenset(),
) -> str | None:
    parts = module_name.split(".")
    if len(parts) < 3:
        return None
    collection = ".".join(parts[:2]).strip()
    if not collection or any(
        collection.startswith(p) for p in builtin_collection_prefixes
    ):
        return None
    return collection


def _compact_task_parameters(task: dict, module_name: str) -> str:
    value = task.get(module_name)
    if isinstance(value, dict):
        pairs = [
            f"{key}={format_inline_yaml(val)}"
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


def _collect_task_handler_catalog(
    role_path: str,
    exclude_paths: list[str] | None = None,
    marker_prefix: str = "",
    *,
    di: object | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    role_root = Path(role_path).resolve()

    def _collect_tasks_recursive(
        task_file: Path,
        task_entries: list[dict[str, object]],
        seen_files: set[Path],
    ) -> None:
        if task_file in seen_files or not task_file.is_file():
            return
        if tft.is_path_excluded(task_file, role_root, exclude_paths):
            return

        seen_files.add(task_file)
        data = tft.load_yaml_file(task_file, di=di)
        try:
            raw_lines = task_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            raw_lines = []
        implicit_annotations, explicit_annotations = (
            tap.extract_task_annotations_for_file(
                raw_lines,
                marker_prefix=marker_prefix,
                include_task_index=True,
                di=di,
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
        if relpath.startswith("tasks/"):
            relpath = relpath[6:]

        for task in tft.iter_task_mappings(data, di=di):
            module_name = _detect_task_module(task, di=di) or "unknown"
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
            anchor = tap.task_anchor(
                relpath,
                task_name,
                len(task_entries) + 1,
                di=di,
            )
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

            for include_key in _get_task_line_parsing_policy(di).TASK_INCLUDE_KEYS:
                if include_key not in task:
                    continue
                include_target = task[include_key]
                include_paths: list[str] = []
                if isinstance(include_target, str):
                    include_paths.extend(
                        tft.expand_include_target_candidates(
                            task,
                            include_target,
                            di=di,
                        )
                    )
                elif isinstance(include_target, dict):
                    candidate = include_target.get("file") or include_target.get(
                        "_raw_params"
                    )
                    if isinstance(candidate, str):
                        include_paths.extend(
                            tft.expand_include_target_candidates(
                                task,
                                candidate,
                                di=di,
                            )
                        )

                for include_path in include_paths:
                    included_file = tft.resolve_task_include(
                        role_root,
                        task_file,
                        include_path,
                    )
                    if included_file:
                        _collect_tasks_recursive(
                            included_file,
                            task_entries,
                            seen_files,
                        )

            task_index += 1

    tasks_dir = role_root / "tasks"
    task_entries: list[dict[str, object]] = []
    seen_files: set[Path] = set()

    if tasks_dir.is_dir():
        main_file = tasks_dir / "main.yml"
        if main_file.exists():
            _collect_tasks_recursive(main_file, task_entries, seen_files)
        else:
            for task_file in sorted(
                path
                for path in tasks_dir.rglob("*")
                if path.is_file() and path.suffix in {".yml", ".yaml"}
            ):
                _collect_tasks_recursive(task_file, task_entries, seen_files)

    handler_entries: list[dict[str, object]] = []
    handlers_dir = role_root / "handlers"
    if handlers_dir.is_dir():
        for handler_file in sorted(
            path for path in handlers_dir.rglob("*.yml") if path.is_file()
        ):
            if tft.is_path_excluded(handler_file, role_root, exclude_paths):
                continue
            data = tft.load_yaml_file(handler_file, di=di)
            relpath = str(handler_file.relative_to(role_root))
            if relpath.startswith("handlers/"):
                relpath = relpath[9:]
            for task in tft.iter_task_mappings(data, di=di):
                module_name = _detect_task_module(task, di=di) or "unknown"
                task_name = str(task.get("name") or "(unnamed handler)")
                handler_entries.append(
                    {
                        "file": relpath,
                        "name": task_name,
                        "module": module_name,
                        "parameters": _compact_task_parameters(task, module_name),
                        "anchor": tap.task_anchor(
                            relpath,
                            task_name,
                            len(handler_entries) + 1,
                            di=di,
                        ),
                    }
                )

    return task_entries, handler_entries


def collect_molecule_scenarios(
    role_path: str,
    exclude_paths: list[str] | None = None,
    *,
    di: object | None = None,
) -> list[dict[str, object]]:
    role_root = Path(role_path).resolve()
    molecule_root = role_root / "molecule"
    if not molecule_root.is_dir():
        return []

    scenarios: list[dict[str, object]] = []
    for scenario_dir in sorted(
        path for path in molecule_root.iterdir() if path.is_dir()
    ):
        molecule_file = scenario_dir / "molecule.yml"
        if not molecule_file.is_file() or tft.is_path_excluded(
            molecule_file, role_root, exclude_paths
        ):
            continue
        doc = tft.load_yaml_file(molecule_file, di=di)
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


def detect_task_module(task: dict, *, di: object | None = None) -> str | None:
    return _detect_task_module(task, di=di)


def extract_collection_from_module_name(
    module_name: str,
    builtin_collection_prefixes: frozenset[str] = frozenset(),
) -> str | None:
    return _extract_collection_from_module_name(
        module_name, builtin_collection_prefixes=builtin_collection_prefixes
    )


def collect_task_handler_catalog(
    role_path: str,
    exclude_paths: list[str] | None = None,
    marker_prefix: str = "",
    *,
    di: object | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    return _collect_task_handler_catalog(
        role_path,
        exclude_paths=exclude_paths,
        marker_prefix=marker_prefix,
        di=di,
    )
