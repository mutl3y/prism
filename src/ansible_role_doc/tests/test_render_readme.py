from pathlib import Path
import shutil
import subprocess
import sys

from ansible_role_doc import scanner

HERE = Path(__file__).parent


def test_render_readme_for_mock_role(tmp_path):
    """Render the README for the bundled `mock_role` and verify output."""
    role_src = HERE / "mock_role"
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    out = tmp_path / "REVIEW_README.md"
    python_code = (
        "import sys;"
        "sys.path.insert(0, '{src_dir}');"
        "from ansible_role_doc.scanner import run_scan;"
        "run_scan('{role}', output='{out}')"
    ).format(src_dir=str(HERE.parent.parent), role=str(target), out=str(out))

    cmd = [sys.executable, "-c", python_code]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
    assert res.returncode == 0
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Galaxy Info" in content
    assert "Detected usages" in content or "default()" in content
    assert "Auto-detected role features" in content
    assert "unique_modules" in content
    assert "handlers_notified" in content
    assert "Role purpose and capabilities" in content
    assert "Inputs / variables summary" in content
    assert "Task/module usage summary" in content
    assert "Inferred example usage" in content
    assert "| Name | Type | Default | Source |" in content


def test_render_readme_with_local_comparison(tmp_path):
    """Render README with --compare-role-path baseline details."""
    role_src = HERE / "mock_role"
    target = tmp_path / "mock_role"
    baseline = tmp_path / "baseline_role"
    shutil.copytree(role_src, target)
    shutil.copytree(role_src, baseline)

    out = tmp_path / "REVIEW_README_COMPARE.md"
    python_code = (
        "import sys;"
        "sys.path.insert(0, '{src_dir}');"
        "from ansible_role_doc.scanner import run_scan;"
        "run_scan('{role}', output='{out}', compare_role_path='{baseline}')"
    ).format(
        src_dir=str(HERE.parent.parent),
        role=str(target),
        out=str(out),
        baseline=str(baseline),
    )

    cmd = [sys.executable, "-c", python_code]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
    assert res.returncode == 0
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Comparison against local baseline role" in content
    assert "Target score" in content
    assert "Baseline score" in content
    assert "Score delta" in content
    assert "Task/module usage summary" in content


def test_render_readme_with_style_guide_ordering(tmp_path):
    """Render README using a guide README for ordering and heading style."""
    role_src = HERE / "mock_role"
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    style = tmp_path / "STYLE_README.md"
    style.write_text(
        "# Style Guide\n\n## Example Playbook\n\n## Role Variables\n\n## Requirements\n",
        encoding="utf-8",
    )

    out = tmp_path / "REVIEW_README_STYLED.md"
    python_code = (
        "import sys;"
        "sys.path.insert(0, '{src_dir}');"
        "from ansible_role_doc.scanner import run_scan;"
        "run_scan('{role}', output='{out}', style_readme_path='{style}')"
    ).format(
        src_dir=str(HERE.parent.parent),
        role=str(target),
        out=str(out),
        style=str(style),
    )

    cmd = [sys.executable, "-c", python_code]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
    assert res.returncode == 0
    content = out.read_text(encoding="utf-8")
    assert "# mock_role" in content
    assert "## Example Playbook" in content
    assert "## Role Variables" in content
    assert "## Requirements" in content
    assert content.index("## Example Playbook") < content.index("## Role Variables")
    assert content.index("## Role Variables") < content.index("## Requirements")


def test_render_readme_maps_extended_style_sections(tmp_path):
    """Render README with extended guide headings and ensure no unknown placeholders."""
    role_src = HERE / "mock_role"
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    style = tmp_path / "STYLE_EXTENDED.md"
    style.write_text(
        "# Style Guide\n\n"
        "## Configuring settings not listed in role-variables\n\n"
        "## Changing the default port and idempotency\n\n"
        "## Local Testing\n\n"
        "## FAQ / Pitfalls\n\n"
        "## Contributing\n\n"
        "## Sponsors\n\n"
        "## License and Author\n",
        encoding="utf-8",
    )

    out = tmp_path / "REVIEW_README_STYLED_EXTENDED.md"
    python_code = (
        "import sys;"
        "sys.path.insert(0, '{src_dir}');"
        "from ansible_role_doc.scanner import run_scan;"
        "run_scan('{role}', output='{out}', style_readme_path='{style}')"
    ).format(
        src_dir=str(HERE.parent.parent),
        role=str(target),
        out=str(out),
        style=str(style),
    )

    cmd = [sys.executable, "-c", python_code]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
    assert res.returncode == 0

    content = out.read_text(encoding="utf-8")
    assert "## Configuring settings not listed in role-variables" in content
    assert "## Local Testing" in content
    assert "## FAQ / Pitfalls" in content
    assert "## Contributing" in content
    assert "## Sponsors" in content
    assert "## License and Author" in content
    assert (
        "Style section retained from guide; scanner does not map this section yet."
        not in content
    )


