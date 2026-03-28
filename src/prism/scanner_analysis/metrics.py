"""Scanner metrics and uncertainty-shaping helpers."""

from __future__ import annotations

from typing import Any

from .report import (
    ScannerCounters,
    extract_scanner_counters as _report_extract_scanner_counters,
)


def extract_scanner_counters(
    variable_insights: list[dict[str, Any]],
    default_filters: list[dict[str, Any]],
    features: dict[str, Any] | None = None,
    parse_failures: list[dict[str, object]] | None = None,
) -> ScannerCounters:
    """Summarize scanner findings by certainty and variable category."""
    return _report_extract_scanner_counters(
        variable_insights,
        default_filters,
        features,
        parse_failures,
    )


def build_referenced_variable_uncertainty_reason(
    *,
    name: str,
    seeded: bool,
    dynamic_include_vars_refs: list[str],
    dynamic_include_var_tokens: set[str],
    dynamic_task_include_tokens: set[str],
) -> str:
    """Return uncertainty reason text for inferred referenced variables."""
    if seeded:
        return "Provided by external seed vars."
    message = "Referenced in role but no static definition found."
    if dynamic_include_vars_refs and name in dynamic_include_var_tokens:
        message = (
            "Referenced in role but no static definition found. "
            "Dynamic include_vars paths detected."
        )
    if name in dynamic_task_include_tokens:
        message += " Dynamic include_tasks/import_tasks paths detected."
    if name.isupper():
        message += (
            " Uppercase name suggests an environment variable or external constant."
        )
    return message


def append_non_authoritative_test_evidence_uncertainty_reason(
    *,
    prior_reason: str,
    match_count: int,
    matched_file_count: int,
    saturation_threshold: int,
    scan_budget_hit: bool,
) -> str:
    """Append test-evidence telemetry to an uncertainty reason string."""
    suffix = (
        " Non-authoritative test evidence found "
        f"({match_count} match(es) across {matched_file_count} file(s)); "
        "likely runtime-provided."
    )
    if match_count >= saturation_threshold:
        suffix += " Match counting is saturated at threshold for performance."
    if scan_budget_hit:
        suffix += " Evidence scan budget limit was reached."
    return f"{prior_reason}{suffix}".strip()
