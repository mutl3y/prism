"""Tests for ScanPayloadBuilder pattern implementation.

Validates fluent interface, invariant validation, and immutability for
builder pattern used to construct immutable RunScanOutputPayload TypedDicts.
"""

from __future__ import annotations

from typing import Any

import pytest

from prism.scanner_data.builders import ScanPayloadBuilder
from prism.scanner_data.contracts import RunScanOutputPayload, ScanMetadata


class TestScanPayloadBuilderInterface:
    """Test fluent interface and method chaining."""

    def test_builder_returns_self_from_all_setter_methods(self) -> None:
        """All setter methods return Self for method chaining."""
        builder = ScanPayloadBuilder()

        assert builder.role_name("test_role") is builder
        assert builder.description("Role description") is builder
        assert builder.display_variables({"x": {"type": "string"}}) is builder
        assert builder.requirements_display(["ansible>=2.15"]) is builder
        assert builder.undocumented_default_filters([{"name": "legacy_var"}]) is builder
        assert builder.metadata(_build_test_metadata()) is builder

    def test_builder_allows_method_chaining(self) -> None:
        """Builder supports fluent method chaining."""
        payload = (
            ScanPayloadBuilder()
            .role_name("test_role")
            .description("Test description")
            .display_variables({"var1": {"type": "string"}})
            .requirements_display(["ansible>=2.15"])
            .undocumented_default_filters([{"name": "legacy_var"}])
            .metadata(_build_test_metadata())
            .build()
        )

        assert payload["role_name"] == "test_role"
        assert payload["description"] == "Test description"
        assert "var1" in payload["display_variables"]


class TestScanPayloadBuilderInvariants:
    """Test invariant validation on build()."""

    def test_build_requires_role_name(self) -> None:
        """build() raises ValueError if role_name is missing."""
        builder = ScanPayloadBuilder()
        builder.description("desc")
        builder.metadata(_build_test_metadata())

        with pytest.raises(ValueError, match="role_name"):
            builder.build()

    def test_build_requires_description(self) -> None:
        """build() raises ValueError if description is missing."""
        builder = ScanPayloadBuilder()
        builder.role_name("test")
        builder.metadata(_build_test_metadata())

        with pytest.raises(ValueError, match="description"):
            builder.build()

    def test_build_requires_metadata(self) -> None:
        """build() raises ValueError if metadata is missing."""
        builder = ScanPayloadBuilder()
        builder.role_name("test")
        builder.description("desc")

        with pytest.raises(ValueError, match="metadata"):
            builder.build()

    def test_build_rejects_empty_role_name(self) -> None:
        """build() rejects empty role_name string."""
        builder = ScanPayloadBuilder()
        builder.role_name("  ")
        builder.description("desc")
        builder.metadata(_build_test_metadata())

        with pytest.raises(ValueError, match="role_name"):
            builder.build()

    def test_build_rejects_non_string_description(self) -> None:
        """build() rejects non-string description values."""
        builder = ScanPayloadBuilder()
        builder.role_name("test")
        builder.description("desc")
        builder.metadata(_build_test_metadata())
        builder._payload["description"] = 123  # type: ignore[assignment]

        with pytest.raises(ValueError, match="description"):
            builder.build()


class TestScanPayloadBuilderDefaults:
    """Test default values applied by builder."""

    def test_display_variables_defaults_to_empty_dict(self) -> None:
        """display_variables defaults to {} if not set."""
        payload = (
            ScanPayloadBuilder()
            .role_name("test")
            .description("desc")
            .metadata(_build_test_metadata())
            .build()
        )

        assert payload["display_variables"] == {}

    def test_requirements_display_defaults_to_empty_list(self) -> None:
        """requirements_display defaults to [] if not set."""
        payload = (
            ScanPayloadBuilder()
            .role_name("test")
            .description("desc")
            .metadata(_build_test_metadata())
            .build()
        )

        assert payload["requirements_display"] == []

    def test_undocumented_default_filters_defaults_to_empty_list(self) -> None:
        """undocumented_default_filters defaults to [] if not set."""
        payload = (
            ScanPayloadBuilder()
            .role_name("test")
            .description("desc")
            .metadata(_build_test_metadata())
            .build()
        )

        assert payload["undocumented_default_filters"] == []

    def test_explicit_values_override_defaults(self) -> None:
        """Explicitly set values override defaults."""
        payload = (
            ScanPayloadBuilder()
            .role_name("test_role")
            .description("Role desc")
            .display_variables({"var1": {"type": "string"}})
            .requirements_display(["community.general"])
            .undocumented_default_filters([{"name": "var2"}])
            .metadata(_build_test_metadata())
            .build()
        )

        assert payload["display_variables"] == {"var1": {"type": "string"}}
        assert payload["requirements_display"] == ["community.general"]
        assert payload["undocumented_default_filters"] == [{"name": "var2"}]


