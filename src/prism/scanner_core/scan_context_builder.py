"""Scan-context assembly builder for scanner runtime paths."""

from __future__ import annotations

from typing import Any, Callable

from prism.scanner_data.contracts import (
    ScanBaseContext,
    ScanContextPayload,
    ScanOptionsDict,
)

CollectScanBaseContext = Callable[[ScanOptionsDict], ScanBaseContext]
LoadIgnoreUnresolvedReferences = Callable[[str, str | None, bool], bool]
LoadEvidenceBudget = Callable[[str, str | None, int], int]
EnrichScanContextWithInsights = Callable[
    ..., tuple[list[dict[str, Any]], dict[str, Any]]
]
FinalizeScanContextPayload = Callable[..., ScanContextPayload]


class ScanContextBuilder:
    """Build scan-context payloads while preserving scanner assembly order."""

    def __init__(
        self,
        *,
        collect_scan_base_context: CollectScanBaseContext,
        load_ignore_unresolved_internal_underscore_references: LoadIgnoreUnresolvedReferences,
        load_non_authoritative_test_evidence_max_file_bytes: LoadEvidenceBudget,
        load_non_authoritative_test_evidence_max_files_scanned: LoadEvidenceBudget,
        load_non_authoritative_test_evidence_max_total_bytes: LoadEvidenceBudget,
        enrich_scan_context_with_insights: EnrichScanContextWithInsights,
        finalize_scan_context_payload: FinalizeScanContextPayload,
        non_authoritative_test_evidence_max_file_bytes: int,
        non_authoritative_test_evidence_max_files_scanned: int,
        non_authoritative_test_evidence_max_total_bytes: int,
    ) -> None:
        self._collect_scan_base_context = collect_scan_base_context
        self._load_ignore_unresolved_internal_underscore_references = (
            load_ignore_unresolved_internal_underscore_references
        )
        self._load_non_authoritative_test_evidence_max_file_bytes = (
            load_non_authoritative_test_evidence_max_file_bytes
        )
        self._load_non_authoritative_test_evidence_max_files_scanned = (
            load_non_authoritative_test_evidence_max_files_scanned
        )
        self._load_non_authoritative_test_evidence_max_total_bytes = (
            load_non_authoritative_test_evidence_max_total_bytes
        )
        self._enrich_scan_context_with_insights = enrich_scan_context_with_insights
        self._finalize_scan_context_payload = finalize_scan_context_payload
        self._non_authoritative_test_evidence_max_file_bytes = (
            non_authoritative_test_evidence_max_file_bytes
        )
        self._non_authoritative_test_evidence_max_files_scanned = (
            non_authoritative_test_evidence_max_files_scanned
        )
        self._non_authoritative_test_evidence_max_total_bytes = (
            non_authoritative_test_evidence_max_total_bytes
        )

    def build_scan_context(self, scan_options: ScanOptionsDict) -> ScanContextPayload:
        """Collect role metadata and scanner context required for rendering outputs."""
        base_context = self._collect_scan_base_context(scan_options)
        metadata = base_context["metadata"]

        config_default_ignore = (
            self._load_ignore_unresolved_internal_underscore_references(
                scan_options["role_path"],
                scan_options["readme_config_path"],
                True,
            )
        )
        effective_ignore = (
            config_default_ignore
            if scan_options["ignore_unresolved_internal_underscore_references"] is None
            else bool(scan_options["ignore_unresolved_internal_underscore_references"])
        )
        metadata["ignore_unresolved_internal_underscore_references"] = effective_ignore

        max_file_bytes = self._load_non_authoritative_test_evidence_max_file_bytes(
            scan_options["role_path"],
            scan_options["readme_config_path"],
            self._non_authoritative_test_evidence_max_file_bytes,
        )
        max_files_scanned = (
            self._load_non_authoritative_test_evidence_max_files_scanned(
                scan_options["role_path"],
                scan_options["readme_config_path"],
                self._non_authoritative_test_evidence_max_files_scanned,
            )
        )
        max_total_bytes = self._load_non_authoritative_test_evidence_max_total_bytes(
            scan_options["role_path"],
            scan_options["readme_config_path"],
            self._non_authoritative_test_evidence_max_total_bytes,
        )
        metadata["non_authoritative_test_evidence_limits"] = {
            "max_file_bytes": max_file_bytes,
            "max_files_scanned": max_files_scanned,
            "max_total_bytes": max_total_bytes,
        }

        undocumented_default_filters, display_variables = (
            self._enrich_scan_context_with_insights(
                role_path=scan_options["role_path"],
                role_name=base_context["role_name"],
                description=base_context["description"],
                vars_seed_paths=scan_options["vars_seed_paths"],
                include_vars_main=scan_options["include_vars_main"],
                exclude_path_patterns=scan_options["exclude_path_patterns"],
                marker_prefix=base_context["marker_prefix"],
                found=base_context["found"],
                variables=base_context["variables"],
                metadata=metadata,
                style_readme_path=scan_options["style_readme_path"],
                policy_context=scan_options.get("policy_context"),
                style_source_path=scan_options["style_source_path"],
                style_guide_skeleton=scan_options["style_guide_skeleton"],
                compare_role_path=scan_options["compare_role_path"],
                ignore_unresolved_internal_underscore_references=effective_ignore,
                non_authoritative_test_evidence_max_file_bytes=max_file_bytes,
                non_authoritative_test_evidence_max_files_scanned=max_files_scanned,
                non_authoritative_test_evidence_max_total_bytes=max_total_bytes,
            )
        )
        return self._finalize_scan_context_payload(
            rp=base_context["rp"],
            role_name=base_context["role_name"],
            description=base_context["description"],
            requirements_display=base_context["requirements_display"],
            undocumented_default_filters=undocumented_default_filters,
            display_variables=display_variables,
            metadata=metadata,
        )


