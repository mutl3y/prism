from prism.scanner_analysis import metrics as analysis_metrics
from prism.scanner_analysis import report as scanner_report
from prism.scanner_analysis.report import classify_provenance_issue
from prism.scanner_analysis.report import is_unresolved_noise_category
from prism.scanner_readme import guide as readme_guide


def build_scanner_report_markdown(**kwargs):
    return scanner_report.build_scanner_report_markdown(
        render_section_body=readme_guide._render_guide_section_body,
        **kwargs,
    )


def test_build_scanner_report_markdown_includes_annotation_quality_counters():
    """_build_scanner_report_markdown renders annotation quality counters."""
    report = build_scanner_report_markdown(
        role_name="test_role",
        description="Test description",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={
            "scanner_counters": {
                "total_variables": 0,
                "documented_variables": 0,
                "undocumented_variables": 0,
                "unresolved_variables": 0,
                "ambiguous_variables": 0,
                "secret_variables": 0,
                "required_variables": 0,
                "high_confidence_variables": 0,
                "medium_confidence_variables": 0,
                "low_confidence_variables": 0,
                "total_default_filters": 0,
                "undocumented_default_filters": 0,
                "included_role_calls": 0,
                "dynamic_included_role_calls": 0,
                "disabled_task_annotations": 2,
                "yaml_like_task_annotations": 1,
                "yaml_parse_failures": 0,
                "provenance_issue_categories": {
                    "unresolved_readme_documented_only": 0,
                    "ambiguous_include_vars_sources": 0,
                    "unresolved_dynamic_include_vars": 0,
                    "unresolved_no_static_definition": 0,
                    "unresolved_other": 0,
                    "precedence_defaults_overridden_by_vars": 0,
                    "ambiguous_set_fact_runtime": 0,
                    "ambiguous_other": 0,
                },
            }
        },
    )

    assert "Task annotation quality" in report
    assert "disabled=2" in report
    assert "yaml_like=1" in report


def test_build_scanner_report_markdown_renders_unresolved_variables():
    """_build_scanner_report_markdown renders unresolved variables section."""
    report = build_scanner_report_markdown(
        role_name="test_role",
        description="Test description",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={
            "variable_insights": [
                {
                    "name": "unresolved_var",
                    "is_unresolved": True,
                    "is_ambiguous": False,
                    "uncertainty_reason": "No static definition found.",
                }
            ],
            "scanner_counters": {
                "total_variables": 1,
                "documented_variables": 0,
                "undocumented_variables": 1,
                "unresolved_variables": 1,
                "ambiguous_variables": 0,
                "secret_variables": 0,
                "required_variables": 0,
                "high_confidence_variables": 0,
                "medium_confidence_variables": 0,
                "low_confidence_variables": 1,
                "total_default_filters": 0,
                "undocumented_default_filters": 0,
                "included_role_calls": 0,
                "dynamic_included_role_calls": 0,
                "yaml_parse_failures": 0,
                "provenance_issue_categories": {
                    "unresolved_no_static_definition": 1,
                    "unresolved_readme_documented_only": 0,
                    "unresolved_dynamic_include_vars": 0,
                    "unresolved_other": 0,
                    "precedence_defaults_overridden_by_vars": 0,
                    "ambiguous_include_vars_sources": 0,
                    "ambiguous_set_fact_runtime": 0,
                    "ambiguous_other": 0,
                },
            },
        },
    )

    assert "Variable provenance issues" in report
    assert "Unresolved variables:" in report
    assert "unresolved_var" in report
    assert "No static definition found." in report


def test_build_scanner_report_markdown_renders_yaml_parse_failures_without_ambiguous():
    """_build_scanner_report_markdown renders parse failures without ambiguous vars."""
    report = build_scanner_report_markdown(
        role_name="test_role",
        description="Test description",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={
            "yaml_parse_failures": [
                {
                    "file": "tasks/bad.yml",
                    "line": 5,
                    "column": 10,
                    "error": "expected ',', found EOF",
                }
            ],
            "variable_insights": [],
            "scanner_counters": {
                "total_variables": 0,
                "documented_variables": 0,
                "undocumented_variables": 0,
                "unresolved_variables": 0,
                "ambiguous_variables": 0,
                "secret_variables": 0,
                "required_variables": 0,
                "high_confidence_variables": 0,
                "medium_confidence_variables": 0,
                "low_confidence_variables": 0,
                "total_default_filters": 0,
                "undocumented_default_filters": 0,
                "included_role_calls": 0,
                "dynamic_included_role_calls": 0,
                "yaml_parse_failures": 1,
                "provenance_issue_categories": {
                    "unresolved_readme_documented_only": 0,
                    "unresolved_dynamic_include_vars": 0,
                    "unresolved_no_static_definition": 0,
                    "unresolved_other": 0,
                    "precedence_defaults_overridden_by_vars": 0,
                    "ambiguous_include_vars_sources": 0,
                    "ambiguous_set_fact_runtime": 0,
                    "ambiguous_other": 0,
                },
            },
        },
    )

    assert "YAML parse failures" in report
    assert "tasks/bad.yml:5:10" in report
    assert "expected ',', found EOF" in report


