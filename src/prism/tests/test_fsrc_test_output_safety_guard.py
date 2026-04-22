"""Guardrails to prevent test output writes to repository root files."""

from __future__ import annotations

import re
from pathlib import Path


def test_fsrc_tests_do_not_use_bare_readme_output_target() -> None:
    tests_dir = Path(__file__).resolve().parent
    pattern = re.compile(r"output\s*=\s*['\"]README\.md['\"]|--output\s+README\.md")

    violations: list[str] = []
    for test_file in sorted(tests_dir.glob("test_fsrc_*.py")):
        lines = test_file.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            if pattern.search(line):
                violations.append(f"{test_file.name}:{line_number}: {line.strip()}")

    assert not violations, (
        "Found bare README output target in fsrc tests. "
        "Use tmp_path / 'README.md' and pass str(path) instead:\n"
        + "\n".join(violations)
    )
