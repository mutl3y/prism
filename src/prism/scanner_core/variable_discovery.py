"""VariableDiscovery orchestration for the fsrc scanner core lane."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any, cast

from prism.scanner_core.di import clone_scan_options
from prism.scanner_core.di_helpers import (
    HasVariableDiscoveryPluginFactory,
    get_event_bus_or_none,
)
from prism.scanner_core.events import PHASE_VARIABLE_DISCOVERY
from prism.scanner_data.contracts_request import (
    ScanOptionsDict,
    validate_variable_discovery_inputs,
)
from prism.scanner_data.contracts_variables import VariableRow
from prism.scanner_plugins.interfaces import VariableDiscoveryPlugin

if TYPE_CHECKING:
    from prism.scanner_core.di import DIContainer

__all__ = [
    "VariableDiscovery",
]


logger = logging.getLogger(__name__)


class VariableDiscovery:
    """Discover static and referenced role variables for fsrc scans."""

    def __init__(
        self,
        di: DIContainer,
        role_path: str,
        options: ScanOptionsDict,
    ) -> None:
        validate_variable_discovery_inputs(
            role_path=role_path,
            options=cast(dict[str, Any], options),
        )
        self._di = di
        self._role_path = role_path
        self._options = clone_scan_options(options)
        self._plugin: VariableDiscoveryPlugin | None = None
        self._plugin_resolved = False
        self._plugin_lock = threading.Lock()

    def _snapshot_options(self) -> ScanOptionsDict:
        return clone_scan_options(self._options)

    def _resolve_plugin(self) -> VariableDiscoveryPlugin:
        if self._plugin_resolved:
            if self._plugin is None:
                raise ValueError(
                    "VariableDiscovery requires a plugin via DI "
                    "factory_variable_discovery_plugin"
                )
            return self._plugin
        with self._plugin_lock:
            if not self._plugin_resolved:
                if not isinstance(self._di, HasVariableDiscoveryPluginFactory):
                    raise ValueError(
                        "VariableDiscovery requires a plugin via DI "
                        "factory_variable_discovery_plugin"
                    )
                factory = self._di.factory_variable_discovery_plugin
                if not callable(factory):
                    raise ValueError(
                        "VariableDiscovery requires a plugin via DI "
                        "factory_variable_discovery_plugin (must be callable)"
                    )
                logger.debug(
                    "VariableDiscovery resolving plugin via DI "
                    "factory_variable_discovery_plugin"
                )
                plugin = factory()
                if plugin is None:
                    raise ValueError(
                        "VariableDiscovery requires a plugin via DI "
                        "factory_variable_discovery_plugin (factory returned None)"
                    )
                self._plugin = plugin
                self._plugin_resolved = True
        if self._plugin is None:
            raise ValueError(
                "VariableDiscovery requires a plugin via DI "
                "factory_variable_discovery_plugin"
            )
        return self._plugin

    def discover_static(self) -> tuple[VariableRow, ...]:
        """Discover static variables from defaults/vars/argument_specs/set_fact."""
        plugin = self._resolve_plugin()
        options = self._snapshot_options()
        plugin_options = cast(dict[str, Any], options)
        event_bus = get_event_bus_or_none(self._di)
        ctx: dict[str, object] = {"role_path": self._role_path, "step": "static"}
        if event_bus is not None:
            with event_bus.phase(PHASE_VARIABLE_DISCOVERY, context=ctx):
                discovered = plugin.discover_static_variables(
                    self._role_path,
                    plugin_options,
                )
        else:
            discovered = plugin.discover_static_variables(
                self._role_path,
                plugin_options,
            )
        return tuple(discovered)

    def discover_referenced(self) -> frozenset[str]:
        """Discover referenced variable names from tasks/templates/handlers/README."""
        plugin = self._resolve_plugin()
        options = self._snapshot_options()
        plugin_options = cast(dict[str, Any], options)
        event_bus = get_event_bus_or_none(self._di)
        ctx: dict[str, object] = {
            "role_path": self._role_path,
            "step": "referenced",
        }
        if event_bus is not None:
            with event_bus.phase(PHASE_VARIABLE_DISCOVERY, context=ctx):
                discovered = plugin.discover_referenced_variables(
                    self._role_path,
                    plugin_options,
                )
        else:
            discovered = plugin.discover_referenced_variables(
                self._role_path,
                plugin_options,
            )
        return frozenset(discovered)

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
        resolved = plugin.resolve_unresolved_variables(
            effective_static_names,
            effective_referenced,
            cast(dict[str, Any], self._snapshot_options()),
        )
        return dict(resolved)

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
                .provenance_source_file(None)
                .provenance_line(None)
                .provenance_confidence(0.5)
                .uncertainty_reason(unresolved.get(variable_name))
                .is_unresolved(True)
                .is_ambiguous(False)
                .build()
            )
        return tuple(rows)
