"""Presentation helpers for prism CLI commands."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import re
import shutil

import yaml

from .scanner_io.collection_renderer import render_collection_markdown

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
    return render_collection_markdown(payload)


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
        keep_demo_destination = (
            style_dir / f"DEMO_GENERATED_KEEP_UNKNOWN{output_suffix}"
        )
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
        cfg_destination.read_text(encoding="utf-8")
        if cfg_destination.exists()
        else None
    )
    if existing_cfg != rendered_cfg:
        cfg_destination.write_text(rendered_cfg, encoding="utf-8")

    return str(source_destination.resolve()), str(demo_destination.resolve())
