"""Task file traversal, catalog, and annotation helpers.

These functions are extracted from scanner.py to improve cohesion.
They have zero prism-internal dependencies (stdlib + yaml only).

Exported names consumed by scanner.py:
  Constants: TASK_INCLUDE_KEYS, INCLUDE_VARS_KEYS, SET_FACT_KEYS,
             TASK_BLOCK_KEYS, TASK_META_KEYS
    Regex:     ROLE_NOTES_RE, TASK_NOTES_LONG_RE, COMMENT_CONTINUATION_RE
  Functions: _normalize_exclude_patterns, _is_relpath_excluded,
             _is_path_excluded, _format_inline_yaml, _load_yaml_file,
             _iter_task_include_targets, _iter_task_mappings,
             _resolve_task_include, _collect_task_files,
             _extract_role_notes_from_comments, _split_task_annotation_label,
             _extract_task_annotations_for_file, _task_anchor,
             _detect_task_module, _extract_collection_from_module_name,
             _compact_task_parameters, _collect_task_handler_catalog,
             _collect_molecule_scenarios, extract_role_features
"""

from __future__ import annotations

import re
import yaml
from collections import defaultdict
from fnmatch import fnmatch
from pathlib import Path

# ---------------------------------------------------------------------------
# Task key sets
# ---------------------------------------------------------------------------

TASK_INCLUDE_KEYS = {
    "include_tasks",
    "import_tasks",
    "ansible.builtin.include_tasks",
    "ansible.builtin.import_tasks",
}
ROLE_INCLUDE_KEYS = {
    "include_role",
    "import_role",
    "ansible.builtin.include_role",
    "ansible.builtin.import_role",
}
INCLUDE_VARS_KEYS = {
    "include_vars",
    "ansible.builtin.include_vars",
}
SET_FACT_KEYS = {
    "set_fact",
    "ansible.builtin.set_fact",
}
TASK_BLOCK_KEYS = ("block", "rescue", "always")
TASK_META_KEYS = {
    "name",
    "when",
    "tags",
    "register",
    "notify",
    "vars",
    "become",
    "become_user",
    "become_method",
    "check_mode",
    "changed_when",
    "failed_when",
    "ignore_errors",
    "ignore_unreachable",
    "delegate_to",
    "run_once",
    "loop",
    "loop_control",
    "with_items",
    "with_dict",
    "with_fileglob",
    "with_first_found",
    "with_nested",
    "with_sequence",
    "environment",
    "args",
    "retries",
    "delay",
    "until",
    "throttle",
    "no_log",
}

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

DEFAULT_DOC_MARKER_PREFIX = "prism"


def _normalize_marker_prefix(marker_prefix: str | None) -> str:
    """Return a safe marker prefix, falling back to the default."""
    if not isinstance(marker_prefix, str):
        return DEFAULT_DOC_MARKER_PREFIX
    prefix = marker_prefix.strip()
    if not prefix:
        return DEFAULT_DOC_MARKER_PREFIX
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", prefix):
        return DEFAULT_DOC_MARKER_PREFIX
    return prefix


def _build_marker_line_re(marker_prefix: str):
    """Build a regex for ``# <prefix>~<label>: ...`` marker comments."""
    escaped_prefix = re.escape(_normalize_marker_prefix(marker_prefix))
    return re.compile(
        rf"^\s*#\s*{escaped_prefix}\s*~\s*(?P<label>[a-z0-9_-]+)\s*:?\s*(?P<body>.*)$",
        flags=re.IGNORECASE,
    )


# Default compiled regexes kept for backwards import compatibility.
ROLE_NOTES_RE = _build_marker_line_re(DEFAULT_DOC_MARKER_PREFIX)
TASK_NOTES_LONG_RE = _build_marker_line_re(DEFAULT_DOC_MARKER_PREFIX)
ROLE_NOTES_SHORT_RE = ROLE_NOTES_RE
TASK_NOTES_SHORT_RE = TASK_NOTES_LONG_RE
COMMENT_CONTINUATION_RE = re.compile(r"^\s*#\s?(.*)$")
# Matches a stripped (de-commented) line that begins a YAML task list entry.
# Used to detect commented-out task blocks following an annotation.
COMMENTED_TASK_ENTRY_RE = re.compile(r"^\s*-\s+name:\s*\S")
# Heuristic markers for YAML-like payloads in annotation comments.
YAML_LIKE_KEY_VALUE_RE = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_-]*\s*:\s*\S")
YAML_LIKE_LIST_ITEM_RE = re.compile(r"^\s*-\s+[A-Za-z_][A-Za-z0-9_-]*\s*:\s*\S")
WHEN_IN_LIST_RE = re.compile(
    r"^\s*(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s+in\s+(?P<values>\[[^\]]*\])\s*$"
)
TEMPLATED_INCLUDE_RE = re.compile(
    r"^\s*(?P<prefix>[^{}]*)\{\{\s*(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*\}\}(?P<suffix>[^{}]*)\s*$"
)

