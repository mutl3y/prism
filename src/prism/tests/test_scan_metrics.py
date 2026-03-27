"""Focused tests for scanner metrics and uncertainty-shaping helpers."""

from typing import get_type_hints

from prism import scanner
from prism.scanner_submodules import scan_metrics, scanner_report


def test_build_referenced_variable_uncertainty_reason_shapes_expected_messages():
    unresolved = scan_metrics.build_referenced_variable_uncertainty_reason(
        name="env",
        seeded=False,
        dynamic_include_vars_refs=["{{ env }}.yml"],
        dynamic_include_var_tokens={"env"},
        dynamic_task_include_tokens={"env"},
    )
    seeded = scan_metrics.build_referenced_variable_uncertainty_reason(
        name="seeded_var",
        seeded=True,
        dynamic_include_vars_refs=[],
        dynamic_include_var_tokens=set(),
        dynamic_task_include_tokens=set(),
    )

    assert "Dynamic include_vars paths detected." in unresolved
    assert "Dynamic include_tasks/import_tasks paths detected." in unresolved
    assert seeded == "Provided by external seed vars."


def test_append_non_authoritative_test_evidence_uncertainty_reason_shapes_suffix():
    reason = scan_metrics.append_non_authoritative_test_evidence_uncertainty_reason(
        prior_reason="Referenced in role but no static definition found.",
        match_count=4,
        matched_file_count=2,
        saturation_threshold=4,
        scan_budget_hit=True,
    )

    assert reason.startswith("Referenced in role but no static definition found.")
    assert "(4 match(es) across 2 file(s))" in reason
    assert "Match counting is saturated at threshold for performance." in reason
    assert "Evidence scan budget limit was reached." in reason


def test_scanner_wrapper_extract_scanner_counters_delegates(monkeypatch):
    captured = {}

    def fake_extract_scanner_counters(
        variable_insights,
        default_filters,
        features,
        parse_failures,
    ):
        captured["variable_insights"] = variable_insights
        captured["default_filters"] = default_filters
        captured["features"] = features
        captured["parse_failures"] = parse_failures
        return {"ok": 1}

    monkeypatch.setattr(
        scanner,
        "_scan_metrics_extract_scanner_counters",
        fake_extract_scanner_counters,
    )

    result = scanner._extract_scanner_counters(
        [{"name": "a"}],
        [{"match": "b"}],
        {"included_role_calls": 1},
        [{"file": "tasks/main.yml"}],
    )

    assert result == {"ok": 1}
    assert captured["variable_insights"] == [{"name": "a"}]
    assert captured["default_filters"] == [{"match": "b"}]
    assert captured["features"] == {"included_role_calls": 1}
    assert captured["parse_failures"] == [{"file": "tasks/main.yml"}]


def test_scanner_wrapper_uncertainty_helpers_delegate(monkeypatch):
    monkeypatch.setattr(
        scanner,
        "_scan_metrics_build_referenced_variable_uncertainty_reason",
        lambda **kwargs: f"build::{kwargs['name']}",
    )
    monkeypatch.setattr(
        scanner,
        "_scan_metrics_append_non_authoritative_test_evidence_uncertainty_reason",
        lambda **kwargs: (f"append::{kwargs['prior_reason']}::{kwargs['match_count']}"),
    )

    reason = scanner._build_referenced_variable_uncertainty_reason(
        name="MY_ENV",
        seeded=False,
        dynamic_include_vars_refs=[],
        dynamic_include_var_tokens=set(),
        dynamic_task_include_tokens=set(),
    )
    merged = scanner._append_non_authoritative_test_evidence_uncertainty_reason(
        prior_reason="base",
        match_count=2,
        matched_file_count=1,
        saturation_threshold=4,
        scan_budget_hit=False,
    )

    assert reason == "build::MY_ENV"
    assert merged == "append::base::2"


def test_extract_scanner_counters_keeps_provenance_categories_mapping_shape():
    counters = scanner_report.extract_scanner_counters(
        [
            {
                "documented": False,
                "is_unresolved": True,
                "is_ambiguous": False,
                "secret": False,
                "required": True,
                "provenance_confidence": 0.3,
                "uncertainty_reason": "Referenced in role but no static definition found.",
            }
        ],
        [],
    )

    categories = counters["provenance_issue_categories"]
    assert isinstance(categories, dict)
    assert categories["unresolved_no_static_definition"] == 1
    assert counters["unresolved_noise_variables"] == 1


