"""Fail-closed Terraform execution-bundle participants for the first slice."""

from __future__ import annotations

import re
from collections.abc import Collection, Iterable
from pathlib import Path
from typing import Any

from prism.scanner_data.builders import VariableRowBuilder
from prism.scanner_data.contracts_request import TaskAnnotation, TaskMapping
from prism.scanner_data.contracts_request import YamlParseFailure
from prism.scanner_data.contracts_variables import VariableRow


_RESOURCE_BLOCK_RE = re.compile(
    r'^\s*resource\s+"([^"]+)"\s+"([^"]+)"\s*\{',
    re.MULTILINE,
)
_DATA_BLOCK_RE = re.compile(
    r'^\s*data\s+"([^"]+)"\s+"([^"]+)"\s*\{',
    re.MULTILINE,
)
_MODULE_BLOCK_RE = re.compile(r'^\s*module\s+"([^"]+)"\s*\{', re.MULTILINE)
_VARIABLE_BLOCK_RE = re.compile(r'^\s*variable\s+"([^"]+)"\s*\{', re.MULTILINE)
_REQUIRED_PROVIDERS_BLOCK_RE = re.compile(
    r'^\s*required_providers\s*\{',
    re.MULTILINE,
)
_REQUIRED_VERSION_RE = re.compile(r'^\s*required_version\s*=\s*"([^"]+)"', re.MULTILINE)
_PROVIDER_ENTRY_RE = re.compile(r'^\s*([A-Za-z0-9_-]+)\s*=\s*\{', re.MULTILINE)
_PROVIDER_SOURCE_RE = re.compile(r'^\s*source\s*=\s*"([^"]+)"', re.MULTILINE)
_PROVIDER_VERSION_RE = re.compile(r'^\s*version\s*=\s*"([^"]+)"', re.MULTILINE)
_BACKEND_BLOCK_RE = re.compile(r'^\s*backend\s+"([^"]+)"\s*\{', re.MULTILINE)
_DESCRIPTION_RE = re.compile(r'^\s*description\s*=\s*"([^"]*)"', re.MULTILINE)
_TYPE_RE = re.compile(r'^\s*type\s*=\s*(.+)$', re.MULTILINE)
_DEFAULT_RE = re.compile(r'^\s*default\s*=\s*(.+)$', re.MULTILINE)
_SENSITIVE_NAME_RE = re.compile(r'(?:secret|token|password|passwd|key)', re.IGNORECASE)


