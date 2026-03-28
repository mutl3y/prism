"""Tests for VariableRowBuilder pattern implementation.

Validates fluent interface, invariant validation, immutability, and
default value handling for the builder pattern used to construct
immutable VariableRow TypedDicts.
"""

from __future__ import annotations

import pytest

from prism.scanner_data.builders import VariableRowBuilder


class TestVariableRowBuilderInterface:
    """Test fluent interface and method chaining."""

    def test_builder_returns_self_from_all_setter_methods(self) -> None:
        """All setter methods return Self for method chaining."""
        builder = VariableRowBuilder()

        # Each setter returns the builder instance (self)
        assert builder.name("test_var") is builder
        assert builder.type("string") is builder
        assert builder.default("value") is builder
        assert builder.source("defaults/main.yml") is builder
        assert builder.documented(True) is builder
        assert builder.required(False) is builder
        assert builder.secret(False) is builder
        assert builder.provenance_source_file("defaults/main.yml") is builder
        assert builder.provenance_line(42) is builder
        assert builder.provenance_confidence(0.95) is builder
        assert builder.uncertainty_reason("test reason") is builder
        assert builder.is_unresolved(False) is builder
        assert builder.is_ambiguous(False) is builder

    def test_builder_allows_method_chaining(self) -> None:
        """Builder supports fluent method chaining."""
        row = (
            VariableRowBuilder()
            .name("my_var")
            .type("string")
            .default("default_value")
            .source("defaults/main.yml")
            .required(False)
            .build()
        )

        assert row["name"] == "my_var"
        assert row["type"] == "string"
        assert row["default"] == "default_value"
        assert row["source"] == "defaults/main.yml"
        assert row["required"] is False

    def test_builder_supports_complex_chaining(self) -> None:
        """Builder supports complex multi-line chaining."""
        row = (
            VariableRowBuilder()
            .name("database_password")
            .type("string")
            .default(None)
            .required(True)
            .secret(True)
            .documented(False)
            .source("meta/argument_spec.yml")
            .provenance_source_file("meta/main.yml")
            .provenance_line(15)
            .provenance_confidence(0.95)
            .uncertainty_reason(None)
            .is_unresolved(False)
            .is_ambiguous(False)
            .build()
        )

        assert row["name"] == "database_password"
        assert row["required"] is True
        assert row["secret"] is True
        assert row["provenance_line"] == 15

    def test_builder_allows_method_override(self) -> None:
        """Later method calls override earlier values."""
        row = (
            VariableRowBuilder()
            .name("my_var")
            .type("string")
            .type("list")  # Override type
            .default("first")
            .default("second")  # Override default
            .build()
        )

        assert row["type"] == "list"
        assert row["default"] == "second"


class TestVariableRowBuilderInvariants:
    """Test invariant validation on build()."""

    def test_build_requires_name(self) -> None:
        """build() raises ValueError if name is missing."""
        builder = VariableRowBuilder()
        builder.type("string")

        with pytest.raises(ValueError, match="name.*required|name is required"):
            builder.build()

    def test_build_requires_type(self) -> None:
        """build() raises ValueError if type is missing."""
        builder = VariableRowBuilder()
        builder.name("my_var")

        with pytest.raises(ValueError, match="type.*required|type is required"):
            builder.build()

    def test_build_requires_both_name_and_type(self) -> None:
        """build() requires both name and type."""
        with pytest.raises(ValueError):
            VariableRowBuilder().build()

    def test_build_rejects_empty_name(self) -> None:
        """build() rejects empty name string."""
        builder = VariableRowBuilder()
        builder.name("")
        builder.type("string")

        with pytest.raises(ValueError, match="name.*empty|blank|name is required"):
            builder.build()

    def test_build_rejects_empty_type(self) -> None:
        """build() rejects empty type string."""
        builder = VariableRowBuilder()
        builder.name("my_var")
        builder.type("")

        with pytest.raises(ValueError, match="type.*empty|blank|type is required"):
            builder.build()

    def test_build_accepts_valid_types(self) -> None:
        """build() accepts all valid type values."""
        valid_types = [
            "string",
            "list",
            "dict",
            "int",
            "bool",
            "computed",
            "documented",
            "required",
        ]

        for valid_type in valid_types:
            row = VariableRowBuilder().name("my_var").type(valid_type).build()
            assert row["type"] == valid_type

    def test_build_ignores_invalid_type(self) -> None:
        """build() doesn't reject unrecognized type values (future-proof)."""
        # Type values may be extended, so we allow custom types
        row = VariableRowBuilder().name("my_var").type("custom_type").build()
        assert row["type"] == "custom_type"

    def test_build_allows_none_optional_fields(self) -> None:
        """build() allows None for optional fields."""
        row = (
            VariableRowBuilder()
            .name("my_var")
            .type("string")
            .default(None)
            .provenance_line(None)
            .uncertainty_reason(None)
            .build()
        )

        assert row["default"] is None
        assert row.get("provenance_line") is None
        assert row.get("uncertainty_reason") is None


