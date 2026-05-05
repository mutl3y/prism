"""T4-06: PRISM_* environment variable configuration overlay.

Reads ``PRISM_*`` environment variables and produces a partial scan_options
overlay that callers can merge into explicit options. Explicit API/CLI
options always win; env vars only fill in unspecified keys.

This module is the canonical source for the env-var namespace. Any new
env-var binding must be added to :data:`PRISM_ENV_BINDINGS` so it shows up
in :func:`get_env_var_documentation`.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Mapping, NamedTuple


class EnvBinding(NamedTuple):
    env_var: str
    option_key: str | None
    coercer: Callable[[str], Any]
    description: str


def _coerce_bool(raw: str) -> bool:
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _coerce_str(raw: str) -> str:
    return raw


PRISM_ENV_BINDINGS: tuple[EnvBinding, ...] = (
    EnvBinding(
        env_var="PRISM_POLICY_CONFIG",
        option_key="policy_config_path",
        coercer=_coerce_str,
        description="Path to optional pattern-policy override YAML.",
    ),
    EnvBinding(
        env_var="PRISM_README_CONFIG",
        option_key="readme_config_path",
        coercer=_coerce_str,
        description="Path to optional README config file.",
    ),
    EnvBinding(
        env_var="PRISM_FAIL_ON_UNCONSTRAINED_DYNAMIC_INCLUDES",
        option_key="fail_on_unconstrained_dynamic_includes",
        coercer=_coerce_bool,
        description="Fail scan on unconstrained dynamic includes (1/true/yes/on).",
    ),
    EnvBinding(
        env_var="PRISM_FAIL_ON_YAML_LIKE_TASK_ANNOTATIONS",
        option_key="fail_on_yaml_like_task_annotations",
        coercer=_coerce_bool,
        description="Fail scan on YAML-like marker comment payloads.",
    ),
    EnvBinding(
        env_var="PRISM_PROGRESS",
        option_key=None,
        coercer=_coerce_bool,
        description="Enable CLI progress streaming to stderr (consumed by CLI).",
    ),
    EnvBinding(
        env_var="PRISM_TELEMETRY_JSON_LOG",
        option_key=None,
        coercer=_coerce_bool,
        description=(
            "Enable structured JSON telemetry log to stderr "
            "(consumed by TelemetryCollector)."
        ),
    ),
)


def load_env_overlay(
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return a dict of scan_options overrides derived from PRISM_* env vars.

    Only bindings with a non-None ``option_key`` produce overlay entries.
    Bindings without an option key are advisory documentation for env vars
    consumed elsewhere (e.g. CLI flag, telemetry log toggle).
    """
    env = environ if environ is not None else os.environ
    overlay: dict[str, Any] = {}
    for binding in PRISM_ENV_BINDINGS:
        if binding.option_key is None:
            continue
        raw = env.get(binding.env_var)
        if raw is None:
            continue
        overlay[binding.option_key] = binding.coercer(raw)
    return overlay


def merge_with_env_overlay(
    explicit_options: Mapping[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Merge env overlay into ``explicit_options``; explicit keys always win."""
    overlay = load_env_overlay(environ=environ)
    merged: dict[str, Any] = dict(overlay)
    merged.update(explicit_options)
    return merged


def get_env_var_documentation() -> str:
    """Return a markdown table documenting every PRISM_* env var."""
    header = "| Env Var | Maps To | Description |\n" "| --- | --- | --- |\n"
    rows = [
        f"| `{b.env_var}` | "
        f"{('`' + b.option_key + '`') if b.option_key else '_(consumer-specific)_'}"
        f" | {b.description} |"
        for b in PRISM_ENV_BINDINGS
    ]
    return header + "\n".join(rows) + "\n"


__all__ = [
    "EnvBinding",
    "PRISM_ENV_BINDINGS",
    "get_env_var_documentation",
    "load_env_overlay",
    "merge_with_env_overlay",
]
