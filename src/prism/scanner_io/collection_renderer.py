"""Collection markdown renderer utilities reusable outside CLI layers."""

from __future__ import annotations

from pathlib import Path


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _bounded_list(items: list[dict], limit: int) -> tuple[list[dict], int]:
    if len(items) <= limit:
        return items, 0
    return items[:limit], len(items) - limit


def render_collection_markdown(payload: dict) -> str:
    max_plugin_rows = 40
    max_filter_rows = 25
    max_role_rows = 60
    max_failure_rows = 30

    collection = payload.get("collection", {}) if isinstance(payload, dict) else {}
    metadata = _as_dict(collection.get("metadata", {}))
    namespace = str(metadata.get("namespace") or "unknown")
    name = str(metadata.get("name") or "collection")
    fqcn = f"{namespace}.{name}"
    version = str(metadata.get("version") or "unknown")

    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    total_roles = int(summary.get("total_roles") or 0)
    scanned_roles = int(summary.get("scanned_roles") or 0)
    failed_roles = int(summary.get("failed_roles") or 0)

    lines: list[str] = [
        f"# {fqcn} Collection Documentation",
        "",
        "## Collection",
        "",
        f"- FQCN: `{fqcn}`",
        f"- Version: {version}",
        "",
        "## Summary",
        "",
        f"- Total roles: {total_roles}",
        f"- Scanned roles: {scanned_roles}",
        f"- Failed roles: {failed_roles}",
    ]

    dependencies = payload.get("dependencies", {}) if isinstance(payload, dict) else {}
    collections = (
        dependencies.get("collections", []) if isinstance(dependencies, dict) else []
    )
    role_dependencies = (
        dependencies.get("roles", []) if isinstance(dependencies, dict) else []
    )
    if collections:
        lines.extend(["", "## Collection Dependencies", ""])
        for item in collections:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or item.get("name") or "unknown")
            dep_version = str(item.get("version") or "latest")
            lines.append(f"- `{key}` ({dep_version})")
    if role_dependencies:
        lines.extend(["", "## Role Dependencies", ""])
        for item in role_dependencies:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or item.get("name") or "unknown")
            dep_version = str(item.get("version") or "latest")
            lines.append(f"- `{key}` ({dep_version})")

    conflicts = (
        dependencies.get("conflicts", []) if isinstance(dependencies, dict) else []
    )
    if conflicts:
        lines.extend(["", "## Dependency Conflicts", ""])
        for conflict in conflicts:
            if not isinstance(conflict, dict):
                continue
            key = str(conflict.get("key") or "unknown")
            versions = ", ".join(str(v) for v in conflict.get("versions", []))
            lines.append(f"- `{key}`: {versions}")

    roles = payload.get("roles", []) if isinstance(payload, dict) else []
    if roles:
        lines.extend(["", "## Roles", ""])
        sorted_roles = sorted(
            (entry for entry in roles if isinstance(entry, dict)),
            key=lambda entry: str(entry.get("role") or ""),
        )
        bounded_roles, role_overflow = _bounded_list(sorted_roles, max_role_rows)
        for entry in bounded_roles:
            role_name = str(entry.get("role") or "unknown")
            role_payload = _as_dict(entry.get("payload", {}))
            scanner_counters = _as_dict(
                _as_dict(role_payload.get("metadata", {})).get("scanner_counters", {})
            )
            tasks = int(scanner_counters.get("task_files") or 0)
            templates = int(scanner_counters.get("templates") or 0)
            lines.append(
                f"- [{role_name}](roles/{role_name}.md): task_files={tasks}, templates={templates}"
            )
        if role_overflow:
            lines.append(f"- ... and {role_overflow} more roles")

    plugin_catalog = (
        payload.get("plugin_catalog", {}) if isinstance(payload, dict) else {}
    )
    plugin_summary = _as_dict(plugin_catalog.get("summary", {}))
    plugins_by_type = _as_dict(plugin_catalog.get("by_type", {}))
    plugin_failures = plugin_catalog.get("failures", [])
    if plugin_summary or plugins_by_type:
        lines.extend(["", "## Plugin Catalog", ""])
        lines.append(
            f"- Total plugins: {int(plugin_summary.get('total_plugins') or 0)}"
        )
        lines.append(
            f"- Files scanned: {int(plugin_summary.get('files_scanned') or 0)}"
        )
        lines.append(f"- Files failed: {int(plugin_summary.get('files_failed') or 0)}")

        non_empty_types = [
            plugin_type
            for plugin_type, records in plugins_by_type.items()
            if isinstance(records, list) and records
        ]
        if non_empty_types:
            lines.append(f"- Types present: {', '.join(non_empty_types)}")

        type_rows: list[dict] = []
        for plugin_type, records in plugins_by_type.items():
            if not isinstance(records, list):
                continue
            type_rows.append({"type": str(plugin_type), "count": len(records)})
        type_rows.sort(key=lambda item: item["type"])
        bounded_rows, overflow = _bounded_list(type_rows, max_plugin_rows)
        if bounded_rows:
            lines.extend(["", "### Plugin Types", ""])
            for row in bounded_rows:
                lines.append(f"- `{row['type']}`: {row['count']}")
        if overflow:
            lines.append(f"- ... and {overflow} more plugin types")

        filters = plugins_by_type.get("filter", [])
        if isinstance(filters, list) and filters:
            lines.extend(["", "### Filter Capabilities", ""])
            sorted_filters = sorted(
                (record for record in filters if isinstance(record, dict)),
                key=lambda record: str(record.get("name") or ""),
            )
            bounded_filters, filter_overflow = _bounded_list(
                sorted_filters,
                max_filter_rows,
            )
            for record in bounded_filters:
                plugin_name = str(record.get("name") or "unknown")
                symbols = record.get("symbols", [])
                if isinstance(symbols, list) and symbols:
                    symbol_text = ", ".join(str(symbol) for symbol in symbols[:6])
                    if len(symbols) > 6:
                        symbol_text += ", ..."
                else:
                    symbol_text = "(none discovered)"
                confidence = str(record.get("confidence") or "unknown")
                lines.append(f"- `{plugin_name}` [{confidence}]: {symbol_text}")
            if filter_overflow:
                lines.append(f"- ... and {filter_overflow} more filter plugins")

        if isinstance(plugin_failures, list) and plugin_failures:
            lines.extend(["", "### Plugin Scan Failures", ""])
            for failure in plugin_failures:
                if not isinstance(failure, dict):
                    continue
                relpath = str(failure.get("relative_path") or "unknown")
                stage = str(failure.get("stage") or "unknown")
                error = str(failure.get("error") or "unknown error")
                lines.append(f"- `{relpath}` ({stage}): {error}")

    failures = payload.get("failures", []) if isinstance(payload, dict) else []
    if failures:
        lines.extend(["", "## Role Scan Failures", ""])
        sorted_failures = sorted(
            (failure for failure in failures if isinstance(failure, dict)),
            key=lambda failure: str(failure.get("role") or ""),
        )
        bounded_failures, failure_overflow = _bounded_list(
            sorted_failures,
            max_failure_rows,
        )
        for failure in bounded_failures:
            role_name = str(failure.get("role") or "unknown")
            error = str(failure.get("error") or "unknown error")
            lines.append(f"- `{role_name}`: {error}")
        if failure_overflow:
            lines.append(f"- ... and {failure_overflow} more role failures")

    lines.append("")
    return "\n".join(lines)


