"""Unit tests for the ansible_role_doc scanner CLI.

These tests exercise the package CLI by importing the local package and
invoking the entrypoint in a subprocess to simulate real usage.
"""

from pathlib import Path
import shutil
import subprocess
import sys

from ansible_role_doc import scanner
from ansible_role_doc.scanner import scan_for_default_filters

HERE = Path(__file__).parent


def test_scan_detects_defaults(tmp_path):
    role_src = HERE / "mock_role"
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
    role_src = HERE / "mock_role"
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    found = scan_for_default_filters(str(target))

    args = "\n".join(item["args"] for item in found)
    files = {item["file"] for item in found}

    assert "Nested default value" in args
    assert "Deep default value" in args
    assert "tasks/nested/setup.yml" in files
    assert "tasks/nested/deeper.yml" in files


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


def test_collect_role_contents_and_features_handle_sparse_role(tmp_path):
    role = tmp_path / "role"
    (role / "templates").mkdir(parents=True)
    (role / "templates" / "only.j2").write_text("hello", encoding="utf-8")

    contents = scanner.collect_role_contents(str(role))

    assert contents["tasks"] == []
    assert contents["templates"] == ["templates/only.j2"]
    assert contents["features"]["task_files_scanned"] == 0
    assert contents["features"]["tasks_scanned"] == 0
