#!/usr/bin/env python3
"""Generate prism demo outputs in small observable steps.

This helper prepares stable role/collection fixtures under debug_readmes/ and then
runs one or more CLI scenarios locally. It is designed so each scenario can be
invoked independently from a terminal or VS Code task, which avoids large
hard-to-observe shell scripts.

Containerized Podman workflows moved to the companion project:
https://github.com/mutl3y/prism-learn
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "debug_readmes" / "option_demos"
ENHANCED_ROLE_SOURCE = ROOT / "src" / "prism" / "tests" / "roles" / "enhanced_mock_role"
BASE_ROLE_SOURCE = ROOT / "src" / "prism" / "tests" / "roles" / "base_mock_role"
DEFAULT_LOCAL_PYTHON = ROOT / ".venv" / "bin" / "python"
DEFAULT_LANE = "src"
DEFAULT_CONTAINER_PYTHON = "/workspace/.venv/bin/python"
DEFAULT_SERVICE = "learning-base"
DEFAULT_COMPOSE_FILE = ROOT / "podman-compose.yml"
DEFAULT_ENV_FILE = ROOT / ".env.podman"


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    output_path: str
    uses_pdf: bool = False

    def build_args(self, output_dir: Path) -> list[str]:
        role_demo = output_dir / "enhanced_role_demo"
        collection_demo = output_dir / "demo_collection"
        role_readme = role_demo / "README.md"
        output_path = output_dir / self.output_path
        mapping: dict[str, list[str]] = {
            "role-default": ["role", str(role_demo), "-o", str(output_path)],
            "role-concise": [
                "role",
                str(role_demo),
                "--concise-readme",
                "-o",
                str(output_path),
            ],
            "role-detailed-catalog": [
                "role",
                str(role_demo),
                "--detailed-catalog",
                "-o",
                str(output_path),
            ],
            "role-styled": [
                "role",
                str(role_demo),
                "--style-readme",
                str(role_readme),
                "-o",
                str(output_path),
            ],
            "role-html": ["role", str(role_demo), "-f", "html", "-o", str(output_path)],
            "role-json": ["role", str(role_demo), "-f", "json", "-o", str(output_path)],
            "role-pdf": ["role", str(role_demo), "-f", "pdf", "-o", str(output_path)],
            "collection-md": [
                "collection",
                str(collection_demo),
                "-f",
                "md",
                "-o",
                str(output_path),
            ],
            "collection-json": [
                "collection",
                str(collection_demo),
                "-f",
                "json",
                "-o",
                str(output_path),
            ],
        }
        return mapping[self.name]


SCENARIOS = [
    Scenario("role-default", "Full markdown role README", "default.md"),
    Scenario(
        "role-concise", "Concise markdown README with sidecar report", "concise.md"
    ),
    Scenario(
        "role-detailed-catalog",
        "Markdown README with task and handler catalogs",
        "detailed-catalog.md",
    ),
    Scenario(
        "role-styled", "Markdown README rendered with fixture README style", "styled.md"
    ),
    Scenario("role-html", "HTML render of the enhanced role", "default.html"),
    Scenario("role-json", "JSON payload for the enhanced role", "default.json"),
    Scenario(
        "role-pdf", "PDF render of the enhanced role", "default.pdf", uses_pdf=True
    ),
    Scenario(
        "collection-md", "Collection markdown with per-role docs", "collection.md"
    ),
    Scenario("collection-json", "Collection JSON payload", "collection.json"),
]
SCENARIO_INDEX = {scenario.name: scenario for scenario in SCENARIOS}
DEFAULT_SCENARIOS = [
    "role-default",
    "role-concise",
    "role-detailed-catalog",
    "role-styled",
    "role-html",
    "role-json",
    "collection-md",
    "collection-json",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate comparable prism demo outputs.",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        choices=sorted(SCENARIO_INDEX),
        help="Scenario to run. Repeat to run multiple scenarios. Defaults to the standard comparison set.",
    )
    parser.add_argument(
        "--runtime",
        choices=("local", "podman"),
        default="local",
        help="Where to run the CLI: local virtualenv or Podman learning-base container.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where demo artifacts are written.",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Prepare the demo fixtures and stop without running any scenarios.",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Reuse any existing prepared fixtures instead of recreating them.",
    )
    parser.add_argument(
        "--start-stack",
        action="store_true",
        help="When using --runtime podman, start postgres and learning-base before running scenarios.",
    )
    parser.add_argument(
        "--compose-file",
        default=str(DEFAULT_COMPOSE_FILE),
        help="Compose file path for Podman runtime.",
    )
    parser.add_argument(
        "--env-file",
        default=str(DEFAULT_ENV_FILE),
        help="Env file used with podman-compose.",
    )
    parser.add_argument(
        "--service",
        default=DEFAULT_SERVICE,
        help="Compose service name used for podman exec.",
    )
    parser.add_argument(
        "--python-command",
        default=None,
        help="Explicit Python command to use inside the selected runtime.",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List scenarios and exit.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue through later scenarios after a failure.",
    )
    parser.add_argument(
        "--lane",
        choices=("src",),
        default=DEFAULT_LANE,
        help="Which source lane to run against.",
    )
    return parser


def _run(
    cmd: list[str], *, cwd: Path, lane: str = DEFAULT_LANE
) -> subprocess.CompletedProcess[str]:
    printable = " ".join(cmd)
    print(f"$ {printable}", flush=True)
    env = dict(os.environ)
    lane_path = str(ROOT / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{lane_path}:{existing_pythonpath}" if existing_pythonpath else lane_path
    )
    return subprocess.run(cmd, cwd=str(cwd), check=True, text=True, env=env)


def prepare_output_tree(output_dir: Path, *, keep_existing: bool) -> None:
    role_demo = output_dir / "enhanced_role_demo"
    collection_demo = output_dir / "demo_collection"

    output_dir.mkdir(parents=True, exist_ok=True)
    if not keep_existing:
        shutil.rmtree(role_demo, ignore_errors=True)
        shutil.rmtree(collection_demo, ignore_errors=True)

    if not role_demo.exists():
        shutil.copytree(ENHANCED_ROLE_SOURCE, role_demo)

    collection_roles_dir = collection_demo / "roles"
    collection_roles_dir.mkdir(parents=True, exist_ok=True)
    base_target = collection_roles_dir / "base_mock_role"
    enhanced_target = collection_roles_dir / "enhanced_mock_role"
    if not base_target.exists():
        shutil.copytree(BASE_ROLE_SOURCE, base_target)
    if not enhanced_target.exists():
        shutil.copytree(ENHANCED_ROLE_SOURCE, enhanced_target)

    filter_dir = collection_demo / "plugins" / "filter"
    lookup_dir = collection_demo / "plugins" / "lookup"
    filter_dir.mkdir(parents=True, exist_ok=True)
    lookup_dir.mkdir(parents=True, exist_ok=True)
    (filter_dir / "network.py").write_text(
        '"""Network filter helpers for demo output."""\n\n'
        "class FilterModule:\n"
        "    def filters(self):\n"
        "        return {\n"
        '            "cidr_contains": cidr_contains,\n'
        '            "ip_version": ip_version,\n'
        "        }\n",
        encoding="utf-8",
    )
    (lookup_dir / "vault_lookup.py").write_text(
        "DOCUMENTATION = '''\\n"
        "---\\n"
        "short_description: demo lookup plugin\\n"
        "'''\\n",
        encoding="utf-8",
    )

    galaxy_yml = collection_demo / "galaxy.yml"
    galaxy_yml.write_text(
        "namespace: demo\n" "name: docsuite\n" "version: 1.0.0\n" "readme: README.md\n",
        encoding="utf-8",
    )


def _local_python_command(explicit: str | None) -> str:
    if explicit:
        return explicit
    if DEFAULT_LOCAL_PYTHON.is_file():
        return str(DEFAULT_LOCAL_PYTHON)
    return shutil.which("python3") or shutil.which("python") or "python3"


def _compose_base(compose_file: Path, env_file: Path) -> list[str]:
    return [
        "podman-compose",
        "-f",
        str(compose_file),
        "--env-file",
        str(env_file),
    ]


def _podman_python_command(explicit: str | None) -> str:
    return explicit or DEFAULT_CONTAINER_PYTHON


def _pdf_available_local(python_command: str) -> bool:
    return (
        subprocess.run(
            [
                python_command,
                "-c",
                "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('weasyprint') else 1)",
            ],
            cwd=str(ROOT),
            check=False,
            text=True,
        ).returncode
        == 0
    )


def _pdf_available_podman(
    compose_file: Path,
    env_file: Path,
    service: str,
    python_command: str,
) -> bool:
    command = _compose_base(compose_file, env_file) + [
        "exec",
        "-T",
        service,
        python_command,
        "-c",
        "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('weasyprint') else 1)",
    ]
    return (
        subprocess.run(command, cwd=str(ROOT), check=False, text=True).returncode == 0
    )


def run_local_scenarios(
    output_dir: Path,
    scenarios: list[Scenario],
    python_command: str,
    continue_on_error: bool,
    lane: str = DEFAULT_LANE,
) -> int:
    failures = 0
    for scenario in scenarios:
        if scenario.uses_pdf and not _pdf_available_local(python_command):
            print(
                f"SKIP {scenario.name}: weasyprint is not available in the local environment.",
                flush=True,
            )
            continue
        try:
            _run(
                [
                    python_command,
                    "-m",
                    "prism.cli",
                    *scenario.build_args(output_dir),
                ],
                cwd=ROOT,
                lane=lane,
            )
        except subprocess.CalledProcessError:
            failures += 1
            if not continue_on_error:
                return failures
    return failures


def run_podman_scenarios(
    output_dir: Path,
    scenarios: list[Scenario],
    compose_file: Path,
    env_file: Path,
    service: str,
    python_command: str,
    start_stack: bool,
    continue_on_error: bool,
) -> int:
    if start_stack:
        _run(
            _compose_base(compose_file, env_file) + ["up", "-d", "postgres", service],
            cwd=ROOT,
        )

    failures = 0
    for scenario in scenarios:
        if scenario.uses_pdf and not _pdf_available_podman(
            compose_file, env_file, service, python_command
        ):
            print(
                f"SKIP {scenario.name}: weasyprint is not available in the {service} container.",
                flush=True,
            )
            continue
        container_args = []
        for item in scenario.build_args(output_dir):
            if item.startswith(str(ROOT)):
                container_args.append(item.replace(str(ROOT), "/workspace", 1))
            else:
                container_args.append(item)
        try:
            _run(
                _compose_base(compose_file, env_file)
                + [
                    "exec",
                    "-T",
                    service,
                    python_command,
                    "-m",
                    "prism.cli",
                    *container_args,
                ],
                cwd=ROOT,
            )
        except subprocess.CalledProcessError:
            failures += 1
            if not continue_on_error:
                return failures
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_scenarios:
        for scenario in SCENARIOS:
            print(f"{scenario.name}: {scenario.description}")
        return 0

    output_dir = Path(args.output_dir).resolve()
    prepare_output_tree(output_dir, keep_existing=args.keep_existing)

    selected_names = args.scenario or list(DEFAULT_SCENARIOS)
    scenarios = [SCENARIO_INDEX[name] for name in selected_names]

    print(f"Prepared demo fixtures under {output_dir}", flush=True)
    if args.prepare_only:
        return 0

    if args.runtime == "local":
        failures = run_local_scenarios(
            output_dir,
            scenarios,
            _local_python_command(args.python_command),
            args.continue_on_error,
            lane=args.lane,
        )
    else:
        print(
            "Podman runtime moved to prism-learn. Use local runtime here, or run the containerized workflow from https://github.com/mutl3y/prism-learn.",
            flush=True,
        )
        return 2

    print("Artifacts:", flush=True)
    for scenario in scenarios:
        print(f"- {output_dir / scenario.output_path}", flush=True)
    concise_report = output_dir / "concise.scan-report.md"
    if concise_report.exists():
        print(f"- {concise_report}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
