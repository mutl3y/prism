"""Minimal builders used by the fsrc scanner-core migration lane."""

from __future__ import annotations

from typing import Any

from prism.scanner_data.contracts_variables import VariableRow


class VariableRowBuilder:
    """Fluent helper for constructing VariableRow payloads."""

    def __init__(self) -> None:
        self._payload: dict[str, Any] = {}

    def name(self, value: str) -> VariableRowBuilder:
        self._payload["name"] = value
        return self

    def type(self, value: str) -> VariableRowBuilder:
        self._payload["type"] = value
        return self

    def default(self, value: str) -> VariableRowBuilder:
        self._payload["default"] = value
        return self

    def source(self, value: str) -> VariableRowBuilder:
        self._payload["source"] = value
        return self

    def documented(self, value: bool) -> VariableRowBuilder:
        self._payload["documented"] = value
        return self

    def required(self, value: bool) -> VariableRowBuilder:
        self._payload["required"] = value
        return self

    def secret(self, value: bool) -> VariableRowBuilder:
        self._payload["secret"] = value
        return self

    def provenance_source_file(self, value: str | None) -> VariableRowBuilder:
        self._payload["provenance_source_file"] = value
        return self

    def provenance_line(self, value: int | None) -> VariableRowBuilder:
        self._payload["provenance_line"] = value
        return self

    def provenance_confidence(self, value: float) -> VariableRowBuilder:
        self._payload["provenance_confidence"] = value
        return self

    def uncertainty_reason(self, value: str | None) -> VariableRowBuilder:
        self._payload["uncertainty_reason"] = value
        return self

    def is_unresolved(self, value: bool) -> VariableRowBuilder:
        self._payload["is_unresolved"] = value
        return self

    def is_ambiguous(self, value: bool) -> VariableRowBuilder:
        self._payload["is_ambiguous"] = value
        return self

    def build(self) -> VariableRow:
        name = self._payload.get("name")
        var_type = self._payload.get("type")
        if not isinstance(name, str) or not name:
            raise ValueError("VariableRowBuilder requires non-empty 'name'")
        if not isinstance(var_type, str) or not var_type:
            raise ValueError("VariableRowBuilder requires non-empty 'type'")

        result: VariableRow = {
            "name": name,
            "type": var_type,
            "default": str(self._payload.get("default", "")),
            "source": str(self._payload.get("source", "")),
            "documented": bool(self._payload.get("documented", False)),
            "required": bool(self._payload.get("required", False)),
            "secret": bool(self._payload.get("secret", False)),
            "provenance_source_file": self._payload.get("provenance_source_file"),
            "provenance_line": self._payload.get("provenance_line"),
            "provenance_confidence": float(
                self._payload.get("provenance_confidence", 0.5)
            ),
            "uncertainty_reason": self._payload.get("uncertainty_reason"),
            "is_unresolved": bool(self._payload.get("is_unresolved", False)),
            "is_ambiguous": bool(self._payload.get("is_ambiguous", False)),
        }
        self._payload = {}
        return result
