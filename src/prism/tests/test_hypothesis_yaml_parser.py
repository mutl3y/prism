"""Property-based tests for YAML parsing robustness."""

from __future__ import annotations

import os
import tempfile

import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from prism.scanner_plugins.parsers.yaml.parsing_policy import (
    DefaultYAMLParsingPolicyPlugin,
)


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
            assert str(exc).startswith("yaml_load_error")
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


@settings(max_examples=100)
@given(st.dictionaries(st.text(min_size=1, max_size=20), st.text(max_size=100)))
def test_yaml_round_trip_dict_stays_stable(data: dict) -> None:
    """Dicts serialized via yaml.dump then re-loaded must not raise unexpected exceptions.

    yaml.YAMLError is the only acceptable failure mode; anything else indicates
    a gap in the safe_load contract.
    """
    try:
        serialized = yaml.dump(data)
        yaml.safe_load(serialized)
    except yaml.YAMLError:
        pass  # acceptable for edge-case key content
