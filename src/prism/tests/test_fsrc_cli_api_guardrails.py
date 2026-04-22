"""fsrc-lane guardrails: CLI/API facade import boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FSRC_RUNTIME_DIR = PROJECT_ROOT / "src" / "prism"


def _module_name_for_path(
    module_path: Path,
    *,
    package_name: str,
    package_dir: Path,
) -> str:
    if package_name != "prism" and not package_name.startswith("prism."):
        raise ValueError(
            "package_name must be prism or use the fully qualified Prism package name"
        )

    package_root = Path(*package_name.split("."))
    stem = module_path.with_suffix("")
    try:
        rel = stem.relative_to(PROJECT_ROOT / "src" / package_root)
        parts = package_name.split(".") + list(rel.parts)
    except ValueError:
        rel = stem.relative_to(package_dir)
        parts = package_name.split(".") + list(rel.parts)

    if stem.name == "__init__":
        return ".".join(parts[:-1])
    return ".".join(parts)


def _resolve_import_from(module_name: str, node: ast.ImportFrom) -> str | None:
    if node.module is None:
        return None
    if node.level <= 0:
        return node.module

    module_parts = module_name.split(".")
    if module_name.endswith(".__init__"):
        module_parts = module_parts[:-1]
    keep = max(0, len(module_parts) - node.level)
    prefix = ".".join(module_parts[:keep])
    return f"{prefix}.{node.module}" if prefix else node.module


def _iter_package_modules(package_dir: Path) -> list[Path]:
    return sorted(package_dir.rglob("*.py"))


def _iter_forbidden_import_offenders(
    *,
    package_dir: Path,
    package_name: str,
    forbidden_roots: tuple[str, ...],
    allowed_import_pairs: tuple[tuple[str, str], ...] = (),
) -> list[str]:
    offenders: list[str] = []

    for module_path in _iter_package_modules(package_dir):
        if "tests" in module_path.parts:
            continue
        module_name = _module_name_for_path(
            module_path,
            package_name=package_name,
            package_dir=package_dir,
        )
        tree = ast.parse(module_path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
                    if (module_name, target) in allowed_import_pairs:
                        continue
                    if any(
                        target == root or target.startswith(f"{root}.")
                        for root in forbidden_roots
                    ):
                        offenders.append(f"{module_name}:{target}")
            if isinstance(node, ast.ImportFrom):
                resolved_target = _resolve_import_from(module_name, node)
                if not resolved_target:
                    continue
                if (module_name, resolved_target) in allowed_import_pairs:
                    continue
                if any(
                    resolved_target == root or resolved_target.startswith(f"{root}.")
                    for root in forbidden_roots
                ):
                    offenders.append(f"{module_name}:{resolved_target}")

    return sorted(set(offenders))


def test_fsrc_runtime_modules_do_not_import_src_facade_packages() -> None:
    offenders = _iter_forbidden_import_offenders(
        package_dir=FSRC_RUNTIME_DIR,
        package_name="prism",
        forbidden_roots=(
            "prism.api_layer",
            "prism.cli_app",
            "prism.repo_layer",
            "prism.repo_services",
        ),
        allowed_import_pairs=(("prism.api", "prism.api_layer"),),
    )

    assert (
        not offenders
    ), "fsrc runtime modules import src facade packages: " + ", ".join(offenders)


def test_fsrc_cross_path_guardrail_detects_facade_import(tmp_path: Path) -> None:
    package_dir = tmp_path / "prism"
    package_dir.mkdir()
    module_path = package_dir / "cli.py"
    module_path.write_text(
        "from prism.cli_app.commands import build_parser\n", encoding="utf-8"
    )

    offenders = _iter_forbidden_import_offenders(
        package_dir=package_dir,
        package_name="prism",
        forbidden_roots=("prism.cli_app",),
    )

    assert offenders == ["prism.cli:prism.cli_app.commands"]
