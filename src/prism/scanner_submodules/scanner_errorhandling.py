"""Error handling and uncertainty reason building for scanner variable insights.

This module handles:
- Building uncertainty reason text for inferred referenced variables
- Collecting and attaching non-authoritative test evidence
- Suppressing internal unresolved references based on policy
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
from typing import Counter as CounterType

from .task_parser import _is_path_excluded
from .scan_metrics import (
    append_non_authoritative_test_evidence_uncertainty_reason as _scan_metrics_append_non_authoritative_test_evidence_uncertainty_reason,
    build_referenced_variable_uncertainty_reason as _scan_metrics_build_referenced_variable_uncertainty_reason,
)

# Non-authoritative test evidence configuration
NON_AUTHORITATIVE_TEST_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
NON_AUTHORITATIVE_TEST_EVIDENCE_ALLOWED_SUFFIXES = {
    ".yml",
    ".yaml",
    ".j2",
    ".jinja2",
    ".json",
    ".ini",
    ".cfg",
    ".conf",
    ".md",
    ".txt",
}
NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES = 512 * 1024
NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED = 400
NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES = 8 * 1024 * 1024
NON_AUTHORITATIVE_TEST_EVIDENCE_SATURATION_MATCH_COUNT = 4


def should_suppress_internal_unresolved_reference(
    *,
    name: str,
    seed_values: dict,
    ignore_unresolved_internal_underscore_references: bool,
) -> bool:
    """Return whether an unresolved internal temp-style name should be skipped.

    Args:
        name: Variable name to check.
        seed_values: Dictionary of seeded variable values.
        ignore_unresolved_internal_underscore_references: Policy flag for suppression.

    Returns:
        True if the name should be suppressed (skipped), False otherwise.
    """
    if not ignore_unresolved_internal_underscore_references:
        return False
    if not name.startswith("_"):
        return False
    # Keep externally seeded underscore names; suppress unresolved temp-like names.
    return name not in seed_values


def build_referenced_variable_uncertainty_reason(
    *,
    name: str,
    seeded: bool,
    dynamic_include_vars_refs: list[str],
    dynamic_include_var_tokens: set[str],
    dynamic_task_include_tokens: set[str],
) -> str:
    """Return uncertainty reason text for inferred referenced variables.

    Delegates to scan_metrics submodule which contains the actual logic.

    Args:
        name: Variable name.
        seeded: Whether the variable comes from seed values.
        dynamic_include_vars_refs: Dynamic include_vars references.
        dynamic_include_var_tokens: Dynamic tokens from include_vars.
        dynamic_task_include_tokens: Dynamic tokens from task includes.

    Returns:
        Uncertainty reason text (may be empty string).
    """
    return _scan_metrics_build_referenced_variable_uncertainty_reason(
        name=name,
        seeded=seeded,
        dynamic_include_vars_refs=dynamic_include_vars_refs,
        dynamic_include_var_tokens=dynamic_include_var_tokens,
        dynamic_task_include_tokens=dynamic_task_include_tokens,
    )


def append_non_authoritative_test_evidence_uncertainty_reason(
    *,
    prior_reason: str,
    match_count: int,
    matched_file_count: int,
    saturation_threshold: int,
    scan_budget_hit: bool,
) -> str:
    """Append non-authoritative test-evidence telemetry to uncertainty notes.

    Delegates to scan_metrics submodule.

    Args:
        prior_reason: Prior uncertainty reason text.
        match_count: Number of matches found.
        matched_file_count: Number of files containing matches.
        saturation_threshold: Maximum match count before saturation.
        scan_budget_hit: Whether scanning was truncated.

    Returns:
        Updated uncertainty reason text.
    """
    return _scan_metrics_append_non_authoritative_test_evidence_uncertainty_reason(
        prior_reason=prior_reason,
        match_count=match_count,
        matched_file_count=matched_file_count,
        saturation_threshold=saturation_threshold,
        scan_budget_hit=scan_budget_hit,
    )


def collect_non_authoritative_test_variable_evidence(
    *,
    role_path: str,
    unresolved_names: set[str],
    exclude_paths: list[str] | None,
    max_file_bytes: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES,
    max_files_scanned: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED,
    max_total_bytes: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES,
) -> dict[str, dict]:
    """Collect non-authoritative unresolved-name evidence from tests/molecule files.

    Scans test and molecule directories looking for token matches to unresolved
    variable names. Returns evidence aggregated by variable name with match counts
    and file paths.

    Args:
        role_path: Path to role root directory.
        unresolved_names: Set of unresolved variable names to search for.
        exclude_paths: Optional list of path patterns to exclude.
        max_file_bytes: Maximum bytes per file to scan.
        max_files_scanned: Maximum number of files to scan total.
        max_total_bytes: Maximum total bytes to scan across all files.

    Returns:
        Dictionary keyed by variable name with match stats and file list.
    """
    if not unresolved_names:
        return {}

    active_names = set(unresolved_names)
    role_root = Path(role_path).resolve()
    files_scanned = 0
    total_bytes_scanned = 0
    budget_hit = False
    evidence: dict[str, dict] = {
        name: {"match_count": 0, "matched_files": set()} for name in unresolved_names
    }

    for dirname in ("tests", "molecule"):
        root = role_root / dirname
        if not root.is_dir():
            continue
        for file_path in sorted(root.rglob("*")):
            if not active_names:
                break
            if files_scanned >= max_files_scanned:
                budget_hit = True
                break
            if total_bytes_scanned >= max_total_bytes:
                budget_hit = True
                break
            if not file_path.is_file():
                continue
            if _is_path_excluded(file_path, role_root, exclude_paths):
                continue
            if (
                file_path.suffix.lower()
                not in NON_AUTHORITATIVE_TEST_EVIDENCE_ALLOWED_SUFFIXES
            ):
                continue
            try:
                raw = file_path.read_bytes()
            except OSError:
                continue
            if len(raw) > max_file_bytes:
                continue
            if total_bytes_scanned + len(raw) > max_total_bytes:
                budget_hit = True
                break
            try:
                text = raw.decode(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            files_scanned += 1
            total_bytes_scanned += len(raw)

            file_counts: CounterType[str] = Counter()
            for token_match in NON_AUTHORITATIVE_TEST_TOKEN_RE.finditer(text):
                token = token_match.group(0)
                if token in active_names:
                    file_counts[token] += 1
            if not file_counts:
                continue

            rel_path = str(file_path.relative_to(role_root))
            for name, matches in file_counts.items():
                current = int(evidence[name]["match_count"])
                remaining = (
                    NON_AUTHORITATIVE_TEST_EVIDENCE_SATURATION_MATCH_COUNT - current
                )
                if remaining <= 0:
                    active_names.discard(name)
                    continue
                applied = min(matches, remaining)
                evidence[name]["match_count"] += applied
                evidence[name]["matched_files"].add(rel_path)
                if (
                    evidence[name]["match_count"]
                    >= NON_AUTHORITATIVE_TEST_EVIDENCE_SATURATION_MATCH_COUNT
                ):
                    active_names.discard(name)

        if not active_names:
            break
        if files_scanned >= max_files_scanned:
            break
        if total_bytes_scanned >= max_total_bytes:
            break

    normalized: dict[str, dict] = {}
    for name, item in evidence.items():
        if item["match_count"] <= 0:
            continue
        normalized[name] = {
            "match_count": item["match_count"],
            "matched_files": sorted(item["matched_files"]),
            "scan_budget_hit": budget_hit,
        }
    return normalized


def test_evidence_probability(match_count: int) -> float:
    """Return a bounded confidence score for non-authoritative test evidence.

    Args:
        match_count: Number of token matches found.

    Returns:
        Confidence score between 0.0 and 0.85.
    """
    if match_count <= 0:
        return 0.0
    return round(min(0.25 + (0.15 * min(match_count, 4)), 0.85), 2)


def attach_non_authoritative_test_evidence(
    *,
    role_path: str,
    rows: list[dict],
    exclude_paths: list[str] | None,
    max_file_bytes: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILE_BYTES,
    max_files_scanned: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_FILES_SCANNED,
    max_total_bytes: int = NON_AUTHORITATIVE_TEST_EVIDENCE_MAX_TOTAL_BYTES,
) -> None:
    """Enrich unresolved rows with non-authoritative evidence from tests files.

    Modifies rows in-place, adding non_authoritative_test_evidence and updating
    uncertainty_reason for unresolved variables that match tokens in test files.

    Args:
        role_path: Path to role root directory.
        rows: List of variable rows (modified in-place).
        exclude_paths: Optional list of path patterns to exclude.
        max_file_bytes: Maximum bytes per file to scan.
        max_files_scanned: Maximum number of files to scan total.
        max_total_bytes: Maximum total bytes to scan across all files.
    """
    unresolved_names = {
        row["name"]
        for row in rows
        if row.get("is_unresolved") and isinstance(row.get("name"), str)
    }
    if not unresolved_names:
        return

    evidence_by_name = collect_non_authoritative_test_variable_evidence(
        role_path=role_path,
        unresolved_names=unresolved_names,
        exclude_paths=exclude_paths,
        max_file_bytes=max_file_bytes,
        max_files_scanned=max_files_scanned,
        max_total_bytes=max_total_bytes,
    )
    if not evidence_by_name:
        return

    for row in rows:
        if not row.get("is_unresolved"):
            continue
        name = row.get("name")
        if not isinstance(name, str):
            continue
        evidence = evidence_by_name.get(name)
        if not evidence:
            continue
        match_count = int(evidence["match_count"])
        probability = test_evidence_probability(match_count)
        row["non_authoritative_test_evidence"] = {
            "authoritative": False,
            "match_count": match_count,
            "matched_files": evidence["matched_files"],
            "confidence": probability,
            "probability": probability,
            "saturation_applied": (
                match_count >= NON_AUTHORITATIVE_TEST_EVIDENCE_SATURATION_MATCH_COUNT
            ),
            "saturation_threshold": NON_AUTHORITATIVE_TEST_EVIDENCE_SATURATION_MATCH_COUNT,
            "scan_budget_hit": bool(evidence.get("scan_budget_hit")),
        }
        row["uncertainty_reason"] = (
            append_non_authoritative_test_evidence_uncertainty_reason(
                prior_reason=str(row.get("uncertainty_reason") or "").strip(),
                match_count=match_count,
                matched_file_count=len(evidence["matched_files"]),
                saturation_threshold=NON_AUTHORITATIVE_TEST_EVIDENCE_SATURATION_MATCH_COUNT,
                scan_budget_hit=bool(evidence.get("scan_budget_hit")),
            )
        )
