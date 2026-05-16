"""T4-06: PRISM_* env var configuration overlay tests."""

from __future__ import annotations

from prism.env_config import (
    PRISM_ENV_BINDINGS,
    get_env_var_documentation,
    load_env_overlay,
    merge_with_env_overlay,
)
from prism.scanner_data.scan_options_schema import (
    SCAN_OPTIONS_SCHEMA,
    validate_scan_options,
)


def test_load_env_overlay_empty_when_no_env_vars() -> None:
    assert load_env_overlay(environ={}) == {}


def test_load_env_overlay_maps_known_env_vars() -> None:
    overlay = load_env_overlay(
        environ={
            "PRISM_POLICY_CONFIG": "/etc/prism/policy.yml",
            "PRISM_README_CONFIG": "/etc/prism/readme.yml",
            "PRISM_FAIL_ON_UNCONSTRAINED_DYNAMIC_INCLUDES": "true",
            "PRISM_FAIL_ON_YAML_LIKE_TASK_ANNOTATIONS": "0",
            "UNRELATED": "ignored",
        }
    )
    assert overlay == {
        "policy_config_path": "/etc/prism/policy.yml",
        "readme_config_path": "/etc/prism/readme.yml",
        "fail_on_unconstrained_dynamic_includes": True,
        "fail_on_yaml_like_task_annotations": False,
    }


def test_load_env_overlay_skips_consumer_only_bindings() -> None:
    overlay = load_env_overlay(
        environ={"PRISM_PROGRESS": "1", "PRISM_TELEMETRY_JSON_LOG": "yes"}
    )
    assert overlay == {}


def test_merge_explicit_options_win_over_env() -> None:
    merged = merge_with_env_overlay(
        {"policy_config_path": "/explicit.yml"},
        environ={"PRISM_POLICY_CONFIG": "/env.yml"},
    )
    assert merged == {"policy_config_path": "/explicit.yml"}


def test_merge_env_fills_unspecified_keys() -> None:
    merged = merge_with_env_overlay(
        {"role_path": "/roles/x"},
        environ={"PRISM_POLICY_CONFIG": "/env.yml"},
    )
    assert merged == {
        "role_path": "/roles/x",
        "policy_config_path": "/env.yml",
    }


def test_overlay_keys_are_valid_scan_options_schema_keys() -> None:
    for binding in PRISM_ENV_BINDINGS:
        if binding.option_key is None:
            continue
        assert (
            binding.option_key in SCAN_OPTIONS_SCHEMA
        ), f"{binding.env_var} maps to unknown option key {binding.option_key!r}"


def test_overlay_passes_scan_options_validation() -> None:
    overlay = load_env_overlay(
        environ={
            "PRISM_POLICY_CONFIG": "/p.yml",
            "PRISM_FAIL_ON_UNCONSTRAINED_DYNAMIC_INCLUDES": "1",
        }
    )
    validate_scan_options(overlay)


def test_documentation_includes_every_binding() -> None:
    doc = get_env_var_documentation()
    for binding in PRISM_ENV_BINDINGS:
        assert binding.env_var in doc


def test_bool_coercer_truthy_falsy() -> None:
    overlay_true = load_env_overlay(
        environ={"PRISM_FAIL_ON_YAML_LIKE_TASK_ANNOTATIONS": "ON"}
    )
    overlay_false = load_env_overlay(
        environ={"PRISM_FAIL_ON_YAML_LIKE_TASK_ANNOTATIONS": "no"}
    )
    assert overlay_true["fail_on_yaml_like_task_annotations"] is True
    assert overlay_false["fail_on_yaml_like_task_annotations"] is False
