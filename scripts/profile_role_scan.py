#!/usr/bin/env python3
"""Run repeatable local Prism role-scan timing and profiling baselines."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PYTHON = ROOT / ".venv" / "bin" / "python"
DEFAULT_OUTPUT_DIR = ROOT / "debug_readmes" / "profiles"
DEFAULT_FIXTURES: dict[str, Path] = {
    "mock_role": ROOT / "src" / "prism" / "tests" / "mock_role",
    "enhanced_mock_role": ROOT / "src" / "prism" / "tests" / "enhanced_mock_role",
    "comment_driven_demo_role": (
        ROOT / "src" / "prism" / "tests" / "roles" / "comment_driven_demo_role"
    ),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure Prism CLI role-scan timings against stable local fixtures.",
    )
    parser.add_argument(
        "--fixture",
        action="append",
        choices=sorted(DEFAULT_FIXTURES),
        help="Fixture name to profile. Repeat to select multiple fixtures.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of dry-run timing iterations per fixture (default: 3).",
    )
    parser.add_argument(
        "--python-command",
        default=str(DEFAULT_PYTHON),
        help="Python executable used to run Prism CLI.",
    )
    parser.add_argument(
        "--detailed-catalog",
        action="store_true",
        help="Include --detailed-catalog in the measured role scan.",
    )
    parser.add_argument(
        "--profile-fixture",
        choices=sorted(DEFAULT_FIXTURES),
        default=None,
        help="Fixture to profile with cProfile in addition to timing.",
    )
    parser.add_argument(
        "--profile-output",
        default=None,
        help="Explicit cProfile output path. Defaults under debug_readmes/profiles/.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a markdown table.",
    )
    return parser


def _python_command(path: str) -> str:
    return str(Path(path).expanduser())


def _base_env() -> dict[str, str]:
    env = dict(os.environ)
    src_path = str(ROOT / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{src_path}:{existing_pythonpath}" if existing_pythonpath else src_path
    )
    return env


def _build_cli_args(
    fixture_path: Path,
    *,
    detailed_catalog: bool,
) -> list[str]:
    args = [
        "role",
        str(fixture_path),
        "--dry-run",
        "-o",
        str(ROOT / "debug_readmes" / "profiles" / f"{fixture_path.name}.md"),
    ]
    if detailed_catalog:
        args.append("--detailed-catalog")
    return args


def _run_role_scan(
    python_command: str,
    fixture_path: Path,
    *,
    detailed_catalog: bool,
) -> float:
    cmd = [
        python_command,
        "-m",
        "prism.cli",
        *_build_cli_args(fixture_path, detailed_catalog=detailed_catalog),
    ]
    started = time.perf_counter()
    subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=_base_env(),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return time.perf_counter() - started


def _profile_role_scan(
    python_command: str,
    fixture_path: Path,
    *,
    detailed_catalog: bool,
    profile_output: Path,
) -> None:
    profile_output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        python_command,
        "-m",
        "cProfile",
        "-o",
        str(profile_output),
        "-m",
        "prism.cli",
        *_build_cli_args(fixture_path, detailed_catalog=detailed_catalog),
    ]
    subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=_base_env(),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def _summarize_measurements(values: list[float]) -> dict[str, float]:
    return {
        "min_seconds": min(values),
        "mean_seconds": statistics.mean(values),
        "max_seconds": max(values),
    }


def _render_markdown(
    *,
    python_command: str,
    iterations: int,
    detailed_catalog: bool,
    rows: list[dict[str, object]],
    profile_output: Path | None,
) -> str:
    scenario = (
        "role --dry-run --detailed-catalog" if detailed_catalog else "role --dry-run"
    )
    lines = [
        f"Python: `{python_command}`",
        f"Iterations: `{iterations}`",
        f"Scenario: `{scenario}`",
        "",
        "| Fixture | Min (s) | Mean (s) | Max (s) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {fixture} | {min:.4f} | {mean:.4f} | {max:.4f} |".format(
                fixture=row["fixture"],
                min=row["min_seconds"],
                mean=row["mean_seconds"],
                max=row["max_seconds"],
            )
        )
    if profile_output is not None:
        lines.extend(
            [
                "",
                f"cProfile artifact: `{profile_output}`",
            ]
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    python_command = _python_command(args.python_command)
    fixtures = args.fixture or list(DEFAULT_FIXTURES)
    rows: list[dict[str, object]] = []

    for fixture_name in fixtures:
        fixture_path = DEFAULT_FIXTURES[fixture_name]
        measurements = [
            _run_role_scan(
                python_command,
                fixture_path,
                detailed_catalog=args.detailed_catalog,
            )
            for _ in range(args.iterations)
        ]
        rows.append(
            {
                "fixture": fixture_name,
                **_summarize_measurements(measurements),
            }
        )

    profile_output: Path | None = None
    if args.profile_fixture is not None:
        profile_output = (
            Path(args.profile_output).expanduser()
            if args.profile_output is not None
            else DEFAULT_OUTPUT_DIR
            / f"{args.profile_fixture}-{'detailed' if args.detailed_catalog else 'default'}.prof"
        )
        _profile_role_scan(
            python_command,
            DEFAULT_FIXTURES[args.profile_fixture],
            detailed_catalog=args.detailed_catalog,
            profile_output=profile_output,
        )

    if args.json:
        payload = {
            "python_command": python_command,
            "iterations": args.iterations,
            "detailed_catalog": args.detailed_catalog,
            "rows": rows,
            "profile_output": str(profile_output) if profile_output else None,
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(
        _render_markdown(
            python_command=python_command,
            iterations=args.iterations,
            detailed_catalog=args.detailed_catalog,
            rows=rows,
            profile_output=profile_output,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
