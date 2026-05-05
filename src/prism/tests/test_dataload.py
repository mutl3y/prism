"""Unit tests for prism.scanner_extract.dataload (FIND-13 closure)."""

from __future__ import annotations

from pathlib import Path

import pytest

from prism.scanner_extract import discovery
from prism.scanner_extract.discovery import (
    REQUIREMENTS_YAML_INVALID,
    ROLE_METADATA_SHAPE_INVALID,
    VARIABLE_FILE_IO_ERROR,
    load_meta,
    load_requirements,
    load_variables,
)
from prism.scanner_extract.dataload import (
    RoleVariableMaps,
    iter_role_argument_spec_entries,
    load_role_variable_maps,
)
from prism.scanner_io.loader import load_yaml_file


def test_role_variable_maps_is_namedtuple() -> None:
    rvm = RoleVariableMaps({"a": 1}, {"b": 2}, {"a": Path("/x")}, {"b": Path("/y")})
    assert rvm.defaults_data == {"a": 1}
    assert rvm.vars_data == {"b": 2}
    assert rvm.defaults_sources == {"a": Path("/x")}


def test_load_role_variable_maps_collects_defaults_and_vars() -> None:
    candidates = {
        "defaults": [Path("/r/defaults/main.yml"), Path("/r/defaults/extra.yml")],
        "vars": [Path("/r/vars/main.yml")],
    }

    def iter_candidates(_root: Path, kind: str) -> list[Path]:
        return candidates[kind]

    yaml_files: dict[Path, dict] = {
        Path("/r/defaults/main.yml"): {"a": 1, "b": 2},
        Path("/r/defaults/extra.yml"): {"c": 3},
        Path("/r/vars/main.yml"): {"v": 9},
    }

    def loader(p: Path) -> object:
        return yaml_files.get(p, None)

    rvm = load_role_variable_maps("/r", True, iter_candidates, loader)
    assert rvm.defaults_data == {"a": 1, "b": 2, "c": 3}
    assert rvm.vars_data == {"v": 9}
    assert rvm.defaults_sources["a"] == Path("/r/defaults/main.yml")
    assert rvm.defaults_sources["c"] == Path("/r/defaults/extra.yml")
    assert rvm.vars_sources["v"] == Path("/r/vars/main.yml")


def test_load_role_variable_maps_skips_vars_when_include_vars_main_false() -> None:
    def iter_candidates(_root: Path, kind: str) -> list[Path]:
        return [Path(f"/r/{kind}/main.yml")]

    def loader(p: Path) -> object:
        return {"k": 1} if "defaults" in str(p) else {"v": 2}

    rvm = load_role_variable_maps("/r", False, iter_candidates, loader)
    assert rvm.defaults_data == {"k": 1}
    assert rvm.vars_data == {}


def test_load_role_variable_maps_skips_non_dict_payloads() -> None:
    def iter_candidates(_root: Path, kind: str) -> list[Path]:
        return [Path(f"/r/{kind}/main.yml")]

    rvm = load_role_variable_maps("/r", True, iter_candidates, lambda _p: "string")
    assert rvm.defaults_data == {} and rvm.vars_data == {}


def test_load_role_variable_maps_propagates_yaml_load_failures(
    tmp_path: Path,
) -> None:
    defaults_dir = tmp_path / "defaults"
    defaults_dir.mkdir()
    bad_yaml = defaults_dir / "main.yml"
    bad_yaml.write_text("broken: [\n", encoding="utf-8")

    def iter_candidates(role_root: Path, kind: str) -> list[Path]:
        assert role_root == tmp_path
        return [tmp_path / kind / "main.yml"] if kind == "defaults" else []

    with pytest.raises(Exception):
        load_role_variable_maps(
            str(tmp_path),
            True,
            iter_candidates,
            load_yaml_file,
        )


