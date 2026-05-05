"""T1-02: targeted unit tests, batch 4 — config/policy and variable_extractor helpers."""

from __future__ import annotations

from pathlib import Path

import pytest


CONFIG_NAME = ".prism.yml"


# ---- scanner_config/policy.py ---------------------------------------------


def _write_cfg(tmp_path: Path, content: str) -> Path:
    cfg = tmp_path / CONFIG_NAME
    cfg.write_text(content, encoding="utf-8")
    return cfg


def test_load_fail_on_unconstrained_dynamic_includes_branches(tmp_path: Path) -> None:
    from prism.scanner_config.policy import (
        load_fail_on_unconstrained_dynamic_includes as fn,
    )

    assert fn(str(tmp_path), default=False) is False
    assert fn(str(tmp_path), default=True) is True

    _write_cfg(tmp_path, "scan:\n  fail_on_unconstrained_dynamic_includes: true\n")
    assert fn(str(tmp_path), default=False) is True

    _write_cfg(tmp_path, "fail_on_unconstrained_dynamic_includes: 'no'\n")
    assert fn(str(tmp_path), default=True) is False

    _write_cfg(tmp_path, "scan:\n  fail_on_unconstrained_dynamic_includes: not-bool\n")
    assert fn(str(tmp_path), default=True) is True


def test_load_fail_on_yaml_like_task_annotations_branches(tmp_path: Path) -> None:
    from prism.scanner_config.policy import (
        load_fail_on_yaml_like_task_annotations as fn,
    )

    assert fn(str(tmp_path)) is False

    _write_cfg(tmp_path, "scan:\n  fail_on_yaml_like_task_annotations: yes\n")
    assert fn(str(tmp_path)) is True

    _write_cfg(tmp_path, "fail_on_yaml_like_task_annotations: 'off'\n")
    assert fn(str(tmp_path), default=True) is False


def test_load_ignore_unresolved_internal_underscore_references(tmp_path: Path) -> None:
    from prism.scanner_config.policy import (
        load_ignore_unresolved_internal_underscore_references as fn,
    )

    assert fn(str(tmp_path)) is True
    _write_cfg(
        tmp_path, "scan:\n  ignore_unresolved_internal_underscore_references: false\n"
    )
    assert fn(str(tmp_path)) is False


def test_load_non_authoritative_test_evidence_max_file_bytes(tmp_path: Path) -> None:
    from prism.scanner_config.policy import (
        load_non_authoritative_test_evidence_max_file_bytes as fn,
    )

    default = 512 * 1024
    assert fn(str(tmp_path)) == default

    _write_cfg(
        tmp_path, "scan:\n  non_authoritative_test_evidence_max_file_bytes: 4096\n"
    )
    assert fn(str(tmp_path)) == 4096

    _write_cfg(tmp_path, "non_authoritative_test_evidence_max_file_bytes: '2048'\n")
    assert fn(str(tmp_path)) == 2048

    _write_cfg(
        tmp_path, "scan:\n  non_authoritative_test_evidence_max_file_bytes: -1\n"
    )
    assert fn(str(tmp_path)) == default

    _write_cfg(
        tmp_path, "scan:\n  non_authoritative_test_evidence_max_file_bytes: not-int\n"
    )
    assert fn(str(tmp_path)) == default


def test_load_policy_config_raises_on_invalid_yaml(tmp_path: Path) -> None:
    from prism.scanner_config.policy import (
        POLICY_CONFIG_YAML_INVALID,
        load_fail_on_unconstrained_dynamic_includes,
    )

    _write_cfg(tmp_path, "scan: [oops\n")
    with pytest.raises(RuntimeError) as ei:
        load_fail_on_unconstrained_dynamic_includes(str(tmp_path))
    assert POLICY_CONFIG_YAML_INVALID in str(ei.value)


def test_load_policy_config_non_dict_returns_empty(tmp_path: Path) -> None:
    from prism.scanner_config.policy import (
        load_fail_on_unconstrained_dynamic_includes as fn,
    )

    _write_cfg(tmp_path, "- just\n- a\n- list\n")
    assert fn(str(tmp_path), default=True) is True


# ---- scanner_extract/variable_extractor.py --------------------------------


def test_looks_secret_name_and_resembles_password_like() -> None:
    from prism.scanner_extract.variable_extractor import (
        looks_secret_name,
        resembles_password_like,
    )

    assert looks_secret_name("admin_password") is True
    assert looks_secret_name("api_token") is True
    assert looks_secret_name("client_secret") is True
    assert looks_secret_name("ssh_key") is True
    assert looks_secret_name("user_name") is False

    assert resembles_password_like("MyPassword123") is True
    assert resembles_password_like("$6$rounds$abc") is True
    assert resembles_password_like("hello") is False
    assert resembles_password_like("") is False


def test_extract_default_target_var() -> None:
    from prism.scanner_extract.variable_extractor import extract_default_target_var

    assert extract_default_target_var("{{ foo | default('x') }}") == "foo"
    assert extract_default_target_var("nothing here") is None
    assert extract_default_target_var("") is None


def testget_variable_extractor_policy_raises_without_bundle() -> None:
    from prism.scanner_extract.variable_extractor import get_variable_extractor_policy

    class _DI:
        scan_options: dict = {}

    with pytest.raises(ValueError, match="prepared_policy_bundle.variable_extractor"):
        get_variable_extractor_policy(_DI())


def testget_variable_extractor_policy_returns_bundle_value() -> None:
    from prism.scanner_extract.variable_extractor import get_variable_extractor_policy

    sentinel = object()

    class _DI:
        scan_options = {"prepared_policy_bundle": {"variable_extractor": sentinel}}

    assert get_variable_extractor_policy(_DI()) is sentinel


def test_load_seed_variables_empty_paths() -> None:
    from prism.scanner_extract.variable_extractor import load_seed_variables

    values, secrets, sources = load_seed_variables(None)
    assert values == {} and secrets == set() and sources == {}

    values, secrets, sources = load_seed_variables([])
    assert values == {} and secrets == set() and sources == {}


def test_load_seed_variables_loads_dict_and_marks_secrets(tmp_path: Path) -> None:
    from prism.scanner_extract.variable_extractor import load_seed_variables

    seed = tmp_path / "seed.yml"
    seed.write_text("admin_password: hunter2\nuser_name: alice\n", encoding="utf-8")

    values, secrets, sources = load_seed_variables([str(seed)])
    assert values == {"admin_password": "hunter2", "user_name": "alice"}
    assert secrets == {"admin_password"}
    assert sources["admin_password"] == str(seed)


def test_load_seed_variables_skips_missing_files(tmp_path: Path) -> None:
    from prism.scanner_extract.variable_extractor import load_seed_variables

    values, _, _ = load_seed_variables([str(tmp_path / "absent.yml")])
    assert values == {}


def test_load_seed_variables_skips_non_dict_yaml(tmp_path: Path) -> None:
    from prism.scanner_extract.variable_extractor import load_seed_variables

    seed = tmp_path / "list.yml"
    seed.write_text("- a\n- b\n", encoding="utf-8")
    values, _, _ = load_seed_variables([str(seed)])
    assert values == {}


def test_load_seed_variables_skips_non_string_keys(tmp_path: Path) -> None:
    from prism.scanner_extract.variable_extractor import load_seed_variables

    seed = tmp_path / "weird.yml"
    seed.write_text("1: int_key\nfoo: bar\n", encoding="utf-8")
    values, _, _ = load_seed_variables([str(seed)])
    assert values == {"foo": "bar"}