class TestScanPayloadBuilderImmutability:
    """Test immutability guarantees after build()."""

    def test_build_returns_dict_typed_as_run_scan_output_payload(self) -> None:
        """build() returns dict that satisfies RunScanOutputPayload contract."""
        payload = (
            ScanPayloadBuilder()
            .role_name("test")
            .description("desc")
            .metadata(_build_test_metadata())
            .build()
        )

        assert isinstance(payload, dict)
        assert "role_name" in payload
        assert "description" in payload
        assert "metadata" in payload

    def test_builder_state_isolated_between_builds(self) -> None:
        """Multiple build() calls from same builder produce independent payloads."""
        builder = ScanPayloadBuilder()
        builder.role_name("role1").description("desc1").metadata(_build_test_metadata())
        payload1 = builder.build()

        payload2 = (
            builder.role_name("role2")
            .description("desc2")
            .metadata(_build_test_metadata())
            .build()
        )

        assert payload1["role_name"] == "role1"
        assert payload2["role_name"] == "role2"


class TestScanPayloadBuilderEquivalence:
    """Test equivalence with manual payload construction."""

    def test_builder_payload_matches_manual_construction(self) -> None:
        """Payload from builder matches manually constructed dict."""
        metadata = _build_test_metadata()
        display_variables = {"var1": {"type": "string", "default": "x"}}
        requirements_display: list[Any] = ["ansible>=2.15"]
        undocumented_default_filters: list[Any] = [{"name": "legacy_var"}]

        manual_payload: RunScanOutputPayload = {
            "role_name": "role_a",
            "description": "A role",
            "display_variables": display_variables,
            "requirements_display": requirements_display,
            "undocumented_default_filters": undocumented_default_filters,
            "metadata": metadata,
        }

        builder_payload = (
            ScanPayloadBuilder()
            .role_name("role_a")
            .description("A role")
            .display_variables(display_variables)
            .requirements_display(requirements_display)
            .undocumented_default_filters(undocumented_default_filters)
            .metadata(metadata)
            .build()
        )

        assert builder_payload == manual_payload

    def test_builder_produces_minimal_required_payload(self) -> None:
        """Builder can produce minimal valid RunScanOutputPayload."""
        payload = (
            ScanPayloadBuilder()
            .role_name("role")
            .description("")
            .metadata(_build_test_metadata())
            .build()
        )

        assert payload["role_name"] == "role"
        assert payload["description"] == ""
        assert payload["display_variables"] == {}
        assert payload["requirements_display"] == []
        assert payload["undocumented_default_filters"] == []


class TestScanPayloadBuilderMethodOverride:
    """Test method override behavior."""

    def test_builder_allows_method_override(self) -> None:
        """Later method calls override earlier values."""
        payload = (
            ScanPayloadBuilder()
            .role_name("role1")
            .role_name("role2")
            .description("desc1")
            .description("desc2")
            .display_variables({"x": {"type": "string"}})
            .display_variables({})
            .metadata(_build_test_metadata())
            .build()
        )

        assert payload["role_name"] == "role2"
        assert payload["description"] == "desc2"
        assert payload["display_variables"] == {}


def _build_test_metadata() -> ScanMetadata:
    """Build minimal valid metadata for payload tests."""
    return {
        "marker_prefix": "ansible_doc",
        "detailed_catalog": False,
        "include_task_parameters": False,
        "include_task_runbooks": False,
        "inline_task_runbooks": False,
        "keep_unknown_style_sections": False,
        "handlers": [],
        "tasks": [],
        "templates": [],
        "files": [],
        "tests": [],
        "defaults": [],
        "vars": [],
        "meta": {},
        "features": {
            "task_files_scanned": 0,
            "tasks_scanned": 0,
            "recursive_task_includes": 0,
            "unique_modules": "",
            "external_collections": "",
            "handlers_notified": "",
            "privileged_tasks": 0,
            "conditional_tasks": 0,
            "tagged_tasks": 0,
            "included_role_calls": 0,
            "included_roles": "",
            "dynamic_included_role_calls": 0,
            "dynamic_included_roles": "",
            "disabled_task_annotations": 0,
            "yaml_like_task_annotations": 0,
        },
        "molecule_scenarios": [],
        "unconstrained_dynamic_task_includes": [],
        "unconstrained_dynamic_role_includes": [],
        "enabled_sections": [],
        "variable_insights": [],
        "yaml_parse_failures": [],
        "role_notes": [],
        "scanner_counters": None,
        "fail_on_unconstrained_dynamic_includes": False,
        "fail_on_yaml_like_task_annotations": False,
        "ignore_unresolved_internal_underscore_references": False,
        "doc_insights": {},
    }
