"""Presentation helpers for prism CLI commands."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import re
import shutil

import yaml

_CAPTURE_SCHEMA_VERSION = 1
_CAPTURE_MAX_SECTIONS = 50
_CAPTURE_MAX_CONTENT_CHARS = 20000
_CAPTURE_MAX_TOTAL_CHARS = 1_000_000
_TRUNCATION_MARKER = "\n[truncated]"

_REDACTION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"(?im)\\b(password|passwd|token|secret|api[_-]?key)\\b\\s*[:=]\\s*([^\\s]+)"
        ),
        r"\\1: <redacted>",
    ),
    (
        re.compile(r"(?i)\\b(bearer)\\s+[A-Za-z0-9._~+/-]+=*"),
        r"\\1 <redacted>",
    ),
)


class _ReadableYamlDumper(yaml.SafeDumper):
    """YAML dumper that emits multiline strings as literal blocks."""


def _str_presenter(dumper: yaml.SafeDumper, data: str) -> yaml.nodes.ScalarNode:
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_ReadableYamlDumper.add_representer(str, _str_presenter)


def _sanitize_captured_content(text: str) -> str:
    sanitized = text
    for pattern, replacement in _REDACTION_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def _truncate_content(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    clipped = text[:max_chars].rstrip()
    return f"{clipped}{_TRUNCATION_MARKER}", True


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _bounded_list(items: list[dict], limit: int) -> tuple[list[dict], int]:
    if len(items) <= limit:
        return items, 0
    return items[:limit], len(items) - limit


def _render_collection_markdown(payload: dict) -> str:
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


def _emit_success(
    args: object,
    outpath: str,
    style_source_path: str | None = None,
    style_demo_path: str | None = None,
) -> int:
    if getattr(args, "verbose", False):
        if getattr(args, "dry_run", False):
            print("\nDry run: no files written.")
        else:
            print("Wrote:", outpath)
        if style_source_path:
            print("Style guide source:", style_source_path)
        if style_demo_path:
            print("Generated demo copy:", style_demo_path)
    return 0


def _save_style_comparison_artifacts(
    style_readme_path: str | None,
    generated_output: str,
    style_source_name: str | None = None,
    role_config_path: str | None = None,
    keep_unknown_style_sections: bool = False,
    *,
    parse_style_readme_fn,
    capture_schema_version: int = _CAPTURE_SCHEMA_VERSION,
    capture_max_sections: int = _CAPTURE_MAX_SECTIONS,
    capture_max_content_chars: int = _CAPTURE_MAX_CONTENT_CHARS,
    capture_max_total_chars: int = _CAPTURE_MAX_TOTAL_CHARS,
) -> tuple[str | None, str | None]:
    if not style_readme_path:
        return None, None

    source = Path(style_readme_path)
    if not source.is_file():
        raise FileNotFoundError(f"style README not found: {style_readme_path}")

    output_path = Path(generated_output)
    style_slug = style_source_name or source.stem
    if style_slug.lower() in {"readme", "source_style_guide", "style_guide_source"}:
        style_slug = source.parent.name or style_slug
    style_slug = re.sub(r"^style_", "", style_slug, flags=re.IGNORECASE)
    style_slug = re.sub(
        r"\.source_style_guide$|\.style_guide_source$",
        "",
        style_slug,
        flags=re.IGNORECASE,
    )
    style_slug = (
        re.sub(r"[^a-zA-Z0-9]+", "_", style_slug).strip("_").lower() or "style_guide"
    )
    expected_style_dir_name = f"style_{style_slug}"
    if output_path.parent.name == expected_style_dir_name:
        style_dir = output_path.parent
    else:
        style_dir = output_path.parent / expected_style_dir_name
    style_dir.mkdir(parents=True, exist_ok=True)

    source_suffix = source.suffix or ".md"
    source_destination = style_dir / f"SOURCE_STYLE_GUIDE{source_suffix}"
    if source.resolve() != source_destination.resolve():
        shutil.copyfile(source, source_destination)

    output_suffix = output_path.suffix or ".md"
    demo_destination = style_dir / f"DEMO_GENERATED{output_suffix}"
    if output_path.resolve() != demo_destination.resolve():
        shutil.copyfile(output_path, demo_destination)

    if keep_unknown_style_sections:
        keep_demo_destination = style_dir / f"DEMO_GENERATED_KEEP_UNKNOWN{output_suffix}"
        if output_path.resolve() != keep_demo_destination.resolve():
            shutil.copyfile(output_path, keep_demo_destination)

    cfg_destination = style_dir / "ROLE_README_CONFIG.yml"

    if role_config_path:
        cfg_source = Path(role_config_path)
        if cfg_source.is_file():
            if cfg_source.resolve() != cfg_destination.resolve():
                shutil.copyfile(cfg_source, cfg_destination)
            return str(source_destination.resolve()), str(demo_destination.resolve())

    parsed = parse_style_readme_fn(str(source))
    unknown_sections: list[dict[str, str]] = []
    seen_keys: set[str] = set()
    total_chars = 0
    truncated_any = False

    for section in parsed.get("sections", []):
        if section.get("id") != "unknown":
            continue
        if len(unknown_sections) >= capture_max_sections:
            truncated_any = True
            break

        title = str(section.get("title") or "").strip()
        key = re.sub(r"\\s+", " ", title).lower()
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)

        body = str(section.get("body") or "").strip()
        body = _sanitize_captured_content(body)
        body, truncated_one = _truncate_content(body, capture_max_content_chars)
        if truncated_one:
            truncated_any = True

        proposed_chars = total_chars + len(title) + len(body)
        if proposed_chars > capture_max_total_chars:
            remaining = max(0, capture_max_total_chars - total_chars - len(title))
            body, _ = _truncate_content(body, remaining)
            truncated_any = True

        unknown_sections.append({"title": title, "content": body})
        total_chars += len(title) + len(body)

        if total_chars >= capture_max_total_chars:
            break

    unknown_sections.sort(key=lambda row: row["title"].lower())

    payload = {
        "readme": {
            "capture_metadata": {
                "schema_version": capture_schema_version,
                "captured_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "style_source_path": str(source),
                "truncated": truncated_any,
            },
            "unknown_style_sections": unknown_sections,
        }
    }
    cfg_lines = [
        "# Auto-generated sample: promote this file into the role as .prism.yml",
        "# to keep unknown style sections as your source-of-truth.",
        yaml.dump(
            payload,
            Dumper=_ReadableYamlDumper,
            sort_keys=False,
            default_flow_style=False,
            width=10000,
        ).rstrip(),
        "",
    ]
    rendered_cfg = "\n".join(cfg_lines)
    existing_cfg = (
        cfg_destination.read_text(encoding="utf-8") if cfg_destination.exists() else None
    )
    if existing_cfg != rendered_cfg:
        cfg_destination.write_text(rendered_cfg, encoding="utf-8")

    return str(source_destination.resolve()), str(demo_destination.resolve())
