"""Objective-critical API/CLI/repo parity checks for the fsrc package lane."""

from __future__ import annotations

import argparse
import inspect
import importlib
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from urllib.error import URLError


PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_SOURCE_ROOT = PROJECT_ROOT / "src"
FSRC_SOURCE_ROOT = PROJECT_ROOT / "fsrc" / "src"


@contextmanager
def _prefer_fsrc_prism_on_sys_path() -> object:
    original_path = list(sys.path)
    original_modules = {
        key: value
        for key, value in sys.modules.items()
        if key == "prism" or key.startswith("prism.")
    }
    try:
        sys.path.insert(0, str(FSRC_SOURCE_ROOT))
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        yield
    finally:
        sys.path[:] = original_path
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        sys.modules.update(original_modules)


@contextmanager
def _prefer_prism_lane_on_sys_path(lane_root: Path) -> object:
    original_path = list(sys.path)
    original_modules = {
        key: value
        for key, value in sys.modules.items()
        if key == "prism" or key.startswith("prism.")
    }
    lane_roots = {SRC_SOURCE_ROOT.resolve(), FSRC_SOURCE_ROOT.resolve()}
    try:
        sys.path[:] = [str(lane_root.resolve())] + [
            path for path in original_path if Path(path).resolve() not in lane_roots
        ]
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        yield
    finally:
        sys.path[:] = original_path
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        sys.modules.update(original_modules)


def test_fsrc_api_declares_objective_critical_entrypoints() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

    assert api_module.API_PUBLIC_ENTRYPOINTS == (
        "scan_collection",
        "scan_role",
        "scan_repo",
    )
    for symbol in api_module.API_PUBLIC_ENTRYPOINTS:
        assert hasattr(api_module, symbol)
    assert api_module.__all__ == ["scan_collection", "scan_repo", "scan_role"]


def test_fsrc_api_objective_critical_entrypoint_signatures_match_src() -> None:
    with _prefer_prism_lane_on_sys_path(SRC_SOURCE_ROOT):
        src_api_module = importlib.import_module("prism.api")

    with _prefer_prism_lane_on_sys_path(FSRC_SOURCE_ROOT):
        fsrc_api_module = importlib.import_module("prism.api")

    for name in ("scan_collection", "scan_role", "scan_repo"):
        src_signature = inspect.signature(getattr(src_api_module, name))
        fsrc_signature = inspect.signature(getattr(fsrc_api_module, name))
        assert fsrc_signature == src_signature


def test_fsrc_repo_services_objective_critical_signature_parity_with_src() -> None:
    with _prefer_prism_lane_on_sys_path(SRC_SOURCE_ROOT):
        src_repo_services_module = importlib.import_module("prism.repo_services")

    with _prefer_prism_lane_on_sys_path(FSRC_SOURCE_ROOT):
        fsrc_repo_services_module = importlib.import_module("prism.repo_services")

    for name in (
        "resolve_repo_scan_target",
        "normalize_repo_scan_payload",
        "run_repo_scan",
    ):
        src_signature = inspect.signature(getattr(src_repo_services_module, name))
        fsrc_signature = inspect.signature(getattr(fsrc_repo_services_module, name))
        assert fsrc_signature == src_signature


def test_fsrc_cli_parser_exposes_collection_and_completion_commands() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        cli_module = importlib.import_module("prism.cli")

    parser = cli_module.build_parser()
    parsed_collection = parser.parse_args(["collection", "./demo-collection"])
    parsed_completion = parser.parse_args(["completion", "bash"])

    assert parsed_collection.command == "collection"
    assert parsed_completion.command == "completion"


def test_fsrc_cli_completion_dispatch_returns_zero_and_prints_script(capsys) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        cli_module = importlib.import_module("prism.cli")
        rc = cli_module.main(["completion", "bash"])

    captured = capsys.readouterr()
    assert rc == 0
    assert "complete -F _prism_completion prism" in captured.out


