import importlib
from pathlib import Path
import shutil
import subprocess
import sys

from prism import scanner

HERE = Path(__file__).parent
ROLE_FIXTURES = HERE / "roles"
BASE_ROLE_FIXTURE = ROLE_FIXTURES / "base_mock_role"
ENHANCED_ROLE_FIXTURE = ROLE_FIXTURES / "enhanced_mock_role"
INROLE_CONFIG_ROLE_FIXTURE = ROLE_FIXTURES / "inrole_config_role"


def test_render_readme_module_compose_section_body_merges_requirements_content():
    render_readme_module = importlib.import_module(
        "prism.scanner_submodules.render_readme"
    )

    composed = render_readme_module._compose_section_body(
        {
            "id": "requirements",
            "body": "Install collections first.",
        },
        "- acme.collection",
        "merge",
    )

    assert "Install collections first." in composed
    assert "Detected requirements from scanner:" in composed
    assert "- acme.collection" in composed
    assert "<!-- prism:generated:start:requirements -->" in composed


def test_render_readme_module_renders_style_guide_and_scanner_report_link():
    render_readme_module = importlib.import_module(
        "prism.scanner_submodules.render_readme"
    )

    rendered = render_readme_module.render_readme(
        output="/tmp/README.md",
        role_name="demo_role",
        description="Demo description",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={
            "style_guide": {
                "title_style": "setext",
                "section_style": "setext",
                "section_level": 2,
                "sections": [{"id": "purpose", "title": "Purpose"}],
            },
            "scanner_report_relpath": "reports/scan.md",
            "include_scanner_report_link": True,
        },
        write=False,
    )

    assert "demo_role" in rendered
    assert "Purpose" in rendered
    assert "Demo description" in rendered
    assert "Scanner report" in rendered
    assert "reports/scan.md" in rendered


def test_scanner_render_readme_wrapper_delegates_to_extracted_module(monkeypatch):
    captured = {}

    def fake_render_readme(**kwargs):
        captured.update(kwargs)
        return "delegated"

    monkeypatch.setattr(scanner, "_render_readme_mod_render_readme", fake_render_readme)

    result = scanner.render_readme(
        output="/tmp/README.md",
        role_name="demo_role",
        description="Demo description",
        variables={"demo": {"required": False}},
        requirements=["dep"],
        default_filters=[{"match": "demo | default('x')"}],
        template="custom.md.j2",
        metadata={"feature": True},
        write=False,
    )

    assert result == "delegated"
    assert captured == {
        "output": "/tmp/README.md",
        "role_name": "demo_role",
        "description": "Demo description",
        "variables": {"demo": {"required": False}},
        "requirements": ["dep"],
        "default_filters": [{"match": "demo | default('x')"}],
        "template": "custom.md.j2",
        "metadata": {"feature": True},
        "write": False,
    }


