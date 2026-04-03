"""Style guide parsing, markdown heading, and variable rendering helpers.

This module serves as a facade for focused style services:
- style_config: Alias and configuration management
- style_formatter: Heading formatting utilities
- style_parser: README parsing and detection
- variable_renderer: Variable rendering in various markdown styles
- notes_renderer: Role notes and summaries
"""

from __future__ import annotations

# Re-export public config APIs
from .style_config import (
    STYLE_SECTION_ALIASES,
    get_style_section_aliases_snapshot,
    refresh_policy_derived_state,
    style_section_aliases_scope,
)

# Re-export public formatter APIs
from .style_formatter import format_heading, normalize_style_heading

# Re-export public parser APIs
from .style_parser import (
    build_section_title_stats,
    detect_style_section_level,
    parse_style_readme,
)

# Re-export public variable renderer APIs
from .variable_renderer import (
    describe_variable,
    is_role_local_variable_row,
    render_role_variables_for_style,
    render_role_variables_nested_bullets_style,
    render_role_variables_simple_list_style,
    render_role_variables_table_style,
    render_role_variables_yaml_block_style,
)

# Re-export public notes renderer APIs
from .notes_renderer import (
    render_role_notes_section,
    render_template_overrides_section,
    render_variable_summary_section,
    render_variable_uncertainty_notes,
)

# Internal-only re-export for backward compatibility with private helpers
from .variable_renderer import (
    is_role_local_variable_row as _is_role_local_variable_row,
)  # noqa: F401
from .variable_renderer import describe_variable as _describe_variable  # noqa: F401
from .variable_renderer import (
    render_role_variables_for_style as _render_role_variables_for_style,
)  # noqa: F401
from .variable_renderer import (
    render_role_variables_table_style as _render_role_variables_table_style,
)  # noqa: F401
from .variable_renderer import (
    render_role_variables_nested_bullets_style as _render_role_variables_nested_bullets_style,
)  # noqa: F401
from .variable_renderer import (
    render_role_variables_yaml_block_style as _render_role_variables_yaml_block_style,
)  # noqa: F401
from .variable_renderer import (
    render_role_variables_simple_list_style as _render_role_variables_simple_list_style,
)  # noqa: F401
from .notes_renderer import (
    render_role_notes_section as _render_role_notes_section,
)  # noqa: F401
from .notes_renderer import (
    render_variable_uncertainty_notes as _render_variable_uncertainty_notes,
)  # noqa: F401
from .notes_renderer import (
    render_variable_summary_section as _render_variable_summary_section,
)  # noqa: F401
from .notes_renderer import (
    render_template_overrides_section as _render_template_overrides_section,
)  # noqa: F401

# Keep legacy private alias imports live for compatibility lookups.
_LEGACY_PRIVATE_EXPORTS = (
    _is_role_local_variable_row,
    _describe_variable,
    _render_role_variables_for_style,
    _render_role_variables_table_style,
    _render_role_variables_nested_bullets_style,
    _render_role_variables_yaml_block_style,
    _render_role_variables_simple_list_style,
    _render_role_notes_section,
    _render_variable_uncertainty_notes,
    _render_variable_summary_section,
    _render_template_overrides_section,
)


# Legacy API support for legacy callers using private functions
def _refresh_policy_derived_state(policy: dict) -> None:
    """Refresh module-level policy state after scanner policy reloads. (Legacy)"""
    refresh_policy_derived_state(policy)


# Support legacy internal imports
_build_section_title_stats = build_section_title_stats

__all__ = [
    "STYLE_SECTION_ALIASES",
    "detect_style_section_level",
    "describe_variable",
    "format_heading",
    "get_style_section_aliases_snapshot",
    "is_role_local_variable_row",
    "normalize_style_heading",
    "parse_style_readme",
    "render_role_notes_section",
    "render_role_variables_for_style",
    "render_role_variables_nested_bullets_style",
    "render_role_variables_simple_list_style",
    "render_role_variables_table_style",
    "render_role_variables_yaml_block_style",
    "render_template_overrides_section",
    "render_variable_summary_section",
    "render_variable_uncertainty_notes",
    "style_section_aliases_scope",
]
