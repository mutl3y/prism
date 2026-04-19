"""Package export parity tests for required scanner_* package surfaces."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[4]
FSRC_SOURCE_ROOT = PROJECT_ROOT / "fsrc" / "src"

REQUIRED_SCANNER_PACKAGE_EXPORTS: dict[str, set[str]] = {
    "prism.scanner_data": {
        "AnnotationQualityCounters",
        "CollectionScanResult",
        "EmitScanOutputsArgs",
        "FailureDetail",
        "FailurePolicyContract",
        "FeaturesContext",
        "FinalOutputPayload",
        "NormalizedScannerReportMetadata",
        "OutputConfiguration",
        "ReadmeSectionRenderInput",
        "ReferenceContext",
        "RepoScanResult",
        "ReportRenderingMetadata",
        "RoleScanResult",
        "RunbookSidecarPayload",
        "RunbookSidecarArgs",
        "RunScanOutputPayload",
        "ScanPayloadBuilder",
        "ScanRenderPayload",
        "ScanBaseContext",
        "ScanContext",
        "ScanContextPayload",
        "ScanMetadata",
        "ScanOptionsDict",
        "ScanPhaseError",
        "ScanPhaseStatus",
        "ScanReportSidecarArgs",
        "ScannerCounters",
        "ScannerReportIssueListRow",
        "ScannerReportMetadata",
        "ScannerReportSectionRenderInput",
        "ScannerReportYamlParseFailureRow",
        "SectionBodyRenderResult",
        "StyleGuideConfig",
        "Variable",
        "VariableAnalysisResults",
        "VariableProvenance",
        "VariableRow",
        "VariableRowBuilder",
        "VariableRowWithMeta",
    },
    "prism.scanner_extract": {
        "TASK_INCLUDE_KEYS",
        "ROLE_INCLUDE_KEYS",
        "INCLUDE_VARS_KEYS",
        "SET_FACT_KEYS",
        "TASK_BLOCK_KEYS",
        "TASK_META_KEYS",
        "ROLE_NOTES_RE",
        "ROLE_NOTES_SHORT_RE",
        "TASK_NOTES_LONG_RE",
        "TASK_NOTES_SHORT_RE",
        "COMMENT_CONTINUATION_RE",
        "is_path_excluded",
        "load_yaml_file",
        "collect_task_files",
        "is_relpath_excluded",
        "extract_role_notes_from_comments",
        "collect_unconstrained_dynamic_role_includes",
        "collect_unconstrained_dynamic_task_includes",
        "collect_task_handler_catalog",
        "collect_molecule_scenarios",
        "extract_role_features",
        "DEFAULT_TARGET_RE",
        "JINJA_VAR_RE",
        "JINJA_IDENTIFIER_RE",
        "VAULT_KEY_RE",
        "looks_secret_name",
        "resembles_password_like",
        "extract_default_target_var",
        "load_seed_variables",
        "collect_include_vars_files",
        "iter_role_variable_map_candidates",
        "load_meta",
        "load_requirements",
        "load_variables",
        "resolve_scan_identity",
        "iter_role_yaml_candidates",
        "parse_yaml_candidate",
        "collect_yaml_parse_failures",
        "load_role_variable_maps",
        "iter_role_argument_spec_entries",
        "map_argument_spec_type",
        "format_requirement_line",
        "normalize_requirements",
        "normalize_meta_role_dependencies",
        "normalize_included_role_dependencies",
        "extract_declared_collections_from_meta",
        "extract_declared_collections_from_requirements",
        "build_collection_compliance_notes",
        "build_requirements_display",
    },
    "prism.scanner_readme": {
        "ALL_SECTION_IDS",
        "DEFAULT_SECTION_SPECS",
        "EXTRA_SECTION_IDS",
        "SCANNER_STATS_SECTION_IDS",
        "render_readme",
        "append_scanner_report_section_if_enabled",
        "render_guide_section_body",
        "STYLE_SECTION_ALIASES",
        "get_style_section_aliases_snapshot",
        "detect_style_section_level",
        "format_heading",
        "normalize_style_heading",
        "parse_style_readme",
        "refresh_policy_derived_state",
        "build_doc_insights",
        "parse_comma_values",
    },
    "prism.scanner_io": {
        "collect_yaml_parse_failures",
        "iter_role_yaml_candidates",
        "load_yaml_file",
        "map_argument_spec_type",
        "parse_yaml_candidate",
        "render_collection_markdown",
        "FinalOutputPayload",
        "build_final_output_payload",
        "render_final_output",
        "resolve_output_path",
        "write_output",
    },
}


@contextmanager
def _prefer_lane_on_sys_path(lane_root: Path) -> Iterator[None]:
    original_path = list(sys.path)
    original_modules = {
        key: value
        for key, value in sys.modules.items()
        if key == "prism" or key.startswith("prism.")
    }
    try:
        sys.path.insert(0, str(lane_root))
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        yield
    finally:
        sys.path[:] = original_path
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        sys.modules.update(original_modules)


def _load_module_exports(module_name: str, lane_root: Path) -> set[str]:
    with _prefer_lane_on_sys_path(lane_root):
        module = importlib.import_module(module_name)
    public = getattr(module, "__all__", None)
    assert isinstance(public, list)
    return set(public)


def test_fsrc_required_scanner_package_exports_match_contract() -> None:
    for module_name, required_exports in REQUIRED_SCANNER_PACKAGE_EXPORTS.items():
        fsrc_exports = _load_module_exports(module_name, FSRC_SOURCE_ROOT)
        assert fsrc_exports == required_exports, module_name
