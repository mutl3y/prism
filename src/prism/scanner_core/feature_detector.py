"""Feature detector orchestration for foundational fsrc scanner-core parity."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, cast

from prism.scanner_core.di import clone_scan_options
from prism.scanner_core.di_helpers import (
    HasFeatureDetectionPluginFactory,
    get_event_bus_or_none,
)
from prism.scanner_core.events import PHASE_FEATURE_DETECTION
from prism.scanner_data.contracts_request import (
    FeaturesContext,
    ScanOptionsDict,
    validate_feature_detector_inputs,
)
from prism.scanner_plugins.interfaces import FeatureDetectionPlugin, TaskCatalog

if TYPE_CHECKING:
    from prism.scanner_core.di import DIContainer


def _collect_task_handler_catalog(
    role_path: str,
    exclude_paths: list[str] | None = None,
    *,
    di: object | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Import task-catalog adapters lazily to keep detector bootstrap acyclic."""
    from prism.scanner_core.task_extract_adapters import collect_task_handler_catalog

    return collect_task_handler_catalog(
        role_path,
        exclude_paths=exclude_paths,
        di=di,
    )


class FeatureDetector:
    """Detect aggregate role features and produce task-catalog summaries."""

    def __init__(
        self,
        di: DIContainer,
        role_path: str,
        options: ScanOptionsDict,
    ) -> None:
        validate_feature_detector_inputs(
            di=di,
            role_path=role_path,
            options=cast(dict[str, Any], options),
        )
        self._di = di
        self._role_path = role_path
        self._options = clone_scan_options(options)
        self._plugin: FeatureDetectionPlugin | None = None
        self._plugin_resolved = False
        self._plugin_lock = threading.Lock()

    def _snapshot_options(self) -> ScanOptionsDict:
        return clone_scan_options(self._options)

    def _resolve_plugin(self) -> FeatureDetectionPlugin | None:
        if self._plugin_resolved:
            return self._plugin
        with self._plugin_lock:
            if not self._plugin_resolved:
                if not isinstance(self._di, HasFeatureDetectionPluginFactory):
                    raise ValueError(
                        "FeatureDetector requires a plugin via DI "
                        "factory_feature_detection_plugin"
                    )
                factory = self._di.factory_feature_detection_plugin
                if not callable(factory):
                    raise ValueError(
                        "FeatureDetector requires a plugin via DI "
                        "factory_feature_detection_plugin (must be callable)"
                    )
                self._plugin = factory()
                self._plugin_resolved = True
        return self._plugin

    def detect(self) -> FeaturesContext:
        plugin = self._resolve_plugin()
        options = self._snapshot_options()
        if plugin is not None:
            event_bus = get_event_bus_or_none(self._di)
            ctx: dict[str, object] = {"role_path": self._role_path}
            if event_bus is not None:
                with event_bus.phase(PHASE_FEATURE_DETECTION, context=ctx):
                    return plugin.detect_features(
                        self._role_path,
                        cast(dict[str, Any], options),
                    )
            return plugin.detect_features(
                self._role_path,
                cast(dict[str, Any], options),
            )

        raise ValueError(
            "FeatureDetector requires a plugin via DI factory_feature_detection_plugin"
        )

    def analyze_task_catalog(self) -> TaskCatalog:
        plugin = self._resolve_plugin()
        if plugin is not None:
            return plugin.analyze_task_catalog(
                self._role_path,
                cast(dict[str, Any], self._snapshot_options()),
            )

        raise ValueError(
            "FeatureDetector requires a plugin via DI factory_feature_detection_plugin"
        )

    def collect_task_handler_catalog(
        self,
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        return _collect_task_handler_catalog(
            self._role_path,
            exclude_paths=self._options.get("exclude_path_patterns"),
            di=self._di,
        )
