"""Plugin registry for scanner extensibility seams in the fsrc lane."""

from __future__ import annotations

import importlib
from typing import Any

from prism.scanner_plugins.interfaces import CommentDrivenDocumentationPlugin
from prism.scanner_plugins.interfaces import FeatureDetectionPlugin
from prism.scanner_plugins.interfaces import OutputOrchestrationPlugin
from prism.scanner_plugins.interfaces import ScanPipelinePlugin
from prism.scanner_plugins.interfaces import VariableDiscoveryPlugin


class PluginRegistry:
    """Registry for scanner plugin classes and dynamic plugin loaders."""

    def __init__(self) -> None:
        self._variable_discovery_plugins: dict[str, type[VariableDiscoveryPlugin]] = {}
        self._feature_detection_plugins: dict[str, type[FeatureDetectionPlugin]] = {}
        self._output_orchestration_plugins: dict[
            str, type[OutputOrchestrationPlugin]
        ] = {}
        self._scan_pipeline_plugins: dict[str, type[ScanPipelinePlugin]] = {}
        self._comment_driven_doc_plugins: dict[
            str, type[CommentDrivenDocumentationPlugin]
        ] = {}
        self._loaded_plugins: dict[str, Any] = {}

    def register_variable_discovery_plugin(
        self,
        name: str,
        plugin_class: type[VariableDiscoveryPlugin],
    ) -> None:
        self._variable_discovery_plugins[name] = plugin_class

    def register_feature_detection_plugin(
        self,
        name: str,
        plugin_class: type[FeatureDetectionPlugin],
    ) -> None:
        self._feature_detection_plugins[name] = plugin_class

    def register_output_orchestration_plugin(
        self,
        name: str,
        plugin_class: type[OutputOrchestrationPlugin],
    ) -> None:
        self._output_orchestration_plugins[name] = plugin_class

    def register_scan_pipeline_plugin(
        self,
        name: str,
        plugin_class: type[ScanPipelinePlugin],
    ) -> None:
        self._scan_pipeline_plugins[name] = plugin_class

    def register_comment_driven_doc_plugin(
        self,
        name: str,
        plugin_class: type[CommentDrivenDocumentationPlugin],
    ) -> None:
        self._comment_driven_doc_plugins[name] = plugin_class

    def get_variable_discovery_plugin(
        self,
        name: str,
    ) -> type[VariableDiscoveryPlugin] | None:
        return self._variable_discovery_plugins.get(name)

    def get_feature_detection_plugin(
        self,
        name: str,
    ) -> type[FeatureDetectionPlugin] | None:
        return self._feature_detection_plugins.get(name)

    def get_output_orchestration_plugin(
        self,
        name: str,
    ) -> type[OutputOrchestrationPlugin] | None:
        return self._output_orchestration_plugins.get(name)

    def get_scan_pipeline_plugin(self, name: str) -> type[ScanPipelinePlugin] | None:
        return self._scan_pipeline_plugins.get(name)

    def get_comment_driven_doc_plugin(
        self,
        name: str,
    ) -> type[CommentDrivenDocumentationPlugin] | None:
        return self._comment_driven_doc_plugins.get(name)

    def list_variable_discovery_plugins(self) -> list[str]:
        return list(self._variable_discovery_plugins.keys())

    def list_feature_detection_plugins(self) -> list[str]:
        return list(self._feature_detection_plugins.keys())

    def list_output_orchestration_plugins(self) -> list[str]:
        return list(self._output_orchestration_plugins.keys())

    def list_scan_pipeline_plugins(self) -> list[str]:
        return list(self._scan_pipeline_plugins.keys())

    def list_comment_driven_doc_plugins(self) -> list[str]:
        return list(self._comment_driven_doc_plugins.keys())

    def load_plugin_from_module(self, module_name: str, class_name: str) -> Any:
        if module_name in self._loaded_plugins:
            return self._loaded_plugins[module_name]

        module = importlib.import_module(module_name)
        plugin_class = getattr(module, class_name)
        self._loaded_plugins[module_name] = plugin_class
        return plugin_class


plugin_registry = PluginRegistry()
