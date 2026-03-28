"""Focused tests for pattern policy loading and remote override behavior."""

from pathlib import Path
import json
import urllib.error
import urllib.request

import pytest

from prism.scanner_config import patterns as pattern_config
from prism.scanner_config.patterns import (
    _load_yaml,
    fetch_remote_policy,
    load_pattern_config,
    write_unknown_headings_log,
)
from prism import scanner_config


class _FakeHTTPResponse:
    """Minimal stub for urllib.request.urlopen context-manager response."""

    def __init__(self, content: bytes) -> None:
        self._content = content

    def read(self) -> bytes:
        return self._content

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


def test_load_pattern_config_reads_cwd_override(monkeypatch, tmp_path):
    override = tmp_path / ".prism_patterns.yml"
    override.write_text(
        "sensitivity:\n  name_tokens:\n    - from_cwd_override\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    config = load_pattern_config()

    assert "from_cwd_override" in config["sensitivity"]["name_tokens"]


def test_load_pattern_config_reads_legacy_cwd_override(monkeypatch, tmp_path):
    override = tmp_path / ".ansible_role_doc_patterns.yml"
    override.write_text(
        "sensitivity:\n  name_tokens:\n    - from_legacy_cwd_override\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    config = load_pattern_config()

    assert "from_legacy_cwd_override" in config["sensitivity"]["name_tokens"]


def test_load_pattern_config_reads_xdg_user_override(monkeypatch, tmp_path):
    xdg_home = tmp_path / "xdg-home"
    override = xdg_home / "prism" / pattern_config.CWD_OVERRIDE_FILENAME
    override.parent.mkdir(parents=True)
    override.write_text(
        "sensitivity:\n  name_tokens:\n    - from_xdg_override\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_home))
    monkeypatch.chdir(tmp_path)
    config = load_pattern_config()

    assert "from_xdg_override" in config["sensitivity"]["name_tokens"]


def test_load_pattern_config_reads_env_override(monkeypatch, tmp_path):
    override = tmp_path / "patterns-env.yml"
    override.write_text(
        "sensitivity:\n  name_tokens:\n    - from_env_override\n",
        encoding="utf-8",
    )

    monkeypatch.setenv(pattern_config.ENV_PATTERNS_OVERRIDE_PATH, str(override))
    monkeypatch.chdir(tmp_path)
    config = load_pattern_config()

    assert "from_env_override" in config["sensitivity"]["name_tokens"]


def test_load_pattern_config_reads_legacy_env_override(monkeypatch, tmp_path):
    override = tmp_path / "patterns-legacy-env.yml"
    override.write_text(
        "sensitivity:\n  name_tokens:\n    - from_legacy_env_override\n",
        encoding="utf-8",
    )

    monkeypatch.setenv(pattern_config.LEGACY_ENV_PATTERNS_OVERRIDE_PATH, str(override))
    monkeypatch.chdir(tmp_path)
    config = load_pattern_config()

    assert "from_legacy_env_override" in config["sensitivity"]["name_tokens"]


def test_load_pattern_config_reads_system_override(monkeypatch, tmp_path):
    system_override = tmp_path / "system" / pattern_config.CWD_OVERRIDE_FILENAME
    system_override.parent.mkdir(parents=True)
    system_override.write_text(
        "sensitivity:\n  name_tokens:\n    - from_system_override\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        scanner_config.patterns, "SYSTEM_PATTERN_OVERRIDE_PATH", system_override
    )
    monkeypatch.chdir(tmp_path)
    config = load_pattern_config()

    assert "from_system_override" in config["sensitivity"]["name_tokens"]


def test_load_pattern_config_precedence_later_overrides_earlier(monkeypatch, tmp_path):
    def write_name_tokens(path: Path, token: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"sensitivity:\n  name_tokens:\n    - {token}\n",
            encoding="utf-8",
        )

    system_override = tmp_path / "system" / pattern_config.CWD_OVERRIDE_FILENAME
    xdg_home = tmp_path / "xdg-home"
    xdg_override = xdg_home / "prism" / pattern_config.CWD_OVERRIDE_FILENAME
    cwd_override = tmp_path / pattern_config.CWD_OVERRIDE_FILENAME
    env_override = tmp_path / "patterns-env.yml"
    explicit_override = tmp_path / "patterns-explicit.yml"

    write_name_tokens(system_override, "from_system")
    write_name_tokens(xdg_override, "from_xdg")
    write_name_tokens(cwd_override, "from_cwd")
    write_name_tokens(env_override, "from_env")
    write_name_tokens(explicit_override, "from_explicit")

    monkeypatch.setattr(
        scanner_config.patterns, "SYSTEM_PATTERN_OVERRIDE_PATH", system_override
    )
    monkeypatch.setenv(pattern_config.XDG_DATA_HOME_ENV, str(xdg_home))
    monkeypatch.setenv(pattern_config.ENV_PATTERNS_OVERRIDE_PATH, str(env_override))
    monkeypatch.chdir(tmp_path)

    implicit = load_pattern_config()
    explicit = load_pattern_config(override_path=explicit_override)

    assert implicit["sensitivity"]["name_tokens"] == ["from_env"]
    assert explicit["sensitivity"]["name_tokens"] == ["from_explicit"]


def test_load_yaml_returns_empty_dict_on_io_error(tmp_path, monkeypatch):
    """_load_yaml catches IOError and returns {} without propagating."""
    target = tmp_path / "bad.yml"
    target.write_text("key: value", encoding="utf-8")

    def raise_oserror(*a, **kw):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "open", raise_oserror)
    assert _load_yaml(target) == {}


def test_load_pattern_config_ignores_nonexistent_override_path(tmp_path):
    """load_pattern_config silently skips a non-existent explicit override_path."""
    config = load_pattern_config(override_path=str(tmp_path / "missing.yml"))
    assert isinstance(config, dict)
    assert "section_aliases" in config


def test_load_pattern_config_ignores_blank_override_file(tmp_path):
    """load_pattern_config skips an override whose YAML yields no mapping."""
    blank = tmp_path / "empty.yml"
    blank.write_text("", encoding="utf-8")
    config = load_pattern_config(override_path=str(blank))
    assert isinstance(config, dict)
    assert "section_aliases" in config


def test_fetch_remote_policy_success(monkeypatch):
    """fetch_remote_policy returns a normalised policy on a successful fetch."""
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *a, **kw: _FakeHTTPResponse(b"section_aliases:\n  foo: bar\n"),
    )
    result = fetch_remote_policy("http://example.test/policy.yml")
    assert isinstance(result, dict)
    assert "section_aliases" in result


def test_fetch_remote_policy_writes_cache_bytes(monkeypatch, tmp_path):
    """A successful fetch writes the raw YAML bytes to cache_path."""
    content = b"section_aliases: {}\n"
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *a, **kw: _FakeHTTPResponse(content),
    )
    cache = tmp_path / "sub" / "policy.yml"
    fetch_remote_policy("http://example.test/policy.yml", cache_path=cache)
    assert cache.read_bytes() == content