class TestVariableRowBuilderDefaults:
    """Test default values applied by builder."""

    def test_defaults_are_applied_on_build(self) -> None:
        """build() applies documented defaults for unset fields."""
        row = VariableRowBuilder().name("my_var").type("string").build()

        # These fields should have default values
        assert row.get("required") is False
        assert row.get("secret") is False
        assert row.get("documented") is False
        assert row.get("provenance_confidence") == 0.5

    def test_explicit_values_override_defaults(self) -> None:
        """Explicitly set values override defaults."""
        row = (
            VariableRowBuilder()
            .name("my_var")
            .type("string")
            .required(True)
            .secret(True)
            .documented(True)
            .provenance_confidence(0.95)
            .build()
        )

        assert row["required"] is True
        assert row["secret"] is True
        assert row["documented"] is True
        assert row["provenance_confidence"] == 0.95

    def test_default_confidence_is_half(self) -> None:
        """Default confidence is 0.5 (unknown)."""
        row = VariableRowBuilder().name("my_var").type("string").build()
        assert row.get("provenance_confidence") == 0.5

    def test_false_flags_with_defaults(self) -> None:
        """Boolean fields default to False."""
        row = VariableRowBuilder().name("my_var").type("string").build()

        assert row.get("required") is False
        assert row.get("secret") is False
        assert row.get("documented") is False
        assert row.get("is_unresolved") is False
        assert row.get("is_ambiguous") is False


class TestVariableRowBuilderImmutability:
    """Test immutability guarantees after build()."""

    def test_build_returns_dict_typed_as_variable_row(self) -> None:
        """build() returns dict that satisfies VariableRow TypedDict contract."""
        row = VariableRowBuilder().name("my_var").type("string").build()

        # Verify it's a dict (TypedDict at runtime is just dict)
        assert isinstance(row, dict)

        # Verify required fields exist
        assert "name" in row
        assert "type" in row

    def test_builder_state_isolated_between_builds(self) -> None:
        """Multiple build() calls from same builder produce independent rows."""
        builder = VariableRowBuilder()
        builder.name("var1").type("string")

        row1 = builder.build()

        # Build again with different values
        row2 = builder.name("var2").type("list").build()

        # Both should be different since we modified the builder
        assert row1["name"] == "var1"
        assert row2["name"] == "var2"

    def test_separate_builders_dont_interfere(self) -> None:
        """Multiple separate builders don't share state."""
        builder1 = VariableRowBuilder().name("var1").type("string")
        builder2 = VariableRowBuilder().name("var2").type("list")

        row1 = builder1.build()
        row2 = builder2.build()

        assert row1["name"] == "var1"
        assert row2["name"] == "var2"
        assert row1["type"] == "string"
        assert row2["type"] == "list"


class TestVariableRowBuilderEquivalence:
    """Test equivalence with expected VariableRow structure."""

    def test_builder_row_matches_expected_structure(self) -> None:
        """Row from builder matches expected VariableRow structure."""
        row = (
            VariableRowBuilder()
            .name("test_var")
            .type("string")
            .default("test_default")
            .source("defaults/main.yml")
            .documented(True)
            .required(False)
            .secret(False)
            .provenance_source_file("defaults/main.yml")
            .provenance_line(5)
            .provenance_confidence(0.95)
            .uncertainty_reason(None)
            .is_unresolved(False)
            .is_ambiguous(False)
            .build()
        )

        # Verify expected signature fields
        assert row["name"] == "test_var"
        assert row["type"] == "string"
        assert row["default"] == "test_default"
        assert row["source"] == "defaults/main.yml"
        assert row["documented"] is True
        assert row["required"] is False
        assert row["secret"] is False
        assert row["provenance_source_file"] == "defaults/main.yml"
        assert row["provenance_line"] == 5
        assert row["provenance_confidence"] == 0.95
        assert row.get("uncertainty_reason") is None
        assert row["is_unresolved"] is False
        assert row["is_ambiguous"] is False

    def test_builder_produces_minimal_required_row(self) -> None:
        """Builder can produce minimal valid VariableRow."""
        row = VariableRowBuilder().name("minimal_var").type("string").build()

        # Minimal row should have name and type
        assert row["name"] == "minimal_var"
        assert row["type"] == "string"

        # And should have defaults for other fields
        assert row.get("required") is False
        assert row.get("secret") is False


class TestVariableRowBuilderConvenience:
    """Test convenience methods and patterns."""

    def test_builder_with_full_provenance(self) -> None:
        """Builder supports setting full provenance metadata."""
        row = (
            VariableRowBuilder()
            .name("var_with_provenance")
            .type("string")
            .provenance_source_file("defaults/main.yml")
            .provenance_line(10)
            .provenance_confidence(0.95)
            .build()
        )

        assert row["provenance_source_file"] == "defaults/main.yml"
        assert row["provenance_line"] == 10
        assert row["provenance_confidence"] == 0.95

    def test_builder_with_uncertainty(self) -> None:
        """Builder supports uncertainty tracking."""
        row = (
            VariableRowBuilder()
            .name("unresolved_var")
            .type("computed")
            .is_unresolved(True)
            .uncertainty_reason("Variable resolved at runtime via set_fact")
            .provenance_confidence(0.4)
            .build()
        )

        assert row["is_unresolved"] is True
        assert row["uncertainty_reason"] == "Variable resolved at runtime via set_fact"
        assert row["provenance_confidence"] == 0.4

    def test_builder_with_secret_detection(self) -> None:
        """Builder supports secret/sensitive variable marking."""
        row = (
            VariableRowBuilder()
            .name("database_password")
            .type("string")
            .secret(True)
            .required(True)
            .build()
        )

        assert row["secret"] is True
        assert row["required"] is True


class TestVariableRowBuilderEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_builder_with_none_default_value(self) -> None:
        """Builder accepts None as a default value."""
        row = (
            VariableRowBuilder()
            .name("optional_var")
            .type("string")
            .default(None)
            .build()
        )
        assert row["default"] is None

    def test_builder_with_string_none_value(self) -> None:
        """Builder distinguishes between None and string 'None'."""
        row1 = VariableRowBuilder().name("var1").type("string").default(None).build()

        row2 = VariableRowBuilder().name("var2").type("string").default("None").build()

        assert row1["default"] is None
        assert row2["default"] == "None"

    def test_builder_with_zero_confidence(self) -> None:
        """Builder accepts confidence value of 0.0."""
        row = (
            VariableRowBuilder()
            .name("guessed_var")
            .type("string")
            .provenance_confidence(0.0)
            .build()
        )
        assert row["provenance_confidence"] == 0.0

    def test_builder_with_full_confidence(self) -> None:
        """Builder accepts confidence value of 1.0."""
        row = (
            VariableRowBuilder()
            .name("certain_var")
            .type("string")
            .provenance_confidence(1.0)
            .build()
        )
        assert row["provenance_confidence"] == 1.0

    def test_builder_with_long_variable_name(self) -> None:
        """Builder handles long variable names."""
        long_name = "very_long_variable_name_" * 10
        row = VariableRowBuilder().name(long_name).type("string").build()
        assert row["name"] == long_name

    def test_builder_with_special_characters_in_name(self) -> None:
        """Builder handles special characters in variable name."""
        special_name = "var_with-special.chars[0]"
        row = VariableRowBuilder().name(special_name).type("string").build()
        assert row["name"] == special_name

    def test_builder_with_multiline_uncertainty_reason(self) -> None:
        """Builder handles multiline uncertainty reasons."""
        reason = "This variable is unresolved because:\n- It's set dynamically\n- Source code imports it"
        row = (
            VariableRowBuilder()
            .name("unresolved_var")
            .type("computed")
            .uncertainty_reason(reason)
            .build()
        )
        assert row["uncertainty_reason"] == reason


class TestVariableRowBuilderIntegration:
    """Integration tests with real usage patterns."""

    def test_builder_pattern_matches_variable_discovery_usage(self) -> None:
        """Builder works with patterns used in VariableDiscovery."""
        # Simulate a variable discovered from defaults/main.yml
        row = (
            VariableRowBuilder()
            .name("web_port")
            .type("int")
            .default("8080")
            .source("defaults/main.yml")
            .required(False)
            .secret(False)
            .provenance_source_file("defaults/main.yml")
            .provenance_line(3)
            .provenance_confidence(0.95)
            .is_unresolved(False)
            .is_ambiguous(False)
            .build()
        )

        assert row["name"] == "web_port"
        assert row["type"] == "int"
        assert row["default"] == "8080"
        assert row["provenance_confidence"] == 0.95

    def test_builder_pattern_with_variable_from_meta(self) -> None:
        """Builder works with variables from meta/argument_spec."""
        row = (
            VariableRowBuilder()
            .name("api_key")
            .type("string")
            .required(True)
            .secret(True)
            .documented(True)
            .source("meta/argument_spec.yml")
            .provenance_source_file("meta/main.yml")
            .provenance_line(12)
            .provenance_confidence(0.95)
            .build()
        )

        assert row["required"] is True
        assert row["secret"] is True
        assert row["documented"] is True
        assert row["provenance_confidence"] == 0.95

    def test_builder_pattern_with_unresolved_variable(self) -> None:
        """Builder works with variables that are unresolved."""
        row = (
            VariableRowBuilder()
            .name("runtime_config")
            .type("computed")
            .is_unresolved(True)
            .uncertainty_reason("Set at runtime via set_fact block")
            .provenance_confidence(0.4)
            .source("tasks/configure.yml")
            .provenance_source_file("tasks/configure.yml")
            .build()
        )

        assert row["is_unresolved"] is True
        assert row["provenance_confidence"] == 0.4
        assert "runtime" in row["uncertainty_reason"]

    def test_builder_creates_well_formed_rows_for_collection(self) -> None:
        """Multiple rows from builder can be collected."""
        rows = []
        for i in range(3):
            row = (
                VariableRowBuilder()
                .name(f"var_{i}")
                .type("string")
                .default(f"default_{i}")
                .build()
            )
            rows.append(row)

        assert len(rows) == 3
        assert rows[0]["name"] == "var_0"
        assert rows[1]["name"] == "var_1"
        assert rows[2]["name"] == "var_2"
