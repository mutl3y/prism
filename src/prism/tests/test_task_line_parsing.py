"""Unit tests for prism.scanner_extract.task_line_parsing (FIND-13 closure).

These proxies require a prepared_policy_bundle on the DI container; without one
they must fail closed via require_prepared_policy. The tests assert that
contract directly.
"""

from __future__ import annotations

import pytest

from prism.scanner_extract import task_line_parsing as tlp


def test_get_task_include_keys_raises_without_bundle() -> None:
    with pytest.raises(ValueError):
        tlp.get_task_include_keys(None)


def test_get_role_include_keys_raises_without_bundle() -> None:
    with pytest.raises(ValueError):
        tlp.get_role_include_keys(None)


def test_get_include_vars_keys_raises_without_bundle() -> None:
    with pytest.raises(ValueError):
        tlp.get_include_vars_keys(None)


def test_get_set_fact_keys_raises_without_bundle() -> None:
    with pytest.raises(ValueError):
        tlp.get_set_fact_keys(None)


def test_get_task_block_keys_raises_without_bundle() -> None:
    with pytest.raises(ValueError):
        tlp.get_task_block_keys(None)


def test_get_task_meta_keys_raises_without_bundle() -> None:
    with pytest.raises(ValueError):
        tlp.get_task_meta_keys(None)


def test_get_templated_include_re_raises_without_bundle() -> None:
    with pytest.raises(ValueError):
        tlp.get_templated_include_re(None)


def test_collection_proxy_iter_returns_empty_when_policy_unavailable() -> None:
    with pytest.raises(ValueError):
        list(tlp.TASK_INCLUDE_KEYS)


def test_collection_proxy_contains_returns_false_when_policy_unavailable() -> None:
    with pytest.raises(ValueError):
        _ = "import_tasks" in tlp.TASK_INCLUDE_KEYS


def test_collection_proxy_len_raises_without_bundle() -> None:
    with pytest.raises(ValueError):
        len(tlp.TASK_INCLUDE_KEYS)


def test_marker_line_regex_proxy_raises_without_bundle() -> None:
    with pytest.raises(ValueError):
        tlp.ROLE_NOTES_RE.match("anything")


def test_annotation_regex_proxy_raises_without_bundle() -> None:
    with pytest.raises(ValueError):
        tlp.TASK_ENTRY_RE.match("- name: x")
