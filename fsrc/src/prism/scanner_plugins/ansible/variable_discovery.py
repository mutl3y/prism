"""AnsibleVariableDiscoveryPlugin — Ansible-specific variable discovery logic."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from prism.scanner_core.variable_pipeline import _format_inline_yaml
from prism.scanner_core.variable_pipeline import _infer_variable_type
from prism.scanner_core.variable_pipeline import _is_sensitive_variable
from prism.scanner_data.builders import VariableRowBuilder
from prism.scanner_data.contracts_variables import VariableRow
from prism.scanner_io.loader import load_yaml_file as _load_yaml_loader_file
from prism.scanner_io.loader import parse_yaml_candidate
from prism.scanner_core.task_extract_adapters import collect_task_files
from prism.scanner_core.task_extract_adapters import is_path_excluded
from prism.scanner_core.task_extract_adapters import iter_task_mappings
from prism.scanner_core.task_extract_adapters import load_task_yaml_file

IGNORED_IDENTIFIERS: frozenset[str] = frozenset(
    {
        "ansible_facts",
        "groups",
        "hostvars",
        "inventory_hostname",
        "item",
        "omit",
        "vars",
    }
)


def _get_prepared_policy_bundle(
    options: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(options, dict):
        return None
    prepared_policy_bundle = options.get("prepared_policy_bundle")
    if isinstance(prepared_policy_bundle, dict):
        return prepared_policy_bundle
    return None


def _require_prepared_policy(
    options: dict[str, Any] | None,
    policy_name: str,
    context_name: str,
) -> Any:
    prepared_policy_bundle = _get_prepared_policy_bundle(options)
    if not isinstance(prepared_policy_bundle, dict):
        raise ValueError(
            "prepared_policy_bundle must be provided before "
            f"{context_name} native execution"
        )

    policy = prepared_policy_bundle.get(policy_name)
    if policy is None:
        raise ValueError(
            f"prepared_policy_bundle.{policy_name} must be provided before "
            f"{context_name} native execution"
        )
    return policy


def _get_task_line_parsing_policy(
    options: dict[str, Any] | None = None,
    di: object | None = None,
) -> Any:
    del di
    return _require_prepared_policy(
        options,
        "task_line_parsing",
        "VariableDiscovery",
    )


JINJA_VARIABLE_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_\.]*)")
JINJA_IDENTIFIER_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")
JINJA_EXPRESSION_RE = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)
QUOTED_STRING_RE = re.compile(r'"[^"]*"|\'[^\']*\'')
FILTER_OR_TEST_CONTEXT_RE = re.compile(r"(?:\|\s*|is\s+|is\s+not\s+)$")

REGISTERED_RESULT_ATTRS: frozenset[str] = frozenset(
    {
        "stdout",
        "stderr",
        "rc",
        "stdout_lines",
        "stderr_lines",
        "results",
        "changed",
        "failed",
        "skipped",
        "msg",
    }
)

WHEN_OPERATOR_KEYWORDS: frozenset[str] = frozenset(
    {
        "and",
        "or",
        "not",
        "is",
        "defined",
        "in",
        "eq",
        "ne",
        "lt",
        "gt",
        "le",
        "ge",
        "default",
        "true",
        "false",
        "none",
        "omit",
    }
)


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    return _load_yaml_mapping_with_metadata(path)


def _load_yaml_mapping_with_metadata(
    path: Path,
    *,
    role_root: Path | None = None,
    yaml_failure_collector: list[dict[str, object]] | None = None,
    di: object | None = None,
) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = _load_yaml_loader_file(path, di=di)
    except Exception:
        if yaml_failure_collector is not None:
            collector_root = role_root or path.resolve().parent
            failure = parse_yaml_candidate(path, collector_root, di=di)
            if isinstance(failure, dict):
                yaml_failure_collector.append(failure)
        return {}
    if parsed is None:
        if yaml_failure_collector is not None:
            collector_root = role_root or path.resolve().parent
            failure = parse_yaml_candidate(path, collector_root, di=di)
            if isinstance(failure, dict):
                yaml_failure_collector.append(failure)
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(key): value for key, value in parsed.items() if isinstance(key, str)}


def _iter_variable_map_candidates(role_root: Path, subdir: str) -> list[Path]:
    candidates: list[Path] = []
    main_yml = role_root / subdir / "main.yml"
    main_yaml = role_root / subdir / "main.yaml"
    if main_yml.exists():
        candidates.append(main_yml)
    elif main_yaml.exists():
        candidates.append(main_yaml)

    fragment_dir = role_root / subdir / "main"
    if fragment_dir.is_dir():
        candidates.extend(sorted(fragment_dir.glob("*.yml")))
        candidates.extend(sorted(fragment_dir.glob("*.yaml")))
    return candidates


def _map_argument_spec_type(spec_type: object) -> str:
    if not isinstance(spec_type, str):
        return "documented"
    normalized = spec_type.strip().lower()
    if normalized in {"str", "raw", "path", "bytes", "bits"}:
        return "string"
    if normalized in {"int"}:
        return "int"
    if normalized in {"bool"}:
        return "bool"
    if normalized in {"dict"}:
        return "dict"
    if normalized in {"list"}:
        return "list"
    if normalized in {"float"}:
        return "string"
    return "documented"


def _iter_role_argument_spec_entries(role_root: Path, *, di: object | None = None):
    return _iter_role_argument_spec_entries_with_metadata(role_root, di=di)


def _iter_role_argument_spec_entries_with_metadata(
    role_root: Path,
    *,
    yaml_failure_collector: list[dict[str, object]] | None = None,
    di: object | None = None,
):
    sources: list[tuple[str, dict[str, Any]]] = []
    arg_specs_file = role_root / "meta" / "argument_specs.yml"
    if arg_specs_file.is_file():
        loaded = _load_yaml_mapping_with_metadata(
            arg_specs_file,
            role_root=role_root,
            yaml_failure_collector=yaml_failure_collector,
            di=di,
        )
        if loaded:
            sources.append(("meta/argument_specs.yml", loaded))

    meta_main = _load_yaml_mapping_with_metadata(
        role_root / "meta" / "main.yml",
        role_root=role_root,
        yaml_failure_collector=yaml_failure_collector,
        di=di,
    )
    if meta_main:
        sources.append(("meta/main.yml", meta_main))

    for source_file, payload in sources:
        argument_specs = payload.get("argument_specs")
        if not isinstance(argument_specs, dict):
            continue
        for task_spec in argument_specs.values():
            if not isinstance(task_spec, dict):
                continue
            options = task_spec.get("options")
            if not isinstance(options, dict):
                continue
            for variable_name, spec in options.items():
                if not isinstance(variable_name, str) or not isinstance(spec, dict):
                    continue
                if "{{" in variable_name or "{%" in variable_name:
                    continue
                yield source_file, variable_name, spec


def _find_variable_line(path: Path, variable_name: str) -> int | None:
    if not path.exists():
        return None
    pattern = re.compile(rf"^\s*{re.escape(variable_name)}\s*:")
    try:
        for line_no, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if pattern.search(line):
                return line_no
    except OSError:
        return None
    return None


def _collect_include_vars_files(
    role_root: Path,
    exclude_paths: list[str] | None,
    *,
    options: dict[str, Any] | None = None,
    di: object | None = None,
    yaml_failure_collector: list[dict[str, object]] | None = None,
) -> list[Path]:
    result: list[Path] = []
    seen: set[Path] = set()
    include_vars_keys = _get_task_line_parsing_policy(options, di).INCLUDE_VARS_KEYS
    for task_file in collect_task_files(
        role_root,
        exclude_paths=exclude_paths,
        di=di,
    ):
        data = load_task_yaml_file(
            task_file,
            yaml_failure_collector=yaml_failure_collector,
            role_root=role_root,
            di=di,
        )
        for task in iter_task_mappings(data, di=di):
            for key in include_vars_keys:
                if key not in task:
                    continue
                value = task[key]
                ref: str | None = None
                if isinstance(value, str):
                    ref = value
                elif isinstance(value, dict):
                    file_candidate = value.get("file")
                    name_candidate = value.get("name")
                    ref = (
                        file_candidate
                        if isinstance(file_candidate, str)
                        else name_candidate if isinstance(name_candidate, str) else None
                    )
                if not ref or "{{" in ref or "{%" in ref:
                    continue
                for candidate in (
                    (task_file.parent / ref).resolve(),
                    (role_root / "vars" / ref).resolve(),
                    (role_root / ref).resolve(),
                ):
                    if not candidate.is_file() or candidate in seen:
                        continue
                    try:
                        candidate.relative_to(role_root)
                    except ValueError:
                        continue
                    seen.add(candidate)
                    result.append(candidate)
                    break
    return result


def _read_variable_sources(
    role_root: Path,
    *,
    include_vars_main: bool,
    exclude_paths: list[str] | None,
    options: dict[str, Any] | None = None,
    di: object | None = None,
    yaml_failure_collector: list[dict[str, object]] | None = None,
) -> tuple[dict[str, Any], dict[str, Path], dict[str, Any], dict[str, Path]]:
    defaults_map: dict[str, Any] = {}
    vars_map: dict[str, Any] = {}
    defaults_sources: dict[str, Path] = {}
    vars_sources: dict[str, Path] = {}

    for candidate in _iter_variable_map_candidates(role_root, "defaults"):
        loaded = _load_yaml_mapping_with_metadata(
            candidate,
            role_root=role_root,
            yaml_failure_collector=yaml_failure_collector,
            di=di,
        )
        for name in loaded:
            defaults_sources[name] = candidate
        defaults_map.update(loaded)

    if include_vars_main:
        for candidate in _iter_variable_map_candidates(role_root, "vars"):
            loaded = _load_yaml_mapping_with_metadata(
                candidate,
                role_root=role_root,
                yaml_failure_collector=yaml_failure_collector,
                di=di,
            )
            for name in loaded:
                vars_sources[name] = candidate
            vars_map.update(loaded)

        for candidate in _collect_include_vars_files(
            role_root,
            exclude_paths,
            options=options,
            di=di,
            yaml_failure_collector=yaml_failure_collector,
        ):
            loaded = _load_yaml_mapping_with_metadata(
                candidate,
                role_root=role_root,
                yaml_failure_collector=yaml_failure_collector,
                di=di,
            )
            for name in loaded:
                vars_sources[name] = candidate
            vars_map.update(loaded)

    return defaults_map, defaults_sources, vars_map, vars_sources


def _collect_set_fact_names(
    role_root: Path,
    exclude_paths: list[str] | None,
    *,
    options: dict[str, Any] | None = None,
    di: object | None = None,
    yaml_failure_collector: list[dict[str, object]] | None = None,
) -> set[str]:
    names: set[str] = set()
    set_fact_keys = _get_task_line_parsing_policy(options, di).SET_FACT_KEYS
    for task_file in collect_task_files(
        role_root,
        exclude_paths=exclude_paths,
        di=di,
    ):
        data = load_task_yaml_file(
            task_file,
            yaml_failure_collector=yaml_failure_collector,
            role_root=role_root,
            di=di,
        )
        for task in iter_task_mappings(data, di=di):
            for key in set_fact_keys:
                if key not in task:
                    continue
                value = task[key]
                if not isinstance(value, dict):
                    continue
                for variable_name in value:
                    if isinstance(variable_name, str) and "{{" not in variable_name:
                        names.add(variable_name)
    return names


def _is_when_expression_token_candidate(
    expression: str,
    token_match: re.Match[str],
) -> bool:
    token = token_match.group(1).lower()
    if token in WHEN_OPERATOR_KEYWORDS:
        return False

    start = token_match.start(1)
    end = token_match.end(1)
    if start > 0 and expression[start - 1] == ".":
        return False

    before = expression[:start].rstrip()
    if FILTER_OR_TEST_CONTEXT_RE.search(before):
        return False

    after = expression[end:].lstrip()
    if after.startswith("("):
        return False

    return True


def _collect_undeclared_jinja_variables(
    text: str,
    *,
    options: dict[str, Any] | None = None,
    di: object | None = None,
) -> set[str]:
    del di
    plugin = _require_prepared_policy(
        options,
        "jinja_analysis",
        "VariableDiscovery",
    )
    analyzer = getattr(plugin, "collect_undeclared_jinja_variables", None)
    if callable(analyzer):
        values = analyzer(text)
        if isinstance(values, (set, frozenset, list, tuple)):
            return {item for item in values if isinstance(item, str)}
    return set(JINJA_VARIABLE_RE.findall(text))


def _collect_referenced_variable_names(
    role_root: Path,
    *,
    exclude_paths: list[str] | None,
    options: dict[str, Any] | None = None,
    di: object | None = None,
) -> set[str]:
    candidates: set[str] = set()
    ignored_identifiers = set(IGNORED_IDENTIFIERS)
    ignored_identifiers.update({"lookup"})

    for dirname in ("tasks", "templates", "handlers", "vars"):
        root = role_root / dirname
        if not root.is_dir():
            continue
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            if is_path_excluded(file_path, role_root, exclude_paths):
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue

            for token in _collect_undeclared_jinja_variables(
                text,
                options=options,
                di=di,
            ):
                lowered = token.lower()
                if lowered in ignored_identifiers or lowered in WHEN_OPERATOR_KEYWORDS:
                    continue
                candidates.add(token)

            if file_path.suffix.lower() in {".yml", ".yaml"}:
                for line in text.splitlines():
                    if "when:" not in line:
                        continue
                    expression = QUOTED_STRING_RE.sub("", line.split("when:", 1)[1])
                    for token_match in JINJA_IDENTIFIER_RE.finditer(expression):
                        token = token_match.group(1)
                        if token.lower() in ignored_identifiers:
                            continue
                        if not _is_when_expression_token_candidate(
                            expression,
                            token_match,
                        ):
                            continue
                        candidates.add(token)

    return candidates - REGISTERED_RESULT_ATTRS


def _build_uncertainty_reason(variable_name: str) -> str:
    if variable_name.startswith("_"):
        return "Dynamic or internal variable (underscore prefix)"
    return "Referenced but not defined in role"


class AnsibleVariableDiscoveryPlugin:
    """Ansible-specific variable discovery plugin.

    Implements the VariableDiscoveryPlugin protocol, containing all
    Ansible-native discovery logic previously inline in VariableDiscovery.
    """

    def __init__(self, di: Any = None) -> None:
        self._di = di

    def discover_static_variables(
        self,
        role_path: str,
        options: dict[str, Any],
    ) -> tuple[VariableRow, ...]:
        role_root = Path(role_path).resolve()
        yaml_parse_failures: list[dict[str, object]] = []
        defaults_map, defaults_sources, vars_map, vars_sources = _read_variable_sources(
            role_root,
            include_vars_main=bool(options.get("include_vars_main", True)),
            exclude_paths=options.get("exclude_path_patterns"),
            options=options,
            di=self._di,
            yaml_failure_collector=yaml_parse_failures,
        )

        rows: list[VariableRow] = []
        seen_names: set[str] = set()
        builder = VariableRowBuilder()

        for variable_name, variable_value in defaults_map.items():
            if variable_name in seen_names:
                continue
            seen_names.add(variable_name)
            source_file = defaults_sources[variable_name]
            rows.append(
                builder.name(variable_name)
                .type(_infer_variable_type(variable_value))
                .default(_format_inline_yaml(variable_value))
                .source("defaults/main.yml")
                .documented(True)
                .required(False)
                .secret(_is_sensitive_variable(variable_name, variable_value))
                .provenance_source_file(str(source_file.relative_to(role_root)))
                .provenance_line(_find_variable_line(source_file, variable_name))
                .provenance_confidence(0.95)
                .uncertainty_reason(None)
                .is_unresolved(False)
                .is_ambiguous(False)
                .build()
            )

        for variable_name, variable_value in vars_map.items():
            if variable_name in seen_names:
                continue
            seen_names.add(variable_name)
            source_file = vars_sources[variable_name]
            try:
                rel_source = source_file.relative_to(role_root).as_posix()
            except ValueError:
                rel_source = str(source_file)
            source_label = (
                "vars/main.yml" if rel_source.startswith("vars/") else "include_vars"
            )
            rows.append(
                builder.name(variable_name)
                .type(_infer_variable_type(variable_value))
                .default(_format_inline_yaml(variable_value))
                .source(source_label)
                .documented(True)
                .required(False)
                .secret(_is_sensitive_variable(variable_name, variable_value))
                .provenance_source_file(rel_source)
                .provenance_line(_find_variable_line(source_file, variable_name))
                .provenance_confidence(0.90)
                .uncertainty_reason(None)
                .is_unresolved(False)
                .is_ambiguous(False)
                .build()
            )

        for (
            source_file,
            variable_name,
            spec,
        ) in _iter_role_argument_spec_entries_with_metadata(
            role_root,
            yaml_failure_collector=yaml_parse_failures,
            di=self._di,
        ):
            if variable_name in seen_names:
                continue
            seen_names.add(variable_name)

            spec_type = spec.get("type", "documented")
            default_value = spec.get("default", "")
            inferred_type = _map_argument_spec_type(spec_type)
            if default_value != "":
                inferred_type = _infer_variable_type(default_value)

            rows.append(
                builder.name(variable_name)
                .type(inferred_type)
                .default(_format_inline_yaml(default_value) if default_value else "")
                .source("meta/argument_specs")
                .documented(True)
                .required(bool(spec.get("required", False)))
                .secret(_is_sensitive_variable(variable_name, default_value))
                .provenance_source_file(source_file)
                .provenance_line(None)
                .provenance_confidence(0.9)
                .uncertainty_reason(None)
                .is_unresolved(False)
                .is_ambiguous(False)
                .build()
            )

        for variable_name in _collect_set_fact_names(
            role_root,
            exclude_paths=options.get("exclude_path_patterns"),
            options=options,
            di=self._di,
            yaml_failure_collector=yaml_parse_failures,
        ):
            if variable_name in seen_names:
                continue
            seen_names.add(variable_name)
            rows.append(
                builder.name(variable_name)
                .type("dynamic")
                .default("")
                .source("set_fact")
                .documented(False)
                .required(False)
                .secret(False)
                .provenance_source_file("tasks/")
                .provenance_line(None)
                .provenance_confidence(0.7)
                .uncertainty_reason(None)
                .is_unresolved(False)
                .is_ambiguous(True)
                .build()
            )

        if yaml_parse_failures:
            existing = options.get("yaml_parse_failures")
            merged = list(existing) if isinstance(existing, list) else []
            seen: set[tuple[Any, ...]] = {
                (
                    str(item.get("file")),
                    item.get("line"),
                    item.get("column"),
                    str(item.get("error")),
                )
                for item in merged
                if isinstance(item, dict)
            }
            for failure in yaml_parse_failures:
                key = (
                    str(failure.get("file")),
                    failure.get("line"),
                    failure.get("column"),
                    str(failure.get("error")),
                )
                if key in seen:
                    continue
                seen.add(key)
                merged.append(failure)
            options["yaml_parse_failures"] = merged

        return tuple(rows)

    def discover_referenced_variables(
        self,
        role_path: str,
        options: dict[str, Any],
        readme_content: str | None = None,
    ) -> frozenset[str]:
        role_root = Path(role_path).resolve()

        referenced = _collect_referenced_variable_names(
            role_root,
            exclude_paths=options.get("exclude_path_patterns"),
            options=options,
            di=self._di,
        )

        readme_path = role_root / "README.md"
        if readme_path.exists():
            try:
                readme_text = readme_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                readme_text = ""
            for token in _collect_undeclared_jinja_variables(
                readme_text,
                options=options,
                di=self._di,
            ):
                referenced.add(token.split(".", 1)[0])

        return frozenset(referenced)

    def resolve_unresolved_variables(
        self,
        static_names: frozenset[str],
        referenced: frozenset[str],
        options: dict[str, Any],
    ) -> dict[str, str]:
        unresolved: dict[str, str] = {}
        ignore_underscore = bool(
            options.get("ignore_unresolved_internal_underscore_references")
        )
        for variable_name in referenced:
            if ignore_underscore and variable_name.startswith("_"):
                continue
            if variable_name not in static_names:
                unresolved[variable_name] = _build_uncertainty_reason(variable_name)
        return unresolved
