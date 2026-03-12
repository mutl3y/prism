"""Core scanner implementation"""
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

def scan_for_default_filters(role_path: str):
    occurrences = []
    role_path = str(Path(role_path))
    for root, dirs, files in os.walk(role_path):
        dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__', 'venv', '.venv', 'node_modules')]
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as fh:
                    for idx, raw_line in enumerate(fh, start=1):
                        line = raw_line.rstrip('\n')
                        for m in DEFAULT_RE.finditer(line):
                            args = (m.group('args') or '').strip()
                            excerpt = line[max(0, m.start() - 80): m.end() + 80]
                            occurrences.append({
                                'file': os.path.relpath(fpath, role_path),
                                'line_no': idx,
                                'line': line,
                                'match': excerpt.strip(),
                                'args': args,
                            })
            except (UnicodeDecodeError, PermissionError):
                continue
    return occurrences

def load_meta(role_path: str):
    meta_file = Path(role_path) / 'meta' / 'main.yml'
    if meta_file.exists():
        try:
            return yaml.safe_load(meta_file.read_text(encoding='utf-8')) or {}
        except Exception:
            return {}
    return {}

def load_variables(role_path: str):
    vars_out = {}
    for sub in ('defaults', 'vars'):
        p = Path(role_path) / sub / 'main.yml'
        if p.exists():
            try:
                data = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
                if isinstance(data, dict):
                    vars_out.update(data)
            except Exception:
                continue
    return vars_out

def load_requirements(role_path: str):
    p = Path(role_path) / 'meta' / 'requirements.yml'
    if p.exists():
        try:
            return yaml.safe_load(p.read_text(encoding='utf-8')) or []
        except Exception:
            return []
    return []

def render_readme(output: str, role_name: str, description: str, variables: dict, requirements: list, default_filters: list, template: str | None = None):
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
    )
    Path(output).write_text(rendered, encoding='utf-8')
    return str(Path(output).resolve())

def run_scan(role_path: str, output: str = "README.md", template: str | None = None):
    rp = Path(role_path)
    if not rp.is_dir():
        raise FileNotFoundError(f"role path not found: {role_path}")
    meta = load_meta(role_path)
    galaxy = meta.get('galaxy_info', {}) if isinstance(meta, dict) else {}
    role_name = galaxy.get('role_name', rp.name)
    description = galaxy.get('description', '')
    variables = load_variables(role_path)
    requirements = load_requirements(role_path)
    found = scan_for_default_filters(role_path)
    outpath = render_readme(output, role_name, description, variables, requirements, found, template)
    return outpath