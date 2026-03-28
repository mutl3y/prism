"""Builders for immutable data structures used throughout the scanner.

This module provides fluent builder classes for constructing TypedDict instances
with validation and immutability guarantees. Builders enable clean, chainable
construction while maintaining type safety and invariant checking.
"""

from __future__ import annotations

from typing import Any, Self

from .contracts import RunScanOutputPayload, ScanMetadata, VariableRow


class VariableRowBuilder:
    """Fluent builder for constructing immutable VariableRow TypedDicts.

    Provides a clean, chainable interface for building variable row dictionaries
    with full validation of invariants and immutability guarantees on the final
    VariableRow returned by build().

    Usage:
        row = (VariableRowBuilder()
            .name("my_var")
            .type("string")
            .default("value")
            .source("defaults/main.yml")
            .build())

    Guarantees:
        - Immutable after build() (returns TypedDict, not mutable dict)
        - Validates invariants on build() (e.g., name and type required)
        - Fluent interface (all methods return Self for chaining)
        - Type-safe (all fields type-checked by mypy)
    """

    def __init__(self) -> None:
        """Initialize builder with empty state."""
        self._row: dict[str, Any] = {}

    def name(self, value: str) -> Self:
        """Set variable name (required).

        Args:
            value: Variable name (e.g., 'my_var', 'APP_PORT').

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If value is empty (checked in build()).
        """
        self._row["name"] = value
        return self

    def type(self, value: str) -> Self:
        """Set variable type (required).

        Valid types include: string, list, dict, int, bool, computed, documented,
        required, and other inferred types from task_argument_spec or YAML analysis.

        Args:
            value: Type string (e.g., 'string', 'list', 'dict').

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If value is empty (checked in build()).
        """
        self._row["type"] = value
        return self

    def default(self, value: Any) -> Self:
        """Set default value (optional).

        Args:
            value: Default value (typically string representation or None).

        Returns:
            Self for method chaining.
        """
        self._row["default"] = value
        return self

    def example(self, value: str | None) -> Self:
        """Set example value (optional).

        Args:
            value: Example value showing typical usage.

        Returns:
            Self for method chaining.
        """
        if value is not None:
            self._row["example"] = value
        return self

    def description(self, value: str | None) -> Self:
        """Set variable description (optional).

        Args:
            value: Human-readable description or None.

        Returns:
            Self for method chaining.
        """
        if value is not None:
            self._row["description"] = value
        return self

    def source(self, value: str) -> Self:
        """Set human-readable source description.

        Args:
            value: Source description (e.g., 'defaults/main.yml', 'meta/argument_specs').

        Returns:
            Self for method chaining.
        """
        self._row["source"] = value
        return self

    def documented(self, value: bool) -> Self:
        """Set documented flag.

        Args:
            value: True if variable is explicitly documented somewhere.

        Returns:
            Self for method chaining.
        """
        self._row["documented"] = value
        return self

    def required(self, value: bool) -> Self:
        """Set required flag.

        Args:
            value: True if variable appears required (no default found). Default: False.

        Returns:
            Self for method chaining.
        """
        self._row["required"] = value
        return self

    def secret(self, value: bool) -> Self:
        """Set secret flag.

        Args:
            value: True if variable looks like credential/sensitive value. Default: False.

        Returns:
            Self for method chaining.
        """
        self._row["secret"] = value
        return self

    def provenance_source_file(self, value: str) -> Self:
        """Set provenance source file path.

        Args:
            value: Relative path to source file (e.g., 'defaults/main.yml').

        Returns:
            Self for method chaining.
        """
        self._row["provenance_source_file"] = value
        return self

    def provenance_line(self, value: int | None) -> Self:
        """Set provenance line number.

        Args:
            value: Line number in source file, if determinable.

        Returns:
            Self for method chaining.
        """
        self._row["provenance_line"] = value
        return self

    def provenance_confidence(self, value: float) -> Self:
        """Set provenance confidence level.

        Args:
            value: Confidence (0.0-1.0):
                - 0.95+: Explicit definitions (defaults, vars, argument_specs)
                - 0.5-0.7: Inferred from context (task analysis, type inference)
                - 0.4-0.5: Dynamic/uncertain (referenced but unresolved)

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If value is not in [0.0, 1.0] (checked in build()).
        """
        self._row["provenance_confidence"] = value
        return self

    def confidence(self, value: float) -> Self:
        """Set confidence score (alias for provenance_confidence).

        Convenience method for shorter syntax.

        Args:
            value: Confidence (0.0-1.0).

        Returns:
            Self for method chaining.
        """
        return self.provenance_confidence(value)

    def uncertainty_reason(self, value: str | None) -> Self:
        """Set uncertainty reason.

        Args:
            value: Explanation if confidence < 1.0 or variable is ambiguous.
                Examples:
                - "Variable referenced in task but not in defaults/vars/meta"
                - "Multiple possible sources detected"
                - "Dynamic variable assignment"

        Returns:
            Self for method chaining.
        """
        self._row["uncertainty_reason"] = value
        return self

    def is_unresolved(self, value: bool) -> Self:
        """Set unresolved flag.

        Args:
            value: True if variable cannot be resolved to static definition.

        Returns:
            Self for method chaining.
        """
        self._row["is_unresolved"] = value
        return self

    def is_ambiguous(self, value: bool) -> Self:
        """Set ambiguous flag.

        Args:
            value: True if variable has multiple possible sources or values.

        Returns:
            Self for method chaining.
        """
        self._row["is_ambiguous"] = value
        return self

    def provenance(self, source_file: str, line_no: int | None) -> Self:
        """Set source file and line number together (convenience method).

        Args:
            source_file: Relative path to source file.
            line_no: Line number in source, or None if unknown.

        Returns:
            Self for method chaining.
        """
        self.provenance_source_file(source_file)
        self.provenance_line(line_no)
        return self

    def build(self) -> VariableRow:
        """Validate and return immutable VariableRow TypedDict.

        Invariants enforced:
        - name: Required, must not be empty string
        - type: Required, must not be empty string
        - provenance_confidence: Must be in [0.0, 1.0] if provided
        - All other fields: Optional, can be None or unspecified

        Returns:
            Immutable VariableRow TypedDict with all accumulated fields.
            Default values are applied for optional fields:
            - required: False
            - secret: False
            - documented: False
            - provenance_confidence: 0.5 (if not set)
            - is_unresolved: False
            - is_ambiguous: False

        Raises:
            ValueError: If required fields are missing or invalid values provided.

        Examples:
            >>> row = (VariableRowBuilder()
            ...     .name("app_port")
            ...     .type("int")
            ...     .default("8080")
            ...     .source("defaults/main.yml")
            ...     .build())
            >>> row["name"]
            'app_port'
        """
        # Validate required fields
        name = self._row.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            raise ValueError(
                "'name' is required and cannot be empty. " f"Got: {name!r}"
            )

        type_ = self._row.get("type")
        if not type_ or not isinstance(type_, str) or not type_.strip():
            raise ValueError(
                "'type' is required and cannot be empty. " f"Got: {type_!r}"
            )

        # Validate confidence if provided
        confidence = self._row.get("provenance_confidence")
        if confidence is not None:
            if not isinstance(confidence, (int, float)):
                raise ValueError(
                    "provenance_confidence must be float or int. "
                    f"Got: {type(confidence).__name__} = {confidence!r}"
                )
            if not (0.0 <= confidence <= 1.0):
                raise ValueError(
                    "provenance_confidence must be in [0.0, 1.0]. " f"Got: {confidence}"
                )

        # Apply defaults for optional fields (preserving explicitly set values)
        result: dict[str, Any] = dict(self._row)
        result.setdefault("required", False)
        result.setdefault("secret", False)
        result.setdefault("documented", False)
        result.setdefault("provenance_confidence", 0.5)
        result.setdefault("is_unresolved", False)
        result.setdefault("is_ambiguous", False)

        # Return immutable TypedDict
        # Cast to VariableRow TypedDict type; runtime is still a dict
        return result  # type: ignore[return-value]


