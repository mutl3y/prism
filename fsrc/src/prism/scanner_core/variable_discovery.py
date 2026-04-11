"""VariableDiscovery orchestration for the fsrc scanner core lane."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from yaml import YAMLError, safe_load

from prism.scanner_core.di import DIContainer
from prism.scanner_core.variable_pipeline import IGNORED_IDENTIFIERS
from prism.scanner_core.variable_pipeline import _format_inline_yaml
from prism.scanner_core.variable_pipeline import _infer_variable_type
from prism.scanner_core.variable_pipeline import _is_sensitive_variable
from prism.scanner_data.contracts_request import validate_variable_discovery_inputs
from prism.scanner_data.contracts_variables import VariableRow
from prism.scanner_extract.task_parser import _collect_task_files
from prism.scanner_extract.task_parser import _is_path_excluded
from prism.scanner_extract.task_parser import _iter_task_mappings
from prism.scanner_extract.task_parser import _load_yaml_file

JINJA_VARIABLE_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_\.]*)")
JINJA_IDENTIFIER_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")
JINJA_EXPRESSION_RE = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)
QUOTED_STRING_RE = re.compile(r'"[^"]*"|\'[^\']*\'')
FILTER_OR_TEST_CONTEXT_RE = re.compile(r"(?:\|\s*|is\s+|is\s+not\s+)$")

INCLUDE_VARS_KEYS: frozenset[str] = frozenset(
    {
        "include_vars",
        "ansible.builtin.include_vars",
    }
)

SET_FACT_KEYS: frozenset[str] = frozenset(
    {
        "set_fact",
        "ansible.builtin.set_fact",
    }
)

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
    if not path.exists():
        return {}
    try:
        parsed = safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, YAMLError):
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


def _iter_role_argument_spec_entries(role_root: Path):
    sources: list[tuple[str, dict[str, Any]]] = []
    arg_specs_file = role_root / "meta" / "argument_specs.yml"
    if arg_specs_file.is_file():
        loaded = _load_yaml_mapping(arg_specs_file)
        if loaded:
            sources.append(("meta/argument_specs.yml", loaded))

    meta_main = _load_yaml_mapping(role_root / "meta" / "main.yml")
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
) -> list[Path]:
    result: list[Path] = []
    seen: set[Path] = set()
    for task_file in _collect_task_files(role_root, exclude_paths=exclude_paths):
        data = _load_yaml_file(task_file)
        for task in _iter_task_mappings(data):
            for key in INCLUDE_VARS_KEYS:
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
) -> tuple[dict[str, Any], dict[str, Path], dict[str, Any], dict[str, Path]]:
    defaults_map: dict[str, Any] = {}
    vars_map: dict[str, Any] = {}
    defaults_sources: dict[str, Path] = {}
    vars_sources: dict[str, Path] = {}

    for candidate in _iter_variable_map_candidates(role_root, "defaults"):
        loaded = _load_yaml_mapping(candidate)
        for name in loaded:
            defaults_sources[name] = candidate
        defaults_map.update(loaded)

    if include_vars_main:
        for candidate in _iter_variable_map_candidates(role_root, "vars"):
            loaded = _load_yaml_mapping(candidate)
            for name in loaded:
                vars_sources[name] = candidate
            vars_map.update(loaded)

        for candidate in _collect_include_vars_files(role_root, exclude_paths):
            loaded = _load_yaml_mapping(candidate)
            for name in loaded:
                vars_sources[name] = candidate
            vars_map.update(loaded)

    return defaults_map, defaults_sources, vars_map, vars_sources


def _collect_set_fact_names(
    role_root: Path,
    exclude_paths: list[str] | None,
) -> set[str]:
    names: set[str] = set()
    for task_file in _collect_task_files(role_root, exclude_paths=exclude_paths):
        data = _load_yaml_file(task_file)
        for task in _iter_task_mappings(data):
            for key in SET_FACT_KEYS:
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


def _collect_referenced_variable_names(
    role_root: Path,
    *,
    exclude_paths: list[str] | None,
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
            if _is_path_excluded(file_path, role_root, exclude_paths):
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue

            for expression in JINJA_EXPRESSION_RE.findall(text):
                expression_without_strings = QUOTED_STRING_RE.sub("", expression)
                for token_match in JINJA_IDENTIFIER_RE.finditer(
                    expression_without_strings
                ):
                    token = token_match.group(1)
                    lowered = token.lower()
                    if (
                        lowered in ignored_identifiers
                        or lowered in WHEN_OPERATOR_KEYWORDS
                    ):
                        continue
                    start = token_match.start(1)
                    end = token_match.end(1)
                    if start > 0 and expression_without_strings[start - 1] == ".":
                        continue
                    before = expression_without_strings[:start].rstrip()
                    if FILTER_OR_TEST_CONTEXT_RE.search(before):
                        continue
                    after = expression_without_strings[end:].lstrip()
                    if after.startswith("("):
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


class VariableDiscovery:
    """Discover static and referenced role variables for fsrc scans."""

    def __init__(
        self,
        di: DIContainer,
        role_path: str,
        options: dict[str, Any],
    ) -> None:
        validate_variable_discovery_inputs(role_path=role_path, options=options)
        self._di = di
        self._role_path = role_path
        self._options = options
        self._role_root = Path(role_path).resolve()

    def discover_static(self) -> tuple[VariableRow, ...]:
        """Discover static variables from defaults/vars/argument_specs/set_fact."""
        defaults_map, defaults_sources, vars_map, vars_sources = _read_variable_sources(
            self._role_root,
            include_vars_main=bool(self._options.get("include_vars_main", True)),
            exclude_paths=self._options.get("exclude_path_patterns"),
        )

        rows: list[VariableRow] = []
        seen_names: set[str] = set()
        builder = self._di.factory_variable_row_builder()

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
                .provenance_source_file(str(source_file.relative_to(self._role_root)))
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
                rel_source = source_file.relative_to(self._role_root).as_posix()
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

        for source_file, variable_name, spec in _iter_role_argument_spec_entries(
            self._role_root
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
            self._role_root,
            exclude_paths=self._options.get("exclude_path_patterns"),
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

        return tuple(rows)

    def discover_referenced(self) -> frozenset[str]:
        """Discover referenced variable names from tasks/templates/handlers/README."""
        referenced = _collect_referenced_variable_names(
            self._role_root,
            exclude_paths=self._options.get("exclude_path_patterns"),
        )

        readme_path = self._role_root / "README.md"
        if readme_path.exists():
            try:
                readme_text = readme_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                readme_text = ""
            for match in JINJA_VARIABLE_RE.findall(readme_text):
                referenced.add(match.split(".", 1)[0])

        return frozenset(referenced)

    def resolve_unresolved(
        self,
        *,
        static_names: frozenset[str] | None = None,
        referenced: frozenset[str] | None = None,
    ) -> dict[str, str]:
        """Return unresolved variable names mapped to uncertainty reasons."""
        effective_static_names = static_names
        if effective_static_names is None:
            effective_static_names = frozenset(
                row["name"] for row in self.discover_static()
            )
        effective_referenced = referenced or self.discover_referenced()

        unresolved: dict[str, str] = {}
        for variable_name in effective_referenced:
            if variable_name not in effective_static_names:
                unresolved[variable_name] = self._build_uncertainty_reason(
                    variable_name
                )
        return unresolved

    def discover(self) -> tuple[VariableRow, ...]:
        """Discover static rows and append unresolved referenced placeholders."""
        static_rows = self.discover_static()
        static_names = frozenset(row["name"] for row in static_rows)
        referenced = self.discover_referenced()
        unresolved = self.resolve_unresolved(
            static_names=static_names,
            referenced=referenced,
        )

        rows = list(static_rows)
        builder = self._di.factory_variable_row_builder()
        for variable_name in sorted(referenced - static_names):
            rows.append(
                builder.name(variable_name)
                .type("dynamic")
                .default("")
                .source("referenced")
                .documented(False)
                .required(False)
                .secret(False)
                .provenance_source_file("tasks/")
                .provenance_line(None)
                .provenance_confidence(0.5)
                .uncertainty_reason(unresolved.get(variable_name))
                .is_unresolved(True)
                .is_ambiguous(False)
                .build()
            )
        return tuple(rows)

    def _build_uncertainty_reason(self, variable_name: str) -> str:
        if variable_name.startswith("_"):
            return "Dynamic or internal variable (underscore prefix)"
        return "Referenced but not defined in role"