def test_load_variables_strict_raises_on_invalid_yaml(tmp_path: Path) -> None:
    defaults_dir = tmp_path / "defaults"
    defaults_dir.mkdir()
    bad_yaml = defaults_dir / "main.yml"
    bad_yaml.write_text("broken: [\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match=VARIABLE_FILE_IO_ERROR):
        load_variables(
            str(tmp_path),
            collect_include_vars_files=lambda _role_path, _exclude_paths: [],
            strict=True,
        )


def test_load_meta_strict_raises_on_non_mapping_payload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    (meta_dir / "main.yml").write_text("galaxy_info: []\n", encoding="utf-8")
    monkeypatch.setattr(discovery, "load_yaml_file", lambda _path, di=None: ["bad"])

    with pytest.raises(RuntimeError, match=ROLE_METADATA_SHAPE_INVALID):
        load_meta(str(tmp_path), strict=True)


def test_load_meta_non_strict_collects_shape_warning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    (meta_dir / "main.yml").write_text("galaxy_info: []\n", encoding="utf-8")
    warnings: list[str] = []
    monkeypatch.setattr(discovery, "load_yaml_file", lambda _path, di=None: ["bad"])

    loaded = load_meta(str(tmp_path), warning_collector=warnings)

    assert loaded == {}
    assert warnings == [
        f"{ROLE_METADATA_SHAPE_INVALID}: {tmp_path / 'meta' / 'main.yml'}: metadata root must be a mapping"
    ]


def test_load_requirements_strict_raises_on_invalid_yaml(tmp_path: Path) -> None:
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    requirements_file = meta_dir / "requirements.yml"
    requirements_file.write_text("broken: [\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match=REQUIREMENTS_YAML_INVALID):
        load_requirements(str(tmp_path), strict=True)


def test_load_requirements_non_strict_collects_shape_warning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    (meta_dir / "requirements.yml").write_text("name: value\n", encoding="utf-8")
    warnings: list[str] = []
    monkeypatch.setattr(
        discovery, "load_yaml_file", lambda _path, di=None: {"name": "value"}
    )

    loaded = load_requirements(str(tmp_path), warning_collector=warnings)

    assert loaded == []
    assert warnings == [
        f"{REQUIREMENTS_YAML_INVALID}: {tmp_path / 'meta' / 'requirements.yml'}: root must be a list"
    ]


def test_load_meta_empty_yaml_returns_empty_mapping_without_warning(
    tmp_path: Path,
) -> None:
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    (meta_dir / "main.yml").write_text("\n", encoding="utf-8")
    warnings: list[str] = []

    loaded = load_meta(str(tmp_path), warning_collector=warnings)

    assert loaded == {}
    assert warnings == []


def test_iter_role_argument_spec_entries_yields_flat_options(tmp_path: Path) -> None:
    arg_specs_file = tmp_path / "meta" / "argument_specs.yml"
    arg_specs_file.parent.mkdir()
    arg_specs_file.write_text("ignored")

    yaml_payload = {
        "argument_specs": {
            "main": {
                "options": {
                    "name": {"type": "str"},
                    "tags": {"type": "list"},
                    "{{ skip }}": {"type": "str"},
                    123: {"type": "ignored"},
                }
            },
            "broken": "not a dict",
        }
    }

    def loader(_p: Path) -> object:
        return yaml_payload

    def meta_loader(_role_path: str) -> dict:
        return {"argument_specs": {"meta_main": {"options": {"role_var": {}}}}}

    entries = list(iter_role_argument_spec_entries(str(tmp_path), loader, meta_loader))
    sources = {(src, name) for src, name, _spec in entries}
    assert ("meta/argument_specs.yml", "name") in sources
    assert ("meta/argument_specs.yml", "tags") in sources
    assert ("meta/main.yml", "role_var") in sources
    assert not any("skip" in name for _, name, _ in entries)


def test_iter_role_argument_spec_entries_skips_non_dict_meta(tmp_path: Path) -> None:
    def meta_loader(_role_path: str) -> dict:
        return {}

    out = list(
        iter_role_argument_spec_entries(str(tmp_path), lambda _p: None, meta_loader)
    )
    assert out == []
