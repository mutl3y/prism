"""Schema-as-data for scan_options — single source of truth for option keys.

Used by api/cli boundaries to validate scan option dicts before threading them
into scanner-context execution. The schema mirrors ``ScanOptionsDict`` from
``contracts_request`` and is the canonical reference for option name, type,
default, and human-readable description.
"""

from __future__ import annotations

from typing import Any, Mapping, NamedTuple


class ScanOptionsValidationError(ValueError):
    """Raised when scan_options fail boundary validation."""


class ScanOptionSchemaEntry(NamedTuple):
    name: str
    types: tuple[type, ...]
    allow_none: bool
    required: bool
    default: Any
    description: str


def _entry(
    name: str,
    types: tuple[type, ...],
    *,
    allow_none: bool = False,
    required: bool = True,
    default: Any = None,
    description: str = "",
) -> ScanOptionSchemaEntry:
    return ScanOptionSchemaEntry(
        name=name,
        types=types,
        allow_none=allow_none,
        required=required,
        default=default,
        description=description,
    )


SCAN_OPTIONS_SCHEMA: dict[str, ScanOptionSchemaEntry] = {
    e.name: e
    for e in (
        _entry(
            "role_path", (str,), description="Filesystem path to the role being scanned"
        ),
        _entry(
            "role_name_override",
            (str,),
            allow_none=True,
            description="Optional override for the displayed role name",
        ),
        _entry(
            "readme_config_path",
            (str,),
            allow_none=True,
            description="Optional path to a README config file",
        ),
        _entry(
            "policy_config_path",
            (str,),
            allow_none=True,
            description="Optional path to a policy config file",
        ),
        _entry(
            "include_vars_main",
            (bool,),
            default=True,
            description="Whether to include vars/main.yml when discovering variables",
        ),
        _entry(
            "exclude_path_patterns",
            (list,),
            allow_none=True,
            description="Glob patterns to exclude from scanning",
        ),
        _entry(
            "detailed_catalog",
            (bool,),
            default=False,
            description="Emit a detailed task catalog in the report",
        ),
        _entry(
            "include_task_parameters",
            (bool,),
            default=True,
            description="Include parameter blocks for each task",
        ),
        _entry(
            "include_task_runbooks",
            (bool,),
            default=True,
            description="Emit runbook companion content",
        ),
        _entry(
            "inline_task_runbooks",
            (bool,),
            default=True,
            description="Inline runbook entries inside the README",
        ),
        _entry(
            "include_collection_checks",
            (bool,),
            default=True,
            description="Run external-collection check pass",
        ),
        _entry(
            "keep_unknown_style_sections",
            (bool,),
            default=True,
            description="Preserve unknown sections from the style guide",
        ),
        _entry(
            "adopt_heading_mode",
            (str,),
            allow_none=True,
            description="Heading-style adoption mode",
        ),
        _entry(
            "vars_seed_paths",
            (list,),
            allow_none=True,
            description="Optional seed YAML paths for variable values",
        ),
        _entry(
            "style_readme_path",
            (str,),
            allow_none=True,
            description="Path to a style README to enforce",
        ),
        _entry(
            "style_source_path",
            (str,),
            allow_none=True,
            description="Path to the style guide source",
        ),
        _entry(
            "style_guide_skeleton",
            (bool,),
            default=False,
            description="Emit only a skeleton when style guide is missing",
        ),
        _entry(
            "compare_role_path",
            (str,),
            allow_none=True,
            description="Optional path to a sibling role for comparison",
        ),
        _entry(
            "fail_on_unconstrained_dynamic_includes",
            (bool,),
            allow_none=True,
            description="Fail the scan on unconstrained dynamic includes",
        ),
        _entry(
            "fail_on_yaml_like_task_annotations",
            (bool,),
            allow_none=True,
            description="Fail the scan on YAML-like task annotations",
        ),
        _entry(
            "ignore_unresolved_internal_underscore_references",
            (bool,),
            allow_none=True,
            description="Suppress unresolved underscore-prefixed references",
        ),
        _entry(
            "policy_context",
            (dict,),
            allow_none=True,
            description="Optional policy context dict threaded through scanner",
        ),
        # Optional keys that may or may not be present in the canonical dict.
        _entry(
            "comment_doc_marker_prefix",
            (str,),
            allow_none=True,
            required=False,
            description="Override comment-driven doc marker prefix",
        ),
        _entry(
            "prepared_policy_bundle",
            (dict,),
            allow_none=True,
            required=False,
            description="Pre-resolved policy bundle for plugins",
        ),
        _entry(
            "scan_policy_warnings",
            (list,),
            required=False,
            default=[],
            description="Warnings collected while resolving policy context",
        ),
        _entry(
            "strict_phase_failures",
            (bool,),
            required=False,
            default=True,
            description="Halt the scan on first phase failure",
        ),
        _entry(
            "concise_readme",
            (bool,),
            required=False,
            default=False,
            description="Emit the concise README variant",
        ),
        _entry(
            "scanner_report_output",
            (str,),
            allow_none=True,
            required=False,
            description="Path for the scanner report sidecar",
        ),
        _entry(
            "include_scanner_report_link",
            (bool,),
            required=False,
            default=True,
            description="Emit a link to the scanner report from README",
        ),
        _entry(
            "scan_pipeline_plugin",
            (str,),
            allow_none=True,
            required=False,
            description="Name of the scan-pipeline plugin to use",
        ),
        _entry(
            "yaml_parse_failures",
            (list,),
            required=False,
            default=[],
            description="Accumulated YAML parse failures",
        ),
    )
}