def test_render_readme_applies_nested_variable_style(tmp_path):
    """Render role variables using nested-bullet style from a guide README."""
    role_src = HERE / "mock_role"
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    style = tmp_path / "STYLE_NESTED.md"
    style.write_text(
        "# Guide\n\n"
        "## Role Variables\n\n"
        "* `example_var`\n"
        "  * Default: false\n"
        "  * Description: sample description\n",
        encoding="utf-8",
    )

    out = tmp_path / "REVIEW_README_STYLED_NESTED.md"
    python_code = (
        "import sys;"
        "sys.path.insert(0, '{src_dir}');"
        "from ansible_role_doc.scanner import run_scan;"
        "run_scan('{role}', output='{out}', style_readme_path='{style}')"
    ).format(
        src_dir=str(HERE.parent.parent),
        role=str(target),
        out=str(out),
        style=str(style),
    )

    cmd = [sys.executable, "-c", python_code]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    content = out.read_text(encoding="utf-8")
    assert "* `role_install_enabled`" in content
    assert "  * Default:" in content
    assert "  * Description:" in content


def test_render_readme_applies_yaml_variable_style(tmp_path):
    """Render role variables using YAML-block style from a guide README."""
    role_src = HERE / "mock_role"
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    style = tmp_path / "STYLE_YAML.md"
    style.write_text(
        "# Guide\n\n"
        "## Role Variables\n\n"
        "Available variables are listed below, along with default values (see `defaults/main.yml`):\n\n"
        "```yaml\n"
        "example_var: true\n"
        "```\n",
        encoding="utf-8",
    )

    out = tmp_path / "REVIEW_README_STYLED_YAML.md"
    python_code = (
        "import sys;"
        "sys.path.insert(0, '{src_dir}');"
        "from ansible_role_doc.scanner import run_scan;"
        "run_scan('{role}', output='{out}', style_readme_path='{style}')"
    ).format(
        src_dir=str(HERE.parent.parent),
        role=str(target),
        out=str(out),
        style=str(style),
    )

    cmd = [sys.executable, "-c", python_code]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    content = out.read_text(encoding="utf-8")
    assert "Available variables are listed below" in content
    assert "```yaml" in content
    assert "role_install_enabled: true" in content


def test_parse_style_readme_supports_setext_and_unknown_sections(tmp_path):
    style = tmp_path / "STYLE_SETEXT.md"
    style.write_text(
        "Guide Title\n"
        "===========\n\n"
        "Requirements\n"
        "------------\n\n"
        "Totally Custom Section\n"
        "----------------------\n\n"
        "Role Variables\n"
        "--------------\n\n"
        "- custom_var\n",
        encoding="utf-8",
    )

    parsed = scanner.parse_style_readme(str(style))

    assert parsed["title_text"] == "Guide Title"
    assert parsed["title_style"] == "setext"
    assert parsed["section_style"] == "setext"
    assert [section["id"] for section in parsed["sections"]] == [
        "requirements",
        "unknown",
        "role_variables",
    ]
    assert parsed["variable_style"] == "simple_list"


def test_render_readme_retains_unknown_sections_from_setext_guide(tmp_path):
    role_src = HERE / "mock_role"
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    style = tmp_path / "STYLE_UNKNOWN_SETEXT.md"
    style.write_text(
        "Guide Title\n"
        "===========\n\n"
        "Mystery Section\n"
        "---------------\n\n"
        "Role Variables\n"
        "--------------\n",
        encoding="utf-8",
    )

    out = tmp_path / "REVIEW_README_SETEXT_UNKNOWN.md"
    result = scanner.run_scan(
        str(target), output=str(out), style_readme_path=str(style)
    )

    assert result.endswith("REVIEW_README_SETEXT_UNKNOWN.md")
    content = out.read_text(encoding="utf-8")
    assert "mock_role\n=========" in content
    assert "Mystery Section\n---------------" in content
    assert (
        "Style section retained from guide; scanner does not map this section yet."
        in content
    )
    assert "Role Variables\n--------------" in content


