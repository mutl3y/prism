"""Scanner configuration package - centralized configuration loading.

Consolidates README section configuration, scan policies, pattern loading,
style guide resolution, and marker configuration.
"""

from __future__ import annotations

# Section constants
from .section import (
    DEFAULT_DOC_MARKER_PREFIX,
    SECTION_CONFIG_FILENAME,
    SECTION_CONFIG_FILENAMES,
)

# Marker loading
from .marker import (
    load_readme_marker_prefix,
)

# README section configuration
from .readme import (
    load_readme_section_config,
    load_readme_section_visibility,
    resolve_role_config_file,
)

# Scan policy loaders
from .policy import (
    load_fail_on_unconstrained_dynamic_includes,
    load_fail_on_yaml_like_task_annotations,
    load_ignore_unresolved_internal_underscore_references,
    load_non_authoritative_test_evidence_max_file_bytes,
    load_non_authoritative_test_evidence_max_files_scanned,
    load_non_authoritative_test_evidence_max_total_bytes,
)

# Pattern loading
from .patterns import (
    fetch_remote_policy,
    load_pattern_config,
    write_unknown_headings_log,
)

# Style guide and section resolution
from .style import (
    default_style_guide_user_paths,
    load_section_display_titles,
    refresh_policy,
    resolve_default_style_guide_source,
    resolve_section_selector,
)

__all__ = [
    # Section constants
    "DEFAULT_DOC_MARKER_PREFIX",
    "SECTION_CONFIG_FILENAME",
    "SECTION_CONFIG_FILENAMES",
    # Marker loading
    "load_readme_marker_prefix",
    # README section configuration
    "load_readme_section_config",
    "load_readme_section_visibility",
    "resolve_role_config_file",
    # Scan policy loaders
    "load_fail_on_unconstrained_dynamic_includes",
    "load_fail_on_yaml_like_task_annotations",
    "load_ignore_unresolved_internal_underscore_references",
    "load_non_authoritative_test_evidence_max_file_bytes",
    "load_non_authoritative_test_evidence_max_files_scanned",
    "load_non_authoritative_test_evidence_max_total_bytes",
    # Pattern loading
    "fetch_remote_policy",
    "load_pattern_config",
    "write_unknown_headings_log",
    # Style guide and section resolution
    "default_style_guide_user_paths",
    "load_section_display_titles",
    "refresh_policy",
    "resolve_default_style_guide_source",
    "resolve_section_selector",
]
