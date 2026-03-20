"""Unit tests for the prism scanner CLI.

These tests exercise the package CLI by importing the local package and
invoking the entrypoint in a subprocess to simulate real usage.
"""

from pathlib import Path
import json
import pytest
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

from prism import pattern_config
from prism.pattern_config import (
    _load_yaml,
    fetch_remote_policy,
    load_pattern_config,
    write_unknown_headings_log,
)
from prism import scanner
from prism.scanner import scan_for_default_filters

HERE = Path(__file__).parent
ROLE_FIXTURES = HERE / "roles"
BASE_ROLE_FIXTURE = ROLE_FIXTURES / "base_mock_role"


def test_scan_detects_defaults(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    out = tmp_path / "output.md"
    # Run the CLI by importing the package module to avoid path assumptions
    # Import package via sys.path so installed package isn't required.
    python_code = (
        "import sys;"
        "sys.path.insert(0, '{src_dir}');"
        "from prism.cli import main;"
        "sys.exit(main(['role','{role}','-o','{out}']))"
    ).format(src_dir=str(HERE.parent.parent), role=str(target), out=str(out))

    cmd = [sys.executable, "-c", python_code]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode != 0:
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)

    assert res.returncode == 0
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Default value 1" in content
    assert ("Default value 3" in content) or ("default(" in content)
    assert "Nested default value" in content
    assert "Deep default value" in content


