"""Scanner configuration package."""

from prism.scanner_config.audit_rules import (
    AuditReport,
    AuditRule,
    AuditViolation,
    load_audit_rules_from_policy,
)
from prism.scanner_config.legacy_retirement import (
    LEGACY_RUNTIME_PATH_UNAVAILABLE,
    LEGACY_RUNTIME_PATH_UNAVAILABLE_MESSAGE,
    LEGACY_RUNTIME_STYLE_SOURCE_ENV,
    LEGACY_SECTION_CONFIG_FILENAME,
    LEGACY_SECTION_CONFIG_UNSUPPORTED,
    LEGACY_SECTION_CONFIG_UNSUPPORTED_MESSAGE,
    format_legacy_retirement_error,
)
from prism.scanner_config.marker import load_readme_marker_prefix
from prism.scanner_config.patterns import (
    build_policy_context,
    fetch_remote_policy,
    load_pattern_config,
    load_pattern_policy_with_context,
    write_unknown_headings_log,
)
from prism.scanner_config.policy import (
    load_fail_on_unconstrained_dynamic_includes,
    load_fail_on_yaml_like_task_annotations,
    load_ignore_unresolved_internal_underscore_references,
    load_non_authoritative_test_evidence_max_file_bytes,
    load_policy_rules_from_config,
)
from prism.scanner_config.readme import (
    DEFAULT_SECTION_DISPLAY_TITLES_PATH,
    load_readme_section_config,
    resolve_role_config_file,
)
from prism.scanner_config.section import (
    DEFAULT_DOC_MARKER_PREFIX,
    SECTION_CONFIG_FILENAME,
    SECTION_CONFIG_FILENAMES,
)
from prism.scanner_config.style import (
    default_style_guide_user_paths,
    load_section_display_titles,
    resolve_default_style_guide_source,
)

__all__ = [
    "AuditReport",
    "AuditRule",
    "AuditViolation",
    "DEFAULT_DOC_MARKER_PREFIX",
    "DEFAULT_SECTION_DISPLAY_TITLES_PATH",
    "LEGACY_RUNTIME_PATH_UNAVAILABLE",
    "LEGACY_RUNTIME_PATH_UNAVAILABLE_MESSAGE",
    "LEGACY_RUNTIME_STYLE_SOURCE_ENV",
    "LEGACY_SECTION_CONFIG_FILENAME",
    "LEGACY_SECTION_CONFIG_UNSUPPORTED",
    "LEGACY_SECTION_CONFIG_UNSUPPORTED_MESSAGE",
    "SECTION_CONFIG_FILENAME",
    "SECTION_CONFIG_FILENAMES",
    "build_policy_context",
    "default_style_guide_user_paths",
    "fetch_remote_policy",
    "format_legacy_retirement_error",
    "load_audit_rules_from_policy",
    "load_fail_on_unconstrained_dynamic_includes",
    "load_fail_on_yaml_like_task_annotations",
    "load_ignore_unresolved_internal_underscore_references",
    "load_non_authoritative_test_evidence_max_file_bytes",
    "load_pattern_config",
    "load_pattern_policy_with_context",
    "load_policy_rules_from_config",
    "load_readme_marker_prefix",
    "load_readme_section_config",
    "load_section_display_titles",
    "resolve_default_style_guide_source",
    "resolve_role_config_file",
    "write_unknown_headings_log",
]
