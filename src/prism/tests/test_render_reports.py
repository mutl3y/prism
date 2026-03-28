"""Focused tests for scanner-report and runbook rendering helpers."""

from prism.scanner_submodules import render_reports


def _scanner_counters(**overrides):
    counters = {
        "total_variables": 3,
        "documented_variables": 1,
        "undocumented_variables": 2,
        "unresolved_variables": 2,
        "unresolved_noise_variables": 2,
        "ambiguous_variables": 1,
        "secret_variables": 0,
        "required_variables": 1,
        "high_confidence_variables": 0,
        "medium_confidence_variables": 1,
        "low_confidence_variables": 2,
        "total_default_filters": 1,
        "undocumented_default_filters": 1,
        "included_role_calls": 1,
        "dynamic_included_role_calls": 2,
        "disabled_task_annotations": 2,
        "yaml_like_task_annotations": 1,
        "yaml_parse_failures": 2,
        "non_authoritative_test_evidence_variables": 0,
        "non_authoritative_test_evidence_saturation_hits": 0,
        "non_authoritative_test_evidence_budget_hits": 0,
        "provenance_issue_categories": {
            "unresolved_readme_documented_only": 0,
            "unresolved_dynamic_include_vars": 0,
            "unresolved_no_static_definition": 1,
            "unresolved_other": 1,
            "precedence_defaults_overridden_by_vars": 0,
            "ambiguous_defaults_vars_override": 0,
            "ambiguous_include_vars_sources": 1,
            "ambiguous_set_fact_runtime": 0,
            "ambiguous_other": 0,
        },
    }
    counters.update(overrides)
    return counters


def test_render_reports_module_builds_scanner_report_markdown_with_stable_contract():
    section_bodies = {
        "task_summary": "Task summary body.",
        "role_contents": "Role contents body.",
        "features": "Features body.",
        "comparison": "Comparison body.",
        "default_filters": "Default filter body.",
    }

    def fake_render_section_body(
        section_id,
        role_name,
        description,
        variables,
        requirements,
        default_filters,
        metadata,
    ):
        del role_name, description, variables, requirements, default_filters, metadata
        return section_bodies.get(section_id, "")

    report = render_reports.build_scanner_report_markdown(
        role_name="demo_role",
        description="Demo description",
        variables={},
        requirements=[],
        default_filters=[{"match": "fallback"}],
        metadata={
            "variable_insights": [
                {
                    "name": "unresolved_with_reason",
                    "is_unresolved": True,
                    "is_ambiguous": False,
                    "uncertainty_reason": "No static definition found.",
                },
                {
                    "name": "unresolved_fallback",
                    "is_unresolved": True,
                    "is_ambiguous": False,
                    "uncertainty_reason": "",
                },
                {
                    "name": "ambiguous_fallback",
                    "is_unresolved": False,
                    "is_ambiguous": True,
                    "uncertainty_reason": "",
                },
            ],
            "yaml_parse_failures": [
                {
                    "file": "tasks/bad.yml",
                    "line": 5,
                    "column": 10,
                    "error": "expected ',', found EOF",
                },
                {
                    "file": "defaults/main.yml",
                    "error": "",
                },
            ],
            "scanner_counters": _scanner_counters(),
        },
        render_section_body=fake_render_section_body,
    )

    title = "demo_role scanner report"
    assert report.startswith(f"{title}\n{'=' * len(title)}\n\nDemo description\n\n")
    assert "- **Task annotation quality**: disabled=2, yaml_like=1" in report
    assert "- **Provenance issue categories**:" in report
    assert "  - `unresolved_no_static_definition`: 1" in report
    assert "  - `ambiguous_include_vars_sources`: 1" in report
    assert "- `unresolved_with_reason`: No static definition found." in report
    assert "- `unresolved_fallback`: Unknown source." in report
    assert "- `ambiguous_fallback`: Multiple possible sources." in report
    assert "- `tasks/bad.yml:5:10`: expected ',', found EOF" in report
    assert "- `defaults/main.yml`: parse error" in report

    ordered_headings = [
        "Summary",
        "Variable provenance issues",
        "YAML parse failures",
        "Task/module usage summary",
        "Role contents summary",
        "Auto-detected role features",
        "Comparison against local baseline role",
        "Detected usages of the default() filter",
    ]
    heading_indexes = [
        report.index(f"{heading}\n{'-' * len(heading)}") for heading in ordered_headings
    ]
    assert heading_indexes == sorted(heading_indexes)
    assert report.index("Unresolved variables:") < report.index(
        "YAML parse failures\n-------------------"
    )
    assert report.index("Ambiguous variables:") > report.index(
        "YAML parse failures\n-------------------"
    )


def test_render_reports_module_renders_runbook_markdown_with_stable_sections():
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

    content = render_reports.render_runbook("my_role", metadata)

    assert "# RUNBOOK: my_role" in content
    assert "## Role Notes" in content
    assert "standard deploy role" in content
    assert "## Task Runbooks" in content
    assert "#### `tasks/main.yml` - Deploy app" in content
    assert '<a id="task-main-yml-deploy-app-1"></a>' in content
    assert "copy /tmp/app to /opt/app then restart" in content
    assert "Warning: requires sudo" in content
    assert "#### `tasks/main.yml` - Validate app" in content
    assert "| Field | Value |" not in content
    assert "- No comments." not in content


def test_render_reports_module_builds_runbook_rows_with_stable_value_shaping():
    rows = render_reports.build_runbook_rows(
        {
            "task_catalog": [
                {
                    "file": "tasks/main.yml",
                    "name": "Deploy app",
                    "annotations": [
                        {
                            "kind": "runbook",
                            "text": "copy /tmp/app to /opt/app then restart",
                        },
                        {"kind": "warning", "text": "requires sudo"},
                        {"kind": "note", "text": "verify config"},
                    ],
                },
                {
                    "file": "tasks/main.yml",
                    "name": "Validate app",
                    "annotations": [],
                },
            ]
        }
    )

    assert rows == [
        (
            "tasks/main.yml",
            "Deploy app",
            "copy /tmp/app to /opt/app then restart",
        ),
        ("tasks/main.yml", "Deploy app", "Warning: requires sudo"),
        ("tasks/main.yml", "Deploy app", "Note: verify config"),
    ]


def test_render_reports_module_renders_runbook_csv_with_stable_header_and_rows():
    content = render_reports.render_runbook_csv(
        {
            "task_catalog": [
                {
                    "file": "tasks/main.yml",
                    "name": "Deploy app",
                    "annotations": [
                        {
                            "kind": "runbook",
                            "text": "copy /tmp/app to /opt/app then restart",
                        },
                        {"kind": "warning", "text": "requires sudo"},
                    ],
                }
            ]
        }
    )

    assert content.splitlines() == [
        "file,task_name,step",
        "tasks/main.yml,Deploy app,copy /tmp/app to /opt/app then restart",
        "tasks/main.yml,Deploy app,Warning: requires sudo",
    ]
