"""VariableDiscovery orchestration for the fsrc scanner core lane."""

from __future__ import annotations

from typing import Any

from prism.scanner_core.di import DIContainer
from prism.scanner_data.contracts_request import validate_variable_discovery_inputs
from prism.scanner_data.contracts_variables import VariableRow

__all__ = [
    "VariableDiscovery",
]


class VariableDiscovery:
    """Discover static and referenced role variables for fsrc scans."""

    def __init__(
        self,
        di: DIContainer,
        role_path: str,
        options: dict[str, Any],
    ) -> None:
        validate_variable_discovery_inputs(role_path=role_path, options=options)
        self._di = di
        self._role_path = role_path
        self._options = options
        self._plugin: Any | None = None
        self._plugin_resolved = False

    def _resolve_plugin(self) -> Any | None:
        if self._plugin_resolved:
            return self._plugin

        factory = getattr(self._di, "factory_variable_discovery_plugin", None)
        if callable(factory):
            self._plugin = factory()

        self._plugin_resolved = True
        return self._plugin

    def discover_static(self) -> tuple[VariableRow, ...]:
        """Discover static variables from defaults/vars/argument_specs/set_fact."""
        plugin = self._resolve_plugin()
        if plugin is not None:
            discovered = plugin.discover_static_variables(
                self._role_path,
                self._options,
            )
            return tuple(discovered)

        raise ValueError(
            "VariableDiscovery requires a plugin via DI factory_variable_discovery_plugin"
        )

    def discover_referenced(self) -> frozenset[str]:
        """Discover referenced variable names from tasks/templates/handlers/README."""
        plugin = self._resolve_plugin()
        if plugin is not None:
            discovered = plugin.discover_referenced_variables(
                self._role_path,
                self._options,
            )
            return frozenset(discovered)

        raise ValueError(
            "VariableDiscovery requires a plugin via DI factory_variable_discovery_plugin"
        )

    def resolve_unresolved(
        self,
        *,
        static_names: frozenset[str] | None = None,
        referenced: frozenset[str] | None = None,
    ) -> dict[str, str]:
        """Return unresolved variable names mapped to uncertainty reasons."""
        effective_static_names = static_names
        if effective_static_names is None:
            effective_static_names = frozenset(
                row["name"] for row in self.discover_static()
            )
        effective_referenced = referenced or self.discover_referenced()

        plugin = self._resolve_plugin()
        if plugin is not None:
            resolved = plugin.resolve_unresolved_variables(
                effective_static_names,
                effective_referenced,
                self._options,
            )
            return dict(resolved)

        raise ValueError(
            "VariableDiscovery requires a plugin via DI factory_variable_discovery_plugin"
        )

    def discover(self) -> tuple[VariableRow, ...]:
        """Discover static rows and append unresolved referenced placeholders."""
        static_rows = self.discover_static()
        static_names = frozenset(row["name"] for row in static_rows)
        referenced = self.discover_referenced()
        unresolved = self.resolve_unresolved(
            static_names=static_names,
            referenced=referenced,
        )

        rows = list(static_rows)
        builder = self._di.factory_variable_row_builder()
        for variable_name in sorted(referenced - static_names):
            rows.append(
                builder.name(variable_name)
                .type("dynamic")
                .default("")
                .source("referenced")
                .documented(False)
                .required(False)
                .secret(False)
                .provenance_source_file("tasks/")
                .provenance_line(None)
                .provenance_confidence(0.5)
                .uncertainty_reason(unresolved.get(variable_name))
                .is_unresolved(True)
                .is_ambiguous(False)
                .build()
            )
        return tuple(rows)
