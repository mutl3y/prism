"""Tests for fsrc scanner_config.style module."""

from __future__ import annotations

from pathlib import Path

import pytest

from prism.scanner_config.style import (
    default_style_guide_user_paths,
    resolve_default_style_guide_source,
)


def test_default_style_guide_user_paths_returns_nonempty_list_of_paths():
    result = default_style_guide_user_paths()
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(p, Path) for p in result)


def test_resolve_raises_for_explicit_nonexistent_path(tmp_path):
    nonexistent = str(tmp_path / "no_such_file.md")
    with pytest.raises(FileNotFoundError):
        resolve_default_style_guide_source(explicit_path=nonexistent)


def test_resolve_returns_string_when_no_file_on_disk(tmp_path):
    result = resolve_default_style_guide_source(
        default_style_guide_source_path=tmp_path / "fallback.md",
    )
    assert isinstance(result, str)


def test_resolve_respects_prism_style_source_env(tmp_path, monkeypatch):
    style_file = tmp_path / "custom_style.md"
    style_file.write_text("# Custom Style Guide")
    monkeypatch.setenv("PRISM_STYLE_SOURCE", str(style_file))
    result = resolve_default_style_guide_source(
        default_style_guide_source_path=tmp_path / "fallback.md",
    )
    assert result == str(style_file.resolve())


def test_resolve_default_style_guide_source_importable_from_api():
    from prism.api import resolve_default_style_guide_source as api_fn

    assert callable(api_fn)