# ---------------------------------------------------------------------------
# Path exclusion helpers
# ---------------------------------------------------------------------------


def _normalize_exclude_patterns(exclude_paths: list[str] | None) -> list[str]:
    """Return normalized glob patterns used to exclude role-relative paths."""
    if not exclude_paths:
        return []
    return [
        item.strip() for item in exclude_paths if isinstance(item, str) and item.strip()
    ]


def _is_relpath_excluded(relpath: str, exclude_paths: list[str] | None) -> bool:
    """Return True when a role-relative path should be excluded."""
    normalized = relpath.replace("\\", "/").lstrip("./")
    for pattern in _normalize_exclude_patterns(exclude_paths):
        if fnmatch(normalized, pattern) or fnmatch(f"{normalized}/", pattern):
            return True
        if "/" not in pattern and normalized.split("/", 1)[0] == pattern:
            return True
    return False


def _is_path_excluded(
    path: Path, role_root: Path, exclude_paths: list[str] | None
) -> bool:
    """Return True when an absolute path resolves to an excluded role-relative path."""
    try:
        relpath = str(path.resolve().relative_to(role_root.resolve()))
    except ValueError:
        return False
    return _is_relpath_excluded(relpath, exclude_paths)


# ---------------------------------------------------------------------------
# YAML utility
# ---------------------------------------------------------------------------


def _format_inline_yaml(value: object) -> str:
    """Render a value as compact inline YAML for README tables."""
    text = yaml.safe_dump(value, default_flow_style=True, sort_keys=False).strip()
    return text.replace("\n", " ").replace("...", "").strip()


# ---------------------------------------------------------------------------
# YAML file loading
# ---------------------------------------------------------------------------


