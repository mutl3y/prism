"""Plugin registry for scanner extensibility seams in the fsrc lane."""

from __future__ import annotations

import importlib
import threading
from typing import Any

from prism.scanner_plugins.interfaces import CommentDrivenDocumentationPlugin
from prism.scanner_plugins.interfaces import ExtractPolicyPlugin
from prism.scanner_plugins.interfaces import FeatureDetectionPlugin
from prism.scanner_plugins.interfaces import JinjaAnalysisPolicyPlugin
from prism.scanner_plugins.interfaces import OutputOrchestrationPlugin
from prism.scanner_plugins.interfaces import ReadmeRendererPlugin
from prism.scanner_plugins.interfaces import ScanPipelinePlugin
from prism.scanner_plugins.interfaces import VariableDiscoveryPlugin
from prism.scanner_plugins.interfaces import YAMLParsingPolicyPlugin


PRISM_PLUGIN_API_VERSION: tuple[int, int] = (1, 0)


class PluginAPIVersionMismatch(ValueError):
    """Raised when a plugin declares an incompatible PRISM_PLUGIN_API_VERSION."""


class PluginStatelessRequired(TypeError):
    """Raised when a non-stateless plugin is registered in a singleton-eligible slot."""


# Slots whose plugins are intended to be safe for singleton reuse across scans.
_STATELESS_REQUIRED_SLOTS: frozenset[str] = frozenset(
    {
        "extract_policy",
        "jinja_analysis_policy",
        "readme_renderer",
        "scan_pipeline",
        "yaml_parsing_policy",
    }
)


def require_stateless_plugin(
    plugin_class: type[Any],
    *,
    name: str,
    slot: str,
) -> None:
    """Validate that a plugin declares ``PLUGIN_IS_STATELESS = True`` for slots
    where the registry treats plugins as singletons.

    Plugins that omit the marker entirely are accepted (backward-compat) only
    for slots not in :data:`_STATELESS_REQUIRED_SLOTS`. For required slots,
    the marker must be explicitly set to ``True``.
    """
    if slot not in _STATELESS_REQUIRED_SLOTS:
        return
    declared = getattr(plugin_class, "PLUGIN_IS_STATELESS", None)
    if declared is True:
        return
    if declared is None:
        # Backward-compat: accept plugins lacking the marker but warn loudly.
        import warnings

        warnings.warn(
            f"Plugin '{name}' registered in stateless-required slot '{slot}' "
            "does not declare PLUGIN_IS_STATELESS = True. "
            "Add PLUGIN_IS_STATELESS = True to suppress this warning.",
            stacklevel=4,
        )
        return
    raise PluginStatelessRequired(
        f"Plugin '{name}' for slot '{slot}' declares PLUGIN_IS_STATELESS="
        f"{declared!r}; this slot only accepts stateless plugins"
    )


def _coerce_version(value: object) -> tuple[int, int] | None:
    if isinstance(value, tuple) and len(value) == 2:
        major, minor = value
        if isinstance(major, int) and isinstance(minor, int):
            return (major, minor)
    return None


def validate_plugin_api_version(
    plugin_class: type[Any],
    *,
    name: str,
    slot: str,
    core_version: tuple[int, int] = PRISM_PLUGIN_API_VERSION,
) -> None:
    """Validate a plugin class declares a compatible PRISM_PLUGIN_API_VERSION.

    Compatibility rule: same major version, plugin minor <= core minor.
    Plugins that omit the attribute are accepted (backward-compatible).
    """
    declared = getattr(plugin_class, "PRISM_PLUGIN_API_VERSION", None)
    if declared is None:
        return
    parsed = _coerce_version(declared)
    if parsed is None:
        raise PluginAPIVersionMismatch(
            f"Plugin '{name}' for slot '{slot}' declared an invalid "
            f"PRISM_PLUGIN_API_VERSION: {declared!r} (expected (major, minor) ints)"
        )
    plugin_major, plugin_minor = parsed
    core_major, core_minor = core_version
    if plugin_major != core_major or plugin_minor > core_minor:
        raise PluginAPIVersionMismatch(
            f"Plugin '{name}' for slot '{slot}' declares API version "
            f"{plugin_major}.{plugin_minor} which is incompatible with core "
            f"version {core_major}.{core_minor}"
        )