def test_scanner_report_typed_render_input_contract_annotations():
    assert set(scanner_report.ScannerReportMetadata.__annotations__) == {
        "scanner_counters",
        "variable_insights",
        "features",
        "yaml_parse_failures",
    }
    assert set(scanner_report.ReadmeSectionRenderInput.__annotations__) == {
        "section_id",
        "role_name",
        "description",
        "variables",
        "requirements",
        "default_filters",
        "metadata",
    }
    assert set(scanner_report.ScannerReportIssueListRow.__annotations__) == {
        "name",
        "uncertainty_reason",
    }
    assert set(scanner_report.ScannerReportYamlParseFailureRow.__annotations__) == {
        "location",
        "error",
    }
    assert set(scanner_report.ScannerReportSectionRenderInput.__annotations__) == {
        "title",
        "body",
    }
    assert set(scanner_report.NormalizedScannerReportMetadata.__annotations__) == {
        "scanner_counters",
        "variable_insights",
        "features",
        "yaml_parse_failures",
    }

    build_hints = get_type_hints(scanner_report.build_readme_section_render_input)
    normalize_hints = get_type_hints(
        scanner_report.coerce_optional_scanner_report_metadata_fields
    )
    render_hints = get_type_hints(scanner_report.build_scanner_report_markdown)

    assert build_hints["return"] is scanner_report.ReadmeSectionRenderInput
    assert normalize_hints["return"] is scanner_report.NormalizedScannerReportMetadata
    assert render_hints["metadata"] is scanner_report.ScannerReportMetadata


def test_scanner_report_optional_metadata_coercion_defaults_and_types():
    normalized = scanner_report.coerce_optional_scanner_report_metadata_fields(
        {
            "scanner_counters": "invalid",
            "variable_insights": None,
            "features": [],
            "yaml_parse_failures": None,
        }
    )

    assert normalized == {
        "scanner_counters": None,
        "variable_insights": [],
        "features": {},
        "yaml_parse_failures": [],
    }


def test_scanner_report_optional_metadata_coercion_preserves_markdown_parity():
    kwargs = {
        "role_name": "demo",
        "description": "desc",
        "variables": {},
        "requirements": [],
        "default_filters": [],
        "render_section_body": lambda *_args: "",
    }

    report_with_nones = scanner_report.build_scanner_report_markdown(
        metadata={
            "variable_insights": None,
            "features": None,
            "yaml_parse_failures": None,
        },
        **kwargs,
    )
    report_with_defaults = scanner_report.build_scanner_report_markdown(
        metadata={
            "variable_insights": [],
            "features": {},
            "yaml_parse_failures": [],
        },
        **kwargs,
    )

    assert report_with_nones == report_with_defaults


def test_scanner_report_issue_list_row_helpers_preserve_reason_and_fallback():
    explicit = scanner_report.build_scanner_report_issue_list_row(
        row={"name": "explicit_var", "uncertainty_reason": "From include_vars"}
    )
    missing = scanner_report.build_scanner_report_issue_list_row(
        row={"name": "missing_var", "uncertainty_reason": ""}
    )

    assert explicit == {
        "name": "explicit_var",
        "uncertainty_reason": "From include_vars",
    }
    assert missing == {
        "name": "missing_var",
        "uncertainty_reason": None,
    }
    assert (
        scanner_report.render_scanner_report_issue_list_row(
            row=explicit,
            fallback_reason="Unknown source.",
        )
        == "- `explicit_var`: From include_vars"
    )
    assert (
        scanner_report.render_scanner_report_issue_list_row(
            row=missing,
            fallback_reason="Unknown source.",
        )
        == "- `missing_var`: Unknown source."
    )


def test_scanner_report_yaml_parse_failure_row_helpers_preserve_parity():
    with_location = scanner_report.build_scanner_report_yaml_parse_failure_row(
        row={
            "file": "tasks/bad.yml",
            "line": 7,
            "column": 4,
            "error": "bad yaml",
        }
    )
    fallback = scanner_report.build_scanner_report_yaml_parse_failure_row(
        row={"file": "defaults/main.yml", "error": ""}
    )

    assert with_location == {
        "location": "tasks/bad.yml:7:4",
        "error": "bad yaml",
    }
    assert fallback == {
        "location": "defaults/main.yml",
        "error": "parse error",
    }
    assert (
        scanner_report.render_scanner_report_yaml_parse_failure_row(
            row=with_location,
        )
        == "- `tasks/bad.yml:7:4`: bad yaml"
    )
    assert (
        scanner_report.render_scanner_report_yaml_parse_failure_row(
            row=fallback,
        )
        == "- `defaults/main.yml`: parse error"
    )


def test_scanner_report_build_readme_section_render_input_shapes_payload():
    metadata = {
        "features": {"tasks_scanned": 1},
        "variable_insights": [{"name": "a"}],
    }

    payload = scanner_report.build_readme_section_render_input(
        section_id="features",
        role_name="demo",
        description="desc",
        variables={"x": 1},
        requirements=["dep"],
        default_filters=[{"match": "x | default(1)"}],
        metadata=metadata,
    )

    assert payload == {
        "section_id": "features",
        "role_name": "demo",
        "description": "desc",
        "variables": {"x": 1},
        "requirements": ["dep"],
        "default_filters": [{"match": "x | default(1)"}],
        "metadata": metadata,
    }