def _resolve_collection_display_name(payload: dict) -> str:
    """Return a human-readable collection name for summary output."""
    collection = payload.get("collection", {}) if isinstance(payload, dict) else {}
    metadata = _as_dict(collection.get("metadata", {}))
    namespace = str(metadata.get("namespace") or "").strip()
    name = str(metadata.get("name") or "").strip()
    if namespace and name:
        return f"{namespace}.{name}"
    path = str(collection.get("path") or "")
    basename = path.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    return basename or "collection"


def format_collection_summary(payload: dict) -> str:
    """Return a compact plain-text summary of a collection scan result.

    Suitable for printing to stdout after writing the rendered output to disk,
    giving the user a quick confirmation of what was scanned.
    """
    display_name = _resolve_collection_display_name(payload)
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    scanned = int(summary.get("scanned_roles") or 0)
    failed = int(summary.get("failed_roles") or 0)
    return (
        f"Collection: {display_name}\nRoles scanned: {scanned}\nRoles failed: {failed}"
    )


def write_collection_runbook_artifacts(
    *,
    role_name: str,
    metadata: dict,
    runbook_output_dir: str | None,
    runbook_csv_output_dir: str | None,
    render_runbook_fn,
    render_runbook_csv_fn,
) -> None:
    """Write runbook artifacts only when explicit output directories are provided."""
    if runbook_output_dir:
        rb_dir = Path(runbook_output_dir)
        rb_dir.mkdir(parents=True, exist_ok=True)
        rb_content = render_runbook_fn(role_name, metadata)
        (rb_dir / f"{role_name}.runbook.md").write_text(
            rb_content,
            encoding="utf-8",
        )

    if runbook_csv_output_dir:
        rb_csv_dir = Path(runbook_csv_output_dir)
        rb_csv_dir.mkdir(parents=True, exist_ok=True)
        rb_csv_content = render_runbook_csv_fn(metadata)
        (rb_csv_dir / f"{role_name}.runbook.csv").write_text(
            rb_csv_content,
            encoding="utf-8",
        )
