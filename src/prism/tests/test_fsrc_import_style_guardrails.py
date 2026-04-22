"""fsrc-lane guardrails: hardcoded src-path token checks."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FSRC_RUNTIME_ROOT = PROJECT_ROOT / "src" / "prism"
FSRC_FORBIDDEN_PATH_TOKENS = (
    "src/prism",
    "src\\prism",
    "/src/prism",
    "\\src\\prism",
    "fsrc/prism_next",
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


def test_fsrc_runtime_modules_do_not_contain_hardcoded_src_path_tokens() -> None:
    offenders = _iter_hardcoded_path_token_offenders(
        module_root=FSRC_RUNTIME_ROOT,
        forbidden_tokens=FSRC_FORBIDDEN_PATH_TOKENS,
    )

    assert (
        not offenders
    ), "fsrc runtime modules include hardcoded src-root/path tokens:\n" + "\n".join(
        offenders
    )