def test_build_scanner_report_markdown_renders_ambiguous_after_parse_failures():
    """_build_scanner_report_markdown renders ambiguous variables after parse failures."""
    report = build_scanner_report_markdown(
        role_name="test_role",
        description="Test description",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={
            "yaml_parse_failures": [
                {"file": "broken.yml", "line": 1, "column": 1, "error": "bad yaml"}
            ],
            "variable_insights": [
                {
                    "name": "ambig_var",
                    "is_unresolved": False,
                    "is_ambiguous": True,
                    "uncertainty_reason": "May come from include_vars.",
                }
            ],
            "scanner_counters": {
                "total_variables": 1,
                "documented_variables": 1,
                "undocumented_variables": 0,
                "unresolved_variables": 0,
                "ambiguous_variables": 1,
                "secret_variables": 0,
                "required_variables": 0,
                "high_confidence_variables": 0,
                "medium_confidence_variables": 1,
                "low_confidence_variables": 0,
                "total_default_filters": 0,
                "undocumented_default_filters": 0,
                "included_role_calls": 0,
                "dynamic_included_role_calls": 0,
                "yaml_parse_failures": 1,
                "provenance_issue_categories": {
                    "unresolved_readme_documented_only": 0,
                    "unresolved_dynamic_include_vars": 0,
                    "unresolved_no_static_definition": 0,
                    "unresolved_other": 0,
                    "precedence_defaults_overridden_by_vars": 0,
                    "ambiguous_include_vars_sources": 1,
                    "ambiguous_set_fact_runtime": 0,
                    "ambiguous_other": 0,
                },
            },
        },
    )

    assert "YAML parse failures" in report
    assert "broken.yml:1:1" in report
    assert "Ambiguous variables:" in report
    assert "ambig_var" in report
    assert "May come from include_vars." in report


def test_build_scanner_report_markdown_issue_list_rows_keep_parity_with_fallbacks():
    """Issue-list row rendering keeps unresolved/ambiguous markdown output stable."""
    report = build_scanner_report_markdown(
        role_name="test_role",
        description="Test description",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={
            "yaml_parse_failures": [
                {
                    "file": "tasks/bad.yml",
                    "line": 1,
                    "column": 2,
                    "error": "broken",
                }
            ],
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
                    "name": "ambig_fallback",
                    "is_unresolved": False,
                    "is_ambiguous": True,
                    "uncertainty_reason": "",
                },
            ],
            "scanner_counters": {
                "total_variables": 3,
                "documented_variables": 0,
                "undocumented_variables": 3,
                "unresolved_variables": 2,
                "ambiguous_variables": 1,
                "secret_variables": 0,
                "required_variables": 0,
                "high_confidence_variables": 0,
                "medium_confidence_variables": 0,
                "low_confidence_variables": 3,
                "total_default_filters": 0,
                "undocumented_default_filters": 0,
                "included_role_calls": 0,
                "dynamic_included_role_calls": 0,
                "yaml_parse_failures": 1,
                "provenance_issue_categories": {
                    "unresolved_readme_documented_only": 0,
                    "unresolved_dynamic_include_vars": 0,
                    "unresolved_no_static_definition": 1,
                    "unresolved_other": 1,
                    "precedence_defaults_overridden_by_vars": 0,
                    "ambiguous_include_vars_sources": 1,
                    "ambiguous_set_fact_runtime": 0,
                    "ambiguous_other": 0,
                },
            },
        },
    )

    assert "- `unresolved_with_reason`: No static definition found." in report
    assert "- `unresolved_fallback`: Unknown source." in report
    assert "- `ambig_fallback`: Multiple possible sources." in report


