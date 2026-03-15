"""Unit tests for the ansible_role_doc scanner CLI.

These tests exercise the package CLI by importing the local package and
invoking the entrypoint in a subprocess to simulate real usage.
"""

from pathlib import Path
import shutil
import subprocess
import sys

from ansible_role_doc import pattern_config
from ansible_role_doc.pattern_config import load_pattern_config
from ansible_role_doc import scanner
from ansible_role_doc.scanner import scan_for_default_filters

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
        "from ansible_role_doc.cli import main;"
        "sys.exit(main(['{role}','-o','{out}']))"
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
    override = tmp_path / ".ansible_role_doc_patterns.yml"
    override.write_text(
        "sensitivity:\n" "  name_tokens:\n" "    - from_cwd_override\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    config = load_pattern_config()

    assert "from_cwd_override" in config["sensitivity"]["name_tokens"]


def test_load_pattern_config_reads_xdg_user_override(monkeypatch, tmp_path):
    xdg_home = tmp_path / "xdg-home"
    override = xdg_home / "ansible-role-doc" / pattern_config.CWD_OVERRIDE_FILENAME
    override.parent.mkdir(parents=True)
    override.write_text(
        "sensitivity:\n" "  name_tokens:\n" "    - from_xdg_override\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_home))
    monkeypatch.chdir(tmp_path)
    config = load_pattern_config()

    assert "from_xdg_override" in config["sensitivity"]["name_tokens"]


def test_load_pattern_config_reads_env_override(monkeypatch, tmp_path):
    override = tmp_path / "patterns-env.yml"
    override.write_text(
        "sensitivity:\n" "  name_tokens:\n" "    - from_env_override\n",
        encoding="utf-8",
    )

    monkeypatch.setenv(pattern_config.ENV_PATTERNS_OVERRIDE_PATH, str(override))
    monkeypatch.chdir(tmp_path)
    config = load_pattern_config()

    assert "from_env_override" in config["sensitivity"]["name_tokens"]


def test_load_pattern_config_reads_system_override(monkeypatch, tmp_path):
    system_override = tmp_path / "system" / pattern_config.CWD_OVERRIDE_FILENAME
    system_override.parent.mkdir(parents=True)
    system_override.write_text(
        "sensitivity:\n" "  name_tokens:\n" "    - from_system_override\n",
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
            "sensitivity:\n" "  name_tokens:\n" f"    - {token}\n",
            encoding="utf-8",
        )

    system_override = tmp_path / "system" / pattern_config.CWD_OVERRIDE_FILENAME
    xdg_home = tmp_path / "xdg-home"
    xdg_override = xdg_home / "ansible-role-doc" / pattern_config.CWD_OVERRIDE_FILENAME
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
