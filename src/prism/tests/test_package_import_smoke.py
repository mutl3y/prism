"""Import smoke tests for Prism package surfaces."""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = PROJECT_ROOT / "src" / "prism"

_EXCLUDED_MODULE_TOKENS = (".tests",)
_TARGETED_PACKAGE_IMPORTS = (
    "prism.api_layer",
    "prism.cli_app",
    "prism.repo_layer",
    "prism.scanner_compat",
)


def _iter_non_test_module_names() -> list[str]:
    modules: list[str] = []
    for module_info in pkgutil.walk_packages([str(SOURCE_ROOT)], prefix="prism."):
        name = module_info.name
        if any(token in name for token in _EXCLUDED_MODULE_TOKENS):
            continue
        modules.append(name)
    return sorted(modules)


def test_all_non_test_prism_modules_import_cleanly() -> None:
    failures: list[str] = []

    for module_name in _iter_non_test_module_names():
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # pragma: no cover - exercised only on failure
            failures.append(f"{module_name}: {type(exc).__name__}: {exc}")

    assert not failures, "Prism module import smoke failures:\n" + "\n".join(failures)


def test_targeted_facade_adjacent_packages_import_cleanly() -> None:
    for module_name in _TARGETED_PACKAGE_IMPORTS:
        imported = importlib.import_module(module_name)
        assert imported.__name__ == module_name
