"""Import-style guardrails for production Prism modules."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = PROJECT_ROOT / "src" / "prism"


def test_production_modules_do_not_use_relative_imports() -> None:
    """Keep production imports explicit via absolute `prism.*` imports."""
    offenders: list[str] = []

    for module_path in sorted(SOURCE_ROOT.rglob("*.py")):
        if "tests" in module_path.parts:
            continue
        for line_number, line in enumerate(
            module_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            stripped = line.strip()
            if stripped.startswith("from ."):
                offenders.append(
                    f"{module_path.relative_to(PROJECT_ROOT)}:{line_number}: {stripped}"
                )

    assert (
        not offenders
    ), "Production modules must not use relative imports:\n" + "\n".join(offenders)