def test_scanner_report_section_render_helpers_preserve_parity():
    row = scanner_report.build_scanner_report_section_render_input(
        title="Auto-detected role features",
        body="- includes tasks/main.yml",
    )

    assert row == {
        "title": "Auto-detected role features",
        "body": "- includes tasks/main.yml",
    }
    assert scanner_report.render_scanner_report_section(row=row) == [
        "Auto-detected role features",
        "---------------------------",
        "",
        "- includes tasks/main.yml",
        "",
    ]


def test_section_body_render_result_normalization_strips_and_computes_has_content():
    trimmed = scanner_report.normalize_section_body_render_result("  some body  \n")
    empty = scanner_report.normalize_section_body_render_result("  \n  ")
    inline = scanner_report.normalize_section_body_render_result("- item")

    assert trimmed == {"body": "some body", "has_content": True}
    assert empty == {"body": "", "has_content": False}
    assert inline == {"body": "- item", "has_content": True}


def test_section_body_render_result_type_annotations_match_typeddict():
    hints = get_type_hints(scanner_report.SectionBodyRenderResult)

    assert hints == {"body": str, "has_content": bool}


def test_invoke_readme_section_renderer_unpacks_input_and_normalizes():
    captured = {}

    def fake_renderer(
        section_id,
        role_name,
        description,
        variables,
        requirements,
        default_filters,
        metadata,
    ):
        captured["section_id"] = section_id
        captured["role_name"] = role_name
        captured["description"] = description
        captured["variables"] = variables
        captured["requirements"] = requirements
        captured["default_filters"] = default_filters
        captured["metadata"] = metadata
        return "  rendered body  "

    metadata: dict = {"features": {}}
    render_input = scanner_report.build_readme_section_render_input(
        section_id="features",
        role_name="demo",
        description="desc",
        variables={"x": 1},
        requirements=["req"],
        default_filters=[{"filter": "x"}],
        metadata=metadata,
    )
    result = scanner_report.invoke_readme_section_renderer(
        render_input=render_input,
        renderer=fake_renderer,
    )

    assert result == {"body": "rendered body", "has_content": True}
    assert captured["section_id"] == "features"
    assert captured["role_name"] == "demo"
    assert captured["variables"] == {"x": 1}
    assert captured["default_filters"] == [{"filter": "x"}]


def test_invoke_readme_section_renderer_empty_body_marks_has_content_false():
    render_input = scanner_report.build_readme_section_render_input(
        section_id="task_summary",
        role_name="demo",
        description="desc",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={},
    )
    result = scanner_report.invoke_readme_section_renderer(
        render_input=render_input,
        renderer=lambda *_args: "   ",
    )

    assert result == {"body": "", "has_content": False}


def test_build_scanner_report_markdown_invoke_renderer_section_order_parity():
    invocations: list[str] = []

    def tracking_renderer(
        section_id,
        role_name,
        description,
        variables,
        requirements,
        default_filters,
        metadata,
    ):
        invocations.append(section_id)
        return ""

    scanner_report.build_scanner_report_markdown(
        role_name="demo",
        description="desc",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={},
        render_section_body=tracking_renderer,
    )

    assert invocations == [
        "task_summary",
        "role_contents",
        "features",
        "comparison",
        "default_filters",
    ]


def test_annotation_quality_counters_typeddict_annotations():
    assert set(scanner_report.AnnotationQualityCounters.__annotations__) == {
        "disabled_task_annotations",
        "yaml_like_task_annotations",
    }


def test_coerce_annotation_quality_counters_from_features_standard_values():
    result = scanner_report.coerce_annotation_quality_counters_from_features(
        {"disabled_task_annotations": 3, "yaml_like_task_annotations": 7}
    )

    assert result == {"disabled_task_annotations": 3, "yaml_like_task_annotations": 7}


def test_coerce_annotation_quality_counters_from_features_missing_keys():
    result = scanner_report.coerce_annotation_quality_counters_from_features({})

    assert result == {"disabled_task_annotations": 0, "yaml_like_task_annotations": 0}


def test_coerce_annotation_quality_counters_from_features_none_values():
    result = scanner_report.coerce_annotation_quality_counters_from_features(
        {"disabled_task_annotations": None, "yaml_like_task_annotations": None}
    )

    assert result == {"disabled_task_annotations": 0, "yaml_like_task_annotations": 0}


def test_coerce_annotation_quality_counters_from_features_string_int_values():
    result = scanner_report.coerce_annotation_quality_counters_from_features(
        {"disabled_task_annotations": "2", "yaml_like_task_annotations": "5"}
    )

    assert result == {"disabled_task_annotations": 2, "yaml_like_task_annotations": 5}


def test_extract_scanner_counters_annotation_quality_parity_via_features():
    counters = scanner_report.extract_scanner_counters(
        [],
        [],
        features={
            "disabled_task_annotations": 4,
            "yaml_like_task_annotations": 1,
        },
    )

    assert counters["disabled_task_annotations"] == 4
    assert counters["yaml_like_task_annotations"] == 1