def test_fsrc_cli_runtime_failure_exit_taxonomy(monkeypatch, capsys) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        cli_module = importlib.import_module("prism.cli")
        errors_module = importlib.import_module("prism.errors")

        def _raise_not_found(*_args: object, **_kwargs: object) -> dict[str, object]:
            raise FileNotFoundError("missing")

        monkeypatch.setattr(cli_module.api, "scan_role", _raise_not_found)
        assert cli_module.main(["role", "/tmp/demo"]) == 3

        def _raise_permission(*_args: object, **_kwargs: object) -> dict[str, object]:
            raise PermissionError("denied")

        monkeypatch.setattr(cli_module.api, "scan_role", _raise_permission)
        assert cli_module.main(["role", "/tmp/demo"]) == 4

        def _raise_json(*_args: object, **_kwargs: object) -> dict[str, object]:
            raise json.JSONDecodeError("boom", "{}", 0)

        monkeypatch.setattr(cli_module.api, "scan_role", _raise_json)
        assert cli_module.main(["role", "/tmp/demo"]) == 5

        def _raise_network(*_args: object, **_kwargs: object) -> dict[str, object]:
            raise URLError("net")

        monkeypatch.setattr(cli_module.api, "scan_role", _raise_network)
        assert cli_module.main(["role", "/tmp/demo"]) == 6

        def _raise_os(*_args: object, **_kwargs: object) -> dict[str, object]:
            raise OSError("io")

        monkeypatch.setattr(cli_module.api, "scan_role", _raise_os)
        assert cli_module.main(["role", "/tmp/demo"]) == 7

        def _raise_prism_network(
            *_args: object, **_kwargs: object
        ) -> dict[str, object]:
            raise errors_module.PrismRuntimeError(
                code="repo_transport_failed",
                category="network",
                message="network",
            )

        monkeypatch.setattr(cli_module.api, "scan_role", _raise_prism_network)
        assert cli_module.main(["role", "/tmp/demo"]) == 6

        def _raise_prism_io(*_args: object, **_kwargs: object) -> dict[str, object]:
            raise errors_module.PrismRuntimeError(
                code="role_content_io_error",
                category="io",
                message="io",
            )

        monkeypatch.setattr(cli_module.api, "scan_role", _raise_prism_io)
        assert cli_module.main(["role", "/tmp/demo"]) == 7

        def _raise_generic(*_args: object, **_kwargs: object) -> dict[str, object]:
            raise RuntimeError("boom")

        monkeypatch.setattr(cli_module.api, "scan_role", _raise_generic)
        assert cli_module.main(["role", "/tmp/demo"]) == 2

    captured = capsys.readouterr()
    assert "Scan failed" not in captured.err


def test_fsrc_repo_services_exposes_canonical_repo_surface() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        repo_services_module = importlib.import_module("prism.repo_services")

    expected_symbols = {
        "repo_scan_facade",
        "resolve_repo_scan_target",
        "run_repo_scan",
        "normalize_repo_scan_payload",
    }
    assert expected_symbols.issubset(
        set(repo_services_module.REPO_SERVICE_CANONICAL_SURFACE)
    )
    for symbol in expected_symbols:
        assert hasattr(repo_services_module, symbol)


def test_fsrc_api_scan_repo_uses_fsrc_repo_services_facade(monkeypatch) -> None:
    captured: dict[str, object] = {}

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        def fake_run_repo_scan(**kwargs: object) -> object:
            captured.update(kwargs)
            return {
                "role_name": "demo-role",
                "metadata": {"style_guide": {"path": "README.md"}},
            }

        class _FakeFacade:
            def run_repo_scan(self, **kwargs: object) -> object:
                return fake_run_repo_scan(**kwargs)

        monkeypatch.setattr(api_module, "_repo_scan_facade", _FakeFacade())
        payload = api_module.scan_repo(
            "https://example.invalid/demo.git",
            repo_role_path="roles/demo",
            repo_style_readme_path="README.md",
            style_readme_path="STYLE.md",
        )

    assert payload["role_name"] == "demo-role"
    assert captured["repo_url"] == "https://example.invalid/demo.git"
    assert captured["repo_role_path"] == "roles/demo"
    assert captured["repo_style_readme_path"] == "README.md"