class ScanPayloadBuilder:
    """Fluent builder for constructing immutable RunScanOutputPayload TypedDicts.

    Provides a clean, chainable interface for building scan output payloads
    with full validation of invariants and immutability guarantees on the final
    RunScanOutputPayload returned by build().

    Usage:
        payload = (ScanPayloadBuilder()
            .role_name("my_role")
            .description("Role description")
            .display_variables(rendered_variables)
            .requirements_display(requirements)
            .undocumented_default_filters(default_filters)
            .metadata(scan_metadata)
            .build())

    Guarantees:
        - Immutable after build() (returns TypedDict, not mutable dict)
        - Validates invariants on build() (role_name, description, metadata required)
        - Fluent interface (all methods return Self for chaining)
        - Type-safe (all fields type-checked by mypy)
        - Default values for optional fields (display_variables={}, requirements_display=[], undocumented_default_filters=[])
    """

    def __init__(self) -> None:
        """Initialize builder with empty state."""
        self._payload: dict[str, Any] = {}

    def role_name(self, value: str) -> Self:
        """Set role name (required).

        Args:
            value: Role name.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If value is empty (checked in build()).
        """
        self._payload["role_name"] = value
        return self

    def description(self, value: str) -> Self:
        """Set role description (required).

        Args:
            value: Human-readable role description.

        Returns:
            Self for method chaining.
        """
        self._payload["description"] = value
        return self

    def display_variables(self, value: dict[str, Any]) -> Self:
        """Set rendered variable mapping (optional).

        Args:
            value: Render-ready variable map.

        Returns:
            Self for method chaining.
        """
        self._payload["display_variables"] = value
        return self

    def requirements_display(self, value: list[Any]) -> Self:
        """Set rendered requirements list (optional).

        Args:
            value: List of display-ready requirement rows.

        Returns:
            Self for method chaining.
        """
        self._payload["requirements_display"] = value
        return self

    def undocumented_default_filters(self, value: list[Any]) -> Self:
        """Set undocumented default filter findings (optional).

        Args:
            value: List of undocumented default filter rows.

        Returns:
            Self for method chaining.
        """
        self._payload["undocumented_default_filters"] = value
        return self

    def metadata(self, value: ScanMetadata) -> Self:
        """Set scan metadata (required).

        Args:
                 value: ScanMetadata dict with scan context and configuration.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If required fields are missing (checked in build()).
        """
        self._payload["metadata"] = value
        return self

    def build(self) -> RunScanOutputPayload:
        """Validate and return immutable RunScanOutputPayload TypedDict.

        Invariants enforced:
        - role_name: Required, must not be empty string
        - description: Required, must be string
        - metadata: Required, must be a dict
        - display_variables: Defaults to {} if not set
        - requirements_display: Defaults to [] if not set
        - undocumented_default_filters: Defaults to [] if not set

        Returns:
            Immutable RunScanOutputPayload TypedDict with all accumulated fields.

        Raises:
            ValueError: If required fields are missing or invalid.

        Examples:
            >>> payload = (ScanPayloadBuilder()
            ...     .role_name("my_role")
            ...     .description("Role description")
            ...     .metadata({})
            ...     .build())
            >>> payload["role_name"]
            'my_role'
        """
        # Validate role_name
        role_name = self._payload.get("role_name")
        if not role_name or not isinstance(role_name, str) or not role_name.strip():
            raise ValueError(
                "'role_name' is required and cannot be empty. " f"Got: {role_name!r}"
            )

        # Validate description
        description = self._payload.get("description")
        if description is None or not isinstance(description, str):
            raise ValueError(
                "'description' is required and must be a string. "
                f"Got: {description!r}"
            )

        # Validate metadata
        metadata = self._payload.get("metadata")
        if not metadata or not isinstance(metadata, dict):
            raise ValueError(
                "'metadata' is required and must be a dict. " f"Got: {metadata!r}"
            )

        # Apply defaults for optional fields
        result: dict[str, Any] = dict(self._payload)
        result.setdefault("display_variables", {})
        result.setdefault("requirements_display", [])
        result.setdefault("undocumented_default_filters", [])

        # Return immutable TypedDict
        # Cast to RunScanOutputPayload TypedDict type; runtime is still a dict
        return result  # type: ignore[return-value]