def _load_yaml_file(file_path: Path) -> object | None:
    """Load a YAML file and return its contents, or ``None`` on failure."""
    try:
        return yaml.safe_load(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Task document iteration
# ---------------------------------------------------------------------------


def _iter_task_include_targets(data: object) -> list[str]:
    """Return include/import task targets found in a task YAML structure."""
    targets: list[str] = []
    for task in _iter_task_mappings(data):
        for key in TASK_INCLUDE_KEYS:
            if key not in task:
                continue
            value = task[key]
            if isinstance(value, str):
                expanded = _expand_include_target_candidates(task, value)
                if expanded:
                    targets.extend(expanded)
                else:
                    candidate = value.strip()
                    if candidate:
                        targets.append(candidate)
            elif isinstance(value, dict):
                file_value = value.get("file") or value.get("_raw_params")
                if isinstance(file_value, str):
                    expanded = _expand_include_target_candidates(task, file_value)
                    if expanded:
                        targets.extend(expanded)
                    else:
                        candidate = file_value.strip()
                        if candidate:
                            targets.append(candidate)
    return targets


def _extract_constrained_when_values(task: dict, variable: str) -> list[str]:
    """Return constrained values for ``variable`` from simple ``when`` clauses.

    Supported form:
        when: variable in ["a", "b"]
        when:
          - variable in ["a", "b"]
    """
    when_value = task.get("when")
    conditions: list[str] = []
    if isinstance(when_value, str):
        conditions.append(when_value)
    elif isinstance(when_value, list):
        conditions.extend(item for item in when_value if isinstance(item, str))

    values: list[str] = []
    for condition in conditions:
        match = WHEN_IN_LIST_RE.match(condition.strip())
        if not match:
            continue
        if (match.group("var") or "").strip() != variable:
            continue
        parsed = yaml.safe_load(match.group("values"))
        if not isinstance(parsed, list):
            continue
        for item in parsed:
            if isinstance(item, str):
                values.append(item)

    deduped: list[str] = []
    seen: set[str] = set()
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _expand_include_target_candidates(task: dict, include_target: str) -> list[str]:
    """Return concrete include candidates from static or constrained dynamic target."""
    candidate = include_target.strip()
    if not candidate:
        return []
    if "{{" not in candidate and "{%" not in candidate:
        return [candidate]

    match = TEMPLATED_INCLUDE_RE.match(candidate)
    if not match:
        return []

    variable = (match.group("var") or "").strip()
    if not variable:
        return []
    allowed_values = _extract_constrained_when_values(task, variable)
    if not allowed_values:
        return []

    prefix = (match.group("prefix") or "").strip()
    suffix = (match.group("suffix") or "").strip()
    return [f"{prefix}{value}{suffix}" for value in allowed_values]


def _collect_unconstrained_dynamic_task_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict[str, str]]:
    """Return unconstrained dynamic include/import task references.

    A dynamic include is considered unconstrained when it contains templating
    and cannot be expanded into static candidates via simple ``when`` allow-lists.
    """
    role_root = Path(role_path).resolve()
    findings: list[dict[str, str]] = []

    for task_file in _collect_task_files(role_root, exclude_paths=exclude_paths):
        data = _load_yaml_file(task_file)
        relpath = str(task_file.relative_to(role_root))
        for task in _iter_task_mappings(data):
            task_name = str(task.get("name") or "(unnamed task)")
            for include_key in TASK_INCLUDE_KEYS:
                if include_key not in task:
                    continue
                include_target = task[include_key]
                include_path: str | None = None
                if isinstance(include_target, str):
                    include_path = include_target
                elif isinstance(include_target, dict):
                    candidate = include_target.get("file") or include_target.get(
                        "_raw_params"
                    )
                    if isinstance(candidate, str):
                        include_path = candidate

                if not include_path:
                    continue
                include_path = include_path.strip()
                if "{{" not in include_path and "{%" not in include_path:
                    continue
                if _expand_include_target_candidates(task, include_path):
                    continue

                findings.append(
                    {
                        "file": relpath,
                        "task": task_name,
                        "module": (
                            "import_tasks"
                            if "import_tasks" in include_key
                            else "include_tasks"
                        ),
                        "target": include_path,
                    }
                )

    return findings


def _collect_unconstrained_dynamic_role_includes(
    role_path: str,
    exclude_paths: list[str] | None = None,
) -> list[dict[str, str]]:
    """Return unconstrained dynamic include/import role references.

    A dynamic include role reference is considered unconstrained when it
    contains templating and cannot be expanded into static candidates via
    simple ``when`` allow-lists.
    """
    role_root = Path(role_path).resolve()
    findings: list[dict[str, str]] = []

    for task_file in _collect_task_files(role_root, exclude_paths=exclude_paths):
        data = _load_yaml_file(task_file)
        relpath = str(task_file.relative_to(role_root))
        for task in _iter_task_mappings(data):
            task_name = str(task.get("name") or "(unnamed task)")
            for include_key in ROLE_INCLUDE_KEYS:
                if include_key not in task:
                    continue
                include_target = task[include_key]
                role_ref: str | None = None
                if isinstance(include_target, str):
                    role_ref = include_target
                elif isinstance(include_target, dict):
                    candidate = include_target.get("name") or include_target.get(
                        "_raw_params"
                    )
                    if isinstance(candidate, str):
                        role_ref = candidate

                if not role_ref:
                    continue
                role_ref = role_ref.strip()
                if "{{" not in role_ref and "{%" not in role_ref:
                    continue
                if _expand_include_target_candidates(task, role_ref):
                    continue

                findings.append(
                    {
                        "file": relpath,
                        "task": task_name,
                        "module": (
                            "import_role"
                            if "import_role" in include_key
                            else "include_role"
                        ),
                        "target": role_ref,
                    }
                )

    return findings


def _iter_role_include_targets(task: dict) -> list[str]:
    """Return static role names referenced by include_role/import_role keys."""
    role_targets: list[str] = []
    for key in ROLE_INCLUDE_KEYS:
        if key not in task:
            continue
        value = task[key]
        ref: str | None = None
        if isinstance(value, str):
            ref = value
        elif isinstance(value, dict):
            candidate = value.get("name") or value.get("_raw_params")
            if isinstance(candidate, str):
                ref = candidate
        if not ref:
            continue
        ref = ref.strip()
        if not ref or "{{" in ref or "{%" in ref:
            continue
        role_targets.append(ref)
    return role_targets