def test_fetch_remote_policy_falls_back_to_existing_cache(monkeypatch, tmp_path):
    """fetch_remote_policy reads the cache file when the URL fetch fails."""
    cache = tmp_path / "policy.yml"
    cache.write_bytes(b"section_aliases: {}\n")

    def fake_open(*a, **kw):
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(urllib.request, "urlopen", fake_open)
    result = fetch_remote_policy("http://example.test/policy.yml", cache_path=cache)
    assert isinstance(result, dict)


def test_fetch_remote_policy_raises_on_failure_without_cache(monkeypatch):
    """fetch_remote_policy raises RuntimeError when fetch fails and no cache_path."""

    def fake_open(*a, **kw):
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(urllib.request, "urlopen", fake_open)
    with pytest.raises(RuntimeError, match="Failed to fetch remote patterns"):
        fetch_remote_policy("http://example.test/policy.yml")


def test_fetch_remote_policy_raises_when_cache_file_missing(monkeypatch, tmp_path):
    """fetch_remote_policy raises RuntimeError when fetch fails and cache absent."""

    def fake_open(*a, **kw):
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(urllib.request, "urlopen", fake_open)
    with pytest.raises(RuntimeError, match="no cache found"):
        fetch_remote_policy(
            "http://example.test/policy.yml",
            cache_path=str(tmp_path / "missing.yml"),
        )


def test_fetch_remote_policy_raises_on_invalid_yaml(monkeypatch):
    """fetch_remote_policy raises RuntimeError when response is not parseable YAML."""
    # *undefined_alias triggers a yaml.composer.ComposerError
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *a, **kw: _FakeHTTPResponse(b"*undefined_alias"),
    )
    with pytest.raises(
        RuntimeError, match="Failed to parse remote pattern policy YAML"
    ):
        fetch_remote_policy("http://example.test/policy.yml")


def test_fetch_remote_policy_raises_on_non_mapping_yaml(monkeypatch):
    """fetch_remote_policy raises RuntimeError when YAML parses to a non-dict."""
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *a, **kw: _FakeHTTPResponse(b"- item1\n- item2\n"),
    )
    with pytest.raises(RuntimeError, match="did not parse to a mapping"):
        fetch_remote_policy("http://example.test/policy.yml")


def test_write_unknown_headings_log_creates_valid_json(tmp_path):
    """write_unknown_headings_log writes a JSON file with unknown_headings key."""
    out = tmp_path / "sub" / "report.json"
    write_unknown_headings_log({"some heading": 5, "other": 2}, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data == {"unknown_headings": {"some heading": 5, "other": 2}}
