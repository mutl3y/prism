"""CLI entry point for ansible-role-doc.

Provides a small CLI wrapper around :func:`ansible_role_doc.scanner.run_scan`.
"""

from __future__ import annotations
import base64
import argparse
from datetime import datetime, UTC
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
import sys
import tempfile
import yaml
from .scanner import parse_style_readme, resolve_default_style_guide_source, run_scan


class _ReadableYamlDumper(yaml.SafeDumper):
    """YAML dumper that emits multiline strings as literal blocks."""


def _str_presenter(dumper: yaml.SafeDumper, data: str) -> yaml.nodes.ScalarNode:
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_ReadableYamlDumper.add_representer(str, _str_presenter)

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

_ROLE_MARKER_DIRS = frozenset(
    {"defaults", "files", "handlers", "meta", "tasks", "templates", "tests", "vars"}
)
_MIN_ROLE_MARKER_DIRS = 3


def _sanitize_captured_content(text: str) -> str:
    """Redact obvious secret-like tokens from captured markdown content."""
    sanitized = text
    for pattern, replacement in _REDACTION_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def _truncate_content(text: str, max_chars: int) -> tuple[str, bool]:
    """Return content truncated to max chars with a marker when needed."""
    if len(text) <= max_chars:
        return text, False
    clipped = text[:max_chars].rstrip()
    return f"{clipped}{_TRUNCATION_MARKER}", True


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser.

    The parser includes options for output path, template, format and verbosity.
    """
    p = argparse.ArgumentParser(
        prog="ansible-role-doc",
        description="Scan an Ansible role for default() usages and render README.",
    )
    p.add_argument(
        "role_path",
        nargs="?",
        help="Path to the Ansible role directory to scan",
    )
    p.add_argument(
        "--repo-url",
        default=None,
        help="GitHub/Git repository URL to clone and scan instead of a local role path.",
    )
    p.add_argument(
        "--repo-ref",
        default=None,
        help="Optional branch, tag, or ref to clone from the repository.",
    )
    p.add_argument(
        "--repo-role-path",
        default=".",
        help="Role path inside the cloned repository (default: repository root).",
    )
    p.add_argument(
        "--repo-timeout",
        type=int,
        default=60,
        help="Timeout in seconds for repository clone operations (default: 60).",
    )
    p.add_argument(
        "--compare-role-path",
        default=None,
        help="Optional local role path used as a baseline comparison in the generated review.",
    )
    p.add_argument(
        "--style-readme",
        default=None,
        help="Optional local README path used as a style guide for section order and headings.",
    )
    p.add_argument(
        "--style-source",
        default=None,
        help=(
            "Explicit style source markdown path used when resolving style-guide skeletons "
            "or as fallback style input when --style-readme is not provided."
        ),
    )
    p.add_argument(
        "--create-style-guide",
        action="store_true",
        help=(
            "Generate a style-guide skeleton README that keeps only section headings/order. "
            "When used without --style-readme, style source is resolved from env/cwd/XDG/system/bundled defaults."
        ),
    )
    p.add_argument(
        "--repo-style-readme-path",
        default=None,
        help="Optional README path inside a cloned repository to use as a style guide.",
    )
    p.add_argument(
        "--vars-seed",
        action="append",
        default=None,
        help=(
            "Optional vars seed file or directory (can be passed multiple times), "
            "for example group_vars/ to prime required/undocumented variable detection."
        ),
    )
    p.add_argument(
        "--concise-readme",
        action="store_true",
        help="Keep README concise and write scanner-heavy sections to a sidecar report.",
    )
    p.add_argument(
        "--scanner-report-output",
        default=None,
        help="Optional output path for scanner sidecar report in concise mode.",
    )
    p.add_argument(
        "--include-scanner-report-link",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Include a scanner report section/link in concise README output "
            "(use --no-include-scanner-report-link to hide it)."
        ),
    )
    p.add_argument(
        "--variable-sources",
        choices=("defaults+vars", "defaults-only"),
        default="defaults-only",
        help=(
            "Select which role variable files are documented: "
            "'defaults-only' (default) or 'defaults+vars'."
        ),
    )
    p.add_argument(
        "--readme-config",
        default=None,
        help=(
            "Optional YAML config controlling README section visibility "
            "(defaults to <role>/.ansible_role_doc.yml when present)."
        ),
    )
    p.add_argument(
        "--policy-config",
        default=None,
        help=(
            "Optional pattern-policy override YAML path used during scanning "
            "(highest precedence over env/cwd/XDG/system policy sources)."
        ),
    )
    p.add_argument(
        "--adopt-style-headings",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Adopt include_sections labels as rendered section headings when using README config "
            "(can also be set via readme.adopt_style_headings in .ansible_role_doc.yml)."
        ),
    )
    p.add_argument(
        "--keep-unknown-style-sections",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Keep unmapped headings from style README sources as placeholder sections "
            "(enabled by default; use --no-keep-unknown-style-sections to suppress)."
        ),
    )
    p.add_argument(
        "--exclude-path",
        action="append",
        default=None,
        help=(
            "Exclude role-relative paths or glob patterns from analysis "
            "(can be passed multiple times; examples: templates/*, tests/**, vars/main.yml)."
        ),
    )
    p.add_argument(
        "-o", "--output", default="README.md", help="Output README file path"
    )
    p.add_argument(
        "-t",
        "--template",
        default=None,
        help="Template path (optional). If omitted, uses bundled template.",
    )
    p.add_argument(
        "-f",
        "--format",
        default="md",
        choices=("md", "html", "json"),
        help="Output format (md, html, or json).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Render output without writing files; prints the rendered result to stdout.",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    return p


def _clone_repo(
    repo_url: str,
    destination: Path,
    ref: str | None = None,
    timeout: int = 60,
    sparse_paths: list[str] | None = None,
) -> None:
    """Clone a git repository into ``destination`` with shallow history.

    When ``sparse_paths`` is provided, first attempt a sparse/partial checkout to
    reduce downloaded content. If sparse setup fails, fall back to a regular
    shallow clone so behavior remains reliable.
    """
    parsed = urlparse(repo_url)
    clone_url = repo_url
    if parsed.scheme in {"http", "https"} and parsed.netloc == "github.com":
        repo_path = parsed.path.strip("/")
        if repo_path and repo_path.count("/") >= 1:
            if not repo_path.endswith(".git"):
                repo_path = f"{repo_path}.git"
            clone_url = f"git@github.com:{repo_path}"

    clone_cmd = ["git", "clone", "--depth", "1"]
    if ref:
        clone_cmd.extend(["--branch", ref, "--single-branch"])

    requested_sparse_paths = [
        path.strip() for path in (sparse_paths or []) if path and path.strip()
    ]
    use_sparse_clone = bool(requested_sparse_paths)
    if use_sparse_clone:
        clone_cmd.extend(["--filter=blob:none", "--sparse"])

    clone_cmd.extend([clone_url, str(destination)])

    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"

    def _run_clone(cmd: list[str]) -> None:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env,
        )

    def _run_sparse_checkout(paths: list[str]) -> None:
        sparse_cmd = [
            "git",
            "-C",
            str(destination),
            "sparse-checkout",
            "set",
            "--no-cone",
            *paths,
        ]
        subprocess.run(
            sparse_cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env,
        )

    try:
        if use_sparse_clone:
            try:
                _run_clone(clone_cmd)
                _run_sparse_checkout(requested_sparse_paths)
                return
            except subprocess.CalledProcessError:
                shutil.rmtree(destination, ignore_errors=True)

        fallback_cmd = ["git", "clone", "--depth", "1"]
        if ref:
            fallback_cmd.extend(["--branch", ref, "--single-branch"])
        fallback_cmd.extend([clone_url, str(destination)])
        _run_clone(fallback_cmd)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"repository clone timed out after {timeout}s: {repo_url}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise RuntimeError(f"repository clone failed: {stderr or repo_url}") from exc


def _repo_name_from_url(repo_url: str) -> str | None:
    """Extract a best-effort repository name from a URL or SSH git URL."""
    parsed = urlparse(repo_url)
    if parsed.scheme in {"http", "https", "ssh"} and parsed.path:
        name = Path(parsed.path).name
        return name.removesuffix(".git") or None
    if repo_url.startswith("git@") and ":" in repo_url:
        path = repo_url.split(":", 1)[1]
        name = Path(path).name
        return name.removesuffix(".git") or None
    return None


def _github_repo_from_url(repo_url: str) -> tuple[str, str] | None:
    """Return ``(owner, repo)`` for GitHub repo URLs when parseable."""
    parsed = urlparse(repo_url)
    repo_path = ""
    if parsed.scheme in {"http", "https", "ssh"} and parsed.netloc == "github.com":
        repo_path = parsed.path.strip("/")
    elif repo_url.startswith("git@github.com:"):
        repo_path = repo_url.split(":", 1)[1].strip("/")

    parts = [segment for segment in repo_path.split("/") if segment]
    if len(parts) < 2:
        return None

    owner = parts[0]
    repo = parts[1].removesuffix(".git")
    if not owner or not repo:
        return None
    return owner, repo


def _normalize_repo_path(repo_path: str | None) -> str:
    """Normalize repository-relative paths used for remote GitHub probes."""
    normalized_repo_path = (repo_path or "").strip().strip("/")
    if normalized_repo_path in {"", "."}:
        return ""
    return normalized_repo_path


def _fetch_repo_contents_payload(
    repo_url: str,
    repo_path: str | None = None,
    ref: str | None = None,
    timeout: int = 60,
) -> dict | list | None:
    """Fetch GitHub contents API payload for a repo path when possible."""
    repo_coords = _github_repo_from_url(repo_url)
    if repo_coords is None:
        return None

    normalized_repo_path = _normalize_repo_path(repo_path)
    owner, repo = repo_coords
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
    if normalized_repo_path:
        api_url = f"{api_url}/{quote(normalized_repo_path, safe='/')}"
    if ref:
        api_url = f"{api_url}?ref={quote(ref, safe='')}"

    request = Request(
        api_url,
        headers={
            "Accept": "application/vnd.github.object",
            "User-Agent": "ansible-role-doc",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (
        HTTPError,
        URLError,
        OSError,
        TimeoutError,
        ValueError,
        json.JSONDecodeError,
    ):
        return None


def _fetch_repo_directory_names(
    repo_url: str,
    repo_path: str | None = None,
    ref: str | None = None,
    timeout: int = 60,
) -> set[str] | None:
    """Fetch directory names for a GitHub repo path when possible."""
    payload = _fetch_repo_contents_payload(
        repo_url,
        repo_path=repo_path,
        ref=ref,
        timeout=timeout,
    )
    if not isinstance(payload, list):
        return None

    dir_names: set[str] = set()
    for entry in payload:
        if not isinstance(entry, dict) or entry.get("type") != "dir":
            continue
        name = entry.get("name")
        if isinstance(name, str) and name:
            dir_names.add(name)
    return dir_names


def _repo_path_looks_like_role(dir_names: set[str] | None) -> bool:
    """Return True when a directory listing looks like a useful role source."""
    if not dir_names:
        return False

    role_markers = _ROLE_MARKER_DIRS & dir_names
    return "tasks" in role_markers and len(role_markers) >= _MIN_ROLE_MARKER_DIRS


def _fetch_repo_file(
    repo_url: str,
    repo_path: str | None,
    destination: Path,
    ref: str | None = None,
    timeout: int = 60,
) -> Path | None:
    """Fetch a single file from GitHub into ``destination`` when possible.

    Returns ``None`` for unsupported hosts or when the remote fetch fails so
    callers can fall back to clone-based resolution.
    """
    normalized_repo_path = _normalize_repo_path(repo_path)
    if not normalized_repo_path:
        return None

    payload = _fetch_repo_contents_payload(
        repo_url,
        repo_path=normalized_repo_path,
        ref=ref,
        timeout=timeout,
    )
    if not isinstance(payload, dict):
        return None

    if payload.get("type") != "file":
        return None

    content = payload.get("content")
    encoding = payload.get("encoding")
    if not isinstance(content, str) or encoding != "base64":
        return None

    try:
        decoded = base64.b64decode(content)
    except ValueError:
        return None

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(decoded)
    return destination


def _build_sparse_clone_paths(
    repo_role_path: str,
    repo_style_readme_path: str | None,
) -> list[str]:
    """Build sparse checkout targets for repo-based scans.

    Returns an empty list when sparse checkout would not reduce scope.
    """
    role_path = (repo_role_path or ".").strip()
    if role_path in {"", "."}:
        return []

    paths = [role_path]
    if repo_style_readme_path and repo_style_readme_path.strip():
        paths.append(repo_style_readme_path.strip())

    deduped: list[str] = []
    seen: set[str] = set()
    for path in paths:
        if path not in seen:
            deduped.append(path)
            seen.add(path)
    return deduped


def _save_style_comparison_artifacts(
    style_readme_path: str | None,
    generated_output: str,
    style_source_name: str | None = None,
    role_config_path: str | None = None,
    keep_unknown_style_sections: bool = False,
) -> tuple[str | None, str | None]:
    """Save source/demo comparison artifacts beside generated output."""
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

    # Include the role-level README config beside demo artifacts when available.
    if role_config_path:
        cfg_source = Path(role_config_path)
        if cfg_source.is_file():
            if cfg_source.resolve() != cfg_destination.resolve():
                shutil.copyfile(cfg_source, cfg_destination)
            return str(source_destination.resolve()), str(demo_destination.resolve())

    # If a role config is not present, synthesize a source-of-truth config sample
    # showing unknown style headings captured from the style guide.
    parsed = parse_style_readme(str(source))
    unknown_sections: list[dict[str, str]] = []
    seen_keys: set[str] = set()
    total_chars = 0
    truncated_any = False

    for section in parsed.get("sections", []):
        if section.get("id") != "unknown":
            continue
        if len(unknown_sections) >= _CAPTURE_MAX_SECTIONS:
            truncated_any = True
            break

        title = str(section.get("title") or "").strip()
        key = re.sub(r"\\s+", " ", title).lower()
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)

        body = str(section.get("body") or "").strip()
        body = _sanitize_captured_content(body)
        body, truncated_one = _truncate_content(body, _CAPTURE_MAX_CONTENT_CHARS)
        if truncated_one:
            truncated_any = True

        proposed_chars = total_chars + len(title) + len(body)
        if proposed_chars > _CAPTURE_MAX_TOTAL_CHARS:
            remaining = max(0, _CAPTURE_MAX_TOTAL_CHARS - total_chars - len(title))
            body, _ = _truncate_content(body, remaining)
            truncated_any = True

        unknown_sections.append({"title": title, "content": body})
        total_chars += len(title) + len(body)

        if total_chars >= _CAPTURE_MAX_TOTAL_CHARS:
            break

    unknown_sections.sort(key=lambda row: row["title"].lower())

    payload = {
        "readme": {
            "capture_metadata": {
                "schema_version": _CAPTURE_SCHEMA_VERSION,
                "captured_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "style_source_path": str(source),
                "truncated": truncated_any,
            },
            "unknown_style_sections": unknown_sections,
        }
    }
    cfg_lines = [
        "# Auto-generated sample: promote this file into the role as .ansible_role_doc.yml",
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


def main(argv=None) -> int:
    """CLI entrypoint.

    ``argv`` may be provided for testing; returns an exit code integer.
    """
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.role_path and args.repo_url:
        print(
            "Error: provide either role_path or --repo-url, not both", file=sys.stderr
        )
        return 2
    if not args.role_path and not args.repo_url:
        print("Error: provide role_path or --repo-url", file=sys.stderr)
        return 2

    try:
        if args.repo_url:
            with tempfile.TemporaryDirectory(prefix="ansible-role-doc-") as tmp_dir:
                checkout_dir = Path(tmp_dir) / "repo"
                repo_dir_names = _fetch_repo_directory_names(
                    args.repo_url,
                    repo_path=args.repo_role_path,
                    ref=args.repo_ref,
                    timeout=args.repo_timeout,
                )
                if repo_dir_names is not None and not _repo_path_looks_like_role(
                    repo_dir_names
                ):
                    raise FileNotFoundError(
                        "repository path does not look like an Ansible role: "
                        f"{args.repo_role_path}"
                    )
                fetched_repo_style_readme_path = None
                if args.repo_style_readme_path:
                    fetched_repo_style_readme_path = _fetch_repo_file(
                        args.repo_url,
                        args.repo_style_readme_path,
                        Path(tmp_dir)
                        / "repo-style-readme"
                        / Path(args.repo_style_readme_path).name,
                        ref=args.repo_ref,
                        timeout=args.repo_timeout,
                    )
                if args.verbose:
                    print(f"Cloning: {args.repo_url}")
                _clone_repo(
                    args.repo_url,
                    checkout_dir,
                    args.repo_ref,
                    args.repo_timeout,
                    sparse_paths=_build_sparse_clone_paths(
                        args.repo_role_path,
                        (
                            None
                            if fetched_repo_style_readme_path is not None
                            else args.repo_style_readme_path
                        ),
                    ),
                )
                role_path = (checkout_dir / args.repo_role_path).resolve()
                if not role_path.exists() or not role_path.is_dir():
                    raise FileNotFoundError(
                        f"role path not found in cloned repository: {args.repo_role_path}"
                    )
                style_readme_path = args.style_readme
                if fetched_repo_style_readme_path is not None:
                    style_readme_path = str(fetched_repo_style_readme_path.resolve())
                elif args.repo_style_readme_path:
                    style_readme_path = str(
                        (checkout_dir / args.repo_style_readme_path).resolve()
                    )
                if args.create_style_guide and not style_readme_path:
                    style_readme_path = (
                        args.style_source or resolve_default_style_guide_source()
                    )
                outpath = run_scan(
                    str(role_path),
                    output=args.output,
                    template=args.template,
                    output_format=args.format,
                    compare_role_path=args.compare_role_path,
                    style_readme_path=style_readme_path,
                    role_name_override=_repo_name_from_url(args.repo_url),
                    vars_seed_paths=args.vars_seed,
                    concise_readme=args.concise_readme,
                    scanner_report_output=args.scanner_report_output,
                    include_vars_main=args.variable_sources == "defaults+vars",
                    include_scanner_report_link=args.include_scanner_report_link,
                    readme_config_path=args.readme_config,
                    adopt_style_headings=args.adopt_style_headings,
                    style_guide_skeleton=args.create_style_guide,
                    keep_unknown_style_sections=args.keep_unknown_style_sections,
                    exclude_path_patterns=args.exclude_path,
                    style_source_path=args.style_source,
                    policy_config_path=args.policy_config,
                    dry_run=args.dry_run,
                )
                if args.dry_run:
                    print(outpath, end="")
                    style_source_path, style_demo_path = (None, None)
                else:
                    effective_readme_config_path = args.readme_config
                    if not effective_readme_config_path:
                        default_cfg = role_path / ".ansible_role_doc.yml"
                        if default_cfg.is_file():
                            effective_readme_config_path = str(default_cfg)
                    style_source_path, style_demo_path = (
                        _save_style_comparison_artifacts(
                            style_readme_path,
                            outpath,
                            _repo_name_from_url(args.repo_url),
                            effective_readme_config_path,
                            args.keep_unknown_style_sections,
                        )
                    )
        else:
            style_readme_path = args.style_readme
            if args.create_style_guide and not style_readme_path:
                style_readme_path = (
                    args.style_source or resolve_default_style_guide_source()
                )
            outpath = run_scan(
                args.role_path,
                output=args.output,
                template=args.template,
                output_format=args.format,
                compare_role_path=args.compare_role_path,
                style_readme_path=style_readme_path,
                vars_seed_paths=args.vars_seed,
                concise_readme=args.concise_readme,
                scanner_report_output=args.scanner_report_output,
                include_vars_main=args.variable_sources == "defaults+vars",
                include_scanner_report_link=args.include_scanner_report_link,
                readme_config_path=args.readme_config,
                adopt_style_headings=args.adopt_style_headings,
                style_guide_skeleton=args.create_style_guide,
                keep_unknown_style_sections=args.keep_unknown_style_sections,
                exclude_path_patterns=args.exclude_path,
                style_source_path=args.style_source,
                policy_config_path=args.policy_config,
                dry_run=args.dry_run,
            )
            if args.dry_run:
                print(outpath, end="")
                style_source_path, style_demo_path = (None, None)
            else:
                effective_readme_config_path = args.readme_config
                if not effective_readme_config_path:
                    default_cfg = Path(args.role_path) / ".ansible_role_doc.yml"
                    if default_cfg.is_file():
                        effective_readme_config_path = str(default_cfg)
                style_source_path, style_demo_path = _save_style_comparison_artifacts(
                    args.style_readme,
                    outpath,
                    role_config_path=effective_readme_config_path,
                    keep_unknown_style_sections=args.keep_unknown_style_sections,
                )
        if args.verbose:
            if args.dry_run:
                print("\nDry run: no files written.")
            else:
                print("Wrote:", outpath)
            if style_source_path:
                print("Style guide source:", style_source_path)
            if style_demo_path:
                print("Generated demo copy:", style_demo_path)
        return 0
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
