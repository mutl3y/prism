"""Tests for the Ansible task-traversal bare primitives."""

from __future__ import annotations

from prism.scanner_plugins.ansible import task_traversal_bare


def test_task_include_keys_contain_short_and_fqcn_forms() -> None:
    assert "include_tasks" in task_traversal_bare.TASK_INCLUDE_KEYS
    assert "import_tasks" in task_traversal_bare.TASK_INCLUDE_KEYS
    assert "ansible.builtin.include_tasks" in task_traversal_bare.TASK_INCLUDE_KEYS
    assert "ansible.builtin.import_tasks" in task_traversal_bare.TASK_INCLUDE_KEYS


def test_role_include_keys_contain_short_and_fqcn_forms() -> None:
    assert "include_role" in task_traversal_bare.ROLE_INCLUDE_KEYS
    assert "import_role" in task_traversal_bare.ROLE_INCLUDE_KEYS
    assert "ansible.builtin.include_role" in task_traversal_bare.ROLE_INCLUDE_KEYS
    assert "ansible.builtin.import_role" in task_traversal_bare.ROLE_INCLUDE_KEYS


def test_include_vars_and_set_fact_keys_contain_short_and_fqcn_forms() -> None:
    assert task_traversal_bare.INCLUDE_VARS_KEYS == frozenset(
        {"include_vars", "ansible.builtin.include_vars"}
    )
    assert task_traversal_bare.SET_FACT_KEYS == frozenset(
        {"set_fact", "ansible.builtin.set_fact"}
    )


def test_task_block_keys_are_immutable_tuple_in_order() -> None:
    assert task_traversal_bare.TASK_BLOCK_KEYS == ("block", "rescue", "always")
    assert isinstance(task_traversal_bare.TASK_BLOCK_KEYS, tuple)


def test_task_meta_keys_include_common_ansible_meta_fields() -> None:
    expected_subset = {
        "name",
        "when",
        "tags",
        "register",
        "notify",
        "vars",
        "loop",
        "with_items",
    }
    assert expected_subset.issubset(task_traversal_bare.TASK_META_KEYS)


def test_traversal_constants_are_frozenset_for_hash_safety() -> None:
    for name in (
        "TASK_INCLUDE_KEYS",
        "ROLE_INCLUDE_KEYS",
        "INCLUDE_VARS_KEYS",
        "SET_FACT_KEYS",
        "TASK_META_KEYS",
    ):
        value = getattr(task_traversal_bare, name)
        assert isinstance(
            value, frozenset
        ), f"{name} must be frozenset, got {type(value).__name__}"


def test_extract_constrained_when_values_returns_list_for_string_when() -> None:
    task = {"when": "some_var == 'x'"}
    result = task_traversal_bare.extract_constrained_when_values(task, "some_var")
    assert isinstance(result, list)


def test_extract_constrained_when_values_returns_empty_list_when_missing() -> None:
    task: dict = {}
    result = task_traversal_bare.extract_constrained_when_values(task, "anything")
    assert result == []
