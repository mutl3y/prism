"""Canonical-lane guardrails: hardcoded path-token checks."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_ROOT = PROJECT_ROOT / "src" / "prism"
FORBIDDEN_PATH_TOKENS = (
    "fsrc/",
    "fsrc\\",
    "fsrc/prism_next",
    "/fsrc/",
    "\\fsrc\\",
)


def _iter_hardcoded_path_token_offenders(
    *,
    module_root: Path,
    forbidden_tokens: tuple[str, ...],
) -> list[str]:
    offenders: list[str] = []

    def _display_path(path: Path) -> str:
        try:
            return str(path.relative_to(PROJECT_ROOT))
        except ValueError:
            return str(path.relative_to(module_root.parent))

    for module_path in sorted(module_root.rglob("*.py")):
        if "tests" in module_path.parts:
            continue
        lines = module_path.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            for token in forbidden_tokens:
                if token in line:
                    offenders.append(
                        f"{_display_path(module_path)}:{line_number}: {token}"
                    )

    return sorted(set(offenders))


def test_canonical_runtime_modules_do_not_contain_retired_lane_path_tokens() -> None:
    offenders = _iter_hardcoded_path_token_offenders(
        module_root=RUNTIME_ROOT,
        forbidden_tokens=FORBIDDEN_PATH_TOKENS,
    )

    assert not offenders, (
        "Canonical runtime modules include retired fsrc-lane path tokens:\n"
        + "\n".join(offenders)
    )
