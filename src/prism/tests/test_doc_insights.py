from prism.scanner_submodules.doc_insights import build_doc_insights, parse_comma_values


def test_parse_comma_values_normal():
    assert parse_comma_values("a, b, c") == ["a", "b", "c"]


def test_parse_comma_values_none_string():
    assert parse_comma_values("none") == []


def test_parse_comma_values_empty_string():
    assert parse_comma_values("") == []


def test_parse_comma_values_whitespace_only():
    assert parse_comma_values("   ") == []


def test_parse_comma_values_single_item():
    assert parse_comma_values("ansible.builtin.template") == [
        "ansible.builtin.template"
    ]


def test_parse_comma_values_strips_internal_spaces():
    assert parse_comma_values("  x ,  y  ") == ["x", "y"]


def test_build_doc_insights_returns_required_keys():
    result = build_doc_insights(
        role_name="myrole",
        description="A test role",
        metadata={},
        variables={},
        variable_insights=[],
    )

    assert "purpose_summary" in result
    assert "capabilities" in result
    assert "task_summary" in result
    assert "example_playbook" in result


def test_build_doc_insights_uses_description_as_purpose():
    result = build_doc_insights(
        role_name="myrole",
        description="Installs nginx",
        metadata={},
        variables={},
        variable_insights=[],
    )

    assert result["purpose_summary"] == "Installs nginx"


def test_build_doc_insights_fallback_purpose_when_no_description():
    result = build_doc_insights(
        role_name="myrole",
        description="",
        metadata={},
        variables={},
        variable_insights=[],
    )

    assert "myrole" in result["purpose_summary"]


def test_build_doc_insights_detects_template_capability():
    result = build_doc_insights(
        role_name="myrole",
        description="desc",
        metadata={"features": {"unique_modules": "template, service"}},
        variables={},
        variable_insights=[],
    )

    assert any("configuration" in cap.lower() for cap in result["capabilities"])
    assert any("service" in cap.lower() for cap in result["capabilities"])


def test_build_doc_insights_detects_package_capability():
    result = build_doc_insights(
        role_name="myrole",
        description="desc",
        metadata={"features": {"unique_modules": "apt"}},
        variables={},
        variable_insights=[],
    )

    assert any("package" in cap.lower() for cap in result["capabilities"])


def test_build_doc_insights_detects_user_capability():
    result = build_doc_insights(
        role_name="myrole",
        description="desc",
        metadata={"features": {"unique_modules": "user"}},
        variables={},
        variable_insights=[],
    )

    assert any("user" in cap.lower() for cap in result["capabilities"])


def test_build_doc_insights_detects_lineinfile_capability():
    result = build_doc_insights(
        role_name="myrole",
        description="desc",
        metadata={"features": {"unique_modules": "lineinfile"}},
        variables={},
        variable_insights=[],
    )

    assert any("configuration" in cap.lower() for cap in result["capabilities"])


def test_build_doc_insights_detects_recursive_includes_capability():
    result = build_doc_insights(
        role_name="myrole",
        description="desc",
        metadata={"features": {"recursive_task_includes": 2}},
        variables={},
        variable_insights=[],
    )

    assert any("nested" in cap.lower() for cap in result["capabilities"])


def test_build_doc_insights_detects_handler_capability():
    result = build_doc_insights(
        role_name="myrole",
        description="desc",
        metadata={"features": {"handlers_notified": "restart nginx"}},
        variables={},
        variable_insights=[],
    )

    assert any("handler" in cap.lower() for cap in result["capabilities"])


def test_build_doc_insights_fallback_capability_when_no_modules():
    result = build_doc_insights(
        role_name="myrole",
        description="desc",
        metadata={},
        variables={},
        variable_insights=[],
    )

    assert any("reusable" in cap.lower() for cap in result["capabilities"])


def test_build_doc_insights_example_playbook_includes_role():
    result = build_doc_insights(
        role_name="my_role",
        description="desc",
        metadata={},
        variables={"var_a": "val_a"},
        variable_insights=[
            {"name": "var_a", "default": "val_a"},
        ],
    )

    assert "my_role" in result["example_playbook"]
    assert "var_a" in result["example_playbook"]


def test_build_doc_insights_example_playbook_empty_vars_block():
    result = build_doc_insights(
        role_name="my_role",
        description="desc",
        metadata={},
        variables={"x": 1},
        variable_insights=[],
    )

    assert "vars: {}" in result["example_playbook"]


def test_build_doc_insights_task_summary_counts():
    result = build_doc_insights(
        role_name="myrole",
        description="desc",
        metadata={
            "features": {
                "task_files_scanned": 3,
                "tasks_scanned": 12,
                "recursive_task_includes": 1,
                "unique_modules": "apt, service",
                "handlers_notified": "restart svc",
            }
        },
        variables={},
        variable_insights=[],
    )

    ts = result["task_summary"]
    assert ts["task_files_scanned"] == 3
    assert ts["tasks_scanned"] == 12
    assert ts["recursive_task_includes"] == 1
    assert ts["module_count"] == 2
    assert ts["handler_count"] == 1