def test_render_readme_for_mock_role(tmp_path):
    """Render the README for the bundled `mock_role` and verify output."""
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    out = tmp_path / "REVIEW_README.md"
    python_code = (
        "import sys;"
        "sys.path.insert(0, '{src_dir}');"
        "from prism.scanner import run_scan;"
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
    assert "\n- example.role_dependency (version: 1.0.0)\n" in content
    assert "\n- example.collection_dependency\n" in content


def test_render_readme_for_enhanced_mock_role(tmp_path):
    role_src = ENHANCED_ROLE_FIXTURE
    target = tmp_path / "enhanced_mock_role"
    shutil.copytree(role_src, target)

    out = tmp_path / "REVIEW_README_ENHANCED.md"
    scanner.run_scan(str(target), output=str(out))

    content = out.read_text(encoding="utf-8")
    assert "mock_role_install_enabled" in content
    assert "mock_role_validate_config" in content
    assert "setup.yml" in content
    assert "deploy.yml" in content
    assert "validate.yml" in content


def test_run_scan_concise_readme_writes_scanner_sidecar(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    out = tmp_path / "CONCISE_README.md"
    report = tmp_path / "SCAN_REPORT.md"
    result = scanner.run_scan(
        str(target),
        output=str(out),
        concise_readme=True,
        scanner_report_output=str(report),
    )

    assert result.endswith("CONCISE_README.md")
    assert out.exists()
    assert report.exists()

    readme = out.read_text(encoding="utf-8")
    report_content = report.read_text(encoding="utf-8")

    assert "Scanner report" in readme
    assert "Detailed scanner output is available in" in readme
    assert "Task/module usage summary" not in readme
    assert "Role contents summary" not in readme
    assert "Auto-detected role features" not in readme
    assert "Detected usages of the default() filter" not in readme
    assert "Role Variables" not in readme
    assert "scanner report" in report_content.lower()
    assert "Auto-detected role features" in report_content
    assert "Summary" in report_content
    assert "Total variables" in report_content


def test_run_scan_concise_readme_can_hide_scanner_link_section(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    out = tmp_path / "CONCISE_NO_LINK.md"
    report = tmp_path / "SCAN_REPORT_NO_LINK.md"
    scanner.run_scan(
        str(target),
        output=str(out),
        concise_readme=True,
        scanner_report_output=str(report),
        include_scanner_report_link=False,
    )

    readme = out.read_text(encoding="utf-8")

    assert report.exists()
    assert "Scanner report" not in readme
    assert "Detailed scanner output is available in" not in readme


def test_run_scan_renders_comment_driven_role_notes(tmp_path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)
    (role / "tasks" / "main.yml").write_text(
        "---\n"
        "# prism~warning: this package is unhealthy\n"
        "# prism~note: test in staging first\n"
        "# prism~additional: coordinate with platform team\n"
        "- name: noop\n"
        "  debug:\n"
        "    msg: ok\n",
        encoding="utf-8",
    )

    out = tmp_path / "README_NOTES.md"
    scanner.run_scan(str(role), output=str(out))

    content = out.read_text(encoding="utf-8")
    assert "Role notes" in content
    assert "this package is unhealthy" in content
    assert "test in staging first" in content
    assert "coordinate with platform team" in content
    assert "Additionals:" in content


def test_run_scan_renders_task_catalog_with_links_and_details(tmp_path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)
    (role / "tasks" / "main.yml").write_text(
        "---\n"
        "# prism~runbook: manually copy /tmp/demo if template fails\n"
        "- name: noop\n"
        "  debug:\n"
        "    msg: ok\n",
        encoding="utf-8",
    )

    out = tmp_path / "README_TASK_CATALOG.md"
    scanner.run_scan(str(role), output=str(out), detailed_catalog=True)

    content = out.read_text(encoding="utf-8")
    assert "| File | Task | Module | Parameters | Runbook |" in content
    assert "| `main.yml` | [noop](#task-main-yml-noop-1) | debug |" in content
    assert "#### Task details and runbooks" in content
    assert '<a id="task-main-yml-noop-1"></a>' in content
    assert "<details>" in content
    assert "manually copy /tmp/demo if template fails" in content


def test_run_scan_renders_task_catalog_role_include_entries(tmp_path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)
    (role / "tasks" / "main.yml").write_text(
        "---\n"
        "- name: include common role\n"
        "  include_role:\n"
        "    name: acme.common\n"
        "- name: import web role\n"
        "  ansible.builtin.import_role:\n"
        "    name: acme.web\n",
        encoding="utf-8",
    )

    out = tmp_path / "README_TASK_CATALOG_ROLE_INCLUDE.md"
    scanner.run_scan(str(role), output=str(out), detailed_catalog=True)

    content = out.read_text(encoding="utf-8")
    assert "| `main.yml` | [include common role]" in content
    assert "| include_role | name=acme.common |" in content
    assert "| `main.yml` | [import web role]" in content
    assert "| import_role | name=acme.web |" in content


def test_render_runbook_standalone_returns_role_name_and_sections(tmp_path):
    metadata = {
        "task_catalog": [
            {
                "file": "tasks/main.yml",
                "name": "Deploy app",
                "module": "ansible.builtin.copy",
                "parameters": "src=/tmp/app dest=/opt/app",
                "anchor": "task-main-yml-deploy-app-1",
                "runbook": "copy /tmp/app to /opt/app then restart",
                "annotations": [
                    {
                        "kind": "runbook",
                        "text": "copy /tmp/app to /opt/app then restart",
                    },
                    {"kind": "warning", "text": "requires sudo"},
                ],
            },
            {
                "file": "tasks/main.yml",
                "name": "Validate app",
                "module": "ansible.builtin.command",
                "parameters": "cmd=/usr/local/bin/validate",
                "anchor": "task-main-yml-validate-app-2",
                "runbook": "",
                "annotations": [],
            },
        ],
        "role_notes": {
            "warnings": [],
            "deprecations": [],
            "notes": ["standard deploy role"],
            "additionals": [],
        },
    }
    content = scanner.render_runbook("my_role", metadata)
    assert "# RUNBOOK: my_role" in content
    assert "## Role Notes" in content
    assert "standard deploy role" in content
    assert "## Task Runbooks" in content
    assert "#### `tasks/main.yml` - Deploy app" in content
    assert '<a id="task-main-yml-deploy-app-1"></a>' in content
    assert "| Field | Value |" not in content
    assert "copy /tmp/app to /opt/app then restart" in content
    assert "Warning: requires sudo" in content
    assert "#### `tasks/main.yml` - Validate app" in content
    assert "- No comments." not in content


def test_run_scan_writes_runbook_output_file(tmp_path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)
    (role / "tasks" / "main.yml").write_text(
        "---\n"
        "# prism~runbook: manually restart nginx if deploy fails\n"
        "- name: restart nginx\n"
        "  ansible.builtin.service:\n"
        "    name: nginx\n"
        "    state: restarted\n"
        "- name: validate nginx\n"
        "  ansible.builtin.command:\n"
        "    cmd: /usr/sbin/nginx -t\n",
        encoding="utf-8",
    )

    out = tmp_path / "README.md"
    rb_out = tmp_path / "RUNBOOK.md"
    scanner.run_scan(str(role), output=str(out), runbook_output=str(rb_out))

    assert rb_out.is_file(), "runbook file should be written"
    content = rb_out.read_text(encoding="utf-8")
    assert "# RUNBOOK:" in content
    assert "## Task Runbooks" in content
    assert "restart nginx" in content
    assert "manually restart nginx if deploy fails" in content
    assert "validate nginx" in content
    assert "- No comments." not in content


def test_run_scan_writes_runbook_csv_output_file(tmp_path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)
    (role / "tasks" / "main.yml").write_text(
        "---\n"
        "# prism~runbook: manually restart nginx if deploy fails\n"
        "# prism~task: restart nginx | warning: confirm service user exists before restart\n"
        "- name: restart nginx\n"
        "  ansible.builtin.service:\n"
        "    name: nginx\n"
        "    state: restarted\n"
        "- name: validate nginx\n"
        "  ansible.builtin.command:\n"
        "    cmd: /usr/sbin/nginx -t\n",
        encoding="utf-8",
    )

    out = tmp_path / "README.md"
    rb_csv_out = tmp_path / "RUNBOOK.csv"
    scanner.run_scan(
        str(role),
        output=str(out),
        runbook_csv_output=str(rb_csv_out),
    )

    assert rb_csv_out.is_file(), "runbook csv file should be written"
    content = rb_csv_out.read_text(encoding="utf-8")
    assert "file,task_name,step" in content
    assert "main.yml,restart nginx,manually restart nginx if deploy fails" in content
    assert (
        "main.yml,restart nginx,Warning: confirm service user exists before restart"
        in content
    )
    assert "validate nginx," not in content


def test_run_scan_scanner_report_includes_issue_categories(tmp_path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)
    (role / "tasks" / "main.yml").write_text(
        "---\n"
        "- name: unresolved usage\n"
        "  debug:\n"
        '    msg: "{{ missing_required_var }}"\n',
        encoding="utf-8",
    )

    out = tmp_path / "CONCISE.md"
    report = tmp_path / "SCAN_REPORT.md"
    scanner.run_scan(
        str(role),
        output=str(out),
        concise_readme=True,
        scanner_report_output=str(report),
    )

    report_content = report.read_text(encoding="utf-8")
    assert "Provenance issue categories" in report_content
    assert "unresolved_no_static_definition" in report_content
    assert "Role include graph signals" in report_content
    assert "Task annotation quality" in report_content


def test_run_scan_scanner_report_includes_yaml_parse_failures(tmp_path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)
    (role / "defaults").mkdir(parents=True)
    (role / "tasks" / "main.yml").write_text(
        "---\n" "- name: noop\n" "  debug:\n" '    msg: "ok"\n',
        encoding="utf-8",
    )
    (role / "defaults" / "main.yml").write_text(
        "---\n" "broken: [unterminated\n",
        encoding="utf-8",
    )

    out = tmp_path / "CONCISE_PARSE_FAILURE.md"
    report = tmp_path / "SCAN_REPORT_PARSE_FAILURE.md"
    scanner.run_scan(
        str(role),
        output=str(out),
        concise_readme=True,
        scanner_report_output=str(report),
    )

    report_content = report.read_text(encoding="utf-8")
    assert "YAML parse failures" in report_content
    assert "defaults/main.yml" in report_content


def test_render_task_summary_includes_yaml_parse_failure_details():
    metadata = {
        "doc_insights": {
            "task_summary": {
                "task_files_scanned": 1,
                "tasks_scanned": 1,
                "recursive_task_includes": 0,
                "module_count": 1,
                "handler_count": 0,
            }
        },
        "yaml_parse_failures": [
            {
                "file": "defaults/main.yml",
                "line": 2,
                "column": 9,
                "error": "expected ',' or ']'",
            }
        ],
    }

    content = scanner._render_guide_section_body(
        "task_summary",
        "role",
        "",
        {},
        [],
        [],
        metadata,
    )

    assert "**YAML parse failures**: 1" in content
    assert "Parse failures detected:" in content
    assert "defaults/main.yml:2:9" in content


def test_run_scan_reports_missing_non_ansible_collection_declarations(tmp_path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)
    (role / "meta").mkdir(parents=True)

    (role / "tasks" / "main.yml").write_text(
        "---\n"
        "- name: Manage ini file\n"
        "  community.general.ini_file:\n"
        "    path: /tmp/app.ini\n"
        "    section: demo\n"
        "    option: enabled\n"
        '    value: "true"\n',
        encoding="utf-8",
    )
    (role / "meta" / "main.yml").write_text(
        "---\n" "galaxy_info:\n" "  role_name: demo\n" "  description: demo role\n",
        encoding="utf-8",
    )
    (role / "meta" / "requirements.yml").write_text("---\n[]\n", encoding="utf-8")

    out = tmp_path / "README_COLLECTION_CHECK.md"
    scanner.run_scan(str(role), output=str(out))
    content = out.read_text(encoding="utf-8")

    assert (
        "[Collection check] Detected non-ansible collections from task usage: community.general."
        in content
    )
    assert (
        "[Collection check] Missing from meta/main.yml galaxy_info.collections: community.general."
        in content
    )
    assert (
        "[Collection check] Missing from meta/requirements.yml: community.general."
        in content
    )


def test_run_scan_does_not_report_missing_collection_when_declared(tmp_path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)
    (role / "meta").mkdir(parents=True)

    (role / "tasks" / "main.yml").write_text(
        "---\n"
        "- name: Manage ini file\n"
        "  community.general.ini_file:\n"
        "    path: /tmp/app.ini\n"
        "    section: demo\n"
        "    option: enabled\n"
        '    value: "true"\n',
        encoding="utf-8",
    )
    (role / "meta" / "main.yml").write_text(
        "---\n"
        "galaxy_info:\n"
        "  role_name: demo\n"
        "  description: demo role\n"
        "  collections:\n"
        "    - community.general\n",
        encoding="utf-8",
    )
    (role / "meta" / "requirements.yml").write_text(
        "---\n- src: community.general\n",
        encoding="utf-8",
    )

    out = tmp_path / "README_COLLECTION_DECLARED.md"
    scanner.run_scan(str(role), output=str(out))
    content = out.read_text(encoding="utf-8")

    assert (
        "[Collection check] Detected non-ansible collections from task usage: community.general."
        in content
    )
    assert "Missing from meta/main.yml" not in content
    assert "Missing from meta/requirements.yml" not in content


def test_run_scan_includes_meta_role_dependencies_in_requirements(tmp_path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)
    (role / "meta").mkdir(parents=True)

    (role / "tasks" / "main.yml").write_text("---\n", encoding="utf-8")
    (role / "meta" / "main.yml").write_text(
        "---\n"
        "galaxy_info:\n"
        "  role_name: demo\n"
        "  description: demo role\n"
        "dependencies:\n"
        "  - src: custom.role_dep\n"
        "    version: 2.0.0\n"
        "  - custom.other_dep\n",
        encoding="utf-8",
    )
    (role / "meta" / "requirements.yml").write_text("---\n[]\n", encoding="utf-8")

    out = tmp_path / "README_ROLE_DEPS.md"
    scanner.run_scan(str(role), output=str(out))
    content = out.read_text(encoding="utf-8")

    assert "custom.role_dep (version: 2.0.0)" in content
    assert "custom.other_dep" in content


def test_run_scan_includes_static_role_include_dependencies_in_requirements(tmp_path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)
    (role / "meta").mkdir(parents=True)

    (role / "tasks" / "main.yml").write_text(
        "---\n"
        "- name: include common role\n"
        "  include_role:\n"
        "    name: acme.common\n"
        "- name: import web role\n"
        "  ansible.builtin.import_role:\n"
        "    name: acme.web\n",
        encoding="utf-8",
    )
    (role / "meta" / "main.yml").write_text(
        "---\n" "galaxy_info:\n" "  role_name: demo\n" "  description: demo role\n",
        encoding="utf-8",
    )
    (role / "meta" / "requirements.yml").write_text("---\n[]\n", encoding="utf-8")

    out = tmp_path / "README_ROLE_INCLUDE_DEPS.md"
    scanner.run_scan(str(role), output=str(out))
    content = out.read_text(encoding="utf-8")

    assert "[Role include] acme.common" in content
    assert "[Role include] acme.web" in content


def test_run_scan_readme_includes_uncertainty_notes_for_precedence_and_unresolved(
    tmp_path,
):
    role = tmp_path / "role"
    (role / "defaults").mkdir(parents=True)
    (role / "vars").mkdir(parents=True)
    (role / "tasks").mkdir(parents=True)

    (role / "defaults" / "main.yml").write_text(
        "---\n" "app_port: 8080\n",
        encoding="utf-8",
    )
    (role / "vars" / "main.yml").write_text(
        "---\n" "app_port: 9090\n",
        encoding="utf-8",
    )
    (role / "tasks" / "main.yml").write_text(
        "---\n"
        "- name: unresolved usage\n"
        "  debug:\n"
        '    msg: "{{ missing_runtime_value }}"\n',
        encoding="utf-8",
    )

    out = tmp_path / "README_WITH_UNCERTAINTY.md"
    scanner.run_scan(str(role), output=str(out))

    content = out.read_text(encoding="utf-8")
    assert "Variable provenance and confidence notes:" in content
    assert "Ambiguous variables:" in content
    assert (
        "`app_port`: Defaults value is superseded by vars/main.yml precedence "
        "(informational)." in content
    )
    assert "Unresolved variables:" in content
    assert "`missing_runtime_value`:" in content


def test_run_scan_readme_config_can_gate_sections(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    cfg = target / ".prism.yml"
    cfg.write_text(
        "readme:\n"
        "  include_sections:\n"
        "    - Role purpose and capabilities\n"
        "    - inputs / variables summary\n",
        encoding="utf-8",
    )

    out = tmp_path / "README_CONFIG_GATED.md"
    scanner.run_scan(str(target), output=str(out))

    content = out.read_text(encoding="utf-8")
    assert "Role purpose and capabilities" in content
    assert "Inputs / variables summary" in content
    assert "Galaxy Info" not in content
    assert "Requirements" not in content
    assert "Task/module usage summary" not in content


def test_run_scan_uses_inrole_readme_config_fixture(tmp_path):
    role_src = INROLE_CONFIG_ROLE_FIXTURE
    target = tmp_path / "inrole_config_role"
    shutil.copytree(role_src, target)

    out = tmp_path / "README_CONFIG_FROM_ROLE.md"
    scanner.run_scan(str(target), output=str(out))

    content = out.read_text(encoding="utf-8")
    assert "Capabilities" in content
    assert "Inputs / variables summary" in content
    assert "Galaxy Info" not in content
    assert "Requirements" not in content
    assert "Task/module usage summary" not in content


def test_run_scan_uses_legacy_inrole_readme_config_filename(tmp_path):
    role_src = INROLE_CONFIG_ROLE_FIXTURE
    target = tmp_path / "inrole_config_role"
    shutil.copytree(role_src, target)

    legacy_cfg = target / ".ansible_role_doc.yml"
    modern_cfg = target / ".prism.yml"
    modern_cfg.write_text(legacy_cfg.read_text(encoding="utf-8"), encoding="utf-8")
    legacy_cfg.unlink()

    out = tmp_path / "README_CONFIG_FROM_LEGACY_ROLE.md"
    scanner.run_scan(str(target), output=str(out))

    content = out.read_text(encoding="utf-8")
    assert "Capabilities" in content
    assert "Galaxy Info" not in content


def test_run_scan_inrole_config_heading_mode_can_be_set_to_canonical(tmp_path):
    role_src = INROLE_CONFIG_ROLE_FIXTURE
    target = tmp_path / "inrole_config_role"
    shutil.copytree(role_src, target)

    out = tmp_path / "README_CONFIG_CANONICAL_HEADINGS.md"
    scanner.run_scan(
        str(target),
        output=str(out),
        adopt_heading_mode="canonical",
    )

    content = out.read_text(encoding="utf-8")
    assert "Capabilities\n------------" not in content
    assert "Role purpose and capabilities\n-----------------------------" in content
    assert "Inputs / variables summary" in content


def test_run_scan_style_guide_skeleton_renders_sections_only(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    out = tmp_path / "STYLE_GUIDE_SKELETON.md"
    scanner.run_scan(
        str(target),
        output=str(out),
        style_guide_skeleton=True,
    )

    content = out.read_text(encoding="utf-8")
    assert "A mock Ansible role for tests" in content
    assert "This is a description for this role" in content
    assert (
        "I sourced it from the meta/main.yml file in the prism repository." in content
    )
    assert "Requirements" in content
    assert "Role Variables" in content
    assert "- **Role name**:" not in content
    assert "The following variables are available:" not in content
    assert "No additional requirements." not in content


def test_run_scan_style_guide_skeleton_uses_xdg_style_source(monkeypatch, tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    xdg_home = tmp_path / "xdg-data"
    xdg_style = xdg_home / "prism" / "STYLE_GUIDE_SOURCE.md"
    xdg_style.parent.mkdir(parents=True)
    xdg_style.write_text(
        "# XDG Style\n\n## Requirements\n\n## Role Variables\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_home))

    out = tmp_path / "STYLE_GUIDE_SKELETON_XDG.md"
    scanner.run_scan(
        str(target),
        output=str(out),
        style_guide_skeleton=True,
    )

    content = out.read_text(encoding="utf-8")
    assert "## Requirements" in content
    assert "## Role Variables" in content


def test_run_scan_style_guide_skeleton_uses_legacy_env_style_source(
    monkeypatch, tmp_path
):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    legacy_style = tmp_path / "legacy-style.md"
    legacy_style.write_text(
        "# Legacy Style\n\n## Requirements\n\n## Role Variables\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANSIBLE_ROLE_DOC_STYLE_SOURCE", str(legacy_style))

    out = tmp_path / "STYLE_GUIDE_SKELETON_LEGACY_ENV.md"
    scanner.run_scan(
        str(target),
        output=str(out),
        style_guide_skeleton=True,
    )

    content = out.read_text(encoding="utf-8")
    assert "## Requirements" in content
    assert "## Role Variables" in content


def test_render_readme_with_local_comparison(tmp_path):
    """Render README with --compare-role-path baseline details."""
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    baseline = tmp_path / "baseline_role"
    shutil.copytree(role_src, target)
    shutil.copytree(role_src, baseline)

    out = tmp_path / "REVIEW_README_COMPARE.md"
    python_code = (
        "import sys;"
        "sys.path.insert(0, '{src_dir}');"
        "from prism.scanner import run_scan;"
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
    role_src = BASE_ROLE_FIXTURE
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
        "from prism.scanner import run_scan;"
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


def test_render_readme_requirements_augments_guide_text_with_scanner_dependencies(
    tmp_path,
):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    style = tmp_path / "STYLE_REQUIREMENTS_AUGMENT.md"
    style.write_text(
        "# Guide\n\n"
        "## Requirements\n\n"
        "Install baseline packages before applying this role.\n\n"
        "## Role Variables\n\n",
        encoding="utf-8",
    )

    out = tmp_path / "REVIEW_README_REQUIREMENTS_AUGMENT.md"
    scanner.run_scan(str(target), output=str(out), style_readme_path=str(style))

    content = out.read_text(encoding="utf-8")
    assert "Install baseline packages before applying this role." in content
    assert "Detected requirements from scanner:" in content
    assert "- example.role_dependency (version: 1.0.0)" in content


def test_render_readme_config_can_replace_requirements_body(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    cfg = target / ".prism.yml"
    cfg.write_text(
        "readme:\n  section_content_modes:\n    requirements: replace\n",
        encoding="utf-8",
    )

    style = tmp_path / "STYLE_REQUIREMENTS_REPLACE.md"
    style.write_text(
        "# Guide\n\n"
        "## Requirements\n\n"
        "Guide-owned requirements text.\n\n"
        "## Role Variables\n\n",
        encoding="utf-8",
    )

    out = tmp_path / "REVIEW_README_REQUIREMENTS_REPLACE.md"
    scanner.run_scan(str(target), output=str(out), style_readme_path=str(style))

    content = out.read_text(encoding="utf-8")
    assert "Guide-owned requirements text." in content
    assert "Detected requirements from scanner:" not in content
    assert "example.role_dependency" not in content


def test_render_readme_content_modes_follow_include_section_titles(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    cfg = target / ".prism.yml"
    cfg.write_text(
        "readme:\n"
        "  include_sections:\n"
        "    - Requirements\n"
        "    - Role Variables\n"
        "  section_content_modes:\n"
        "    Requirements: replace\n"
        "    Role Variables: generate\n",
        encoding="utf-8",
    )

    style = tmp_path / "STYLE_CONTENT_MODE_TITLES.md"
    style.write_text(
        "# Guide\n\n"
        "## Requirements\n\n"
        "Guide requirements paragraph.\n\n"
        "## Role Variables\n\n"
        "Guide variable prose that should be replaced by generated content.\n",
        encoding="utf-8",
    )

    out = tmp_path / "REVIEW_README_CONTENT_MODE_TITLES.md"
    scanner.run_scan(str(target), output=str(out), style_readme_path=str(style))

    content = out.read_text(encoding="utf-8")
    assert "Guide requirements paragraph." in content
    assert "example.role_dependency (version: 1.0.0)" not in content
    assert "Guide variable prose" not in content
    assert "The following variables are available:" in content


def test_render_readme_content_mode_title_match_normalizes_spacing(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    cfg = target / ".prism.yml"
    cfg.write_text(
        "readme:\n"
        "  include_sections:\n"
        "    - Role Variables\n"
        "  section_content_modes:\n"
        "    role   variables: replace\n",
        encoding="utf-8",
    )

    style = tmp_path / "STYLE_ROLE_VARIABLES_REPLACE.md"
    style.write_text(
        "# Guide\n\n## Role Variables\n\nGuide-owned role variable text.\n",
        encoding="utf-8",
    )

    out = tmp_path / "REVIEW_README_ROLE_VARIABLES_REPLACE.md"
    scanner.run_scan(str(target), output=str(out), style_readme_path=str(style))

    content = out.read_text(encoding="utf-8")
    assert "Guide-owned role variable text." in content
    assert "The following variables are available:" not in content


def test_render_readme_config_can_force_requirements_generate_only(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    cfg = target / ".prism.yml"
    cfg.write_text(
        "readme:\n  section_content_modes:\n    Requirements: generate\n",
        encoding="utf-8",
    )

    style = tmp_path / "STYLE_REQUIREMENTS_GENERATE.md"
    style.write_text(
        "# Guide\n\n"
        "## Requirements\n\n"
        "Guide requirements prose that should not appear in generate mode.\n\n"
        "## Role Variables\n\n",
        encoding="utf-8",
    )

    out = tmp_path / "REVIEW_README_REQUIREMENTS_GENERATE.md"
    scanner.run_scan(str(target), output=str(out), style_readme_path=str(style))

    content = out.read_text(encoding="utf-8")
    assert "Guide requirements prose" not in content
    assert "example.role_dependency (version: 1.0.0)" in content


def test_render_readme_merge_replaces_prior_generated_requirements_block(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    cfg = target / ".prism.yml"
    cfg.write_text(
        "readme:\n  section_content_modes:\n    requirements: merge\n",
        encoding="utf-8",
    )

    style = tmp_path / "STYLE_REQUIREMENTS_PREMERGED.md"
    style.write_text(
        "# Guide\n\n"
        "## Requirements\n\n"
        "Base guide requirement text.\n\n"
        "Detected requirements from scanner:\n"
        "<!-- prism:generated:start:requirements -->\n"
        "- old.dependency (version: 0.0.1)\n"
        "<!-- prism:generated:end:requirements -->\n\n"
        "## Role Variables\n\n",
        encoding="utf-8",
    )

    out = tmp_path / "REVIEW_README_REQUIREMENTS_IDEMPOTENT.md"
    scanner.run_scan(str(target), output=str(out), style_readme_path=str(style))

    content = out.read_text(encoding="utf-8")
    assert "Base guide requirement text." in content
    assert "old.dependency" not in content
    assert "example.role_dependency (version: 1.0.0)" in content
    assert content.count("<!-- prism:generated:start:requirements -->") == 1
    assert content.count("<!-- prism:generated:end:requirements -->") == 1


def test_render_readme_defaults_to_merge_for_narrative_section_prose(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    style = tmp_path / "STYLE_TASK_SUMMARY_MERGE.md"
    style.write_text(
        "# Guide\n\n"
        "## Task/module usage summary\n\n"
        "Guide task summary prose that should be preserved.\n\n"
        "## Role Variables\n\n",
        encoding="utf-8",
    )

    out = tmp_path / "REVIEW_README_TASK_SUMMARY_MERGE.md"
    scanner.run_scan(str(target), output=str(out), style_readme_path=str(style))

    content = out.read_text(encoding="utf-8")
    assert "Guide task summary prose that should be preserved." in content
    assert "Generated content:" in content
    assert "**Task files scanned**:" in content


def test_render_readme_maps_extended_style_sections(tmp_path):
    """Render README with extended guide headings and ensure no unknown placeholders."""
    role_src = BASE_ROLE_FIXTURE
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
        "from prism.scanner import run_scan;"
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
    role_src = BASE_ROLE_FIXTURE
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
        "from prism.scanner import run_scan;"
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
    role_src = BASE_ROLE_FIXTURE
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
        "from prism.scanner import run_scan;"
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
    assert [section["normalized_title"] for section in parsed["sections"]] == [
        "requirements",
        "totally custom section",
        "role variables",
    ]
    assert parsed["section_title_stats"]["total_sections"] == 3
    assert parsed["section_title_stats"]["known_sections"] == 2
    assert parsed["section_title_stats"]["unknown_sections"] == 1
    assert parsed["section_title_stats"]["by_section_id"]["unknown"]["titles"] == [
        "Totally Custom Section"
    ]
    assert parsed["section_title_stats"]["by_section_id"]["unknown"][
        "normalized_titles"
    ] == ["totally custom section"]
    assert parsed["variable_style"] == "simple_list"


def test_parse_style_readme_ignores_fenced_code_when_detecting_sections(tmp_path):
    style = tmp_path / "STYLE_FENCED_SETEXT.md"
    style.write_text(
        "Guide Title\n"
        "===========\n\n"
        "Role Variables\n"
        "--------------\n\n"
        "Variables from defaults:\n\n"
        "```yaml\n"
        "---\n"
        "demo_var: demo\n"
        "```\n\n"
        "Requirements\n"
        "------------\n\n"
        "No additional requirements.\n",
        encoding="utf-8",
    )

    parsed = scanner.parse_style_readme(str(style))

    assert [section["id"] for section in parsed["sections"]] == [
        "role_variables",
        "requirements",
    ]
    assert all(section["title"] != "```yaml" for section in parsed["sections"])
    assert parsed["variable_style"] == "yaml_block"


def test_parse_style_readme_detects_variable_table_style(tmp_path):
    style = tmp_path / "STYLE_TABLE.md"
    style.write_text(
        "# Guide\n\n"
        "## Role Variables\n\n"
        "Use these settings to customize behavior.\n\n"
        "| Name | Default | Description |\n"
        "| --- | --- | --- |\n"
        "| `demo_var` | `value` | Demo value |\n",
        encoding="utf-8",
    )

    parsed = scanner.parse_style_readme(str(style))

    assert parsed["variable_style"] == "table"
    assert parsed["variable_intro"] == "Use these settings to customize behavior."


def test_parse_style_readme_maps_additional_section_aliases(tmp_path):
    style = tmp_path / "STYLE_ALIASES.md"
    style.write_text(
        "# Guide\n\n"
        "## Installation\n\n"
        "## Handlers\n\n"
        "## Testing\n\n"
        "## Overriding configuration templates\n\n"
        "## .htaccess-based Basic Authorization\n",
        encoding="utf-8",
    )

    parsed = scanner.parse_style_readme(str(style))

    assert [section["id"] for section in parsed["sections"]] == [
        "installation",
        "handlers",
        "local_testing",
        "template_overrides",
        "basic_authorization",
    ]


def test_parse_style_readme_normalizes_markdown_link_headings(tmp_path):
    style = tmp_path / "STYLE_LINK_HEADINGS.md"
    style.write_text(
        "# Guide\n\n"
        "## [Example Playbook](#example-playbook)\n\n"
        "## [License](#license)\n",
        encoding="utf-8",
    )

    parsed = scanner.parse_style_readme(str(style))

    assert [section["id"] for section in parsed["sections"]] == [
        "example_usage",
        "license",
    ]
    assert [section["normalized_title"] for section in parsed["sections"]] == [
        "example playbook",
        "license",
    ]


def test_parse_style_readme_collects_stats_for_existing_section_titles(tmp_path):
    style = tmp_path / "STYLE_STATS.md"
    style.write_text(
        "# Guide\n\n## Role Variables\n\n## Variables\n\n## Example Playbook\n\n",
        encoding="utf-8",
    )

    parsed = scanner.parse_style_readme(str(style))

    stats = parsed["section_title_stats"]
    assert stats["total_sections"] == 3
    assert stats["known_sections"] == 3
    assert stats["unknown_sections"] == 0
    assert stats["by_section_id"]["role_variables"]["count"] == 2
    assert stats["by_section_id"]["role_variables"]["titles"] == [
        "Role Variables",
        "Variables",
    ]
    assert stats["by_section_id"]["role_variables"]["normalized_titles"] == [
        "role variables",
        "variables",
    ]
    assert stats["by_section_id"]["example_usage"]["count"] == 1


def test_parse_style_readme_uses_h3_sections_when_no_h2_exist(tmp_path):
    style = tmp_path / "STYLE_H3_ONLY.md"
    style.write_text(
        "# Guide\n\n### Installation\n\n### Role Variables\n\n- demo_var\n",
        encoding="utf-8",
    )

    parsed = scanner.parse_style_readme(str(style))

    assert parsed["section_style"] == "atx"
    assert parsed["section_level"] == 3
    assert [section["level"] for section in parsed["sections"]] == [3, 3]
    assert [section["id"] for section in parsed["sections"]] == [
        "installation",
        "role_variables",
    ]


def test_render_readme_keeps_unknown_sections_from_setext_guide_by_default(tmp_path):
    role_src = BASE_ROLE_FIXTURE
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
    assert "Style section retained from guide" in content
    assert "Role Variables\n--------------" in content


def test_render_readme_can_keep_unknown_sections_when_enabled(tmp_path):
    role_src = BASE_ROLE_FIXTURE
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

    out = tmp_path / "REVIEW_README_SETEXT_UNKNOWN_KEEP.md"
    result = scanner.run_scan(
        str(target),
        output=str(out),
        style_readme_path=str(style),
        keep_unknown_style_sections=True,
    )

    assert result.endswith("REVIEW_README_SETEXT_UNKNOWN_KEEP.md")
    content = out.read_text(encoding="utf-8")
    assert "Mystery Section\n---------------" in content
    assert (
        "Style section retained from guide; scanner does not map this section yet."
        in content
    )


def test_render_readme_preserves_unknown_section_body_when_present(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    style = tmp_path / "STYLE_UNKNOWN_WITH_BODY.md"
    style.write_text(
        "Guide Title\n"
        "===========\n\n"
        "Mystery Section\n"
        "---------------\n\n"
        "Keep this human-authored troubleshooting note.\n"
        "Second line of human guidance.\n\n"
        "Role Variables\n"
        "--------------\n",
        encoding="utf-8",
    )

    out = tmp_path / "REVIEW_README_SETEXT_UNKNOWN_BODY.md"
    result = scanner.run_scan(
        str(target),
        output=str(out),
        style_readme_path=str(style),
        keep_unknown_style_sections=True,
    )

    assert result.endswith("REVIEW_README_SETEXT_UNKNOWN_BODY.md")
    content = out.read_text(encoding="utf-8")
    assert "Mystery Section\n---------------" in content
    assert "Keep this human-authored troubleshooting note." in content
    assert "Second line of human guidance." in content
    assert "Style section retained from guide" not in content


def test_render_readme_can_suppress_unknown_sections_when_disabled(tmp_path):
    role_src = BASE_ROLE_FIXTURE
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

    out = tmp_path / "REVIEW_README_SETEXT_UNKNOWN_SUPPRESS.md"
    result = scanner.run_scan(
        str(target),
        output=str(out),
        style_readme_path=str(style),
        keep_unknown_style_sections=False,
    )

    assert result.endswith("REVIEW_README_SETEXT_UNKNOWN_SUPPRESS.md")
    content = out.read_text(encoding="utf-8")
    assert "Mystery Section\n---------------" not in content
    assert "Style section retained from guide" not in content
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
    assert "- `demo_var`: `value`" in rendered
    assert "- `other_var`: `2`" in rendered


def test_render_role_variables_simple_list_uses_guide_intro_when_present():
    rendered = scanner._render_role_variables_for_style(
        {"demo_var": "value"},
        {
            "style_guide": {
                "variable_style": "simple_list",
                "variable_intro": "Tune the inputs below for your environment.",
            },
            "variable_insights": [],
        },
    )

    assert rendered.startswith("Tune the inputs below for your environment.")
    assert "- `demo_var`: `value`" in rendered


def test_render_role_variables_renders_markdown_table_style():
    rendered = scanner._render_role_variables_for_style(
        {"role_port": 8080},
        {
            "style_guide": {
                "variable_style": "table",
                "variable_intro": "Documented variables:",
            },
            "variable_insights": [
                {
                    "name": "role_port",
                    "default": "8080",
                    "source": "defaults/main.yml",
                }
            ],
        },
    )

    assert rendered.startswith("Documented variables:")
    assert "| Name | Default | Description |" in rendered
    assert "| `role_port` | `8080` |" in rendered


def test_render_role_variables_simple_list_normalizes_multiline_markdown_values():
    rendered = scanner._render_role_variables_for_style(
        {
            "nginx_log_format": '$remote_addr\\n$status $body_bytes_sent "$http_referer"',
        },
        {"style_guide": {"variable_style": "simple_list"}, "variable_insights": []},
    )

    assert "- `nginx_log_format`: `" in rendered
    assert "$remote_addr\\n$status" in rendered
    assert "$status $body_bytes_sent" in rendered


def test_quality_metrics_and_comparison_report_detect_deltas(tmp_path):
    role_src = BASE_ROLE_FIXTURE
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
        == "No undocumented variables using `default()` were detected."
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
        [
            {"src": "example.role_dependency", "version": "1.0.0"},
            "example.collection_dependency",
        ],
        [],
        metadata,
    )
    assert "example.role_dependency (version: 1.0.0)" in requirements
    assert "example.collection_dependency" in requirements

    installation = scanner._render_guide_section_body(
        "installation", "demo", "", {}, [], [], metadata
    )
    assert "ansible-galaxy install demo-role" in installation
    assert "- src: demo-role" in installation

    variable_summary = scanner._render_guide_section_body(
        "variable_summary",
        "demo",
        "",
        {},
        [],
        [],
        {
            **metadata,
            "external_vars_context": {
                "paths": ["/tmp/group_vars/all.yml"],
                "authoritative": False,
            },
            "variable_insights": [
                {
                    "name": "v",
                    "type": "bool",
                    "default": "true",
                    "source": "defaults/main.yml",
                    "provenance_source_file": "defaults/main.yml",
                },
                {
                    "name": "seed_only",
                    "type": "str",
                    "default": "x",
                    "source": "seed: /tmp/group_vars/all.yml",
                    "provenance_source_file": "/tmp/group_vars/all.yml",
                },
            ],
        },
    )
    assert "| `v` | bool | `true` | defaults/main.yml |" in variable_summary
    assert "seed_only" not in variable_summary
    assert "non-authoritative hints" in variable_summary

    task_summary = scanner._render_guide_section_body(
        "task_summary",
        "demo",
        "",
        {},
        [],
        [],
        {
            **metadata,
            "detailed_catalog": True,
            "task_catalog": [
                {
                    "file": "tasks/main.yml",
                    "name": "Configure service",
                    "module": "ansible.builtin.template",
                    "parameters": "mode=0644, owner=root",
                }
            ],
        },
    )
    assert "**Task files scanned**: 2" in task_summary
    assert "| File | Task | Module | Parameters |" in task_summary
    assert (
        "| `tasks/main.yml` | Configure service | `ansible.builtin.template` | mode=0644, owner=root |"
        in task_summary
    )

    example = scanner._render_guide_section_body(
        "example_usage", "demo", "", {}, [], [], metadata
    )
    assert "```yaml" in example

    testing = scanner._render_guide_section_body(
        "local_testing",
        "demo",
        "",
        {},
        [],
        [],
        {
            **metadata,
            "molecule_scenarios": [
                {
                    "name": "default",
                    "driver": "podman",
                    "verifier": "ansible",
                    "platforms": ["fedora (quay.io/fedora:latest)"],
                }
            ],
        },
    )
    assert "ansible-playbook -i tests/inventory tests/test.yml" in testing
    assert "Molecule scenarios detected" in testing
    assert "driver: `podman`" in testing

    handlers = scanner._render_guide_section_body(
        "handlers",
        "demo",
        "",
        {},
        [],
        [],
        {
            **metadata,
            "handlers": ["handlers/main.yml"],
            "features": {"handlers_notified": "restart ssh"},
            "detailed_catalog": True,
            "handler_catalog": [
                {
                    "file": "handlers/main.yml",
                    "name": "restart ssh",
                    "module": "ansible.builtin.service",
                    "parameters": "state=restarted",
                }
            ],
        },
    )
    assert "**Handler files detected**: 1" in handlers
    assert "restart ssh" in handlers
    assert "| File | Handler | Module | Parameters |" in handlers
    assert (
        "| `handlers/main.yml` | restart ssh | `ansible.builtin.service` | state=restarted |"
        in handlers
    )

    template_overrides = scanner._render_guide_section_body(
        "template_overrides",
        "demo",
        "",
        {},
        [],
        [],
        {
            **metadata,
            "templates": ["templates/example.conf.j2"],
            "variable_insights": [
                {
                    "name": "nginx_conf_template",
                    "type": "str",
                    "default": "nginx.conf.j2",
                    "source": "defaults/main.yml",
                }
            ],
        },
    )
    assert "nginx_conf_template" in template_overrides
    assert "templates/example.conf.j2" in template_overrides

    basic_auth = scanner._render_guide_section_body(
        "basic_authorization", "demo", "", {}, [], [], metadata
    )
    assert ".htpasswd" in basic_auth

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
        "keep_unknown_style_sections": True,
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


def test_render_readme_preserves_h3_style_sections_when_used_by_guide(tmp_path):
    role_src = BASE_ROLE_FIXTURE
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    style = tmp_path / "STYLE_H3_ONLY.md"
    style.write_text(
        "# Guide\n\n### Installation\n\n### Role Variables\n\n",
        encoding="utf-8",
    )

    out = tmp_path / "REVIEW_README_H3.md"
    scanner.run_scan(str(target), output=str(out), style_readme_path=str(style))

    content = out.read_text(encoding="utf-8")
    assert "### Installation" in content
    assert "### Role Variables" in content
    assert "\n## Installation\n" not in content


# ── style_guide: uncovered branch coverage ─────────────────────────────────


def test_detect_style_section_level_skips_headings_inside_fenced_blocks():
    """Headings inside fenced code blocks must not influence the detected level."""
    lines = [
        "# Title",
        "",
        "## Real Section",
        "",
        "```",
        "## Not a heading inside fence",
        "more content",
        "```",
        "",
        "## Another Section",
    ]
    level = scanner.detect_style_section_level(lines)
    assert level == 2


def test_parse_style_readme_detects_table_variable_style(tmp_path):
    """parse_style_readme sets variable_style='table' for pipe-table variable sections."""
    style = tmp_path / "STYLE.md"
    style.write_text(
        "# Role\n\n"
        "Role Variables\n"
        "--------------\n\n"
        "Available variables:\n\n"
        "| Name | Default | Description |\n"
        "| --- | --- | --- |\n"
        "| `var1` | `value` | A variable |\n",
        encoding="utf-8",
    )
    parsed = scanner.parse_style_readme(str(style))
    assert parsed["variable_style"] == "table"
    assert parsed["variable_intro"] == "Available variables:"


def test_parse_style_readme_with_no_role_variables_section_returns_simple_list(
    tmp_path,
):
    """parse_style_readme defaults to simple_list when no Role Variables section exists."""
    style = tmp_path / "STYLE.md"
    style.write_text(
        "# Role\n\n" "Requirements\n" "------------\n\n" "Some requirements here.\n",
        encoding="utf-8",
    )
    parsed = scanner.parse_style_readme(str(style))
    assert parsed["variable_style"] == "simple_list"
    assert parsed["variable_intro"] is None


def test_parse_style_readme_detects_nested_bullets_with_intro(tmp_path):
    """parse_style_readme detects nested_bullets style with intro text before bullets."""
    style = tmp_path / "STYLE_NB_INTRO.md"
    style.write_text(
        "# Role\n\n"
        "Role Variables\n"
        "--------------\n\n"
        "Available below:\n\n"
        "- `var1`\n"
        "- Default: value1\n",
        encoding="utf-8",
    )
    parsed = scanner.parse_style_readme(str(style))
    assert parsed["variable_style"] == "nested_bullets"
    assert parsed["variable_intro"] == "Available below:"


def test_parse_style_readme_detects_nested_bullets_without_intro(tmp_path):
    """parse_style_readme detects nested_bullets style with no intro paragraph."""
    style = tmp_path / "STYLE_NB_PLAIN.md"
    style.write_text(
        "# Role\n\n"
        "Role Variables\n"
        "--------------\n\n"
        "- `var1`\n"
        "- Default: value1\n",
        encoding="utf-8",
    )
    parsed = scanner.parse_style_readme(str(style))
    assert parsed["variable_style"] == "nested_bullets"
    assert parsed["variable_intro"] is None


def test_detect_style_section_level_non_matching_fence_inside_fence():
    """A tilde fence inside a backtick fence does not close the backtick fence."""
    lines = [
        "# Title",
        "",
        "## Real Section",
        "",
        "```",
        "~~~",  # different fence char while in_fence — elif is False (80->84 branch)
        "## Still inside fence",
        "```",  # closes the backtick fence
        "",
        "## Outside Section",
    ]
    level = scanner.detect_style_section_level(lines)
    assert level == 2