def test_render_guide_section_body_handles_license_author_sponsors_and_faq():
    metadata = {
        "meta": {
            "galaxy_info": {
                "license": "BSD-3-Clause",
                "author": "Example Author",
            }
        },
        "features": {"recursive_task_includes": 2},
        "tests": ["tests/inventory", "tests/test.yml"],
        "doc_insights": {"example_playbook": "- hosts: all"},
        "variable_insights": [],
    }

    assert (
        scanner._render_guide_section_body("license", "demo", "", {}, [], [], metadata)
        == "BSD-3-Clause"
    )
    assert (
        scanner._render_guide_section_body(
            "author_information", "demo", "", {}, [], [], metadata
        )
        == "Example Author"
    )

    license_author = scanner._render_guide_section_body(
        "license_author", "demo", "", {}, [], [], metadata
    )
    assert "License: BSD-3-Clause" in license_author
    assert "Author: Example Author" in license_author

    sponsors = scanner._render_guide_section_body(
        "sponsors", "demo", "", {}, [], [], metadata
    )
    assert sponsors == "No sponsorship metadata detected for this role."

    faq = scanner._render_guide_section_body(
        "faq_pitfalls",
        "demo",
        "",
        {},
        [],
        [{"file": "tasks/main.yml", "line_no": 1, "match": "x", "args": "y"}],
        metadata,
    )
    assert "Ensure default values are defined" in faq
    assert "Nested include chains are detected" in faq
    assert "`default()` usages are captured" in faq


def test_render_guide_section_body_handles_empty_variables_and_license_defaults():
    metadata = {"meta": {}, "features": {}, "variable_insights": []}

    assert (
        scanner._render_guide_section_body("license", "demo", "", {}, [], [], metadata)
        == "N/A"
    )
    assert (
        scanner._render_guide_section_body(
            "author_information", "demo", "", {}, [], [], metadata
        )
        == "N/A"
    )
    assert (
        scanner._render_guide_section_body(
            "role_variables", "demo", "", {}, [], [], metadata
        )
        == "No variables found."
    )


def test_render_role_variables_uses_simple_list_when_no_special_style():
    rendered = scanner._render_role_variables_for_style(
        {"demo_var": "value", "other_var": 2},
        {"style_guide": {"variable_style": "simple_list"}, "variable_insights": []},
    )

    assert "The following variables are available:" in rendered
    assert "- `demo_var`: value" in rendered
    assert "- `other_var`: 2" in rendered


def test_quality_metrics_and_comparison_report_detect_deltas(tmp_path):
    role_src = HERE / "mock_role"
    rich_role = tmp_path / "rich_role"
    sparse_role = tmp_path / "sparse_role"
    shutil.copytree(role_src, rich_role)
    sparse_role.mkdir()
    (sparse_role / "tasks").mkdir()
    (sparse_role / "tasks" / "main.yml").write_text(
        "---\n- name: Minimal task\n  debug:\n    msg: hello\n",
        encoding="utf-8",
    )

    rich_metrics = scanner._compute_quality_metrics(str(rich_role))
    sparse_metrics = scanner._compute_quality_metrics(str(sparse_role))
    comparison = scanner.build_comparison_report(str(rich_role), str(sparse_role))

    assert rich_metrics["score"] > sparse_metrics["score"]
    assert comparison["target_score"] == rich_metrics["score"]
    assert comparison["baseline_score"] == sparse_metrics["score"]
    assert comparison["score_delta"] > 0
    assert (
        comparison["metrics"]["task_count"]["target"]
        >= comparison["metrics"]["task_count"]["baseline"]
    )