def _iter_dynamic_role_include_targets(task: dict) -> list[str]:
    """Return templated role refs from include_role/import_role keys."""
    dynamic_targets: list[str] = []
    for key in ROLE_INCLUDE_KEYS:
        if key not in task:
            continue
        value = task[key]
        ref: str | None = None
        if isinstance(value, str):
            ref = value
        elif isinstance(value, dict):
            candidate = value.get("name") or value.get("_raw_params")
            if isinstance(candidate, str):
                ref = candidate
        if not ref:
            continue
        ref = ref.strip()
        if ref and ("{{" in ref or "{%" in ref):
            dynamic_targets.append(ref)
    return dynamic_targets


def _iter_task_mappings(data: object):
    """Yield task dictionaries from a YAML task document recursively."""
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            yield item
            for key in TASK_BLOCK_KEYS:
                nested = item.get(key)
                if nested is not None:
                    yield from _iter_task_mappings(nested)


def _resolve_task_include(
    role_root: Path, current_file: Path, include_target: str
) -> Path | None:
    """Resolve an included task file relative to the current task file or tasks dir."""
    candidate = include_target.strip()
    if not candidate or "{{" in candidate or "{%" in candidate:
        return None

    path = Path(candidate)
    candidates: list[Path] = []
    if path.is_absolute():
        candidates.append(path)
    else:
        candidates.append((current_file.parent / path).resolve())
        candidates.append((role_root / "tasks" / path).resolve())

    if not path.suffix:
        candidates.extend(resolved.with_suffix(".yml") for resolved in list(candidates))

    for resolved in candidates:
        if not resolved.is_file():
            continue
        try:
            resolved.relative_to(role_root)
        except ValueError:
            continue
        return resolved

    # Heuristic fallback for role fixtures/docs: if include target has no
    # directory segment, try finding a unique basename under tasks/**.
    if not path.is_absolute() and len(path.parts) == 1:
        tasks_dir = role_root / "tasks"
        suffixes = [path.suffix] if path.suffix else [".yml", ".yaml"]
        fallback_matches: list[Path] = []
        for suffix in suffixes:
            name = path.name if path.suffix else f"{path.name}{suffix}"
            fallback_matches.extend(p for p in tasks_dir.rglob(name) if p.is_file())
        unique_matches = sorted({p.resolve() for p in fallback_matches})
        if len(unique_matches) == 1:
            return unique_matches[0]

    return None


def _collect_task_files(
    role_root: Path,
    exclude_paths: list[str] | None = None,
) -> list[Path]:
    """Collect task files reachable from ``tasks/main.yml`` recursively."""
    tasks_dir = role_root / "tasks"
    if not tasks_dir.is_dir():
        return []

    entrypoints = [tasks_dir / "main.yml"] if (tasks_dir / "main.yml").exists() else []
    if not entrypoints:
        entrypoints = sorted(
            path
            for path in tasks_dir.rglob("*")
            if path.is_file()
            and path.suffix in {".yml", ".yaml"}
            and not _is_path_excluded(path, role_root, exclude_paths)
        )

    discovered: list[Path] = []
    pending = list(entrypoints)
    seen: set[Path] = set()
    while pending:
        current = pending.pop(0).resolve()
        if current in seen or not current.is_file():
            continue
        if _is_path_excluded(current, role_root, exclude_paths):
            continue
        seen.add(current)
        discovered.append(current)

        data = _load_yaml_file(current)
        for include_target in _iter_task_include_targets(data):
            resolved = _resolve_task_include(role_root, current, include_target)
            if (
                resolved is not None
                and resolved not in seen
                and not _is_path_excluded(resolved, role_root, exclude_paths)
            ):
                pending.append(resolved)

    return sorted(discovered, key=lambda path: str(path.relative_to(role_root)))


# ---------------------------------------------------------------------------
# Role notes extraction from comments
# ---------------------------------------------------------------------------


