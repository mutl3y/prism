"""Variable and provenance contracts owned by the variable-analysis domain."""

from __future__ import annotations

from typing import Any, NotRequired, Self, TypedDict


class Variable(TypedDict, total=False):
    """A variable metadata entry with type, default, and description."""

    name: str
    type: str
    default: str
    description: str
    required: bool
    secret: bool


class VariableProvenance(TypedDict, total=False):
    """Metadata tracking the source and confidence of a variable."""

    source_file: str
    line: int | None
    confidence: float
    source_type: str


class VariableRow(TypedDict, total=False):
    """A variable discovered during role scanning with provenance metadata."""

    name: str
    type: str
    default: str
    source: str
    documented: bool
    required: bool
    secret: bool
    provenance_source_file: str
    provenance_line: int | None
    provenance_confidence: float
    uncertainty_reason: str | None
    is_unresolved: bool
    is_ambiguous: bool
    readme_documented: NotRequired[bool]
    non_authoritative_test_evidence: NotRequired[dict[str, Any]]


class VariableRowWithMeta(TypedDict, total=False):
    """VariableRow augmented with provenance and intermediate metadata."""

    name: str
    type: str
    default: str
    source: str
    documented: bool
    required: bool
    secret: bool
    provenance_source_file: str
    provenance_line: int | None
    provenance_confidence: float
    uncertainty_reason: str | None
    is_unresolved: bool
    is_ambiguous: bool
    external_evidence: NotRequired[list[dict[str, Any]]]
    precedence_category: NotRequired[str]


class ReferenceContext(TypedDict):
    """Typed contract for variable reference context tracking and enrichment."""

    seed_values: dict[str, Any]
    seed_secrets: set[str]
    seed_sources: dict[str, str]
    dynamic_include_vars_refs: list[str]
    dynamic_include_var_tokens: set[str]
    dynamic_task_include_tokens: set[str]
    referenced_names: set[str]
    ignored_identifiers: NotRequired[set[str]]


class VariableRowBuilder:
    """Fluent builder for constructing immutable VariableRow TypedDicts.

    Lives in this module because VariableRow is defined here and builders
    should be co-located with the contracts they produce.
    """

    def __init__(self) -> None:
        self._row: dict[str, Any] = {}

    def name(self, value: str) -> Self:
        self._row["name"] = value
        return self

    def type(self, value: str) -> Self:
        self._row["type"] = value
        return self

    def default(self, value: Any) -> Self:
        self._row["default"] = value
        return self

    def example(self, value: str | None) -> Self:
        if value is not None:
            self._row["example"] = value
        return self

    def description(self, value: str | None) -> Self:
        if value is not None:
            self._row["description"] = value
        return self

    def source(self, value: str) -> Self:
        self._row["source"] = value
        return self

    def documented(self, value: bool) -> Self:
        self._row["documented"] = value
        return self

    def required(self, value: bool) -> Self:
        self._row["required"] = value
        return self

    def secret(self, value: bool) -> Self:
        self._row["secret"] = value
        return self

    def provenance_source_file(self, value: str) -> Self:
        self._row["provenance_source_file"] = value
        return self

    def provenance_line(self, value: int | None) -> Self:
        self._row["provenance_line"] = value
        return self

    def provenance_confidence(self, value: float) -> Self:
        self._row["provenance_confidence"] = value
        return self

    def confidence(self, value: float) -> Self:
        return self.provenance_confidence(value)

    def uncertainty_reason(self, value: str | None) -> Self:
        self._row["uncertainty_reason"] = value
        return self

    def is_unresolved(self, value: bool) -> Self:
        self._row["is_unresolved"] = value
        return self

    def is_ambiguous(self, value: bool) -> Self:
        self._row["is_ambiguous"] = value
        return self

    def provenance(self, source_file: str, line_no: int | None) -> Self:
        self.provenance_source_file(source_file)
        self.provenance_line(line_no)
        return self

    def build(self) -> VariableRow:
        """Validate and return immutable VariableRow TypedDict."""
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

        result: dict[str, Any] = dict(self._row)
        result.setdefault("required", False)
        result.setdefault("secret", False)
        result.setdefault("documented", False)
        result.setdefault("provenance_confidence", 0.5)
        result.setdefault("is_unresolved", False)
        result.setdefault("is_ambiguous", False)
        return result  # type: ignore[return-value]


__all__ = [
    "ReferenceContext",
    "Variable",
    "VariableProvenance",
    "VariableRow",
    "VariableRowBuilder",
    "VariableRowWithMeta",
]