def test_fsrc_api_scan_repo_uses_non_collection_repo_resolver_when_unset(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        class _FakeFacade:
            def run_repo_scan(self, **kwargs: object) -> object:
                captured.update(kwargs)
                return {"role_name": "delegated-role", "metadata": {}}

        monkeypatch.setattr(api_module, "_repo_scan_facade", None)
        monkeypatch.setattr(
            api_module.api_non_collection,
            "_resolve_repo_scan_facade",
            lambda: _FakeFacade(),
        )

        payload = api_module.scan_repo("https://example.invalid/demo.git")

    assert payload == {"role_name": "delegated-role", "metadata": {}}
    assert captured["repo_url"] == "https://example.invalid/demo.git"


def test_fsrc_api_scan_repo_forwards_role_name_override_to_scan_role_fn(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        class _FakeFacade:
            def run_repo_scan(self, **kwargs: object) -> object:
                captured.update(kwargs)
                scan_role_fn = kwargs["scan_role_fn"]
                assert callable(scan_role_fn)
                return scan_role_fn(
                    "/tmp/repo-role",
                    style_readme_path="README.repo.md",
                    role_name_override="derived-role-name",
                )

        monkeypatch.setattr(api_module, "_repo_scan_facade", _FakeFacade())

        def _fake_scan_role(
            role_path: str,
            **kwargs: object,
        ) -> dict[str, object]:
            captured["forwarded_role_path"] = role_path
            captured["forwarded_kwargs"] = dict(kwargs)
            return {"role_name": str(kwargs.get("role_name_override") or "role")}

        monkeypatch.setattr(api_module, "scan_role", _fake_scan_role)
        payload = api_module.scan_repo("https://example.invalid/demo.git")

    assert payload["role_name"] == "derived-role-name"
    assert captured["forwarded_role_path"] == "/tmp/repo-role"
    assert captured["forwarded_kwargs"] == {
        "compare_role_path": None,
        "style_readme_path": "README.repo.md",
        "role_name_override": "derived-role-name",
        "vars_seed_paths": None,
        "concise_readme": False,
        "scanner_report_output": None,
        "include_vars_main": True,
        "include_scanner_report_link": True,
        "readme_config_path": None,
        "adopt_heading_mode": None,
        "style_guide_skeleton": False,
        "keep_unknown_style_sections": True,
        "exclude_path_patterns": None,
        "style_source_path": None,
        "policy_config_path": None,
        "fail_on_unconstrained_dynamic_includes": None,
        "fail_on_yaml_like_task_annotations": None,
        "ignore_unresolved_internal_underscore_references": None,
        "include_collection_checks": False,
        "include_task_parameters": True,
        "include_task_runbooks": True,
        "inline_task_runbooks": True,
        "failure_policy": None,
    }


def test_fsrc_api_scan_repo_forwards_policy_config_path_to_scan_role_fn(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        class _FakeFacade:
            def run_repo_scan(self, **kwargs: object) -> object:
                scan_role_fn = kwargs["scan_role_fn"]
                assert callable(scan_role_fn)
                return scan_role_fn("/tmp/repo-role")

        monkeypatch.setattr(api_module, "_repo_scan_facade", _FakeFacade())

        def _fake_scan_role(
            role_path: str,
            **kwargs: object,
        ) -> dict[str, object]:
            captured["forwarded_role_path"] = role_path
            captured["forwarded_kwargs"] = dict(kwargs)
            return {"role_name": "repo-role"}

        monkeypatch.setattr(api_module, "scan_role", _fake_scan_role)
        payload = api_module.scan_repo(
            "https://example.invalid/demo.git",
            policy_config_path="/tmp/policy.yml",
        )

    assert payload["role_name"] == "repo-role"
    assert captured["forwarded_role_path"] == "/tmp/repo-role"
    assert captured["forwarded_kwargs"]["policy_config_path"] == "/tmp/policy.yml"


def test_fsrc_api_scan_role_forwards_non_collection_output_options(monkeypatch) -> None:
    captured: dict[str, object] = {}

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        def _fake_run_scan(role_path: str, **kwargs: object) -> dict[str, object]:
            captured["role_path"] = role_path
            captured["kwargs"] = dict(kwargs)
            return {"role_name": "demo-role", "metadata": {}}

        monkeypatch.setattr(api_module, "run_scan", _fake_run_scan)
        payload = api_module.scan_role(
            "/tmp/demo-role",
            concise_readme=True,
            scanner_report_output="reports/scanner.json",
            include_scanner_report_link=False,
        )

    assert payload == {"role_name": "demo-role", "metadata": {}}
    assert captured["role_path"] == "/tmp/demo-role"
    assert captured["kwargs"]["concise_readme"] is True
    assert captured["kwargs"]["scanner_report_output"] == "reports/scanner.json"
    assert captured["kwargs"]["include_scanner_report_link"] is False


def test_fsrc_api_scan_repo_forwards_non_collection_output_options_to_scan_role_fn(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        class _FakeFacade:
            def run_repo_scan(self, **kwargs: object) -> object:
                scan_role_fn = kwargs["scan_role_fn"]
                assert callable(scan_role_fn)
                return scan_role_fn("/tmp/repo-role", role_name_override="repo-role")

        monkeypatch.setattr(api_module, "_repo_scan_facade", _FakeFacade())

        def _fake_scan_role(
            role_path: str,
            **kwargs: object,
        ) -> dict[str, object]:
            captured["role_path"] = role_path
            captured["kwargs"] = dict(kwargs)
            return {"role_name": str(kwargs.get("role_name_override") or "role")}

        monkeypatch.setattr(api_module, "scan_role", _fake_scan_role)
        payload = api_module.scan_repo(
            "https://example.invalid/demo.git",
            concise_readme=True,
            scanner_report_output="reports/scanner.json",
            include_scanner_report_link=False,
        )

    assert payload["role_name"] == "repo-role"
    assert captured["role_path"] == "/tmp/repo-role"
    assert captured["kwargs"]["role_name_override"] == "repo-role"
    assert captured["kwargs"]["concise_readme"] is True
    assert captured["kwargs"]["scanner_report_output"] == "reports/scanner.json"
    assert captured["kwargs"]["include_scanner_report_link"] is False


def test_fsrc_cli_repo_command_uses_repo_services_and_emits_json(
    monkeypatch, capsys
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        cli_module = importlib.import_module("prism.cli")

        def fake_scan_repo(*_args: object, **_kwargs: object) -> dict[str, object]:
            return {
                "role_name": "demo-role",
                "metadata": {"style_guide": {"path": "README.md"}},
            }

        monkeypatch.setattr(cli_module.api, "scan_repo", fake_scan_repo)
        rc = cli_module.main(
            [
                "repo",
                "--repo-url",
                "https://example.invalid/demo.git",
                "--json",
            ]
        )

    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["role_name"] == "demo-role"


def _run_cli_main(lane_root: Path, argv: list[str]) -> int:
    with _prefer_prism_lane_on_sys_path(lane_root):
        cli_module = importlib.import_module("prism.cli")
        return cli_module.main(argv)


def _repo_option_contract_for_lane(
    lane_root: Path,
) -> tuple[set[str], dict[str, argparse.Action]]:
    with _prefer_prism_lane_on_sys_path(lane_root):
        cli_module = importlib.import_module("prism.cli")
        parser = cli_module.build_parser()

    subparsers_action = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    repo_parser = subparsers_action.choices["repo"]

    option_strings: set[str] = set()
    actions_by_option: dict[str, argparse.Action] = {}
    for action in repo_parser._actions:
        for option in action.option_strings:
            option_strings.add(option)
            actions_by_option[option] = action

    return option_strings, actions_by_option


def test_fsrc_repo_parser_option_contract_required_rows() -> None:
    src_options, src_actions = _repo_option_contract_for_lane(SRC_SOURCE_ROOT)
    fsrc_options, fsrc_actions = _repo_option_contract_for_lane(FSRC_SOURCE_ROOT)

    src_required_options = {
        "--repo-url",
        "--repo-role-path",
        "--repo-style-readme-path",
        "--repo-ref",
        "--repo-timeout",
        "--style-readme",
        "-f",
        "--format",
    }
    fsrc_required_options = {
        "--repo-url",
        "--repo-role-path",
        "--repo-style-readme-path",
        "--style-readme-path",
        "--repo-ref",
        "--repo-timeout",
        "--json",
    }

    assert src_required_options.issubset(src_options)
    assert fsrc_required_options.issubset(fsrc_options)
    assert src_actions["--repo-url"].required is True
    assert fsrc_actions["--repo-url"].required is True


def test_fsrc_cli_top_level_help_exit_semantics_match_src() -> None:
    src_rc = _run_cli_main(SRC_SOURCE_ROOT, ["--help"])
    fsrc_rc = _run_cli_main(FSRC_SOURCE_ROOT, ["--help"])

    assert src_rc == 0
    assert fsrc_rc == src_rc


def test_fsrc_cli_unknown_first_arg_semantics_match_src() -> None:
    src_rc = _run_cli_main(SRC_SOURCE_ROOT, ["unknown-first-arg"])
    fsrc_rc = _run_cli_main(FSRC_SOURCE_ROOT, ["unknown-first-arg"])

    assert src_rc == 2
    assert fsrc_rc == src_rc


def test_fsrc_api_run_scan_surfaces_role_notes_in_metadata(tmp_path: Path) -> None:
    role_path = tmp_path / "role"
    (role_path / "defaults").mkdir(parents=True)
    (role_path / "tasks").mkdir(parents=True)
    (role_path / "defaults" / "main.yml").write_text(
        "---\nexample_name: prism\n",
        encoding="utf-8",
    )
    (role_path / "tasks" / "main.yml").write_text(
        "# prism~note: emitted from marker comment\n"
        "- name: Use variable\n"
        "  debug:\n"
        '    msg: "{{ example_name }}"\n',
        encoding="utf-8",
    )

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        payload = api_module.run_scan(str(role_path), include_vars_main=True)

    role_notes = payload["metadata"].get("role_notes")
    assert isinstance(role_notes, dict)
    assert "emitted from marker comment" in role_notes.get("notes", [])