def test_render_guide_section_body_covers_remaining_fallbacks():
    metadata = {
        "files": ["files/a.txt"],
        "tests": ["tests/inventory"],
        "features": {"task_files_scanned": 1, "tasks_scanned": 2},
    }

    assert (
        scanner._render_guide_section_body(
            "requirements", "demo", "", {}, [], [], metadata
        )
        == "No additional requirements."
    )
    assert (
        scanner._render_guide_section_body(
            "task_summary", "demo", "", {}, [], [], metadata
        )
        == "No task summary available."
    )
    assert (
        scanner._render_guide_section_body(
            "example_usage", "demo", "", {}, [], [], metadata
        )
        == "No inferred example available."
    )
    assert (
        scanner._render_guide_section_body(
            "comparison", "demo", "", {}, [], [], metadata
        )
        == "No comparison baseline provided."
    )
    assert (
        scanner._render_guide_section_body(
            "default_filters", "demo", "", {}, [], [], metadata
        )
        == "No uses of `default()` were detected."
    )

    role_contents = scanner._render_guide_section_body(
        "role_contents", "demo", "", {}, [], [], metadata
    )
    assert "**files**: 1 files" in role_contents
    assert "**tests**: 1 files" in role_contents

    features = scanner._render_guide_section_body(
        "features", "demo", "", {}, [], [], metadata
    )
    assert "**task_files_scanned**: 1" in features
    assert "**tasks_scanned**: 2" in features


def test_render_guide_section_body_renders_comparison_and_default_filters():
    comparison = {
        "baseline_path": "/tmp/baseline",
        "target_score": 70,
        "baseline_score": 30,
        "score_delta": 40,
        "metrics": {
            "task_count": {"target": 3, "baseline": 1, "delta": 2},
        },
    }
    metadata = {"comparison": comparison}
    default_filters = [
        {
            "file": "tasks/main.yml",
            "line_no": 5,
            "match": "var | default('x')",
            "args": "'x'",
        }
    ]

    comparison_text = scanner._render_guide_section_body(
        "comparison", "demo", "", {}, [], [], metadata
    )
    assert "**Baseline path**: /tmp/baseline" in comparison_text
    assert "**Score delta**: 40" in comparison_text
    assert "**task_count**: target=3, baseline=1, delta=2" in comparison_text

    defaults_text = scanner._render_guide_section_body(
        "default_filters", "demo", "", {}, [], default_filters, metadata
    )
    assert "tasks/main.yml:5" in defaults_text
    assert "args: `'x'`" in defaults_text


def test_render_readme_direct_template_and_style_paths(tmp_path):
    output = tmp_path / "rendered.md"
    template = tmp_path / "custom.j2"
    template.write_text(
        "Role={{ role_name }}\nSummary={{ description }}\n", encoding="utf-8"
    )

    rendered = scanner.render_readme(
        str(output),
        "demo-role",
        "demo description",
        {"x": 1},
        [],
        [],
        template=str(template),
        metadata={},
        write=False,
    )

    assert rendered == "Role=demo-role\nSummary=demo description"
    assert not output.exists()

    written = scanner.render_readme(
        str(output),
        "demo-role",
        "demo description",
        {"x": 1},
        [],
        [],
        template=str(template),
        metadata={},
        write=True,
    )
    assert written.endswith("rendered.md")
    assert (
        output.read_text(encoding="utf-8") == "Role=demo-role\nSummary=demo description"
    )

    styled = scanner.render_readme(
        str(output),
        "demo-role",
        "demo description",
        {"x": 1},
        [],
        [],
        metadata={
            "style_guide": {
                "title_style": "atx",
                "section_style": "atx",
                "sections": [],
            }
        },
        write=False,
    )
    assert "# demo-role" in styled


def test_run_scan_applies_role_name_override_for_sparse_role(tmp_path):
    role = tmp_path / "repo"
    (role / "tasks").mkdir(parents=True)
    (role / "tasks" / "main.yml").write_text(
        "---\n- name: Minimal\n  debug:\n    msg: ok\n",
        encoding="utf-8",
    )

    out = tmp_path / "override.md"
    result = scanner.run_scan(
        str(role),
        output=str(out),
        role_name_override="derived-name",
    )

    assert result.endswith("override.md")
    content = out.read_text(encoding="utf-8")
    assert "derived-name" in content


def test_infer_variable_type_and_describe_variable_branches():
    assert scanner._infer_variable_type(1) == "int"
    assert scanner._infer_variable_type(1.5) == "float"
    assert scanner._infer_variable_type([1]) == "list"
    assert scanner._infer_variable_type({"k": "v"}) == "dict"
    assert scanner._infer_variable_type(None) == "null"

    assert scanner._describe_variable("my_path", "defaults/main.yml").startswith(
        "Override the file or path"
    )
    assert scanner._describe_variable("my_user", "defaults/main.yml").startswith(
        "Set the user or group"
    )


