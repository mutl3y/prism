"""Platform-agnostic default scan-pipeline policy."""

from __future__ import annotations

from typing import Any


class DefaultScanPipelinePlugin:
    """Default scan-pipeline plugin that keeps preflight contract neutral."""

    def process_scan_pipeline(
        self,
        scan_options: dict[str, Any],
        scan_context: dict[str, Any],
    ) -> dict[str, Any]:
        context = dict(scan_context)
        context.setdefault("plugin_platform", "default")
        context.setdefault("plugin_name", "default")
        context["plugin_enabled"] = True
        if "role_path" in scan_options and "role_path" not in context:
            context["role_path"] = scan_options.get("role_path")
        return context
