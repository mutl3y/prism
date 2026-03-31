"""Canonical variable row population pipeline extracted from scanner.py."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from prism.scanner_data.contracts import ReferenceContext, VariableRow

from ..scanner_analysis.metrics import (
    attach_non_authoritative_test_evidence,
    build_referenced_variable_uncertainty_reason,
    should_suppress_internal_unresolved_reference,
    NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES,
    NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED,
    NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES,
)
from ..scanner_extract import (
    IGNORED_IDENTIFIERS,
    JINJA_IDENTIFIER_RE,
    _collect_include_vars_files,
    iter_role_argument_spec_entries,
    load_meta,
    _load_yaml_file,
)
from ..scanner_extract.task_parser import _format_inline_yaml
from ..scanner_extract.variable_extractor import (
    _collect_dynamic_include_vars_refs,
    _collect_dynamic_task_include_refs,
    _collect_referenced_variable_names,
    _collect_register_names,
    _collect_set_fact_names,
    _find_variable_line_in_yaml,
    _infer_variable_type,
    _is_sensitive_variable,
)
from ..scanner_readme.input_parser import collect_readme_input_variables


def collect_dynamic_task_include_tokens(
    role_path: str,
    exclude_paths: list[str] | None,
) -> set[str]:
    """Collect unresolved Jinja identifier tokens from dynamic task includes."""
    dynamic_task_include_refs = _collect_dynamic_task_include_refs(
        role_path,
        exclude_paths=exclude_paths,
    )
    tokens: set[str] = set()
    for ref in dynamic_task_include_refs:
        tokens.update(
            token
            for token in JINJA_IDENTIFIER_RE.findall(ref)
            if token.lower() not in IGNORED_IDENTIFIERS
        )
    return tokens


def collect_dynamic_include_var_tokens(
    dynamic_include_vars_refs: list[str],
) -> set[str]:
    """Collect unresolved Jinja identifier tokens from dynamic include_vars refs."""
    tokens: set[str] = set()
    for ref in dynamic_include_vars_refs:
        tokens.update(
            token
            for token in JINJA_IDENTIFIER_RE.findall(ref)
            if token.lower() not in IGNORED_IDENTIFIERS
        )
    return tokens


def build_static_variable_rows(
    *,
    role_root: Path,
    defaults_data: dict,
    vars_data: dict,
    defaults_sources: dict[str, Path],
    vars_sources: dict[str, Path],
) -> tuple[list[VariableRow], dict[str, VariableRow]]:
    """Build baseline rows from defaults/main.yml and vars/main.yml."""
    rows: list[VariableRow] = []
    rows_by_name: dict[str, VariableRow] = {}
    for name in sorted(set(defaults_data) | set(vars_data)):
        has_default = name in defaults_data
        has_var = name in vars_data
        value = vars_data[name] if has_var else defaults_data.get(name)
        default_source_file = defaults_sources.get(name)
        vars_source_file = vars_sources.get(name)
        source = "defaults/main.yml"
        provenance_source_file = "defaults/main.yml"
        provenance_line = (
            _find_variable_line_in_yaml(default_source_file, name)
            if default_source_file is not None
            else None
        )
        provenance_confidence = 0.95
        uncertainty_reason = None
        is_ambiguous = False
        if default_source_file is not None:
            provenance_source_file = str(default_source_file.relative_to(role_root))
        if has_var and has_default:
            source = "defaults/main.yml + vars/main.yml override"
            provenance_source_file = (
                str(vars_source_file.relative_to(role_root))
                if vars_source_file is not None
                else "vars/main.yml"
            )
            provenance_line = (
                _find_variable_line_in_yaml(vars_source_file, name)
                if vars_source_file is not None
                else None
            )
            provenance_confidence = 0.80
            uncertainty_reason = (
                "Defaults value is superseded by vars/main.yml precedence "
                "(informational)."
            )
            is_ambiguous = True
        elif has_var:
            source = "vars/main.yml"
            provenance_source_file = (
                str(vars_source_file.relative_to(role_root))
                if vars_source_file is not None
                else "vars/main.yml"
            )
            provenance_line = (
                _find_variable_line_in_yaml(vars_source_file, name)
                if vars_source_file is not None
                else None
            )
            provenance_confidence = 0.90
        row: VariableRow = {
            "name": name,
            "type": _infer_variable_type(value),
            "default": _format_inline_yaml(value),
            "source": source,
            "documented": True,
            "required": False,
            "secret": _is_sensitive_variable(name, value),
            "provenance_source_file": provenance_source_file,
            "provenance_line": provenance_line,
            "provenance_confidence": provenance_confidence,
            "uncertainty_reason": uncertainty_reason,
            "is_unresolved": False,
            "is_ambiguous": is_ambiguous,
        }
        rows.append(row)
        rows_by_name[name] = row
    return rows, rows_by_name


def append_include_vars_rows(
    *,
    role_path: str,
    role_root: Path,
    rows: list[VariableRow],
    rows_by_name: dict[str, VariableRow],
    exclude_paths: list[str] | None,
) -> set[str]:
    """Merge include_vars-derived values into variable insight rows."""
    known_names: set[str] = {row["name"] for row in rows}
    include_var_sources = collect_include_var_sources(
        role_path=role_path,
        role_root=role_root,
        exclude_paths=exclude_paths,
    )

    for name in sorted(include_var_sources):
        entries = include_var_sources[name]
        if name in rows_by_name:
            mark_existing_row_as_include_vars_ambiguous(rows_by_name[name], entries)
            continue
        known_names.add(name)
        rows.append(build_include_vars_row(name, entries))

    return known_names


def collect_include_var_sources(
    *,
    role_path: str,
    role_root: Path,
    exclude_paths: list[str] | None,
) -> dict[str, list[dict[str, Any]]]:
    """Collect include_vars value sources keyed by variable name."""
    include_var_sources: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for extra_path in _collect_include_vars_files(
        role_path,
        exclude_paths=exclude_paths,
    ):
        extra_data = _load_yaml_file(extra_path)
        if not isinstance(extra_data, dict):
            continue
        rel_source = str(extra_path.relative_to(role_root))
        for name in sorted(extra_data):
            include_var_sources[name].append(
                {
                    "source": rel_source,
                    "value": extra_data[name],
                    "line": _find_variable_line_in_yaml(extra_path, name),
                }
            )
    return include_var_sources


def mark_existing_row_as_include_vars_ambiguous(
    row: VariableRow, entries: list[dict[str, Any]]
) -> None:
    """Downgrade confidence for rows that can be overridden by include_vars."""
    row["is_ambiguous"] = True
    row["uncertainty_reason"] = (
        "May be overridden by include_vars sources: "
        + ", ".join(entry["source"] for entry in entries)
    )
    row["provenance_confidence"] = min(
        float(row.get("provenance_confidence", 1.0)),
        0.70,
    )


def build_include_vars_row(name: str, entries: list[dict[str, Any]]) -> VariableRow:
    """Build a variable insight row for include_vars-discovered variables."""
    selected = entries[-1]
    ambiguous = len(entries) > 1
    result: VariableRow = {
        "name": name,
        "type": _infer_variable_type(selected["value"]),
        "default": _format_inline_yaml(selected["value"]),
        "source": selected["source"],
        "documented": True,
        "required": False,
        "secret": _is_sensitive_variable(name, selected["value"]),
        "provenance_source_file": selected["source"],
        "provenance_line": selected["line"],
        "provenance_confidence": 0.60 if ambiguous else 0.85,
        "uncertainty_reason": (
            "Defined in multiple include_vars files: "
            + ", ".join(entry["source"] for entry in entries)
            if ambiguous
            else None
        ),
        "is_unresolved": False,
        "is_ambiguous": ambiguous,
    }
    return result


def append_set_fact_rows(
    *,
    role_path: str,
    rows: list[VariableRow],
    known_names: set[str],
    exclude_paths: list[str] | None,
) -> None:
    """Append computed variable placeholders discovered from set_fact usage."""
    for name in sorted(
        _collect_set_fact_names(role_path, exclude_paths=exclude_paths) - known_names
    ):
        row: VariableRow = {
            "name": name,
            "type": "computed",
            "default": "-",
            "source": "tasks (set_fact)",
            "documented": True,
            "required": False,
            "secret": False,
            "provenance_source_file": "tasks (set_fact)",
            "provenance_line": None,
            "provenance_confidence": 0.65,
            "uncertainty_reason": "Computed by set_fact at runtime.",
            "is_unresolved": False,
            "is_ambiguous": True,
        }
        rows.append(row)


def append_register_rows(
    *,
    role_path: str,
    rows: list[VariableRow],
    known_names: set[str],
    exclude_paths: list[str] | None,
) -> None:
    """Append runtime placeholders for task-level register variables."""
    for name in sorted(
        _collect_register_names(role_path, exclude_paths=exclude_paths) - known_names
    ):
        row: VariableRow = {
            "name": name,
            "type": "computed",
            "default": "-",
            "source": "tasks (register)",
            "documented": True,
            "required": False,
            "secret": False,
            "provenance_source_file": "tasks (register)",
            "provenance_line": None,
            "provenance_confidence": 0.75,
            "uncertainty_reason": None,
            "is_unresolved": False,
            "is_ambiguous": False,
        }
        rows.append(row)


def append_readme_documented_rows(
    *,
    role_path: str,
    rows: list[VariableRow],
    style_readme_path: str | None = None,
) -> None:
    """Enrich existing variable rows with README documentation."""
    readme_vars = collect_readme_input_variables(
        role_path, style_readme_path=style_readme_path
    )

    for row in rows:
        name = row["name"]
        if name in readme_vars:
            if not row.get("documented"):
                row["documented"] = True
            row["required"] = False
            row["is_unresolved"] = False
            if "README.md" not in row.get("source", ""):
                row["readme_documented"] = True


def append_argument_spec_rows(
    *,
    role_path: str,
    rows: list[VariableRow],
    known_names: set[str],
    map_argument_spec_type,
) -> set[str]:
    """Append argument_specs-declared inputs not yet present in row set."""
    for source_file, name, spec in iter_role_argument_spec_entries(
        role_path,
        load_yaml_file_fn=_load_yaml_file,
        load_meta_fn=load_meta,
    ):
        if name in known_names:
            continue
        has_default = "default" in spec
        default_value = spec.get("default")
        required = bool(spec.get("required", False) and not has_default)
        line_hint = _find_variable_line_in_yaml(Path(role_path) / source_file, name)
        spec_row: VariableRow = {
            "name": name,
            "type": map_argument_spec_type(spec.get("type")),
            "default": (
                _format_inline_yaml(default_value) if has_default else "<required>"
            ),
            "source": f"{source_file} (argument_specs)",
            "documented": True,
            "required": required,
            "secret": _is_sensitive_variable(name, default_value),
            "provenance_source_file": source_file,
            "provenance_line": line_hint,
            "provenance_confidence": 0.88 if has_default else 0.78,
            "uncertainty_reason": (
                "Declared in argument_specs without a static default value."
                if required
                else None
            ),
            "is_unresolved": required,
            "is_ambiguous": False,
        }
        rows.append(spec_row)
        known_names.add(name)
    return known_names


def append_referenced_variable_rows(
    *,
    role_path: str,
    rows: list[VariableRow],
    known_names: set[str],
    seed_values: dict,
    seed_secrets: set[str],
    seed_sources: dict,
    dynamic_include_vars_refs: list[str],
    dynamic_include_var_tokens: set[str],
    dynamic_task_include_tokens: set[str],
    ignore_unresolved_internal_underscore_references: bool,
    exclude_paths: list[str] | None,
) -> None:
    """Append rows for referenced-but-undefined variable names."""
    referenced_names = _collect_referenced_variable_names(
        role_path,
        exclude_paths=exclude_paths,
    )

    for name in sorted(referenced_names - known_names):
        if should_suppress_internal_unresolved_reference(
            name=name,
            seed_values=seed_values,
            ignore_unresolved_internal_underscore_references=(
                ignore_unresolved_internal_underscore_references
            ),
        ):
            continue
        rows.append(
            build_referenced_variable_row(
                name=name,
                seed_values=seed_values,
                seed_secrets=seed_secrets,
                seed_sources=seed_sources,
                dynamic_include_vars_refs=dynamic_include_vars_refs,
                dynamic_include_var_tokens=dynamic_include_var_tokens,
                dynamic_task_include_tokens=dynamic_task_include_tokens,
            )
        )


def build_referenced_variable_row(
    *,
    name: str,
    seed_values: dict,
    seed_secrets: set[str],
    seed_sources: dict,
    dynamic_include_vars_refs: list[str],
    dynamic_include_var_tokens: set[str],
    dynamic_task_include_tokens: set[str],
) -> VariableRow:
    """Build one inferred variable row for referenced-but-undefined names."""
    seeded = name in seed_values
    value = seed_values.get(name, "<required>")
    source_name = seed_sources.get(name, "external vars")
    result: VariableRow = {
        "name": name,
        "type": _infer_variable_type(value) if seeded else "required",
        "default": _format_inline_yaml(value) if seeded else "<required>",
        "source": f"seed: {source_name}" if seeded else "inferred usage",
        "documented": False,
        "required": not seeded,
        "secret": (name in seed_secrets or _is_sensitive_variable(name, value)),
        "provenance_source_file": source_name if seeded else None,
        "provenance_line": None,
        "provenance_confidence": 0.75 if seeded else 0.40,
        "uncertainty_reason": build_referenced_variable_uncertainty_reason(
            name=name,
            seeded=seeded,
            dynamic_include_vars_refs=dynamic_include_vars_refs,
            dynamic_include_var_tokens=dynamic_include_var_tokens,
            dynamic_task_include_tokens=dynamic_task_include_tokens,
        ),
        "is_unresolved": not seeded,
        "is_ambiguous": False,
    }
    return result


def collect_variable_reference_context(
    *,
    role_path: str,
    seed_paths: list[str] | None,
    exclude_paths: list[str] | None,
    load_seed_variables,
) -> ReferenceContext:
    """Collect seed and dynamic-reference context for inferred variable rows."""
    seed_values, seed_secrets, seed_sources = load_seed_variables(seed_paths)
    dynamic_include_vars_refs = _collect_dynamic_include_vars_refs(
        role_path,
        exclude_paths=exclude_paths,
    )
    dynamic_include_var_tokens = collect_dynamic_include_var_tokens(
        dynamic_include_vars_refs
    )
    dynamic_task_include_tokens = collect_dynamic_task_include_tokens(
        role_path,
        exclude_paths=exclude_paths,
    )
    return {
        "seed_values": seed_values,
        "seed_secrets": seed_secrets,
        "seed_sources": seed_sources,
        "dynamic_include_vars_refs": dynamic_include_vars_refs,
        "dynamic_include_var_tokens": dynamic_include_var_tokens,
        "dynamic_task_include_tokens": dynamic_task_include_tokens,
    }


def populate_variable_rows(
    *,
    role_path: str,
    rows: list[VariableRow],
    rows_by_name: dict[str, VariableRow],
    exclude_paths: list[str] | None,
    reference_context: ReferenceContext,
    map_argument_spec_type,
    style_readme_path: str | None = None,
    ignore_unresolved_internal_underscore_references: bool = True,
    non_authoritative_test_evidence_max_file_bytes: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES,
    non_authoritative_test_evidence_max_files_scanned: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED,
    non_authoritative_test_evidence_max_total_bytes: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES,
) -> None:
    """Populate dynamic, documented, and inferred variable rows in-place."""
    role_root = Path(role_path).resolve()
    known_names = append_include_vars_rows(
        role_path=role_path,
        role_root=role_root,
        rows=rows,
        rows_by_name=rows_by_name,
        exclude_paths=exclude_paths,
    )
    append_set_fact_rows(
        role_path=role_path,
        rows=rows,
        known_names=known_names,
        exclude_paths=exclude_paths,
    )
    known_names = refresh_known_names(rows)
    append_register_rows(
        role_path=role_path,
        rows=rows,
        known_names=known_names,
        exclude_paths=exclude_paths,
    )
    known_names = refresh_known_names(rows)
    known_names = append_argument_spec_rows(
        role_path=role_path,
        rows=rows,
        known_names=known_names,
        map_argument_spec_type=map_argument_spec_type,
    )
    known_names = refresh_known_names(rows)
    append_referenced_variable_rows(
        role_path=role_path,
        rows=rows,
        known_names=known_names,
        seed_values=reference_context["seed_values"],
        seed_secrets=reference_context["seed_secrets"],
        seed_sources=reference_context["seed_sources"],
        dynamic_include_vars_refs=reference_context["dynamic_include_vars_refs"],
        dynamic_include_var_tokens=reference_context["dynamic_include_var_tokens"],
        dynamic_task_include_tokens=reference_context["dynamic_task_include_tokens"],
        ignore_unresolved_internal_underscore_references=(
            ignore_unresolved_internal_underscore_references
        ),
        exclude_paths=exclude_paths,
    )
    append_readme_documented_rows(
        role_path=role_path,
        rows=rows,
        style_readme_path=style_readme_path,
    )
    attach_non_authoritative_test_evidence(
        role_path=role_path,
        rows=rows,
        exclude_paths=exclude_paths,
        max_file_bytes=non_authoritative_test_evidence_max_file_bytes,
        max_files_scanned=non_authoritative_test_evidence_max_files_scanned,
        max_total_bytes=non_authoritative_test_evidence_max_total_bytes,
    )


def refresh_known_names(rows: list[VariableRow]) -> set[str]:
    """Return a set of known variable names from row payloads."""
    return {row["name"] for row in rows}


def redact_secret_defaults(rows: list[VariableRow]) -> None:
    """Mask secret defaults in-place before rendering/output."""
    for row in rows:
        if row.get("secret"):
            row["default"] = "<secret>"
