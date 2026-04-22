"""Import smoke tests for the fsrc Prism package lane."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FSRC_SOURCE_ROOT = PROJECT_ROOT / "src"


@contextmanager
def _prefer_fsrc_prism_on_sys_path() -> object:
    original_path = list(sys.path)
    original_modules = {
        key: value
        for key, value in sys.modules.items()
        if key == "prism" or key.startswith("prism.")
    }
    try:
        sys.path.insert(0, str(FSRC_SOURCE_ROOT))
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


def test_fsrc_prism_package_root_imports_cleanly() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        imported = importlib.import_module("prism")

    module_file = Path(imported.__file__).resolve()
    assert module_file == FSRC_SOURCE_ROOT / "prism" / "__init__.py"


def test_fsrc_lane_cannot_import_src_only_submodules() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        with pytest.raises(ModuleNotFoundError) as excinfo:
            importlib.import_module("prism.scanner")
    assert excinfo.value.name == "prism.scanner"


def test_fsrc_lane_imports_cli_and_api_shells() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        cli_module = importlib.import_module("prism.cli")
        api_module = importlib.import_module("prism.api")

    assert cli_module.__name__ == "prism.cli"
    assert api_module.__name__ == "prism.api"