def _extract_braced_block(text: str, open_brace_index: int) -> str:
    depth = 0
    for index in range(open_brace_index, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[open_brace_index + 1 : index]
    return text[open_brace_index + 1 :]


def _top_level_terraform_files(role_path: str | Path) -> tuple[Path, ...]:
    root = Path(role_path)
    if not root.exists() or not root.is_dir():
        return ()
    return tuple(sorted(path for path in root.glob("*.tf") if path.is_file()))


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _normalize_literal(value: str | None) -> str:
    if value is None:
        return ""
    normalized = value.strip().rstrip(",")
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {
        '"',
        "'",
    }:
        return normalized[1:-1]
    return normalized


def _line_number_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _extract_provider_requirements(text: str) -> tuple[list[str], list[str]]:
    provider_requirements: list[str] = []
    providers: list[str] = []

    required_version_match = _REQUIRED_VERSION_RE.search(text)
    if required_version_match:
        provider_requirements.append(
            f"terraform {required_version_match.group(1).strip()}"
        )

    for block_match in _REQUIRED_PROVIDERS_BLOCK_RE.finditer(text):
        block_body = _extract_braced_block(text, block_match.end() - 1)
        for provider_match in _PROVIDER_ENTRY_RE.finditer(block_body):
            provider_name = provider_match.group(1)
            provider_body = _extract_braced_block(block_body, provider_match.end() - 1)
            source_match = _PROVIDER_SOURCE_RE.search(provider_body)
            version_match = _PROVIDER_VERSION_RE.search(provider_body)
            source = source_match.group(1).strip() if source_match else ""
            version = version_match.group(1).strip() if version_match else ""

            providers.append(provider_name)
            if source and version:
                provider_requirements.append(
                    f"{provider_name} ({source}) {version}"
                )
            elif version:
                provider_requirements.append(f"{provider_name} {version}")
            elif source:
                provider_requirements.append(f"{provider_name} ({source})")
            else:
                provider_requirements.append(provider_name)

    return sorted(set(provider_requirements)), sorted(set(providers))


def _readme_description(role_root: Path) -> str:
    readme_path = role_root / "README.md"
    if not readme_path.is_file():
        return f"Terraform module `{role_root.name}`"

    for line in _read_text(readme_path).splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return f"Terraform module `{role_root.name}`"


def extract_terraform_module_metadata(role_path: str | Path) -> dict[str, object]:
    role_root = Path(role_path)
    terraform_files = _top_level_terraform_files(role_root)
    if not terraform_files:
        return {
            "terraform_files_scanned": 0,
            "managed_resources": [],
            "data_sources": [],
            "provider_requirements": [],
            "providers": [],
            "module_calls": [],
            "module_hints": [],
            "operational_constraints": [
                "Static analysis only: Terraform execution capabilities remain fail-closed.",
            ],
            "module_description": _readme_description(role_root),
        }

    managed_resources: list[str] = []
    data_sources: list[str] = []
    module_calls: list[str] = []
    provider_requirements: list[str] = []
    providers: list[str] = []
    backend_types: list[str] = []

    for terraform_file in terraform_files:
        text = _read_text(terraform_file)
        managed_resources.extend(
            f"{resource_type}.{resource_name}"
            for resource_type, resource_name in _RESOURCE_BLOCK_RE.findall(text)
        )
        data_sources.extend(
            f"{data_type}.{data_name}"
            for data_type, data_name in _DATA_BLOCK_RE.findall(text)
        )
        module_calls.extend(_MODULE_BLOCK_RE.findall(text))
        file_requirements, file_providers = _extract_provider_requirements(text)
        provider_requirements.extend(file_requirements)
        providers.extend(file_providers)
        backend_types.extend(_BACKEND_BLOCK_RE.findall(text))

    operational_constraints = [
        "Static analysis only: Terraform execution capabilities remain fail-closed.",
    ]
    if backend_types:
        operational_constraints.append(
            f"Detected backend declarations: {', '.join(sorted(set(backend_types)))}."
        )
    else:
        operational_constraints.append(
            "No explicit backend block detected in scanned root module."
        )
    if module_calls:
        operational_constraints.append(
            "Module call discovery is limited to root-level module blocks."
        )

    return {
        "terraform_files_scanned": len(terraform_files),
        "managed_resources": sorted(set(managed_resources)),
        "data_sources": sorted(set(data_sources)),
        "provider_requirements": sorted(set(provider_requirements)),
        "providers": sorted(set(providers)),
        "module_calls": sorted(set(module_calls)),
        "module_hints": sorted(set(module_calls)) or ["root_module"],
        "operational_constraints": operational_constraints,
        "module_description": _readme_description(role_root),
    }


def extract_terraform_variable_rows(role_path: str | Path) -> tuple[VariableRow, ...]:
    variable_rows: list[VariableRow] = []

    for terraform_file in _top_level_terraform_files(role_path):
        text = _read_text(terraform_file)
        relative_file = terraform_file.name
        for variable_match in _VARIABLE_BLOCK_RE.finditer(text):
            variable_name = variable_match.group(1)
            block_body = _extract_braced_block(text, variable_match.end() - 1)
            description_match = _DESCRIPTION_RE.search(block_body)
            type_match = _TYPE_RE.search(block_body)
            default_match = _DEFAULT_RE.search(block_body)
            source_file = f"terraform:{relative_file}"
            provenance_line = _line_number_for_offset(text, variable_match.start())

            variable_rows.append(
                VariableRowBuilder()
                .name(variable_name)
                .type(_normalize_literal(type_match.group(1)) if type_match else "any")
                .default(
                    _normalize_literal(default_match.group(1)) if default_match else ""
                )
                .source(source_file)
                .documented(description_match is not None)
                .required(default_match is None)
                .secret(bool(_SENSITIVE_NAME_RE.search(variable_name)))
                .provenance_source_file(relative_file)
                .provenance_line(provenance_line)
                .provenance_confidence(0.95)
                .uncertainty_reason(None)
                .is_unresolved(False)
                .is_ambiguous(False)
                .build()
            )

    return tuple(variable_rows)


class _TerraformTaskLineParsingPolicy:
    TASK_INCLUDE_KEYS: Collection[str] = frozenset()
    ROLE_INCLUDE_KEYS: Collection[str] = frozenset()
    INCLUDE_VARS_KEYS: Collection[str] = frozenset()
    SET_FACT_KEYS: Collection[str] = frozenset()
    TASK_BLOCK_KEYS: Collection[str] = frozenset()
    TASK_META_KEYS: Collection[str] = frozenset()

    @staticmethod
    def detect_task_module(task: TaskMapping) -> str | None:
        del task
        return None


class _TerraformJinjaAnalysisPolicy:
    @staticmethod
    def collect_undeclared_jinja_variables(text: str) -> set[str]:
        del text
        return set()


class _TerraformTaskTraversalPolicy:
    @staticmethod
    def iter_task_mappings(data: object) -> Iterable[TaskMapping]:
        del data
        return ()

    @staticmethod
    def iter_task_include_targets(data: object) -> list[str]:
        del data
        return []

    @staticmethod
    def iter_task_include_edges(data: object) -> list[dict[str, str]]:
        del data
        return []

    @staticmethod
    def expand_include_target_candidates(
        task: TaskMapping, include_target: str
    ) -> list[str]:
        del task, include_target
        return []

    @staticmethod
    def iter_role_include_targets(task: TaskMapping) -> list[str]:
        del task
        return []

    @staticmethod
    def iter_dynamic_role_include_targets(task: TaskMapping) -> list[str]:
        del task
        return []

    @staticmethod
    def collect_unconstrained_dynamic_task_includes(
        *, role_root: object, task_files: list[object], load_yaml_file: object
    ) -> list[dict[str, str]]:
        del role_root, task_files, load_yaml_file
        return []

    @staticmethod
    def collect_unconstrained_dynamic_role_includes(
        *, role_root: object, task_files: list[object], load_yaml_file: object
    ) -> list[dict[str, str]]:
        del role_root, task_files, load_yaml_file
        return []


class _TerraformYAMLParsingPolicy:
    @staticmethod
    def load_yaml_file(path: str | Path) -> object:
        del path
        return {}

    @staticmethod
    def parse_yaml_candidate(
        candidate: str | Path, role_root: str | Path
    ) -> YamlParseFailure | None:
        del role_root
        return {
            "file": str(candidate),
            "line": None,
            "column": None,
            "error": "Terraform execution bundle does not provide YAML parsing.",
        }


class _TerraformVariableExtractorPolicy:
    @staticmethod
    def collect_include_vars_files(
        *,
        role_path: str,
        exclude_paths: list[str] | None,
        collect_task_files: object,
        load_yaml_file: object,
    ) -> list[object]:
        del role_path, exclude_paths, collect_task_files, load_yaml_file
        return []


class _TerraformTaskAnnotationPolicy:
    @staticmethod
    def split_task_annotation_label(text: str) -> tuple[str, str]:
        return text, ""

    @staticmethod
    def split_task_target_payload(text: str) -> tuple[str, str]:
        return text, ""

    @staticmethod
    def annotation_payload_looks_yaml(payload: str) -> bool:
        del payload
        return False

    @staticmethod
    def normalize_marker_prefix(marker_prefix: str | None) -> str:
        return marker_prefix or "prism"

    @staticmethod
    def get_marker_line_re(marker_prefix: str = "prism") -> object:
        return re.compile(rf"^\s*#\s*{re.escape(marker_prefix)}:")

    @staticmethod
    def extract_task_annotations_for_file(
        lines: list[str],
        marker_prefix: str = "prism",
        include_task_index: bool = False,
    ) -> tuple[list[TaskAnnotation], dict[str, list[TaskAnnotation]]]:
        del lines, marker_prefix, include_task_index
        return [], {}

    @staticmethod
    def task_anchor(file_path: str, task_name: str, index: int) -> str:
        del task_name
        return f"{file_path}#task-{index}"


def build_fail_closed_participants() -> dict[str, Any]:
    task_line_parsing = _TerraformTaskLineParsingPolicy()
    jinja_analysis = _TerraformJinjaAnalysisPolicy()
    return {
        "task_line_parsing": task_line_parsing,
        "jinja_analysis": jinja_analysis,
        "task_traversal": _TerraformTaskTraversalPolicy(),
        "yaml_parsing": _TerraformYAMLParsingPolicy(),
        "variable_extractor": _TerraformVariableExtractorPolicy(),
        "task_annotation_parsing": _TerraformTaskAnnotationPolicy(),
    }


def build_terraform_execution_bundle(
    scan_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the Terraform execution bundle for scan pipeline execution.

    Returns a dict containing:
    - prepared_policy: Fail-closed policy participant instances
    - platform_participants: References to key policy participants
    """
    del scan_options
    prepared_policy = build_fail_closed_participants()
    participants = {
        "task_line_parsing": prepared_policy["task_line_parsing"],
        "jinja_analysis": prepared_policy["jinja_analysis"],
    }
    return {
        "prepared_policy": prepared_policy,
        "platform_participants": participants,
    }


__all__ = [
    "build_fail_closed_participants",
    "build_terraform_execution_bundle",
    "extract_terraform_module_metadata",
    "extract_terraform_variable_rows",
]