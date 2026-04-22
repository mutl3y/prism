"""fsrc-lane guardrails: scanner package import boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FSRC_RUNTIME_DIR = PROJECT_ROOT / "src" / "prism"


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


def _module_resolves_within_package_dir(
    *,
    module_name: str,
    package_dir: Path,
    package_name: str,
) -> bool:
    if module_name == package_name:
        return (package_dir / "__init__.py").exists()

    package_prefix = f"{package_name}."
    if not module_name.startswith(package_prefix):
        return False

    rel_parts = module_name[len(package_prefix) :].split(".")
    module_file = package_dir.joinpath(*rel_parts).with_suffix(".py")
    package_init = package_dir.joinpath(*rel_parts, "__init__.py")
    return module_file.exists() or package_init.exists()


def _iter_forbidden_import_offenders(
    *,
    package_dir: Path,
    package_name: str,
    forbidden_roots: tuple[str, ...],
) -> list[str]:
    def _is_external_forbidden_target(target: str) -> bool:
        if not any(
            target == root or target.startswith(f"{root}.") for root in forbidden_roots
        ):
            return False
        return not _module_resolves_within_package_dir(
            module_name=target,
            package_dir=package_dir,
            package_name=package_name,
        )

    offenders: list[str] = []

    for module_path in sorted(package_dir.rglob("*.py")):
        if "tests" in module_path.parts:
            continue
        stem = module_path.with_suffix("")
        try:
            rel = stem.relative_to(PROJECT_ROOT / "src")
            if stem.name == "__init__":
                module_name = ".".join(rel.parts[:-1])
            else:
                module_name = ".".join(rel.parts)
        except ValueError:
            rel = stem.relative_to(package_dir)
            parts = package_name.split(".") + list(rel.parts)
            if stem.name == "__init__":
                module_name = ".".join(parts[:-1])
            else:
                module_name = ".".join(parts)

        tree = ast.parse(module_path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
                    if _is_external_forbidden_target(target):
                        offenders.append(f"{module_name}:{target}")
                continue

            if isinstance(node, ast.ImportFrom):
                resolved_target = _resolve_import_from(module_name, node)
                if not resolved_target:
                    continue
                if _is_external_forbidden_target(resolved_target):
                    offenders.append(f"{module_name}:{resolved_target}")

    return sorted(set(offenders))


def test_fsrc_runtime_modules_do_not_import_src_scanner_packages() -> None:
    offenders = _iter_forbidden_import_offenders(
        package_dir=FSRC_RUNTIME_DIR,
        package_name="prism",
        forbidden_roots=(
            "prism.scanner",
            "prism.scanner_core",
            "prism.scanner_extract",
            "prism.scanner_readme",
            "prism.scanner_reporting",
            "prism.scanner_io",
            "prism.scanner_config",
            "prism.scanner_plugins",
            "prism.scanner_kernel",
            "prism.scanner_extensions",
        ),
    )

    assert (
        not offenders
    ), "fsrc runtime modules import src scanner packages: " + ", ".join(offenders)


def test_fsrc_cross_path_guardrail_allows_local_fsrc_scanner_imports(
    tmp_path: Path,
) -> None:
    runtime_dir = tmp_path / "prism"
    runtime_dir.mkdir()
    scanner_core_dir = runtime_dir / "scanner_core"
    scanner_core_dir.mkdir()
    (scanner_core_dir / "__init__.py").write_text("", encoding="utf-8")
    module_path = runtime_dir / "api.py"
    module_path.write_text(
        "from prism.scanner_core import DIContainer\n", encoding="utf-8"
    )

    offenders = _iter_forbidden_import_offenders(
        package_dir=runtime_dir,
        package_name="prism",
        forbidden_roots=("prism.scanner_core",),
    )

    assert offenders == []


def test_fsrc_cross_path_guardrail_detects_src_only_scanner_imports(
    tmp_path: Path,
) -> None:
    runtime_dir = tmp_path / "prism"
    runtime_dir.mkdir()
    module_path = runtime_dir / "api.py"
    module_path.write_text(
        "from prism.scanner_io.output import emit\n", encoding="utf-8"
    )

    offenders = _iter_forbidden_import_offenders(
        package_dir=runtime_dir,
        package_name="prism",
        forbidden_roots=("prism.scanner_io",),
    )

    assert offenders == ["prism.api:prism.scanner_io.output"]


def test_fsrc_cross_path_guardrail_detects_src_only_resolution_when_local_module_absent(
    tmp_path: Path,
) -> None:
    runtime_dir = tmp_path / "prism"
    runtime_dir.mkdir()
    module_path = runtime_dir / "api.py"
    module_path.write_text(
        "from prism.scanner_reporting.report import build_scanner_report_markdown\n",
        encoding="utf-8",
    )

    offenders = _iter_forbidden_import_offenders(
        package_dir=runtime_dir,
        package_name="prism",
        forbidden_roots=("prism.scanner_reporting",),
    )

    assert offenders == ["prism.api:prism.scanner_reporting.report"]