def _extract_role_notes_from_comments(
    role_path: str,
    exclude_paths: list[str] | None = None,
    marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX,
) -> dict[str, list[str]]:
    """Extract comment-driven role notes from YAML files.

    Supported syntax:
        # prism~warning: text
        # prism~deprecated: text
        # prism~note: text
        # prism~notes: text
        # prism~additional: text
    """
    marker_line_re = _build_marker_line_re(marker_prefix)
    role_root = Path(role_path).resolve()
    categories: dict[str, list[str]] = {
        "warnings": [],
        "deprecations": [],
        "notes": [],
        "additionals": [],
    }
    files: list[Path] = []
    files.extend(_collect_task_files(role_root, exclude_paths=exclude_paths))
    for rel in ("defaults/main.yml", "vars/main.yml", "handlers/main.yml"):
        candidate = role_root / rel
        if candidate.is_file() and not _is_path_excluded(
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
                cont_match = COMMENT_CONTINUATION_RE.match(next_line)
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
# Task annotation helpers
# ---------------------------------------------------------------------------


def _split_task_annotation_label(text: str) -> tuple[str, str]:
    """Return normalized annotation kind and body from a comment payload."""
    raw = text.strip()
    if not raw:
        return "note", ""
    if ":" not in raw:
        return "note", raw

    prefix, remainder = raw.split(":", 1)
    label = prefix.strip().lower()
    body = remainder.strip()
    if label in {
        "runbook",
        "warning",
        "deprecated",
        "note",
        "notes",
        "additional",
        "additionals",
    }:
        if label == "notes":
            label = "note"
        if label == "additionals":
            label = "additional"
        return label, body
    return "note", raw


def _split_task_target_payload(text: str) -> tuple[str, str]:
    """Split ``task`` marker body into ``target | annotation`` parts."""
    if "|" not in text:
        return "", text.strip()
    target, payload = text.split("|", 1)
    return target.strip(), payload.strip()


def _annotation_payload_looks_yaml(payload: str) -> bool:
    """Heuristically detect YAML-style mapping syntax in annotation payloads."""
    return any(
        YAML_LIKE_KEY_VALUE_RE.match(line) or YAML_LIKE_LIST_ITEM_RE.match(line)
        for line in payload.splitlines()
    )


def _extract_task_annotations_for_file(
    lines: list[str],
    marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX,
) -> tuple[list[dict[str, object]], dict[str, list[dict[str, object]]]]:
    """Extract implicit and explicit task annotations from file comment lines."""
    marker_line_re = _build_marker_line_re(marker_prefix)
    implicit: list[dict[str, object]] = []
    explicit: dict[str, list[dict[str, object]]] = defaultdict(list)

    i = 0
    while i < len(lines):
        line = lines[i]
        marker_match = marker_line_re.match(line)
        if not marker_match:
            i += 1
            continue

        target_name = ""
        label = (marker_match.group("label") or "").strip().lower()
        text = (marker_match.group("body") or "").strip()

        if label == "task":
            target_name, text = _split_task_target_payload(text)
            if not target_name:
                # task with no explicit target is treated as a regular note payload
                label = "note"
        elif label not in {
            "runbook",
            "warning",
            "deprecated",
            "note",
            "notes",
            "additional",
            "additionals",
        }:
            i += 1
            continue

        if label == "notes":
            label = "note"
        if label == "additionals":
            label = "additional"

        continuation: list[str] = []
        j = i + 1
        while j < len(lines):
            next_line = lines[j]
            if marker_line_re.match(next_line):
                break
            cont_match = COMMENT_CONTINUATION_RE.match(next_line)
            if not cont_match:
                break
            continuation.append((cont_match.group(1) or "").strip())
            j += 1

        if continuation:
            text = "\n".join(part for part in [text, *continuation] if part)

        disabled = any(COMMENTED_TASK_ENTRY_RE.match(c) for c in continuation)
        if label == "task" and target_name:
            kind, body = _split_task_annotation_label(text)
        else:
            kind, body = _split_task_annotation_label(f"{label}: {text}")
        if body:
            yaml_like = _annotation_payload_looks_yaml(body)
            item: dict[str, object] = {"kind": kind, "text": body}
            if disabled:
                item["disabled"] = True
            if yaml_like:
                item["format_warning"] = "yaml-like-payload-use-key-equals-value"
            if target_name:
                explicit[target_name].append(item)
            else:
                implicit.append(item)

        i = j if j > i + 1 else i + 1

    return implicit, explicit


def _task_anchor(file_path: str, task_name: str, index: int) -> str:
    """Build a stable markdown anchor id for task detail links."""
    raw = f"task-{file_path}-{task_name}-{index}"
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return slug or f"task-{index}"


# ---------------------------------------------------------------------------
# Module and collection detection
# ---------------------------------------------------------------------------


def _detect_task_module(task: dict) -> str | None:
    """Detect the task module key from an Ansible task mapping."""
    # Check for explicit include/import tasks first
    for include_key in TASK_INCLUDE_KEYS:
        if include_key in task:
            # Normalize to short form for readability
            if "import_tasks" in include_key:
                return "import_tasks"
            return "include_tasks"

    for include_key in ROLE_INCLUDE_KEYS:
        if include_key in task:
            if "import_role" in include_key:
                return "import_role"
            return "include_role"

    # Then look for regular modules
    for key in task:
        if key in TASK_META_KEYS or key in TASK_BLOCK_KEYS:
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
            for include_key in ROLE_INCLUDE_KEYS:
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
            f"{key}={_format_inline_yaml(val)}"
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
# Task and handler catalog
# ---------------------------------------------------------------------------


def _collect_task_handler_catalog(
    role_path: str,
    exclude_paths: list[str] | None = None,
    marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX,
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
        if _is_path_excluded(task_file, role_root, exclude_paths):
            return

        seen_files.add(task_file)
        data = _load_yaml_file(task_file)
        try:
            raw_lines = task_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            raw_lines = []
        implicit_annotations, explicit_annotations = _extract_task_annotations_for_file(
            raw_lines,
            marker_prefix=marker_prefix,
        )
        implicit_index = 0
        relpath = str(task_file.relative_to(role_root))
        # Strip "tasks/" prefix since this is a task catalog
        if relpath.startswith("tasks/"):
            relpath = relpath[6:]

        for task in _iter_task_mappings(data):
            # Add this task to the catalog
            module_name = _detect_task_module(task) or "unknown"
            task_name = str(task.get("name") or "(unnamed task)")
            annotations: list[dict[str, object]] = []
            if implicit_index < len(implicit_annotations):
                annotations.append(implicit_annotations[implicit_index])
                implicit_index += 1
            annotations.extend(explicit_annotations.get(task_name, []))

            runbook_items = [
                note.get("text", "")
                for note in annotations
                if note.get("kind") == "runbook" and note.get("text")
            ]
            runbook = runbook_items[0] if runbook_items else ""
            anchor = _task_anchor(relpath, task_name, len(task_entries) + 1)
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
            for include_key in TASK_INCLUDE_KEYS:
                if include_key in task:
                    include_target = task[include_key]
                    include_paths: list[str] = []
                    if isinstance(include_target, str):
                        include_paths.extend(
                            _expand_include_target_candidates(task, include_target)
                        )
                    elif isinstance(include_target, dict):
                        candidate = include_target.get("file") or include_target.get(
                            "_raw_params"
                        )
                        if isinstance(candidate, str):
                            include_paths.extend(
                                _expand_include_target_candidates(task, candidate)
                            )

                    for include_path in include_paths:
                        included_file = _resolve_task_include(
                            role_root, task_file, include_path
                        )
                        if included_file:
                            _collect_tasks_recursive(
                                included_file, task_entries, seen_files
                            )

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
            if _is_path_excluded(handler_file, role_root, exclude_paths):
                continue
            data = _load_yaml_file(handler_file)
            relpath = str(handler_file.relative_to(role_root))
            # Strip "handlers/" prefix since this is a handler catalog
            if relpath.startswith("handlers/"):
                relpath = relpath[9:]
            for task in _iter_task_mappings(data):
                module_name = _detect_task_module(task) or "unknown"
                task_name = str(task.get("name") or "(unnamed handler)")
                handler_entries.append(
                    {
                        "file": relpath,
                        "name": task_name,
                        "module": module_name,
                        "parameters": _compact_task_parameters(task, module_name),
                        "anchor": _task_anchor(
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
        if not molecule_file.is_file() or _is_path_excluded(
            molecule_file, role_root, exclude_paths
        ):
            continue
        doc = _load_yaml_file(molecule_file)
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
    task_files = _collect_task_files(role_root, exclude_paths=exclude_paths)

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
        data = _load_yaml_file(task_file)
        include_count += len(_iter_task_include_targets(data))
        for task in _iter_task_mappings(data):
            tasks_scanned += 1
            included_targets = _iter_role_include_targets(task)
            included_role_calls += len(included_targets)
            included_roles.update(included_targets)
            dynamic_targets = _iter_dynamic_role_include_targets(task)
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
        impl_anns, expl_anns = _extract_task_annotations_for_file(raw_lines)
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
