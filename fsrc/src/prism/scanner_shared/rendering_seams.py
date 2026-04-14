"""Rendering seam helpers shared by reporting/readme domains."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import jinja2


def build_render_jinja_environment(
    *,
    template_dir: Path,
    metadata: Mapping[str, Any] | None = None,
) -> jinja2.Environment:
    """Build a rendering Jinja environment with optional metadata policy overrides."""
    metadata = metadata or {}
    custom_factory = metadata.get("jinja_environment_factory")
    if callable(custom_factory):
        custom_env = custom_factory(template_dir, metadata=metadata)
        if isinstance(custom_env, jinja2.Environment):
            return custom_env

    undefined_policy = str(metadata.get("jinja_undefined_policy") or "").strip()
    undefined_cls = (
        jinja2.StrictUndefined
        if undefined_policy.lower() == "strict"
        else jinja2.Undefined
    )
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(template_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=undefined_cls,
    )