def get_default_scan_options() -> dict[str, Any]:
    """Return a fresh dict of default values for keys with non-None defaults."""
    return {
        name: (
            list(entry.default) if isinstance(entry.default, list) else entry.default
        )
        for name, entry in SCAN_OPTIONS_SCHEMA.items()
        if entry.default is not None
    }


def get_scan_options_documentation() -> str:
    """Return a markdown table documenting every scan option."""
    header = (
        "| Option | Type | Required | Default | Description |\n"
        "| --- | --- | --- | --- | --- |\n"
    )
    rows = []
    for name, entry in SCAN_OPTIONS_SCHEMA.items():
        type_str = " | ".join(t.__name__ for t in entry.types)
        if entry.allow_none:
            type_str += " | None"
        required = "yes" if entry.required else "no"
        default = "" if entry.default is None else repr(entry.default)
        rows.append(
            f"| `{name}` | {type_str} | {required} | {default} | {entry.description} |"
        )
    return header + "\n".join(rows) + "\n"


def validate_scan_options(
    options: Mapping[str, Any],
    *,
    strict: bool = False,
) -> None:
    """Validate scan_options against SCAN_OPTIONS_SCHEMA.

    Raises ScanOptionsValidationError on:
    - non-dict input
    - unknown keys
    - type mismatches for declared keys
    - missing required keys (only when strict=True)
    """
    if not isinstance(options, Mapping):
        raise ScanOptionsValidationError(
            f"scan_options must be a mapping, got {type(options).__name__}"
        )

    unknown = sorted(set(options.keys()) - set(SCAN_OPTIONS_SCHEMA.keys()))
    if unknown:
        raise ScanOptionsValidationError(
            f"unknown scan_options key(s): {', '.join(unknown)}"
        )

    for name, entry in SCAN_OPTIONS_SCHEMA.items():
        if name not in options:
            if strict and entry.required:
                raise ScanOptionsValidationError(
                    f"missing required scan_options key: '{name}'"
                )
            continue
        value = options[name]
        if value is None:
            if entry.allow_none:
                continue
            raise ScanOptionsValidationError(f"scan_options['{name}'] must not be None")
        if not isinstance(value, entry.types):
            expected = " | ".join(t.__name__ for t in entry.types)
            raise ScanOptionsValidationError(
                f"scan_options['{name}'] expected {expected}, "
                f"got {type(value).__name__}"
            )


__all__ = [
    "SCAN_OPTIONS_SCHEMA",
    "ScanOptionSchemaEntry",
    "ScanOptionsValidationError",
    "get_default_scan_options",
    "get_scan_options_documentation",
    "validate_scan_options",
]
