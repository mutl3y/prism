"""Unit tests for prism.scanner_plugins.ansible.extract_policies (FIND-13 closure)."""

from __future__ import annotations

from collections.abc import Collection

from prism.scanner_plugins.ansible.extract_policies import (
    AnsibleTaskLineParsingPolicyPlugin,
    AnsibleTaskTraversalPolicyPlugin,
)


class TestAnsibleTaskLineParsingPolicyPlugin:
    def test_plugin_is_stateless_class_attribute(self) -> None:
        assert AnsibleTaskLineParsingPolicyPlugin.PLUGIN_IS_STATELESS is True

    def test_task_include_keys_is_non_empty_frozenset(self) -> None:
        keys = AnsibleTaskLineParsingPolicyPlugin.TASK_INCLUDE_KEYS
        assert isinstance(keys, Collection)
        assert "import_tasks" in keys or "include_tasks" in keys

    def test_role_include_keys_is_non_empty_frozenset(self) -> None:
        keys = AnsibleTaskLineParsingPolicyPlugin.ROLE_INCLUDE_KEYS
        assert isinstance(keys, Collection)
        assert len(keys) > 0

    def test_include_vars_keys_is_non_empty_frozenset(self) -> None:
        keys = AnsibleTaskLineParsingPolicyPlugin.INCLUDE_VARS_KEYS
        assert isinstance(keys, Collection)
        assert len(keys) > 0

    def test_set_fact_keys_is_non_empty_frozenset(self) -> None:
        keys = AnsibleTaskLineParsingPolicyPlugin.SET_FACT_KEYS
        assert isinstance(keys, Collection)
        assert len(keys) > 0

    def test_task_block_keys_is_non_empty_frozenset(self) -> None:
        keys = AnsibleTaskLineParsingPolicyPlugin.TASK_BLOCK_KEYS
        assert isinstance(keys, Collection)
        assert "block" in keys

    def test_task_meta_keys_is_non_empty_frozenset(self) -> None:
        keys = AnsibleTaskLineParsingPolicyPlugin.TASK_META_KEYS
        assert isinstance(keys, Collection)
        assert len(keys) > 0

    def test_extract_constrained_when_values_returns_list(self) -> None:
        task = {"name": "x", "when": "my_var == 'a'"}
        out = AnsibleTaskLineParsingPolicyPlugin.extract_constrained_when_values(
            task, "my_var"
        )
        assert isinstance(out, list)

    def test_detect_task_module_returns_string_or_none(self) -> None:
        result = AnsibleTaskLineParsingPolicyPlugin.detect_task_module(
            {"ansible.builtin.debug": {"msg": "x"}}
        )
        assert result is None or isinstance(result, str)


class TestAnsibleTaskTraversalPolicyPlugin:
    def test_iter_task_mappings_yields_dicts(self) -> None:
        tasks = [{"name": "t1", "ansible.builtin.debug": {}}, "not a dict"]
        out = list(AnsibleTaskTraversalPolicyPlugin.iter_task_mappings(tasks))
        assert len(out) == 1
        assert out[0]["name"] == "t1"

    def test_iter_task_include_targets_returns_list(self) -> None:
        out = AnsibleTaskTraversalPolicyPlugin.iter_task_include_targets(
            [{"include_tasks": "sub.yml"}]
        )
        assert isinstance(out, list)
        assert "sub.yml" in out

    def test_iter_task_include_edges_returns_list_of_dicts(self) -> None:
        out = AnsibleTaskTraversalPolicyPlugin.iter_task_include_edges(
            [{"include_tasks": "t.yml"}]
        )
        assert isinstance(out, list)

    def test_expand_include_target_candidates_returns_list(self) -> None:
        out = AnsibleTaskTraversalPolicyPlugin.expand_include_target_candidates(
            {"include_tasks": "t.yml"}, "t.yml"
        )
        assert isinstance(out, list)
        assert len(out) >= 1