def test_build_scanner_report_markdown_yaml_parse_failure_rows_keep_parity():
    """YAML parse-failure row rendering keeps markdown output stable."""
    report = build_scanner_report_markdown(
        role_name="test_role",
        description="Test description",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={
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
            "variable_insights": [],
            "scanner_counters": {
                "total_variables": 0,
                "documented_variables": 0,
                "undocumented_variables": 0,
                "unresolved_variables": 0,
                "ambiguous_variables": 0,
                "secret_variables": 0,
                "required_variables": 0,
                "high_confidence_variables": 0,
                "medium_confidence_variables": 0,
                "low_confidence_variables": 0,
                "total_default_filters": 0,
                "undocumented_default_filters": 0,
                "included_role_calls": 0,
                "dynamic_included_role_calls": 0,
                "yaml_parse_failures": 2,
                "provenance_issue_categories": {
                    "unresolved_readme_documented_only": 0,
                    "unresolved_dynamic_include_vars": 0,
                    "unresolved_no_static_definition": 0,
                    "unresolved_other": 0,
                    "precedence_defaults_overridden_by_vars": 0,
                    "ambiguous_include_vars_sources": 0,
                    "ambiguous_set_fact_runtime": 0,
                    "ambiguous_other": 0,
                },
            },
        },
    )

    assert "- `tasks/bad.yml:5:10`: expected ',', found EOF" in report
    assert "- `defaults/main.yml`: parse error" in report


def test_classify_provenance_issue_unresolved_with_dynamic_include_vars_reason():
    """_classify_provenance_issue classifies 'dynamic include_vars' unresolved issues."""
    result = classify_provenance_issue(
        {
            "is_unresolved": True,
            "is_ambiguous": False,
            "uncertainty_reason": "Referenced but not in static analysis; likely from dynamic include_vars.",
        }
    )
    assert result == "unresolved_dynamic_include_vars"


def test_classify_provenance_issue_unresolved_with_other_reason():
    """_classify_provenance_issue classifies unresolved with unrecognized reason."""
    result = classify_provenance_issue(
        {
            "is_unresolved": True,
            "is_ambiguous": False,
            "uncertainty_reason": "Some other reason.",
        }
    )
    assert result == "unresolved_other"


def test_classify_provenance_issue_precedence_defaults_overridden_by_vars():
    """Vars precedence is classified as informational precedence, not unresolved."""
    result = classify_provenance_issue(
        {
            "is_unresolved": False,
            "is_ambiguous": True,
            "uncertainty_reason": "Defaults value is superseded by vars/main.yml precedence (informational).",
        }
    )
    assert result == "precedence_defaults_overridden_by_vars"


def test_is_unresolved_noise_category_excludes_precedence_informational_category():
    """Precedence informational category must not be counted as unresolved noise."""
    assert (
        is_unresolved_noise_category("precedence_defaults_overridden_by_vars") is False
    )
    assert is_unresolved_noise_category("ambiguous_defaults_vars_override") is False
    assert is_unresolved_noise_category("unresolved_other") is True


def test_classify_provenance_issue_ambiguous_with_runtime_reason():
    """_classify_provenance_issue classifies set_fact runtime ambiguous issues."""
    result = classify_provenance_issue(
        {
            "is_unresolved": False,
            "is_ambiguous": True,
            "uncertainty_reason": "Value set at runtime by set_fact.",
        }
    )
    assert result == "ambiguous_set_fact_runtime"


def test_classify_provenance_issue_ambiguous_with_non_set_fact_runtime_reason():
    """Generic runtime ambiguity does not get attributed to set_fact bucket."""
    result = classify_provenance_issue(
        {
            "is_unresolved": False,
            "is_ambiguous": True,
            "uncertainty_reason": "Runtime value may depend on host context.",
        }
    )
    assert result == "ambiguous_other"


def test_build_referenced_variable_uncertainty_reason_targets_dynamic_include_var_tokens():
    reason = analysis_metrics.build_referenced_variable_uncertainty_reason(
        name="foo_var",
        seeded=False,
        dynamic_include_vars_refs=["{{ env }}.yml"],
        dynamic_include_var_tokens={"env"},
        dynamic_task_include_tokens=set(),
    )
    assert reason == "Referenced in role but no static definition found."


def test_build_referenced_variable_uncertainty_reason_marks_matching_dynamic_include_var_tokens():
    reason = analysis_metrics.build_referenced_variable_uncertainty_reason(
        name="env",
        seeded=False,
        dynamic_include_vars_refs=["{{ env }}.yml"],
        dynamic_include_var_tokens={"env"},
        dynamic_task_include_tokens=set(),
    )
    assert "Dynamic include_vars paths detected." in reason


def test_classify_provenance_issue_ambiguous_with_other_reason():
    """_classify_provenance_issue classifies ambiguous with unrecognized reason."""
    result = classify_provenance_issue(
        {
            "is_unresolved": False,
            "is_ambiguous": True,
            "uncertainty_reason": "Some other cause of ambiguity.",
        }
    )
    assert result == "ambiguous_other"


def test_classify_provenance_issue_returns_none_for_resolved_unambiguous():
    """_classify_provenance_issue returns None for resolved, unambiguous rows."""
    result = classify_provenance_issue(
        {
            "is_unresolved": False,
            "is_ambiguous": False,
            "uncertainty_reason": "",
        }
    )
    assert result is None
