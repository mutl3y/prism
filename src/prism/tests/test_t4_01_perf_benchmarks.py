"""T4-01: Performance benchmark suite (pytest-benchmark).

Three scenarios:
  * single-file YAML parse
  * small role end-to-end scan (demos/fixtures/role_demo)
  * large synthetic role scan (100 task files)

Run with::

    pytest src/prism/tests/test_t4_01_perf_benchmarks.py \\
        --benchmark-only --benchmark-json=.benchmarks/results.json

Skipped when pytest-benchmark is not installed so default test runs stay
fast and dependency-light.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

pytest.importorskip("pytest_benchmark")

# Skip the benchmark suite unless explicitly requested. The fixtures touch the
# real filesystem and can be perturbed when other test modules in the run
# enable pyfakefs.
if os.environ.get("PRISM_RUN_BENCHMARKS") != "1":
    pytest.skip(
        "Benchmark suite skipped by default; set PRISM_RUN_BENCHMARKS=1 "
        "(or run this module directly) to exercise it.",
        allow_module_level=True,
    )

REPO_ROOT = Path(__file__).resolve().parents[3]
ROLE_DEMO = REPO_ROOT / "demos" / "fixtures" / "role_demo"


@pytest.fixture()
def small_role(tmp_path) -> Path:
    if not ROLE_DEMO.exists():
        pytest.skip("role_demo fixture not available")
    target = tmp_path / "role"
    shutil.copytree(ROLE_DEMO, target)
    return target


@pytest.fixture()
def large_synthetic_role(tmp_path) -> Path:
    base = tmp_path / "role"
    (base / "tasks").mkdir(parents=True)
    (base / "defaults").mkdir(parents=True)
    (base / "defaults" / "main.yml").write_text("---\nfoo: bar\n", encoding="utf-8")
    main = ["---"]
    for i in range(100):
        task_file = base / "tasks" / f"task_{i:03d}.yml"
        task_file.write_text(
            "---\n"
            f"- name: task {i}\n"
            "  ansible.builtin.debug:\n"
            f"    msg: 'hello {{{{ foo }}}} #{i}'\n",
            encoding="utf-8",
        )
        main.append(f"- import_tasks: task_{i:03d}.yml")
    (base / "tasks" / "main.yml").write_text("\n".join(main) + "\n", encoding="utf-8")
    return base


def test_bench_single_file_yaml_parse(benchmark, small_role) -> None:
    from prism.scanner_io.loader import parse_yaml_candidate

    target = small_role / "tasks" / "main.yml"
    benchmark(parse_yaml_candidate, target, small_role)


def test_bench_small_role_scan(benchmark, small_role) -> None:
    from prism import api

    def _run() -> None:
        api.scan_role(str(small_role))

    benchmark(_run)


def test_bench_large_role_scan(benchmark, large_synthetic_role) -> None:
    from prism import api

    def _run() -> None:
        api.scan_role(str(large_synthetic_role))

    benchmark.pedantic(_run, rounds=3, iterations=1)