def build_scan_context(
    scan_options: ScanOptionsDict,
    *,
    collect_scan_base_context: CollectScanBaseContext,
    load_ignore_unresolved_internal_underscore_references: LoadIgnoreUnresolvedReferences,
    load_non_authoritative_test_evidence_max_file_bytes: LoadEvidenceBudget,
    load_non_authoritative_test_evidence_max_files_scanned: LoadEvidenceBudget,
    load_non_authoritative_test_evidence_max_total_bytes: LoadEvidenceBudget,
    enrich_scan_context_with_insights: EnrichScanContextWithInsights,
    finalize_scan_context_payload: FinalizeScanContextPayload,
    non_authoritative_test_evidence_max_file_bytes: int,
    non_authoritative_test_evidence_max_files_scanned: int,
    non_authoritative_test_evidence_max_total_bytes: int,
) -> ScanContextPayload:
    """Build scan context payload with an explicit dependency seam."""
    builder = ScanContextBuilder(
        collect_scan_base_context=collect_scan_base_context,
        load_ignore_unresolved_internal_underscore_references=(
            load_ignore_unresolved_internal_underscore_references
        ),
        load_non_authoritative_test_evidence_max_file_bytes=(
            load_non_authoritative_test_evidence_max_file_bytes
        ),
        load_non_authoritative_test_evidence_max_files_scanned=(
            load_non_authoritative_test_evidence_max_files_scanned
        ),
        load_non_authoritative_test_evidence_max_total_bytes=(
            load_non_authoritative_test_evidence_max_total_bytes
        ),
        enrich_scan_context_with_insights=enrich_scan_context_with_insights,
        finalize_scan_context_payload=finalize_scan_context_payload,
        non_authoritative_test_evidence_max_file_bytes=(
            non_authoritative_test_evidence_max_file_bytes
        ),
        non_authoritative_test_evidence_max_files_scanned=(
            non_authoritative_test_evidence_max_files_scanned
        ),
        non_authoritative_test_evidence_max_total_bytes=(
            non_authoritative_test_evidence_max_total_bytes
        ),
    )
    return builder.build_scan_context(scan_options)