def test_scan_follows_nested_task_includes(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    found = scan_for_default_filters(str(target))

    args = "\n".join(item["args"] for item in found)
    files = {item["file"] for item in found}

    assert "Nested default value" in args
    assert "Deep default value" in args
    assert "tasks/nested/setup.yml" in files
    assert "tasks/nested/deeper.yml" in files


def test_scan_detects_default_filter_via_jinja_ast(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "main.yml").write_text(
        "---\n"
        "- name: AST default\n"
        "  debug:\n"
        "    msg: \"{{ primary_value | default(lookup('env', 'PRIMARY_VALUE')) | trim }}\"\n",
        encoding="utf-8",
    )

    found = scan_for_default_filters(str(role))

    assert any(item["line_no"] == 4 for item in found)
    assert any("lookup" in item["args"] for item in found)


def test_scan_ast_default_filter_renders_complex_target_match(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "main.yml").write_text(
        "---\n"
        "- name: Complex AST default\n"
        "  debug:\n"
        '    msg: "{{ service_map[service_name].port | default(8080) }}"\n',
        encoding="utf-8",
    )

    found = scan_for_default_filters(str(role))

    assert any(
        item["match"] == "service_map[service_name].port | default(8080)"
        for item in found
    )
    assert any(item["args"] == "8080" for item in found)


def test_scan_default_filter_falls_back_to_regex_when_jinja_parse_fails(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "main.yml").write_text(
        "---\n"
        "- name: Broken Jinja fallback\n"
        "  debug:\n"
        "    msg: \"{{ broken_value | default('fallback value') \"\n",
        encoding="utf-8",
    )

    found = scan_for_default_filters(str(role))

    assert any("fallback value" in item["args"] for item in found)
    assert any(item["file"] == "tasks/main.yml" for item in found)


def test_scan_default_filter_deduplicates_ast_and_regex_results(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "main.yml").write_text(
        "---\n"
        "- name: Duplicate suppression\n"
        "  debug:\n"
        "    msg: \"{{ username | default('admin') }}\"\n",
        encoding="utf-8",
    )

    found = scan_for_default_filters(str(role))
    matches = [item for item in found if item["file"] == "tasks/main.yml"]

    assert len(matches) == 1
    assert matches[0]["args"] == "admin"


def test_collect_referenced_variable_names_uses_jinja_ast(tmp_path):
    role = tmp_path / "role"
    templates = role / "templates"
    tasks = role / "tasks"
    templates.mkdir(parents=True)
    tasks.mkdir(parents=True)

    (tasks / "main.yml").write_text(
        "---\n"
        "- name: Template task\n"
        "  template:\n"
        "    src: app.j2\n"
        "    dest: /tmp/app\n",
        encoding="utf-8",
    )
    (templates / "app.j2").write_text(
        "{{ lookup('env', required_api_token) }}\n",
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    by_name = {row["name"]: row for row in rows}

    assert "required_api_token" in by_name
    assert by_name["required_api_token"]["required"] is True
    assert by_name["required_api_token"]["documented"] is False


def test_collect_referenced_variable_names_uses_jinja_ast_scope_rules(tmp_path):
    role = tmp_path / "role"
    templates = role / "templates"
    tasks = role / "tasks"
    templates.mkdir(parents=True)
    tasks.mkdir(parents=True)

    (tasks / "main.yml").write_text(
        "---\n"
        "- name: Template task\n"
        "  template:\n"
        "    src: app.j2\n"
        "    dest: /tmp/app\n",
        encoding="utf-8",
    )
    (templates / "app.j2").write_text(
        "{% for item in servers %}\n"
        "{{ item.name | default(fallback_name) }}\n"
        "{{ ansible_host }}\n"
        "{% endfor %}\n",
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    names = {row["name"] for row in rows}

    assert "servers" in names
    assert "fallback_name" in names
    assert "item" not in names
    assert "ansible_host" not in names


def test_collect_referenced_variable_names_handles_unknown_jinja_filters(tmp_path):
    role = tmp_path / "role"
    templates = role / "templates"
    tasks = role / "tasks"
    templates.mkdir(parents=True)
    tasks.mkdir(parents=True)

    (tasks / "main.yml").write_text(
        "---\n"
        "- name: Template task\n"
        "  template:\n"
        "    src: app.j2\n"
        "    dest: /tmp/app\n",
        encoding="utf-8",
    )
    (templates / "app.j2").write_text(
        "{{ enabled_state | ternary('enabled', 'disabled') }}\n"
        "{{ config_payload | to_nice_yaml(indent=2) }}\n",
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    by_name = {row["name"]: row for row in rows}

    assert "enabled_state" in by_name
    assert by_name["enabled_state"]["required"] is True
    assert "config_payload" in by_name
    assert by_name["config_payload"]["required"] is True


def test_build_variable_insights_reads_documented_inputs_from_readme(tmp_path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)
    (role / "tasks" / "main.yml").write_text(
        "---\n"
        "- name: Use documented variable\n"
        "  debug:\n"
        '    msg: "{{ documented_api_token }}"\n',
        encoding="utf-8",
    )
    (role / "README.md").write_text(
        "Role Name\n"
        "=========\n\n"
        "Role Variables\n"
        "--------------\n\n"
        "| Name | Description |\n"
        "| --- | --- |\n"
        "| `documented_api_token` | API token for remote service |\n",
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    by_name = {row["name"]: row for row in rows}

    assert "documented_api_token" in by_name
    assert by_name["documented_api_token"]["documented"] is True
    assert by_name["documented_api_token"]["required"] is False
    assert by_name["documented_api_token"]["source"] == "README.md (documented input)"


def test_collect_task_files_falls_back_without_main_yml(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    tasks.mkdir(parents=True)
    alt = tasks / "bootstrap.yaml"
    alt.write_text(
        "---\n- name: Bootstrap\n  debug:\n    msg: \"{{ fallback_var | default('fallback value') }}\"\n",
        encoding="utf-8",
    )

    discovered = scanner._collect_task_files(role)
    found = scan_for_default_filters(str(role))

    assert discovered == [alt.resolve()]
    assert any(item["file"] == "tasks/bootstrap.yaml" for item in found)
    assert any("fallback value" in item["args"] for item in found)


def test_iter_task_include_targets_supports_dict_forms_and_nested_blocks():
    data = [
        {"include_tasks": {"file": "nested/from-file.yml"}},
        {"block": [{"import_tasks": {"_raw_params": "nested/from-raw.yml"}}]},
        {"name": "No include here", "debug": {"msg": "ok"}},
    ]

    targets = scanner._iter_task_include_targets(data)

    assert targets == ["nested/from-file.yml", "nested/from-raw.yml"]


def test_resolve_task_include_ignores_dynamic_or_outside_paths(tmp_path):
    role = tmp_path / "role"
    current = role / "tasks" / "main.yml"
    current.parent.mkdir(parents=True)
    current.write_text("---\n", encoding="utf-8")

    outside = tmp_path / "outside.yml"
    outside.write_text("---\n", encoding="utf-8")

    assert scanner._resolve_task_include(role, current, "{{ dynamic_target }}") is None
    assert (
        scanner._resolve_task_include(role, current, "{% if cond %}x.yml{% endif %}")
        is None
    )
    assert scanner._resolve_task_include(role, current, str(outside)) is None


def test_load_yaml_file_returns_none_for_malformed_yaml(tmp_path):
    broken = tmp_path / "broken.yml"
    broken.write_text("---\nfoo: [unterminated\n", encoding="utf-8")

    assert scanner._load_yaml_file(broken) is None


def test_load_meta_and_requirements_ignore_malformed_yaml(tmp_path):
    role = tmp_path / "role"
    meta_dir = role / "meta"
    meta_dir.mkdir(parents=True)
    (meta_dir / "main.yml").write_text("galaxy_info: [broken\n", encoding="utf-8")
    (meta_dir / "requirements.yml").write_text(
        "- src: good\n  version: [broken\n", encoding="utf-8"
    )

    assert scanner.load_meta(str(role)) == {}
    assert scanner.load_requirements(str(role)) == []


def test_load_variables_and_variable_insights_handle_empty_or_malformed_files(tmp_path):
    role = tmp_path / "role"
    defaults_dir = role / "defaults"
    vars_dir = role / "vars"
    defaults_dir.mkdir(parents=True)
    vars_dir.mkdir(parents=True)

    (defaults_dir / "main.yml").write_text("", encoding="utf-8")
    (vars_dir / "main.yml").write_text("bad: [broken\n", encoding="utf-8")

    assert scanner.load_variables(str(role)) == {}
    assert scanner.build_variable_insights(str(role)) == []


def test_collect_readme_input_variables_ignores_non_utf8_readme(tmp_path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)
    (role / "tasks" / "main.yml").write_text("---\n", encoding="utf-8")
    # Invalid UTF-8 bytes should be ignored instead of aborting the scan.
    (role / "README.md").write_bytes(b"\xff\xfe\x00\x00")

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)

    assert isinstance(rows, list)
    assert rows == []


def test_load_meta_requirements_and_variables_ignore_read_errors(tmp_path, monkeypatch):
    role = tmp_path / "role"
    (role / "meta").mkdir(parents=True)
    (role / "defaults").mkdir(parents=True)
    (role / "vars").mkdir(parents=True)

    (role / "meta" / "main.yml").write_text("galaxy_info: {}\n", encoding="utf-8")
    (role / "meta" / "requirements.yml").write_text("- src: x\n", encoding="utf-8")
    (role / "defaults" / "main.yml").write_text("a: 1\n", encoding="utf-8")
    (role / "vars" / "main.yml").write_text("b: 2\n", encoding="utf-8")

    original_read_text = Path.read_text

    def flaky_read_text(self: Path, *args, **kwargs):
        if self.name in {"main.yml", "requirements.yml"} and self.parent.name in {
            "meta",
            "defaults",
            "vars",
        }:
            raise OSError("permission denied")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", flaky_read_text)

    assert scanner.load_meta(str(role)) == {}
    assert scanner.load_requirements(str(role)) == []
    assert scanner.load_variables(str(role)) == {}


def test_load_variables_defaults_only_excludes_vars_main(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    loaded = scanner.load_variables(str(target), include_vars_main=False)

    assert "variable1" in loaded
    assert "variable2" in loaded
    assert "variable3" not in loaded
    assert "variable4" not in loaded


def test_build_variable_insights_defaults_only_excludes_vars_main_rows(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    rows = scanner.build_variable_insights(str(target), include_vars_main=False)
    names = {row["name"] for row in rows}

    assert "variable1" in names
    assert "variable2" in names
    assert "variable3" not in names
    assert "variable4" not in names


def test_collect_role_contents_and_features_handle_sparse_role(tmp_path):
    role = tmp_path / "role"
    (role / "templates").mkdir(parents=True)
    (role / "templates" / "only.j2").write_text("hello", encoding="utf-8")

    contents = scanner.collect_role_contents(str(role))

    assert contents["tasks"] == []
    assert contents["templates"] == ["templates/only.j2"]
    assert contents["features"]["task_files_scanned"] == 0
    assert contents["features"]["tasks_scanned"] == 0


def test_extract_role_features_tracks_included_roles(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "main.yml").write_text(
        "---\n"
        "- name: include role by dict\n"
        "  include_role:\n"
        "    name: acme.common\n"
        "- name: import role by fqcn\n"
        "  ansible.builtin.import_role:\n"
        "    name: acme.web\n"
        "- name: dynamic include ignored\n"
        "  import_role:\n"
        '    name: "{{ dynamic_role_name }}"\n',
        encoding="utf-8",
    )

    features = scanner.extract_role_features(str(role))

    assert features["included_role_calls"] == 2
    assert features["included_roles"] == "acme.common, acme.web"
    assert features["dynamic_included_role_calls"] == 1
    assert features["dynamic_included_roles"] == "{{ dynamic_role_name }}"


def test_collect_task_handler_catalog_follows_dict_style_task_includes(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    tasks.mkdir(parents=True)

    (tasks / "main.yml").write_text(
        "---\n"
        "- name: include nested by dict\n"
        "  include_tasks:\n"
        '    file: "nested.yml"\n',
        encoding="utf-8",
    )
    (tasks / "nested.yml").write_text(
        "---\n" "- name: nested task\n" "  debug:\n" '    msg: "ok"\n',
        encoding="utf-8",
    )

    task_catalog, _ = scanner._collect_task_handler_catalog(str(role))

    assert [entry["name"] for entry in task_catalog] == [
        "include nested by dict",
        "nested task",
    ]


def test_collect_task_handler_catalog_normalizes_role_include_module_and_parameters(
    tmp_path,
):
    role = tmp_path / "role"
    tasks = role / "tasks"
    tasks.mkdir(parents=True)

    (tasks / "main.yml").write_text(
        "---\n"
        "- name: include common role\n"
        "  include_role:\n"
        "    name: acme.common\n"
        "- name: import fqcn role\n"
        "  ansible.builtin.import_role:\n"
        "    name: acme.web\n",
        encoding="utf-8",
    )

    task_catalog, _ = scanner._collect_task_handler_catalog(str(role))

    by_name = {entry["name"]: entry for entry in task_catalog}
    assert by_name["include common role"]["module"] == "include_role"
    assert by_name["include common role"]["parameters"] == "name=acme.common"
    assert by_name["import fqcn role"]["module"] == "import_role"
    assert by_name["import fqcn role"]["parameters"] == "name=acme.web"


def test_build_variable_insights_detects_required_undocumented_vars(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    rows = scanner.build_variable_insights(str(target))
    by_name = {row["name"]: row for row in rows}

    assert "required_input_var" in by_name
    assert by_name["required_input_var"]["documented"] is False
    assert by_name["required_input_var"]["required"] is True
    assert by_name["required_input_var"]["source"] == "inferred usage"

    assert "required_endpoint" in by_name
    assert by_name["required_endpoint"]["required"] is True

    assert "required_api_token" in by_name
    assert by_name["required_api_token"]["required"] is True
    assert by_name["required_api_token"]["secret"] is False
    assert by_name["required_api_token"]["default"] == "<required>"


def test_build_variable_insights_seed_vars_reduce_required_and_mark_secret(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    seed_dir = target / "tests" / "group_vars"
    rows = scanner.build_variable_insights(str(target), seed_paths=[str(seed_dir)])
    by_name = {row["name"]: row for row in rows}

    assert by_name["required_endpoint"]["required"] is False
    assert by_name["required_endpoint"]["source"].startswith("seed:")

    assert by_name["required_api_token"]["required"] is False
    assert by_name["required_api_token"]["secret"] is True
    assert by_name["required_api_token"]["default"] == "<secret>"


def test_run_scan_redacts_secret_like_default_filter_values(tmp_path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)
    (role / "tasks" / "main.yml").write_text(
        "---\n"
        "- name: Secret fallback\n"
        "  debug:\n"
        "    msg: \"{{ api_secret | default('TopSecret123') }}\"\n",
        encoding="utf-8",
    )

    out = tmp_path / "README.md"
    scanner.run_scan(str(role), output=str(out))
    content = out.read_text(encoding="utf-8")

    assert "TopSecret123" not in content
    assert "api_secret | default(<secret>)" in content
    assert "args: `<secret>`" in content


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

    monkeypatch.setattr(pattern_config, "SYSTEM_PATTERN_OVERRIDE_PATH", system_override)
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

    monkeypatch.setattr(pattern_config, "SYSTEM_PATTERN_OVERRIDE_PATH", system_override)
    monkeypatch.setenv(pattern_config.XDG_DATA_HOME_ENV, str(xdg_home))
    monkeypatch.setenv(pattern_config.ENV_PATTERNS_OVERRIDE_PATH, str(env_override))
    monkeypatch.chdir(tmp_path)

    implicit = load_pattern_config()
    explicit = load_pattern_config(override_path=explicit_override)

    assert implicit["sensitivity"]["name_tokens"] == ["from_env"]
    assert explicit["sensitivity"]["name_tokens"] == ["from_explicit"]


def test_build_variable_insights_include_provenance_fields(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    rows = scanner.build_variable_insights(str(target))
    row = next(item for item in rows if item["name"] == "variable1")

    assert row["provenance_source_file"] == "defaults/main.yml"
    assert isinstance(row["provenance_line"], int)
    assert row["provenance_confidence"] >= 0.9
    assert row["is_unresolved"] is False


def test_build_variable_insights_marks_override_as_ambiguous(tmp_path):
    role = tmp_path / "role"
    (role / "defaults").mkdir(parents=True)
    (role / "vars").mkdir(parents=True)
    (role / "tasks").mkdir(parents=True)
    (role / "tasks" / "main.yml").write_text("---\n", encoding="utf-8")
    (role / "defaults" / "main.yml").write_text("shared_value: 1\n", encoding="utf-8")
    (role / "vars" / "main.yml").write_text("shared_value: 2\n", encoding="utf-8")

    rows = scanner.build_variable_insights(str(role))
    row = next(item for item in rows if item["name"] == "shared_value")

    assert row["is_ambiguous"] is True
    assert row["provenance_source_file"] == "vars/main.yml"
    assert 0.7 <= row["provenance_confidence"] < 0.9


def test_build_variable_insights_mentions_dynamic_include_vars_uncertainty(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    templates = role / "templates"
    tasks.mkdir(parents=True)
    templates.mkdir(parents=True)

    (tasks / "main.yml").write_text(
        "---\n"
        "- name: dynamic include\n"
        '  include_vars: "{{ var_file }}"\n'
        "- name: use unresolved\n"
        "  debug:\n"
        '    msg: "{{ unresolved_name }}"\n',
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    unresolved = next(item for item in rows if item["name"] == "unresolved_name")

    assert unresolved["is_unresolved"] is True
    assert "Dynamic include_vars" in unresolved["uncertainty_reason"]


def test_build_variable_insights_reads_meta_argument_specs_file(tmp_path):
    role = tmp_path / "role"
    (role / "meta").mkdir(parents=True)
    (role / "tasks").mkdir(parents=True)
    (role / "tasks" / "main.yml").write_text("---\n", encoding="utf-8")
    (role / "meta" / "argument_specs.yml").write_text(
        "argument_specs:\n"
        "  main:\n"
        "    options:\n"
        "      arg_required:\n"
        "        type: str\n"
        "        required: true\n"
        "      arg_with_default:\n"
        "        type: int\n"
        "        default: 5\n",
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role))
    by_name = {row["name"]: row for row in rows}

    required = by_name["arg_required"]
    assert required["source"] == "meta/argument_specs.yml (argument_specs)"
    assert required["required"] is True
    assert required["is_unresolved"] is True
    assert required["default"] == "<required>"
    assert "argument_specs" in required["uncertainty_reason"]

    with_default = by_name["arg_with_default"]
    assert with_default["source"] == "meta/argument_specs.yml (argument_specs)"
    assert with_default["required"] is False
    assert with_default["is_unresolved"] is False
    assert with_default["default"] == "5"
    assert with_default["type"] == "int"


def test_build_variable_insights_reads_meta_main_embedded_argument_specs(tmp_path):
    role = tmp_path / "role"
    (role / "meta").mkdir(parents=True)
    (role / "tasks").mkdir(parents=True)
    (role / "tasks" / "main.yml").write_text("---\n", encoding="utf-8")
    (role / "meta" / "main.yml").write_text(
        "argument_specs:\n"
        "  main:\n"
        "    options:\n"
        "      embedded_opt:\n"
        "        type: bool\n"
        "        default: true\n",
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role))
    row = next(item for item in rows if item["name"] == "embedded_opt")

    assert row["source"] == "meta/main.yml (argument_specs)"
    assert row["type"] == "bool"
    assert row["required"] is False
    assert row["is_unresolved"] is False


def test_extract_role_notes_from_comments(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "main.yml").write_text(
        "---\n"
        "# <notes> Warning: This package is unhealthy\n"
        "# <notes> Deprecated: old parameter is deprecated\n"
        "# <notes> Note: run with --check first\n"
        "# <notes> Additional: keep inventory in sync\n"
        "# <notes> this is also a free-form note\n",
        encoding="utf-8",
    )

    notes = scanner._extract_role_notes_from_comments(str(role))

    assert notes["warnings"] == ["This package is unhealthy"]
    assert notes["deprecations"] == ["old parameter is deprecated"]
    assert notes["notes"] == ["run with --check first", "this is also a free-form note"]
    assert notes["additionals"] == ["keep inventory in sync"]


def test_extract_role_notes_from_short_aliases(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "main.yml").write_text(
        "---\n"
        "#w# package is unhealthy\n"
        "#d# old parameter is deprecated\n"
        "#n# run with --check first\n"
        "#a# keep inventory in sync\n",
        encoding="utf-8",
    )

    notes = scanner._extract_role_notes_from_comments(str(role))

    assert notes["warnings"] == ["package is unhealthy"]
    assert notes["deprecations"] == ["old parameter is deprecated"]
    assert notes["notes"] == ["run with --check first"]
    assert notes["additionals"] == ["keep inventory in sync"]


def test_extract_task_annotations_for_file_supports_short_and_explicit():
    lines = [
        "---",
        "#t# Runbook: verify template syntax",
        "- name: Deploy app",
        "  ansible.builtin.template:",
        "    src: app.conf.j2",
        "#t(Deploy app)# Warning: verify permissions manually",
        "#t# note: check service health",
    ]

    implicit, explicit = scanner._extract_task_annotations_for_file(lines)

    assert implicit == [
        {"kind": "runbook", "text": "verify template syntax"},
        {"kind": "note", "text": "check service health"},
    ]
    assert explicit["Deploy app"] == [
        {"kind": "warning", "text": "verify permissions manually"}
    ]


def test_collect_task_handler_catalog_attaches_annotation_metadata(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    handlers = role / "handlers"
    tasks.mkdir(parents=True)
    handlers.mkdir(parents=True)

    (tasks / "main.yml").write_text(
        "---\n"
        "#t# Runbook: fallback to manual copy if automation fails\n"
        "- name: Deploy app\n"
        "  ansible.builtin.template:\n"
        "    src: app.conf.j2\n"
        "    dest: /etc/app.conf\n",
        encoding="utf-8",
    )
    (handlers / "main.yml").write_text(
        "---\n"
        "- name: Restart app\n"
        "  ansible.builtin.service:\n"
        "    name: app\n"
        "    state: restarted\n",
        encoding="utf-8",
    )

    task_catalog, handler_catalog = scanner._collect_task_handler_catalog(str(role))

    assert task_catalog[0]["runbook"] == "fallback to manual copy if automation fails"
    assert task_catalog[0]["annotations"] == [
        {"kind": "runbook", "text": "fallback to manual copy if automation fails"}
    ]
    assert task_catalog[0]["anchor"].startswith("task-main-yml-deploy-app")
    assert handler_catalog[0]["anchor"].startswith("task-main-yml-restart-app")


def test_extract_scanner_counters_groups_by_confidence_and_status():
    counters = scanner._extract_scanner_counters(
        [
            {
                "documented": True,
                "is_unresolved": False,
                "is_ambiguous": False,
                "secret": False,
                "required": False,
                "provenance_confidence": 0.95,
            },
            {
                "documented": False,
                "is_unresolved": True,
                "is_ambiguous": True,
                "secret": True,
                "required": True,
                "provenance_confidence": 0.65,
            },
        ],
        [{"file": "tasks/main.yml", "line_no": 3, "match": "x", "args": "y"}],
    )

    assert counters["total_variables"] == 2
    assert counters["documented_variables"] == 1
    assert counters["undocumented_variables"] == 1
    assert counters["unresolved_variables"] == 1
    assert counters["ambiguous_variables"] == 1
    assert counters["secret_variables"] == 1
    assert counters["required_variables"] == 1
    assert counters["high_confidence_variables"] == 1
    assert counters["low_confidence_variables"] == 1
    assert counters["undocumented_default_filters"] == 1
    assert counters["provenance_issue_categories"]["ambiguous_set_fact_runtime"] == 0
    assert (
        counters["provenance_issue_categories"]["unresolved_no_static_definition"] == 0
    )


def test_extract_scanner_counters_categorizes_provenance_issues():
    counters = scanner._extract_scanner_counters(
        [
            {
                "documented": True,
                "is_unresolved": False,
                "is_ambiguous": True,
                "secret": False,
                "required": False,
                "provenance_confidence": 0.8,
                "uncertainty_reason": "Overridden by vars/main.yml precedence.",
            },
            {
                "documented": True,
                "is_unresolved": False,
                "is_ambiguous": True,
                "secret": False,
                "required": False,
                "provenance_confidence": 0.65,
                "uncertainty_reason": "Computed by set_fact at runtime.",
            },
            {
                "documented": False,
                "is_unresolved": True,
                "is_ambiguous": False,
                "secret": False,
                "required": True,
                "provenance_confidence": 0.4,
                "uncertainty_reason": "Referenced in role but no static definition found.",
            },
            {
                "documented": True,
                "is_unresolved": True,
                "is_ambiguous": False,
                "secret": False,
                "required": False,
                "provenance_confidence": 0.5,
                "source": "README.md (documented input)",
                "uncertainty_reason": "Documented in README; static role definition not found.",
            },
        ],
        [],
    )

    categories = counters["provenance_issue_categories"]
    assert categories["ambiguous_defaults_vars_override"] == 1
    assert categories["ambiguous_set_fact_runtime"] == 1
    assert categories["unresolved_no_static_definition"] == 1
    assert categories["unresolved_readme_documented_only"] == 1


def test_extract_scanner_counters_includes_role_include_observability():
    counters = scanner._extract_scanner_counters(
        [],
        [],
        {
            "included_role_calls": 3,
            "dynamic_included_role_calls": 2,
        },
    )

    assert counters["included_role_calls"] == 3
    assert counters["dynamic_included_role_calls"] == 2


def test_collect_yaml_parse_failures_reports_file_and_line(tmp_path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)
    bad = role / "tasks" / "broken.yml"
    bad.write_text("---\nfoo: [unterminated\n", encoding="utf-8")

    failures = scanner._collect_yaml_parse_failures(str(role))

    assert len(failures) == 1
    assert failures[0]["file"] == "tasks/broken.yml"
    assert isinstance(failures[0]["line"], int)
    assert failures[0]["line"] >= 2
    assert failures[0]["column"] is not None
    assert "expected" in str(failures[0]["error"]).lower()


def test_extract_scanner_counters_includes_yaml_parse_failure_count():
    counters = scanner._extract_scanner_counters(
        [],
        [],
        {},
        [
            {
                "file": "tasks/broken.yml",
                "line": 2,
                "column": 5,
                "error": "expected ',' or ']'",
            }
        ],
    )

    assert counters["yaml_parse_failures"] == 1


def test_scan_for_default_filters_respects_exclude_paths(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "main.yml").write_text(
        "---\n- name: Included\n  debug:\n    msg: \"{{ keep_me | default('ok') }}\"\n",
        encoding="utf-8",
    )

    found_all = scanner.scan_for_default_filters(str(role))
    found_excluded = scanner.scan_for_default_filters(
        str(role),
        exclude_paths=["tasks/**"],
    )

    assert len(found_all) == 1
    assert found_excluded == []


def test_build_variable_insights_respects_exclude_paths(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    templates = role / "templates"
    tasks.mkdir(parents=True)
    templates.mkdir(parents=True)
    (tasks / "main.yml").write_text(
        "---\n- name: Render\n  template:\n    src: app.j2\n    dest: /tmp/app\n",
        encoding="utf-8",
    )
    (templates / "app.j2").write_text("{{ template_only_var }}\n", encoding="utf-8")

    rows_all = scanner.build_variable_insights(str(role), include_vars_main=False)
    rows_excluded = scanner.build_variable_insights(
        str(role),
        include_vars_main=False,
        exclude_paths=["templates/**"],
    )

    names_all = {row["name"] for row in rows_all}
    names_excluded = {row["name"] for row in rows_excluded}
    assert "template_only_var" in names_all
    assert "template_only_var" not in names_excluded


def test_collect_referenced_variable_names_handles_macros_and_control_flow(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    templates = role / "templates"
    tasks.mkdir(parents=True)
    templates.mkdir(parents=True)

    (tasks / "main.yml").write_text(
        "---\n"
        "- name: Render config\n"
        "  template:\n"
        "    src: app.j2\n"
        "    dest: /tmp/app.conf\n",
        encoding="utf-8",
    )
    (templates / "app.j2").write_text(
        "{% macro render_item(item) -%}\n"
        "{{ item.name | default(fallback_name) }}\n"
        "{%- endmacro %}\n"
        "{% for host in target_hosts %}\n"
        "{{ render_item(host) }}\n"
        "{% endfor %}\n",
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    names = {row["name"] for row in rows}

    assert "target_hosts" in names
    assert "fallback_name" in names
    assert "item" not in names
    assert "host" not in names


def test_scan_file_for_default_filters_returns_empty_on_oserror(tmp_path, monkeypatch):
    role = tmp_path / "role"
    role.mkdir(parents=True)
    target_file = role / "tasks.yml"
    target_file.write_text("---\n", encoding="utf-8")

    original_read_text = Path.read_text

    def fake_read_text(self, encoding="utf-8"):
        if self == target_file:
            raise OSError("read failure")
        return original_read_text(self, encoding=encoding)

    monkeypatch.setattr(Path, "read_text", fake_read_text)

    rows = scanner._scan_file_for_default_filters(target_file, role)
    assert rows == []


def test_scanner_style_heading_alias_helpers_delegate(monkeypatch):
    monkeypatch.setattr(scanner, "normalize_style_heading", lambda value: f"n:{value}")
    monkeypatch.setattr(
        scanner,
        "detect_style_section_level",
        lambda lines: 3 if lines else 2,
    )
    monkeypatch.setattr(
        scanner,
        "format_heading",
        lambda text, level, style: f"{style}:{level}:{text}",
    )

    assert scanner._normalize_style_heading("Role Variables") == "n:Role Variables"
    assert scanner._detect_style_section_level(["## Title"]) == 3
    assert scanner._format_heading("Role Variables", 2, "atx") == "atx:2:Role Variables"


def test_default_style_guide_user_paths_respects_xdg(monkeypatch):
    monkeypatch.setenv(scanner.XDG_DATA_HOME_ENV, "/tmp/xdg-data")

    paths = scanner._default_style_guide_user_paths()

    assert str(paths[0]).endswith("/tmp/xdg-data/prism/STYLE_GUIDE_SOURCE.md")
    assert str(paths[1]).endswith(
        "/tmp/xdg-data/ansible_role_doc/STYLE_GUIDE_SOURCE.md"
    )


def test_default_style_guide_user_paths_falls_back_to_local_share(monkeypatch):
    monkeypatch.delenv(scanner.XDG_DATA_HOME_ENV, raising=False)

    paths = scanner._default_style_guide_user_paths()

    assert str(paths[0]).endswith("/.local/share/prism/STYLE_GUIDE_SOURCE.md")
    assert str(paths[1]).endswith(
        "/.local/share/ansible_role_doc/STYLE_GUIDE_SOURCE.md"
    )


def test_resolve_default_style_guide_source_explicit_path_branches(tmp_path):
    existing = tmp_path / "STYLE_GUIDE_SOURCE.md"
    existing.write_text("# Style\n", encoding="utf-8")

    resolved = scanner.resolve_default_style_guide_source(str(existing))
    assert resolved == str(existing.resolve())

    with pytest.raises(FileNotFoundError):
        scanner.resolve_default_style_guide_source(str(tmp_path / "missing.md"))


def test_resolve_default_style_guide_source_falls_back_when_no_candidates(monkeypatch):
    monkeypatch.setenv(scanner.ENV_STYLE_GUIDE_SOURCE_PATH, "")
    monkeypatch.setenv(scanner.LEGACY_ENV_STYLE_GUIDE_SOURCE_PATH, "")
    monkeypatch.setattr(Path, "is_file", lambda self: False)

    resolved = scanner.resolve_default_style_guide_source()

    assert resolved == str(scanner.DEFAULT_STYLE_GUIDE_SOURCE_PATH.resolve())


def test_collect_molecule_scenarios_ignores_malformed_and_excluded_files(tmp_path):
    role = tmp_path / "role"
    valid = role / "molecule" / "default"
    broken = role / "molecule" / "broken"
    hidden = role / "molecule" / "skipme"
    valid.mkdir(parents=True)
    broken.mkdir(parents=True)
    hidden.mkdir(parents=True)

    (valid / "molecule.yml").write_text(
        "---\n"
        "driver:\n"
        "  name: podman\n"
        "verifier:\n"
        "  name: ansible\n"
        "platforms:\n"
        "  - name: fedora\n"
        "    image: quay.io/fedora:latest\n",
        encoding="utf-8",
    )
    (broken / "molecule.yml").write_text("driver: [broken\n", encoding="utf-8")
    (hidden / "molecule.yml").write_text(
        "---\ndriver:\n  name: docker\n",
        encoding="utf-8",
    )

    scenarios = scanner._collect_molecule_scenarios(
        str(role),
        exclude_paths=["molecule/skipme/**"],
    )

    assert scenarios == [
        {
            "name": "default",
            "driver": "podman",
            "verifier": "ansible",
            "platforms": ["fedora (quay.io/fedora:latest)"],
            "path": "molecule/default/molecule.yml",
        }
    ]


def test_scan_file_for_default_filters_deduplicates_duplicate_ast_rows(
    tmp_path, monkeypatch
):
    role = tmp_path / "role"
    role.mkdir(parents=True)
    target = role / "tasks.yml"
    target.write_text("{{ x | default('y') }}\n", encoding="utf-8")

    duplicate_rows = [
        {"line_no": 1, "line": "l", "match": "x | default(y)", "args": "y"},
        {"line_no": 1, "line": "l", "match": "x | default(y)", "args": "y"},
    ]
    monkeypatch.setattr(
        scanner,
        "_scan_text_for_default_filters_with_ast",
        lambda text, lines: duplicate_rows,
    )

    rows = scanner._scan_file_for_default_filters(target, role)

    assert len(rows) == 1


def test_scan_file_for_default_filters_deduplicates_duplicate_regex_matches(
    tmp_path, monkeypatch
):
    role = tmp_path / "role"
    role.mkdir(parents=True)
    target = role / "tasks.yml"
    target.write_text("no jinja but defaults\n", encoding="utf-8")

    class _FakeMatch:
        def group(self, key):
            return "fallback" if key == "args" else None

        def start(self):
            return 0

        def end(self):
            return 8

    class _FakeRegex:
        def finditer(self, line):
            return [_FakeMatch(), _FakeMatch()]

    monkeypatch.setattr(
        scanner, "_scan_text_for_default_filters_with_ast", lambda *_: []
    )
    monkeypatch.setattr(scanner, "DEFAULT_RE", _FakeRegex())

    rows = scanner._scan_file_for_default_filters(target, role)

    assert len(rows) == 1


def test_collect_yaml_parse_failures_read_and_problem_fallback_paths(
    tmp_path, monkeypatch
):
    role = tmp_path / "role"
    tasks = role / "tasks"
    tasks.mkdir(parents=True)
    read_fail = tasks / "read_fail.yml"
    parse_fail = tasks / "parse_fail.yml"
    read_fail.write_text("x: 1\n", encoding="utf-8")
    parse_fail.write_text("x: 2\n", encoding="utf-8")

    original_read_text = Path.read_text

    def fake_read_text(self, encoding="utf-8"):
        if self == read_fail:
            raise OSError("denied")
        return original_read_text(self, encoding=encoding)

    def fake_safe_load(text):
        raise scanner.yaml.YAMLError("plain parser failure")

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    monkeypatch.setattr(scanner.yaml, "safe_load", fake_safe_load)

    failures = scanner._collect_yaml_parse_failures(str(role))
    by_file = {row["file"]: row for row in failures}

    assert "tasks/read_fail.yml" in by_file
    assert str(by_file["tasks/read_fail.yml"]["error"]).startswith("read_error:")
    assert "tasks/parse_fail.yml" in by_file
    assert by_file["tasks/parse_fail.yml"]["error"] == "plain parser failure"


def test_readme_variable_heading_and_blank_text_helpers(monkeypatch):
    monkeypatch.setattr(scanner, "normalize_style_heading", lambda title: "")
    assert scanner._is_readme_variable_section_heading("Variables") is False
    assert scanner._extract_readme_input_variables("   \n\n") == set()


def test_collect_task_handler_catalog_handles_empty_or_non_task_docs(tmp_path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)
    (role / "handlers").mkdir(parents=True)

    # Dict-shaped YAML should be ignored by task iterator and not raise.
    (role / "tasks" / "main.yml").write_text("a: b\n", encoding="utf-8")
    # Non-list handler file should also be ignored.
    (role / "handlers" / "main.yml").write_text("handler: true\n", encoding="utf-8")

    task_catalog, handler_catalog = scanner._collect_task_handler_catalog(str(role))

    assert task_catalog == []
    assert handler_catalog == []


def test_compact_task_parameters_formats_dict_values():
    task = {
        "ansible.builtin.service": {
            "name": "demo",
            "state": "started",
            "enabled": True,
            "daemon_reload": False,
            "masked": False,
        }
    }

    rendered = scanner._compact_task_parameters(task, "ansible.builtin.service")

    assert "state=started" in rendered
    assert "enabled=true" in rendered
    assert rendered.endswith("...")


def test_detect_task_module_normalizes_role_include_keys():
    assert (
        scanner._detect_task_module({"include_role": {"name": "acme.common"}})
        == "include_role"
    )
    assert (
        scanner._detect_task_module(
            {"ansible.builtin.import_role": {"name": "acme.web"}}
        )
        == "import_role"
    )


def test_compact_task_parameters_handles_role_include_string_and_raw_params():
    short_task = {"include_role": "acme.common"}
    fqcn_task = {"ansible.builtin.import_role": {"_raw_params": "acme.web"}}

    short_rendered = scanner._compact_task_parameters(short_task, "include_role")
    fqcn_rendered = scanner._compact_task_parameters(fqcn_task, "import_role")

    assert short_rendered == "name=acme.common"
    assert fqcn_rendered == "name=acme.web"


def test_collect_task_handler_catalog_skips_dynamic_dict_include_path(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    tasks.mkdir(parents=True)

    (tasks / "main.yml").write_text(
        "---\n"
        "- name: include dynamic path\n"
        "  include_tasks:\n"
        '    file: "{{ dynamic_task_file }}"\n'
        "- name: second static task\n"
        "  debug:\n"
        '    msg: "ok"\n',
        encoding="utf-8",
    )
    (tasks / "ignored.yml").write_text(
        "---\n"
        "- name: should never be traversed\n"
        "  debug:\n"
        '    msg: "ignored"\n',
        encoding="utf-8",
    )

    task_catalog, _ = scanner._collect_task_handler_catalog(str(role))

    assert [entry["name"] for entry in task_catalog] == [
        "include dynamic path",
        "second static task",
    ]


def test_collect_task_handler_catalog_skips_missing_static_include_file(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    tasks.mkdir(parents=True)

    (tasks / "main.yml").write_text(
        "---\n"
        "- name: include missing file\n"
        "  include_tasks:\n"
        "    file: missing.yml\n"
        "- name: still present\n"
        "  debug:\n"
        '    msg: "ok"\n',
        encoding="utf-8",
    )

    task_catalog, _ = scanner._collect_task_handler_catalog(str(role))

    assert [entry["name"] for entry in task_catalog] == [
        "include missing file",
        "still present",
    ]


def test_compact_task_parameters_role_include_dict_falls_back_to_non_name_keys():
    task = {
        "include_role": {
            "name": ["unexpected"],
            "tasks_from": "install.yml",
            "vars_from": "main.yml",
        }
    }

    rendered = scanner._compact_task_parameters(task, "include_role")

    assert "tasks_from=install.yml" in rendered
    assert "vars_from=main.yml" in rendered


def test_collect_referenced_variable_names_handles_custom_jinja_tests_and_filters(
    tmp_path,
):
    role = tmp_path / "role"
    tasks = role / "tasks"
    templates = role / "templates"
    tasks.mkdir(parents=True)
    templates.mkdir(parents=True)

    (tasks / "main.yml").write_text(
        "---\n"
        "- name: Render config\n"
        "  template:\n"
        "    src: app.j2\n"
        "    dest: /tmp/app.conf\n",
        encoding="utf-8",
    )
    (templates / "app.j2").write_text(
        "{% if feature_flags is custom_flag %}\n"
        "{{ payload | to_nice_yaml(indent=2) }}\n"
        "{% endif %}\n",
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    names = {row["name"] for row in rows}

    assert "feature_flags" in names
    assert "payload" in names


def test_scan_for_default_filters_handles_complex_template_control_flow(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    templates = role / "templates"
    tasks.mkdir(parents=True)
    templates.mkdir(parents=True)

    (tasks / "main.yml").write_text(
        "---\n"
        "- name: Render config\n"
        "  template:\n"
        "    src: app.j2\n"
        "    dest: /tmp/app.conf\n",
        encoding="utf-8",
    )
    (templates / "app.j2").write_text(
        "{% macro render_host(host) -%}\n"
        "{{ host.name | default(default_host_name) }}\n"
        "{%- endmacro %}\n"
        "{% for host in app_hosts if host.enabled is custom_enabled %}\n"
        "{{ render_host(host) }}\n"
        "{% endfor %}\n"
        "{{ settings.port | default(lookup('env', 'APP_PORT')) }}\n"
        "{{ user_id | default('unknown') if feature_flags is custom_flag else fallback_user | default('n/a') }}\n",
        encoding="utf-8",
    )

    found = scan_for_default_filters(str(role))
    matches = [item for item in found if item["file"] == "templates/app.j2"]
    args = {item["args"] for item in matches}

    assert "default_host_name" in args
    assert any("lookup" in arg for arg in args)
    assert "unknown" in args
    assert "n/a" in args


def test_collect_referenced_variable_names_handles_broader_macro_scope_fixture(
    tmp_path,
):
    role = tmp_path / "role"
    tasks = role / "tasks"
    templates = role / "templates"
    tasks.mkdir(parents=True)
    templates.mkdir(parents=True)

    (tasks / "main.yml").write_text(
        "---\n"
        "- name: Render advanced config\n"
        "  template:\n"
        "    src: advanced.j2\n"
        "    dest: /tmp/advanced.conf\n",
        encoding="utf-8",
    )
    (templates / "advanced.j2").write_text(
        "{% macro render_rule(rule) -%}\n"
        "{% if rule.enabled | default(global_enabled) %}\n"
        "{{ rule.name | default(fallback_rule_name) }}\n"
        "{% endif %}\n"
        "{%- endmacro %}\n"
        "{% for rule in rules %}\n"
        "{{ render_rule(rule) }}\n"
        "{% endfor %}\n"
        "{% set computed = local_value | default(global_value) %}\n"
        "{{ computed }}\n"
        "{{ payload | to_nice_yaml(indent=2) }}\n"
        "{% if feature_flags is custom_flag %}enabled{% endif %}\n",
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    names = {row["name"] for row in rows}

    assert "rules" in names
    assert "global_enabled" in names
    assert "fallback_rule_name" in names
    assert "global_value" in names
    assert "local_value" in names
    assert "payload" in names
    assert "feature_flags" in names
    assert "rule" not in names
    assert "computed" not in names


def test_collect_task_files_ignores_dynamic_include_targets(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    tasks.mkdir(parents=True)

    (tasks / "main.yml").write_text(
        "---\n"
        "- name: Dynamic include\n"
        '  include_tasks: "{{ include_target }}"\n'
        "- name: Static include\n"
        "  include_tasks: static.yml\n",
        encoding="utf-8",
    )
    (tasks / "static.yml").write_text(
        '---\n- name: Use var\n  debug:\n    msg: "{{ static_var }}"\n',
        encoding="utf-8",
    )

    discovered = scanner._collect_task_files(role)
    rel_paths = [str(path.relative_to(role)) for path in discovered]

    assert "tasks/main.yml" in rel_paths
    assert "tasks/static.yml" in rel_paths


def test_collect_task_files_follows_static_conditional_includes(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    tasks.mkdir(parents=True)

    (tasks / "main.yml").write_text(
        "---\n"
        "- name: Conditionally include static task file\n"
        "  include_tasks: conditional.yml\n"
        "  when: feature_enabled | bool\n",
        encoding="utf-8",
    )
    (tasks / "conditional.yml").write_text(
        '---\n- name: Use conditional var\n  debug:\n    msg: "{{ conditional_var }}"\n',
        encoding="utf-8",
    )

    discovered = scanner._collect_task_files(role)
    rel_paths = [str(path.relative_to(role)) for path in discovered]

    assert "tasks/main.yml" in rel_paths
    assert "tasks/conditional.yml" in rel_paths


def test_collect_task_files_resolves_parent_relative_indirection(tmp_path):
    role = tmp_path / "role"
    tasks = role / "tasks"
    nested = tasks / "nested"
    shared = tasks / "shared"
    nested.mkdir(parents=True)
    shared.mkdir(parents=True)

    (tasks / "main.yml").write_text(
        "---\n" "- name: Include nested entry\n" "  include_tasks: nested/entry.yml\n",
        encoding="utf-8",
    )
    (nested / "entry.yml").write_text(
        "---\n"
        "- name: Include parent-relative task file\n"
        "  import_tasks: ../shared/common.yml\n",
        encoding="utf-8",
    )
    (shared / "common.yml").write_text(
        '---\n- name: Shared var usage\n  debug:\n    msg: "{{ shared_var }}"\n',
        encoding="utf-8",
    )

    discovered = scanner._collect_task_files(role)
    rel_paths = [str(path.relative_to(role)) for path in discovered]

    assert "tasks/main.yml" in rel_paths
    assert "tasks/nested/entry.yml" in rel_paths
    assert "tasks/shared/common.yml" in rel_paths


def test_build_variable_insights_precedence_chain_with_include_vars(tmp_path):
    role = tmp_path / "role"
    (role / "defaults").mkdir(parents=True)
    (role / "vars").mkdir(parents=True)
    (role / "tasks").mkdir(parents=True)
    (role / "vars" / "extra").mkdir(parents=True)

    (role / "defaults" / "main.yml").write_text(
        "---\napp_mode: default\n", encoding="utf-8"
    )
    (role / "vars" / "main.yml").write_text("---\napp_mode: vars\n", encoding="utf-8")
    (role / "vars" / "extra" / "runtime.yml").write_text(
        "---\napp_mode: include\n",
        encoding="utf-8",
    )
    (role / "tasks" / "main.yml").write_text(
        "---\n"
        "- name: Include runtime vars\n"
        "  include_vars: ../vars/extra/runtime.yml\n",
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role), include_vars_main=True)
    row = next(item for item in rows if item["name"] == "app_mode")

    assert row["source"] == "defaults/main.yml + vars/main.yml override"
    assert row["is_ambiguous"] is True
    assert "include_vars" in (row.get("uncertainty_reason") or "")
    assert float(row["provenance_confidence"]) <= 0.70


def test_build_variable_insights_mentions_dynamic_include_task_uncertainty(tmp_path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)

    (role / "tasks" / "main.yml").write_text(
        "---\n"
        "- name: Dynamic include task path\n"
        '  include_tasks: "{{ include_target }}"\n'
        "- name: Use include target token\n"
        "  debug:\n"
        '    msg: "{{ include_target }}"\n',
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    row = next(item for item in rows if item["name"] == "include_target")

    assert row["is_unresolved"] is True
    assert "Dynamic include_tasks/import_tasks paths detected." in (
        row.get("uncertainty_reason") or ""
    )


# Batch 5: README & Role Parameters Tests


def test_build_variable_insights_readme_backtick_variables(tmp_path):
    """Test that variables in backticks within README are extracted."""
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)

    (role / "tasks" / "main.yml").write_text("---\n", encoding="utf-8")

    (role / "README.md").write_text(
        "# Role Variables\n"
        "\n"
        "The following variables can be overridden:\n"
        "\n"
        "- `app_name` — The application name\n"
        "- `app_port` — The port number\n"
        "- `app_debug` — Debug mode flag\n",
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    by_name = {row["name"]: row for row in rows}

    # Variables from README should be discovered
    for var_name in ["app_name", "app_port", "app_debug"]:
        assert var_name in by_name
        var_row = by_name[var_name]
        assert var_row["source"] == "README.md (documented input)"
        assert var_row["provenance_source_file"] == "README.md"
        assert var_row["provenance_confidence"] == 0.50
        assert var_row["is_unresolved"] is True
        assert var_row["documented"] is True


def test_build_variable_insights_readme_role_variables_section(tmp_path):
    """Test that Role Variables section headings are recognized."""
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)

    (role / "tasks" / "main.yml").write_text("---\n", encoding="utf-8")

    (role / "README.md").write_text(
        "# Role Name\n"
        "\n"
        "## Role Variables\n"
        "\n"
        "The following variables are available:\n"
        "\n"
        "- `database_host` — Database hostname\n"
        "- `database_port` — Database port\n"
        "\n"
        "## Other Section\n"
        "\n"
        "Some configuration that mentions `ignored_var` should not be extracted.\n",
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    by_name = {row["name"]: row for row in rows}

    # Only variables in role variables section
    assert "database_host" in by_name
    assert "database_port" in by_name
    # Variables outside section should not be extracted
    assert "ignored_var" not in by_name


def test_build_variable_insights_readme_table_format(tmp_path):
    """Test that variables in README markdown tables are extracted."""
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)

    (role / "tasks" / "main.yml").write_text("---\n", encoding="utf-8")

    (role / "README.md").write_text(
        "# Variables\n"
        "\n"
        "| Name | Default | Description |\n"
        "|---|---|---|\n"
        "| `web_server_port` | 8080 | Server port |\n"
        "| `max_connections` | 100 | Max connections |\n"
        "| `enable_ssl` | true | SSL enabled |\n",
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    by_name = {row["name"]: row for row in rows}

    # Variables from table should be discovered
    for var_name in ["web_server_port", "max_connections", "enable_ssl"]:
        assert var_name in by_name
        var_row = by_name[var_name]
        assert var_row["source"] == "README.md (documented input)"


def test_build_variable_insights_readme_in_code_block_ignored(tmp_path):
    """Test that variables in code blocks are not extracted."""
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)

    (role / "tasks" / "main.yml").write_text("---\n", encoding="utf-8")

    (role / "README.md").write_text(
        "# Role Variables\n"
        "\n"
        "Config example:\n"
        "\n"
        "```yaml\n"
        "config_var: value  # Should not be extracted\n"
        "another_var: 123   # Should not be extracted\n"
        "```\n"
        "\n"
        "But `documented_var` is documented.\n",
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    by_name = {row["name"]: row for row in rows}

    # Code block variables should not be extracted
    assert "config_var" not in by_name
    assert "another_var" not in by_name
    # Documented outside code block should be extracted
    assert "documented_var" in by_name


def test_build_variable_insights_readme_variables_consistency(tmp_path):
    """Test that README variables have consistent provenance fields."""
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)

    (role / "tasks" / "main.yml").write_text("---\n", encoding="utf-8")

    (role / "README.md").write_text(
        "# Variables\n\n- `var1` description\n- `var2` description\n",
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    readme_rows = [
        row for row in rows if row.get("source") == "README.md (documented input)"
    ]

    # All README rows should have consistent provenance
    for row in readme_rows:
        assert row["provenance_source_file"] == "README.md"
        assert row["provenance_confidence"] == 0.50
        assert row["is_unresolved"] is True
        assert row["documented"] is True
        assert "static role definition not found" in (
            row.get("uncertainty_reason") or ""
        )


def test_build_variable_insights_meta_galaxy_info_available(tmp_path):
    """Test that meta/main.yml galaxy_info is accessible (if needed)."""
    role = tmp_path / "role"
    (role / "meta").mkdir(parents=True)
    (role / "tasks").mkdir(parents=True)

    (role / "meta" / "main.yml").write_text(
        "---\n"
        "galaxy_info:\n"
        "  author: Test Author\n"
        "  min_ansible_version: 2.10\n"
        "dependencies: []\n",
        encoding="utf-8",
    )
    (role / "tasks" / "main.yml").write_text("---\n", encoding="utf-8")

    # Meta data is loaded but not surfaced as variables by default
    # This test validates the role structure is properly handled
    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    # No variables should be extracted from galaxy_info
    assert not any(row["name"] == "galaxy_info" for row in rows)


def test_build_variable_insights_readme_and_defaults_consolidation(tmp_path):
    """Test that README and defaults/main.yml variables consolidate properly."""
    role = tmp_path / "role"
    (role / "defaults").mkdir(parents=True)
    (role / "tasks").mkdir(parents=True)

    # defaults/main.yml with explicit variables
    (role / "defaults" / "main.yml").write_text(
        "---\n" "app_port: 8080\n" "app_timeout: 30\n",
        encoding="utf-8",
    )

    # README documents same variables plus additional ones
    (role / "README.md").write_text(
        "# Variables\n"
        "\n"
        "Configure via:\n"
        "\n"
        "- `app_port` — Server port\n"
        "- `app_timeout` — Timeout seconds\n"
        "- `app_ssl` — Enable SSL\n",
        encoding="utf-8",
    )

    (role / "tasks" / "main.yml").write_text("---\n", encoding="utf-8")

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    by_name = {row["name"]: row for row in rows}

    # Explicit variables should take precedence with high confidence
    assert "app_port" in by_name
    defaults_row = by_name["app_port"]
    assert defaults_row["provenance_source_file"] == "defaults/main.yml"
    assert defaults_row["provenance_confidence"] >= 0.85

    assert "app_timeout" in by_name
    assert by_name["app_timeout"]["provenance_source_file"] == "defaults/main.yml"

    # README-only documented should be unresolved
    assert "app_ssl" in by_name
    readme_row = by_name["app_ssl"]
    assert readme_row["provenance_source_file"] == "README.md"
    assert readme_row["provenance_confidence"] == 0.50


def test_build_variable_insights_readme_multiple_sections(tmp_path):
    """Test README parsing with multiple variable sections."""
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)

    (role / "tasks" / "main.yml").write_text("---\n", encoding="utf-8")

    # Multiple variable-like sections
    (role / "README.md").write_text(
        "# Overview\n\n"
        "## Configuration Variables\n"
        "- `config_opt1` — First option\n"
        "- `config_opt2` — Second option\n\n"
        "## Input Variables\n"
        "- `input_var1` — First input\n"
        "- `input_var2` — Second input\n\n"
        "## Other Section\n"
        "Not a variable section, so `internal_var` is ignored.\n",
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    by_name = {row["name"]: row for row in rows}

    # Variables from named sections should be extracted
    for var_name in ["config_opt1", "config_opt2", "input_var1", "input_var2"]:
        assert var_name in by_name
        assert by_name[var_name]["source"] == "README.md (documented input)"

    # Non-variable section variables should not be extracted
    assert "internal_var" not in by_name


def test_extract_readme_input_variables_direct(tmp_path):
    """Test direct README variable extraction function."""
    readme_text = (
        "# Variables\n\n"
        "Configure with these:\n\n"
        "| Variable | Default |\n"
        "|---|---|\n"
        "| `db_host` | localhost |\n"
        "| `db_port` | 5432 |\n\n"
        "Or use `db_user` and `db_password`.\n"
    )

    names = scanner._extract_readme_input_variables(readme_text)

    # All documented variables should be found
    assert "db_host" in names
    assert "db_port" in names
    assert "db_user" in names
    assert "db_password" in names


def test_build_variable_insights_readme_with_special_characters(tmp_path):
    """Test that README variables with special naming work."""
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)

    (role / "tasks" / "main.yml").write_text("---\n", encoding="utf-8")

    (role / "README.md").write_text(
        "# Variables\n\n"
        "- `my_var_name` — Underscore style\n"
        "- `myVarName` — Camel case style\n"
        "- `MY_VAR_CONSTANT` — Constant style\n",
        encoding="utf-8",
    )

    rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    by_name = {row["name"]: row for row in rows}

    for var_name in ["my_var_name", "myVarName", "MY_VAR_CONSTANT"]:
        assert var_name in by_name
        assert by_name[var_name]["source"] == "README.md (documented input)"


# ── pattern_config: uncovered branch coverage ──────────────────────────────


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
