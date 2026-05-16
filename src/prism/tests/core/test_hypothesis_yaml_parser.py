"""Property-based tests for YAML parsing robustness."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from prism.scanner_plugins.parsers.yaml.parsing_policy import (
    DefaultYAMLParsingPolicyPlugin,
)

_YAML_SCALAR = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(max_size=80),
)
_YAML_VALUE = st.recursive(
    _YAML_SCALAR,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(st.text(min_size=1, max_size=20), children, max_size=4),
    ),
    max_leaves=10,
)


def _write_temp_yaml(content: str, *, suffix: str = ".yaml") -> Path:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(content)
    return Path(path)


def _unlink_if_present(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


@settings(max_examples=100)
@given(st.text())
def test_yaml_safe_load_raises_only_yaml_error_on_arbitrary_text(text: str) -> None:
    """yaml.safe_load must raise only YAMLError (or nothing) on arbitrary string input."""
    try:
        yaml.safe_load(text)
    except yaml.YAMLError:
        pass  # known, expected exception for malformed YAML


@settings(max_examples=50)
@given(st.text())
def test_load_yaml_file_never_raises_on_arbitrary_content(text: str) -> None:
    """load_yaml_file must only surface the documented yaml_load_error channel.

    Arbitrary file contents may be unreadable or malformed YAML, but the policy
    plugin should wrap those failures as RuntimeError with the stable
    yaml_load_error prefix rather than leaking parser-specific exception types.
    """
    fd, path = tempfile.mkstemp(suffix=".yaml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        try:
            DefaultYAMLParsingPolicyPlugin.load_yaml_file(path)
        except RuntimeError as exc:
            assert "yaml_load_error" in str(exc)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


@settings(max_examples=50)
@given(st.text())
def test_parse_yaml_candidate_returns_none_or_error_dict(text: str) -> None:
    """parse_yaml_candidate must return None (success) or a dict (error info) for any input.

    None signals a parseable file; a dict carries structured error metadata.
    Any uncaught exception is a regression in the error-handling boundary.
    """
    fd, path = tempfile.mkstemp(suffix=".yaml")
    tmpdir = tempfile.gettempdir()
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        result = DefaultYAMLParsingPolicyPlugin.parse_yaml_candidate(path, tmpdir)
        assert result is None or isinstance(result, dict)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


@settings(max_examples=25, deadline=None)
@given(_YAML_VALUE)
def test_load_yaml_file_round_trips_nested_unicode_structures(data: Any) -> None:
    """Nested YAML-safe structures should round-trip through the policy loader.

    This exercises the parser with recursive lists/dicts plus arbitrary Unicode
    strings so T4-04 covers more than flat smoke inputs.
    """
    serialized = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    path = _write_temp_yaml(serialized)
    try:
        loaded = DefaultYAMLParsingPolicyPlugin.load_yaml_file(path)
        assert loaded == yaml.safe_load(serialized)
    finally:
        _unlink_if_present(path)


@settings(max_examples=10, deadline=None)
@given(st.lists(st.text(max_size=120), min_size=64, max_size=128))
def test_load_yaml_file_handles_large_text_sequences(values: list[str]) -> None:
    """Large YAML payloads should stay within the documented success/error boundary."""
    serialized = yaml.safe_dump(values, allow_unicode=True, sort_keys=False)
    path = _write_temp_yaml(serialized)
    try:
        loaded = DefaultYAMLParsingPolicyPlugin.load_yaml_file(path)
        assert loaded == yaml.safe_load(serialized)
    finally:
        _unlink_if_present(path)


def test_yaml_policy_handles_circular_alias_document() -> None:
    """Self-referential YAML anchors should not be mistaken for parser crashes."""
    path = _write_temp_yaml("root: &root\n  self: *root\n")
    try:
        assert (
            DefaultYAMLParsingPolicyPlugin.parse_yaml_candidate(path, path.parent)
            is None
        )
        loaded = DefaultYAMLParsingPolicyPlugin.load_yaml_file(path)
        assert isinstance(loaded, dict)
        root = loaded["root"]
        assert isinstance(root, dict)
        assert root["self"] is root
    finally:
        _unlink_if_present(path)
