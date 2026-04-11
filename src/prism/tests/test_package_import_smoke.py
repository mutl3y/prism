"""Import smoke tests for Prism package surfaces."""

from __future__ import annotations

import importlib
import pkgutil
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_LANE_ROOT = PROJECT_ROOT / "src"
FSRC_LANE_ROOT = PROJECT_ROOT / "fsrc" / "src"
SOURCE_ROOT = PROJECT_ROOT / "src" / "prism"

_EXCLUDED_MODULE_TOKENS = (".tests",)
_TARGETED_PACKAGE_IMPORTS = (
    "prism.api_layer",
    "prism.cli_app",
    "prism.repo_layer",
    "prism.scanner_compat",
)


def _resolve_path(path_entry: str) -> Path:
    return Path(path_entry).resolve()


@contextmanager
def _prefer_src_prism_on_sys_path() -> Iterator[None]:
    original_path = list(sys.path)
    original_modules = {
        key: value
        for key, value in sys.modules.items()
        if key == "prism" or key.startswith("prism.")
    }
    lane_roots = {SRC_LANE_ROOT.resolve(), FSRC_LANE_ROOT.resolve()}
    try:
        sys.path[:] = [str(SRC_LANE_ROOT.resolve())] + [
            path for path in original_path if _resolve_path(path) not in lane_roots
        ]
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        yield
    finally:
        sys.path[:] = original_path
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        sys.modules.update(original_modules)


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

    with _prefer_src_prism_on_sys_path():
        for module_name in _iter_non_test_module_names():
            try:
                importlib.import_module(module_name)
            except Exception as exc:  # pragma: no cover - exercised only on failure
                failures.append(f"{module_name}: {type(exc).__name__}: {exc}")

    assert not failures, "Prism module import smoke failures:\n" + "\n".join(failures)


def test_src_lane_prism_package_root_identity() -> None:
    with _prefer_src_prism_on_sys_path():
        imported = importlib.import_module("prism")

    package_paths = tuple(Path(path).resolve() for path in imported.__path__)
    assert package_paths == (SOURCE_ROOT.resolve(),)


def test_targeted_facade_adjacent_packages_import_cleanly() -> None:
    with _prefer_src_prism_on_sys_path():
        for module_name in _TARGETED_PACKAGE_IMPORTS:
            imported = importlib.import_module(module_name)
            assert imported.__name__ == module_name
