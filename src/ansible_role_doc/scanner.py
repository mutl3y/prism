"""Core scanner implementation.

This module provides utilities to scan an Ansible role for common
patterns (for example uses of the `default()` filter), load role
metadata and variables, and render a README using a Jinja2 template.
"""

from __future__ import annotations
import os
from pathlib import Path
import re
import yaml
import jinja2

DEFAULT_RE = re.compile(
    r"""(?P<context>.{0,40}?)(\|\s*default\b|\bdefault\s*\()\s*(?P<args>[^)\n]{0,200})""",
    flags=re.IGNORECASE,
)


def scan_for_default_filters(role_path: str) -> list:
    """Scan files under ``role_path`` for uses of the ``default()`` filter.

    Returns a list of occurrence dictionaries with keys: ``file``,
    ``line_no``, ``line``, ``match`` and ``args``.
    """
    occurrences: list[dict] = []
    role_path = str(Path(role_path))
    for root, dirs, files in os.walk(role_path):
        dirs[:] = [
            d
            for d in dirs
            if d not in (".git", "__pycache__", "venv", ".venv", "node_modules")
        ]
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as fh:
                    for idx, raw_line in enumerate(fh, start=1):
                        line = raw_line.rstrip("\n")
                        for m in DEFAULT_RE.finditer(line):
                            args = (m.group("args") or "").strip()
                            excerpt = line[max(0, m.start() - 80) : m.end() + 80]
                            occurrences.append(
                                {
                                    "file": os.path.relpath(fpath, role_path),
                                    "line_no": idx,
                                    "line": line,
                                    "match": excerpt.strip(),
                                    "args": args,
                                }
                            )
            except UnicodeDecodeError, PermissionError:
                continue
    return occurrences


def load_meta(role_path: str) -> dict:
    """Load the role metadata file ``meta/main.yml`` if present.

    Returns a mapping (empty if missing or unparsable).
    """
    meta_file = Path(role_path) / "meta" / "main.yml"
    if meta_file.exists():
        try:
            return yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}
    return {}


def load_variables(role_path: str) -> dict:
    """Load variables from ``defaults/main.yml`` and ``vars/main.yml``.

    Values from ``vars`` override values from ``defaults`` when both
    are present. Returns a dict of variables.
    """
    vars_out: dict = {}
    for sub in ("defaults", "vars"):
        p = Path(role_path) / sub / "main.yml"
        if p.exists():
            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                if isinstance(data, dict):
                    vars_out.update(data)
            except Exception:
                continue
    return vars_out


def load_requirements(role_path: str) -> list:
    """Load ``meta/requirements.yml`` as a list, or return an empty list."""
    p = Path(role_path) / "meta" / "requirements.yml"
    if p.exists():
        try:
            return yaml.safe_load(p.read_text(encoding="utf-8")) or []
        except Exception:
            return []
    return []


def collect_role_contents(role_path: str) -> dict:
    """Collect lists of files from common role subdirectories.

    Returns a dict with keys like ``handlers``, ``tasks``, ``templates``,
    ``files`` and ``tests`` containing lists of relative paths.
    """
    rp = Path(role_path)
    result: dict = {}
    for name in (
        "handlers",
        "tasks",
        "templates",
        "files",
        "tests",
        "defaults",
        "vars",
    ):
        subdir = rp / name
        entries: list[str] = []
        if subdir.exists() and subdir.is_dir():
            for p in sorted(subdir.rglob("*")):
                if p.is_file():
                    entries.append(str(p.relative_to(rp)))
        result[name] = entries
    # include parsed meta file for richer template rendering
    try:
        result["meta"] = load_meta(role_path)
    except Exception:
        result["meta"] = {}
    return result


def render_readme(
    output: str,
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    template: str | None = None,
    metadata: dict | None = None,
    write: bool = True,
) -> str:
    if template:
        tpl_file = Path(template)
    else:
        tpl_file = Path(__file__).parent / "templates" / "README.md.j2"

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(tpl_file.parent)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template_obj = env.get_template(tpl_file.name)
    rendered = template_obj.render(
        role_name=role_name,
        description=description,
        variables=variables,
        requirements=requirements,
        default_filters=default_filters,
        metadata=metadata or {},
    )
    if write:
        Path(output).write_text(rendered, encoding="utf-8")
        return str(Path(output).resolve())
    return rendered


def run_scan(
    role_path: str,
    output: str = "README.md",
    template: str | None = None,
    output_format: str = "md",
) -> str:
    rp = Path(role_path)
    if not rp.is_dir():
        raise FileNotFoundError(f"role path not found: {role_path}")
    meta = load_meta(role_path)
    galaxy = meta.get("galaxy_info", {}) if isinstance(meta, dict) else {}
    role_name = galaxy.get("role_name", rp.name)
    description = galaxy.get("description", "")
    variables = load_variables(role_path)
    requirements = load_requirements(role_path)
    found = scan_for_default_filters(role_path)
    metadata = collect_role_contents(role_path)

    # Render Markdown content without writing so we can convert if needed
    rendered = render_readme(
        output,
        role_name,
        description,
        variables,
        requirements,
        found,
        template,
        metadata,
        write=False,
    )

    out_path = Path(output)
    # determine final output path extension for HTML
    if output_format == "html":
        if out_path.suffix.lower() not in (".html", ".htm"):
            out_path = out_path.with_suffix(".html")
    # Convert if necessary
    final_content: str
    if output_format == "md":
        final_content = rendered
    else:
        try:
            import markdown as _md

            html_body = _md.markdown(rendered, extensions=["extra", "toc"])
        except Exception:
            # Fallback: escape and wrap in <pre>
            import html as _html

            html_body = f"<pre>{_html.escape(rendered)}</pre>"

        final_content = f'<!doctype html>\n<html><head><meta charset="utf-8"><title>{role_name}</title></head><body>\n{html_body}\n</body></html>'

    out_path.write_text(final_content, encoding="utf-8")
    return str(out_path.resolve())
