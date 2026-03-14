"""CLI entry point for ansible-role-doc.

Provides a small CLI wrapper around :func:`ansible_role_doc.scanner.run_scan`.
"""

from __future__ import annotations
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlparse
import sys
import tempfile
from .scanner import run_scan


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
        default="defaults+vars",
        help=(
            "Select which role variable files are documented: "
            "'defaults+vars' (default) or 'defaults-only'."
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
        choices=("md", "html"),
        help="Output format (md or html).",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    return p


def _clone_repo(
    repo_url: str,
    destination: Path,
    ref: str | None = None,
    timeout: int = 60,
) -> None:
    """Clone a git repository into ``destination`` with shallow history."""
    parsed = urlparse(repo_url)
    clone_url = repo_url
    if parsed.scheme in {"http", "https"} and parsed.netloc == "github.com":
        repo_path = parsed.path.strip("/")
        if repo_path and repo_path.count("/") >= 1:
            if not repo_path.endswith(".git"):
                repo_path = f"{repo_path}.git"
            clone_url = f"git@github.com:{repo_path}"

    cmd = ["git", "clone", "--depth", "1"]
    if ref:
        cmd.extend(["--branch", ref, "--single-branch"])
    cmd.extend([clone_url, str(destination)])
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env,
        )
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


def _save_style_comparison_artifacts(
    style_readme_path: str | None,
    generated_output: str,
    style_source_name: str | None = None,
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
                if args.verbose:
                    print(f"Cloning: {args.repo_url}")
                _clone_repo(
                    args.repo_url,
                    checkout_dir,
                    args.repo_ref,
                    args.repo_timeout,
                )
                role_path = (checkout_dir / args.repo_role_path).resolve()
                if not role_path.exists() or not role_path.is_dir():
                    raise FileNotFoundError(
                        f"role path not found in cloned repository: {args.repo_role_path}"
                    )
                style_readme_path = args.style_readme
                if args.repo_style_readme_path:
                    style_readme_path = str(
                        (checkout_dir / args.repo_style_readme_path).resolve()
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
                )
                style_source_path, style_demo_path = _save_style_comparison_artifacts(
                    style_readme_path,
                    outpath,
                    _repo_name_from_url(args.repo_url),
                )
        else:
            outpath = run_scan(
                args.role_path,
                output=args.output,
                template=args.template,
                output_format=args.format,
                compare_role_path=args.compare_role_path,
                style_readme_path=args.style_readme,
                vars_seed_paths=args.vars_seed,
                concise_readme=args.concise_readme,
                scanner_report_output=args.scanner_report_output,
                include_vars_main=args.variable_sources == "defaults+vars",
                include_scanner_report_link=args.include_scanner_report_link,
            )
            style_source_path, style_demo_path = _save_style_comparison_artifacts(
                args.style_readme,
                outpath,
            )
        if args.verbose:
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
