"""Scanner I/O package - output rendering and YAML loading utilities."""

from __future__ import annotations

from .loader import (
    collect_yaml_parse_failures,
    iter_role_yaml_candidates,
    load_yaml_file,
    map_argument_spec_type,
    parse_yaml_candidate,
)
from .output import (
    FinalOutputPayload,
    build_final_output_payload,
    render_final_output,
    resolve_output_path,
    write_output,
)

__all__ = [
    "collect_yaml_parse_failures",
    "iter_role_yaml_candidates",
    "load_yaml_file",
    "map_argument_spec_type",
    "parse_yaml_candidate",
    "FinalOutputPayload",
    "build_final_output_payload",
    "render_final_output",
    "resolve_output_path",
    "write_output",
]