class PluginRegistry:
    """Registry for scanner plugin classes and dynamic plugin loaders."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._variable_discovery_plugins: dict[str, type[VariableDiscoveryPlugin]] = {}
        self._feature_detection_plugins: dict[str, type[FeatureDetectionPlugin]] = {}
        self._output_orchestration_plugins: dict[
            str, type[OutputOrchestrationPlugin]
        ] = {}
        self._scan_pipeline_plugins: dict[str, type[ScanPipelinePlugin]] = {}
        self._reserved_unsupported_platforms: frozenset[str] = frozenset()
        self._comment_driven_doc_plugins: dict[
            str, type[CommentDrivenDocumentationPlugin]
        ] = {}
        self._extract_policy_plugins: dict[str, type[ExtractPolicyPlugin]] = {}
        self._yaml_parsing_policy_plugins: dict[str, type[YAMLParsingPolicyPlugin]] = {}
        self._jinja_analysis_policy_plugins: dict[
            str, type[JinjaAnalysisPolicyPlugin]
        ] = {}
        self._readme_renderer_plugins: dict[str, type[ReadmeRendererPlugin]] = {}
        self._loaded_plugins: dict[tuple[str, str], Any] = {}
        self._deferred_variable_discovery: dict[str, tuple[str, str]] = {}
        self._deferred_feature_detection: dict[str, tuple[str, str]] = {}
        self._default_platform_key: str | None = None

    def register_variable_discovery_plugin(
        self,
        name: str,
        plugin_class: type[VariableDiscoveryPlugin],
    ) -> None:
        validate_plugin_api_version(plugin_class, name=name, slot="variable_discovery")
        with self._lock:
            self._variable_discovery_plugins[name] = plugin_class

    def register_deferred_variable_discovery_plugin(
        self,
        name: str,
        module_path: str,
        class_name: str,
    ) -> None:
        with self._lock:
            self._deferred_variable_discovery[name] = (module_path, class_name)

    def register_feature_detection_plugin(
        self,
        name: str,
        plugin_class: type[FeatureDetectionPlugin],
    ) -> None:
        validate_plugin_api_version(plugin_class, name=name, slot="feature_detection")
        with self._lock:
            self._feature_detection_plugins[name] = plugin_class

    def register_deferred_feature_detection_plugin(
        self,
        name: str,
        module_path: str,
        class_name: str,
    ) -> None:
        with self._lock:
            self._deferred_feature_detection[name] = (module_path, class_name)

    def register_output_orchestration_plugin(
        self,
        name: str,
        plugin_class: type[OutputOrchestrationPlugin],
    ) -> None:
        validate_plugin_api_version(
            plugin_class, name=name, slot="output_orchestration"
        )
        with self._lock:
            self._output_orchestration_plugins[name] = plugin_class

    def register_scan_pipeline_plugin(
        self,
        name: str,
        plugin_class: type[ScanPipelinePlugin],
    ) -> None:
        validate_plugin_api_version(plugin_class, name=name, slot="scan_pipeline")
        require_stateless_plugin(plugin_class, name=name, slot="scan_pipeline")
        with self._lock:
            self._scan_pipeline_plugins[name] = plugin_class

    def register_comment_driven_doc_plugin(
        self,
        name: str,
        plugin_class: type[CommentDrivenDocumentationPlugin],
    ) -> None:
        validate_plugin_api_version(plugin_class, name=name, slot="comment_driven_doc")
        with self._lock:
            self._comment_driven_doc_plugins[name] = plugin_class

    def register_extract_policy_plugin(
        self,
        name: str,
        plugin_class: type[ExtractPolicyPlugin],
    ) -> None:
        validate_plugin_api_version(plugin_class, name=name, slot="extract_policy")
        require_stateless_plugin(plugin_class, name=name, slot="extract_policy")
        with self._lock:
            self._extract_policy_plugins[name] = plugin_class

    def register_yaml_parsing_policy_plugin(
        self,
        name: str,
        plugin_class: type[YAMLParsingPolicyPlugin],
    ) -> None:
        validate_plugin_api_version(plugin_class, name=name, slot="yaml_parsing_policy")
        require_stateless_plugin(plugin_class, name=name, slot="yaml_parsing_policy")
        with self._lock:
            self._yaml_parsing_policy_plugins[name] = plugin_class

    def register_jinja_analysis_policy_plugin(
        self,
        name: str,
        plugin_class: type[JinjaAnalysisPolicyPlugin],
    ) -> None:
        validate_plugin_api_version(
            plugin_class, name=name, slot="jinja_analysis_policy"
        )
        require_stateless_plugin(plugin_class, name=name, slot="jinja_analysis_policy")
        with self._lock:
            self._jinja_analysis_policy_plugins[name] = plugin_class

    def register_readme_renderer_plugin(
        self,
        name: str,
        plugin_class: type[ReadmeRendererPlugin],
    ) -> None:
        validate_plugin_api_version(plugin_class, name=name, slot="readme_renderer")
        require_stateless_plugin(plugin_class, name=name, slot="readme_renderer")
        with self._lock:
            self._readme_renderer_plugins[name] = plugin_class

    def register_reserved_unsupported_platform(self, name: str) -> None:
        with self._lock:
            self._reserved_unsupported_platforms = (
                self._reserved_unsupported_platforms | {name}
            )

    def is_reserved_unsupported_platform(self, name: str) -> bool:
        with self._lock:
            return name in self._reserved_unsupported_platforms

    def get_variable_discovery_plugin(
        self,
        name: str,
    ) -> type[VariableDiscoveryPlugin] | None:
        with self._lock:
            result = self._variable_discovery_plugins.get(name)
            if result is not None:
                return result
            deferred = self._deferred_variable_discovery.get(name)
            if deferred is not None:
                module_path, class_name = deferred
                cls = self.load_plugin_from_module(module_path, class_name)
                self._variable_discovery_plugins[name] = cls
                return cls
        return None

    def get_feature_detection_plugin(
        self,
        name: str,
    ) -> type[FeatureDetectionPlugin] | None:
        with self._lock:
            result = self._feature_detection_plugins.get(name)
            if result is not None:
                return result
            deferred = self._deferred_feature_detection.get(name)
            if deferred is not None:
                module_path, class_name = deferred
                cls = self.load_plugin_from_module(module_path, class_name)
                self._feature_detection_plugins[name] = cls
                return cls
        return None

    def get_output_orchestration_plugin(
        self,
        name: str,
    ) -> type[OutputOrchestrationPlugin] | None:
        with self._lock:
            return self._output_orchestration_plugins.get(name)

    def get_scan_pipeline_plugin(self, name: str) -> type[ScanPipelinePlugin] | None:
        with self._lock:
            return self._scan_pipeline_plugins.get(name)

    def get_comment_driven_doc_plugin(
        self,
        name: str,
    ) -> type[CommentDrivenDocumentationPlugin] | None:
        with self._lock:
            return self._comment_driven_doc_plugins.get(name)

    def get_extract_policy_plugin(self, name: str) -> type[ExtractPolicyPlugin] | None:
        with self._lock:
            return self._extract_policy_plugins.get(name)

    def get_yaml_parsing_policy_plugin(
        self, name: str
    ) -> type[YAMLParsingPolicyPlugin] | None:
        with self._lock:
            return self._yaml_parsing_policy_plugins.get(name)

    def get_jinja_analysis_policy_plugin(
        self, name: str
    ) -> type[JinjaAnalysisPolicyPlugin] | None:
        with self._lock:
            return self._jinja_analysis_policy_plugins.get(name)

    def get_readme_renderer_plugin(
        self, name: str
    ) -> type[ReadmeRendererPlugin] | None:
        with self._lock:
            return self._readme_renderer_plugins.get(name)

    def list_variable_discovery_plugins(self) -> list[str]:
        with self._lock:
            names = set(self._variable_discovery_plugins.keys())
            names.update(self._deferred_variable_discovery.keys())
            return sorted(names)

    def list_feature_detection_plugins(self) -> list[str]:
        with self._lock:
            names = set(self._feature_detection_plugins.keys())
            names.update(self._deferred_feature_detection.keys())
            return sorted(names)

    def list_output_orchestration_plugins(self) -> list[str]:
        with self._lock:
            return list(self._output_orchestration_plugins.keys())

    def list_scan_pipeline_plugins(self) -> list[str]:
        with self._lock:
            return list(self._scan_pipeline_plugins.keys())

    def list_comment_driven_doc_plugins(self) -> list[str]:
        with self._lock:
            return list(self._comment_driven_doc_plugins.keys())

    def list_extract_policy_plugins(self) -> list[str]:
        with self._lock:
            return list(self._extract_policy_plugins.keys())

    def list_yaml_parsing_policy_plugins(self) -> list[str]:
        with self._lock:
            return list(self._yaml_parsing_policy_plugins.keys())

    def list_jinja_analysis_policy_plugins(self) -> list[str]:
        with self._lock:
            return list(self._jinja_analysis_policy_plugins.keys())

    def list_readme_renderer_plugins(self) -> dict[str, type[ReadmeRendererPlugin]]:
        with self._lock:
            return dict(self._readme_renderer_plugins)

    def set_default_platform_key(self, name: str) -> None:
        """Explicitly nominate a platform key as the registry default."""
        with self._lock:
            known = (
                set(self._variable_discovery_plugins)
                | set(self._scan_pipeline_plugins)
                | set(self._deferred_variable_discovery)
            )
            if name not in known:
                raise KeyError(
                    f"cannot set default platform key {name!r}: not registered"
                )
            self._default_platform_key = name

    def get_default_platform_key(self) -> str | None:
        """Return the explicitly-set default platform key, or the first registered one."""
        with self._lock:
            if self._default_platform_key is not None:
                return self._default_platform_key
            for source in (
                self._variable_discovery_plugins,
                self._deferred_variable_discovery,
                self._scan_pipeline_plugins,
            ):
                if source:
                    return next(iter(source.keys()))
            return None

    def load_plugin_from_module(self, module_name: str, class_name: str) -> type[Any]:
        """Load a plugin class from module_name.class_name (dynamic import).

        Returns the class itself (not an instance). Runtime type is uncertain
        due to dynamic loading; callers should validate plugin shape after load.
        """
        cache_key = (module_name, class_name)
        cached = self._loaded_plugins.get(cache_key)
        if cached is not None:
            return cached
        with self._lock:
            cached = self._loaded_plugins.get(cache_key)
            if cached is not None:
                return cached
            module = importlib.import_module(module_name)
            if not hasattr(module, class_name):
                raise ValueError(
                    f"Plugin class '{class_name}' not found in module '{module_name}'"
                )
            plugin_class = getattr(module, class_name)
            self._loaded_plugins[cache_key] = plugin_class
        return plugin_class


plugin_registry = PluginRegistry()
