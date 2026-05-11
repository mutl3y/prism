"""Feature detector orchestration for foundational fsrc scanner-core parity."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any, cast

from prism.scanner_core.di import clone_scan_options
from prism.scanner_core.di_helpers import (
    get_event_bus_or_none,
    get_feature_detection_plugin_factory_or_none,
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
    """Import task-catalog adapters lazily to keep detector bootstrap acyclic.

    CRITICAL FIX: Resolves marker_prefix from DI before calling the adapter.
    This ensures feature_detector uses the same comment-driven marker prefix
    as the rest of the scanner, preventing silent use of incorrect defaults.
    """
    from prism.scanner_core.task_extract_adapters import (
        collect_task_handler_catalog as collect_via_adapter,
    )

    # Use the public adapter function which properly resolves marker_prefix from DI
    return collect_via_adapter(
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
        # Synchronize access to detection results for thread-safe concurrent calls
        self._detection_lock = threading.Lock()
        self._cached_features: FeaturesContext | None = None

    def _snapshot_options(self) -> ScanOptionsDict:
        return clone_scan_options(self._options)

    def _resolve_plugin(self) -> FeatureDetectionPlugin | None:
        if self._plugin_resolved:
            return self._plugin
        with self._plugin_lock:
            if not self._plugin_resolved:
                factory = get_feature_detection_plugin_factory_or_none(self._di)
                if factory is None:
                    raise ValueError(
                        "FeatureDetector requires a plugin via DI "
                        "factory_feature_detection_plugin"
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
                        options,
                    )
            return plugin.detect_features(
                self._role_path,
                options,
            )

        # Plugin resolution failed - provide detailed diagnostic
        logger = logging.getLogger(__name__)
        logger.error(
            "FeatureDetector.detect: Plugin resolution failed (factory returned None). "
            "This indicates a DI misconfiguration. "
            "Verify that factory_feature_detection_plugin is registered and returns a valid FeatureDetectionPlugin. "
            "role_path=%r, scan_options_keys=%r",
            self._role_path,
            tuple(options.keys()) if options else None,
        )
        raise ValueError(
            "FeatureDetector.detect: Plugin resolution failed (returned None). "
            "Verify factory_feature_detection_plugin returns a valid FeatureDetectionPlugin."
        )

    def analyze_task_catalog(self) -> TaskCatalog:
        plugin = self._resolve_plugin()
        if plugin is not None:
            return plugin.analyze_task_catalog(
                self._role_path,
                self._snapshot_options(),
            )

        # Plugin resolution failed - provide detailed diagnostic
        logger = logging.getLogger(__name__)
        logger.error(
            "FeatureDetector.analyze_task_catalog: Plugin resolution failed (factory returned None). "
            "This indicates a DI misconfiguration. "
            "Verify that factory_feature_detection_plugin is registered and returns a valid FeatureDetectionPlugin. "
            "role_path=%r",
            self._role_path,
        )
        raise ValueError(
            "FeatureDetector.analyze_task_catalog: Plugin resolution failed (returned None). "
            "Verify factory_feature_detection_plugin returns a valid FeatureDetectionPlugin."
        )

    def collect_task_handler_catalog(
        self,
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        return _collect_task_handler_catalog(
            self._role_path,
            exclude_paths=self._options.get("exclude_path_patterns"),
            di=self._di,
        )
