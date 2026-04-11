"""Import-style guardrails for production Prism modules."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = PROJECT_ROOT / "src" / "prism"
FSRC_RUNTIME_ROOT = PROJECT_ROOT / "fsrc" / "src" / "prism"
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


def test_hardcoded_path_token_guardrail_detects_src_root_token(tmp_path: Path) -> None:
    module_root = tmp_path / "prism"
    module_root.mkdir()
    module_path = module_root / "api.py"
    module_path.write_text('SRC = "src/prism"\n', encoding="utf-8")

    offenders = _iter_hardcoded_path_token_offenders(
        module_root=module_root,
        forbidden_tokens=("src/prism",),
    )

    assert offenders == ["prism/api.py:1: src/prism"]


def test_hardcoded_path_token_guardrail_ignores_test_modules(tmp_path: Path) -> None:
    module_root = tmp_path / "prism"
    tests_dir = module_root / "tests"
    tests_dir.mkdir(parents=True)
    test_module = tests_dir / "test_tokens.py"
    test_module.write_text('SRC = "src/prism"\n', encoding="utf-8")

    offenders = _iter_hardcoded_path_token_offenders(
        module_root=module_root,
        forbidden_tokens=("src/prism",),
    )

    assert offenders == []