def test_build_variable_insights_marks_override_source(tmp_path):
    role = tmp_path / "role"
    (role / "defaults").mkdir(parents=True)
    (role / "vars").mkdir(parents=True)
    (role / "defaults" / "main.yml").write_text(
        "---\nshared_var: false\n", encoding="utf-8"
    )
    (role / "vars" / "main.yml").write_text("---\nshared_var: true\n", encoding="utf-8")

    rows = scanner.build_variable_insights(str(role))
    assert len(rows) == 1
    assert rows[0]["source"] == "defaults/main.yml + vars/main.yml override"


def test_build_doc_insights_emits_empty_vars_block_when_only_variables_dict_provided():
    doc = scanner.build_doc_insights(
        role_name="demo",
        description="",
        metadata={"features": {}},
        variables={"some_var": "value"},
        variable_insights=[],
    )
    assert "      vars: {}" in doc["example_playbook"]


def test_render_guide_sections_for_galaxy_requirements_and_testing_paths():
    metadata = {
        "meta": {
            "galaxy_info": {
                "role_name": "demo-role",
                "description": "desc",
                "license": "MIT",
                "min_ansible_version": "2.15",
                "galaxy_tags": ["demo", "test"],
            }
        },
        "doc_insights": {
            "task_summary": {
                "task_files_scanned": 2,
                "tasks_scanned": 4,
                "recursive_task_includes": 1,
                "module_count": 3,
                "handler_count": 1,
            },
            "example_playbook": "- hosts: all",
        },
        "tests": ["tests/inventory", "tests/test.yml"],
        "features": {"recursive_task_includes": 0},
    }

    galaxy = scanner._render_guide_section_body(
        "galaxy_info", "demo", "desc", {}, [], [], metadata
    )
    assert "**Role name**: demo-role" in galaxy
    assert "**Tags**: demo, test" in galaxy

    requirements = scanner._render_guide_section_body(
        "requirements",
        "demo",
        "",
        {},
        [{"src": "geerlingguy.nginx", "version": "3.1.0"}, "community.general"],
        [],
        metadata,
    )
    assert "geerlingguy.nginx (version: 3.1.0)" in requirements
    assert "community.general" in requirements

    variable_summary = scanner._render_guide_section_body(
        "variable_summary",
        "demo",
        "",
        {},
        [],
        [],
        {
            **metadata,
            "variable_insights": [
                {
                    "name": "v",
                    "type": "bool",
                    "default": "true",
                    "source": "defaults/main.yml",
                }
            ],
        },
    )
    assert "| `v` | bool | `true` | defaults/main.yml |" in variable_summary

    task_summary = scanner._render_guide_section_body(
        "task_summary", "demo", "", {}, [], [], metadata
    )
    assert "**Task files scanned**: 2" in task_summary

    example = scanner._render_guide_section_body(
        "example_usage", "demo", "", {}, [], [], metadata
    )
    assert "```yaml" in example

    testing = scanner._render_guide_section_body(
        "local_testing", "demo", "", {}, [], [], metadata
    )
    assert "ansible-playbook -i tests/inventory tests/test.yml" in testing

    contributing = scanner._render_guide_section_body(
        "contributing", "demo", "", {}, [], [], metadata
    )
    assert "Contributions are welcome." in contributing


def test_detect_task_module_edge_cases_and_heading_fallback():
    assert scanner._detect_task_module({"with_items": [1], "name": "x"}) is None
    assert scanner._detect_task_module({"name": "x", "debug": {"msg": "ok"}}) == "debug"
    assert scanner._format_heading("Deep", 3, "other") == "### Deep"


def test_render_readme_style_write_true_and_empty_section_body_skip(tmp_path):
    output = tmp_path / "style-write.md"
    metadata = {
        "style_guide": {
            "title_style": "atx",
            "section_style": "atx",
            "sections": [
                {"id": "unknown", "title": "Unknown Section"},
                {"id": "variable_summary", "title": "Variables"},
            ],
        },
        "variable_insights": [],
    }

    written = scanner.render_readme(
        str(output),
        "demo-role",
        "desc",
        {},
        [],
        [],
        metadata=metadata,
        write=True,
    )

    assert written.endswith("style-write.md")
    content = output.read_text(encoding="utf-8")
    assert "# demo-role" in content
    assert "## Unknown Section" in content
    assert "Style section retained from guide" in content
    assert "## Variables" in content
    assert "No variable insights available." in content
