"""Focused tests for comment-driven documentation plugin resolution in fsrc."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FSRC_SOURCE_ROOT = PROJECT_ROOT / "src"


@contextmanager
def _prefer_fsrc_prism_on_sys_path() -> object:
    original_path = list(sys.path)
    original_modules = {
        key: value
        for key, value in sys.modules.items()
        if key == "prism" or key.startswith("prism.")
    }
    try:
        sys.path.insert(0, str(FSRC_SOURCE_ROOT))
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        yield
    finally:
        sys.path[:] = original_path
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        sys.modules.update(original_modules)


class _RecordingCommentDocPlugin:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str] | None, str]] = []

    def extract_role_notes_from_comments(
        self,
        role_path: str,
        exclude_paths: list[str] | None = None,
        marker_prefix: str = "prism",
    ) -> dict[str, list[str]]:
        self.calls.append((role_path, exclude_paths, marker_prefix))
        return {
            "warnings": ["plugin warning"],
            "deprecations": [],
            "notes": ["plugin note"],
            "additionals": [],
        }


class _DIWithCommentDocFactory:
    def __init__(self, plugin: _RecordingCommentDocPlugin) -> None:
        self._plugin = plugin

    def factory_comment_driven_doc_plugin(self) -> _RecordingCommentDocPlugin:
        return self._plugin


class _RegistryOnlyCommentDocPlugin:
    def extract_role_notes_from_comments(
        self,
        role_path: str,
        exclude_paths: list[str] | None = None,
        marker_prefix: str = "prism",
    ) -> dict[str, list[str]]:
        return {
            "warnings": [f"registry:{role_path}"],
            "deprecations": [],
            "notes": [f"registry:{marker_prefix}"],
            "additionals": [],
        }


class _TaskAnnotationPluginFromDI:
    @staticmethod
    def split_task_annotation_label(text: str) -> tuple[str, str]:
        return "di", text


class _TaskAnnotationPluginFromRegistry:
    @staticmethod
    def split_task_annotation_label(text: str) -> tuple[str, str]:
        return "registry", text


class _TaskLineParsingPluginFromDI:
    TASK_INCLUDE_KEYS = {"di.include"}
    ROLE_INCLUDE_KEYS = {"include_role"}
    INCLUDE_VARS_KEYS = {"include_vars"}
    SET_FACT_KEYS = {"set_fact"}
    TASK_BLOCK_KEYS = {"block"}
    TASK_META_KEYS = {"meta"}
    TEMPLATED_INCLUDE_RE = __import__("re").compile(r"^.+$")

    @staticmethod
    def extract_constrained_when_values(_task: dict, _variable: str) -> list[str]:
        return []

    @staticmethod
    def detect_task_module(_task: dict) -> str:
        return "debug"


class _TaskLineParsingPluginFromRegistry:
    TASK_INCLUDE_KEYS = {"registry.include"}
    ROLE_INCLUDE_KEYS = {"include_role"}
    INCLUDE_VARS_KEYS = {"include_vars"}
    SET_FACT_KEYS = {"set_fact"}
    TASK_BLOCK_KEYS = {"block"}
    TASK_META_KEYS = {"meta"}
    TEMPLATED_INCLUDE_RE = __import__("re").compile(r"^.+$")

    @staticmethod
    def extract_constrained_when_values(_task: dict, _variable: str) -> list[str]:
        return []

    @staticmethod
    def detect_task_module(_task: dict) -> str:
        return "debug"


class _TaskTraversalPluginFromDI:
    @staticmethod
    def iter_task_mappings(_data: object):
        yield from []

    @staticmethod
    def iter_task_include_targets(_data: object) -> list[str]:
        return ["di.yml"]

    @staticmethod
    def expand_include_target_candidates(_task: dict, include_target: str) -> list[str]:
        return [include_target]

    @staticmethod
    def iter_role_include_targets(_task: dict) -> list[str]:
        return []

    @staticmethod
    def iter_dynamic_role_include_targets(_task: dict) -> list[str]:
        return []

    @staticmethod
    def collect_unconstrained_dynamic_task_includes(
        *, role_root, task_files, load_yaml_file
    ):
        del role_root, task_files, load_yaml_file
        return []

    @staticmethod
    def collect_unconstrained_dynamic_role_includes(
        *, role_root, task_files, load_yaml_file
    ):
        del role_root, task_files, load_yaml_file
        return []


class _TaskTraversalPluginFromRegistry:
    @staticmethod
    def iter_task_mappings(_data: object):
        yield from []

    @staticmethod
    def iter_task_include_targets(_data: object) -> list[str]:
        return ["registry.yml"]

    @staticmethod
    def expand_include_target_candidates(_task: dict, include_target: str) -> list[str]:
        return [include_target]

    @staticmethod
    def iter_role_include_targets(_task: dict) -> list[str]:
        return []

    @staticmethod
    def iter_dynamic_role_include_targets(_task: dict) -> list[str]:
        return []

    @staticmethod
    def collect_unconstrained_dynamic_task_includes(
        *, role_root, task_files, load_yaml_file
    ):
        del role_root, task_files, load_yaml_file
        return []

    @staticmethod
    def collect_unconstrained_dynamic_role_includes(
        *, role_root, task_files, load_yaml_file
    ):
        del role_root, task_files, load_yaml_file
        return []


class _VariableExtractorPluginFromDI:
    @staticmethod
    def collect_include_vars_files(**_kwargs):
        return [Path("di-vars.yml")]


class _VariableExtractorPluginFromRegistry:
    @staticmethod
    def collect_include_vars_files(**_kwargs):
        return [Path("registry-vars.yml")]


class _YAMLParsingPluginFromDI:
    @staticmethod
    def load_yaml_file(path: Path) -> object:
        del path
        return {"source": "di"}


class _YAMLParsingPluginFromRegistry:
    @staticmethod
    def load_yaml_file(path: Path) -> object:
        del path
        return {"source": "registry"}


class _JinjaAnalysisPluginFromDI:
    @staticmethod
    def collect_undeclared_jinja_variables(text: str) -> set[str]:
        del text
        return {"from_di_jinja_plugin"}


class _JinjaAnalysisPluginFromRegistry:
    @staticmethod
    def collect_undeclared_jinja_variables(text: str) -> set[str]:
        del text
        return {"from_registry_jinja_plugin"}


def test_extract_role_notes_routes_via_di_plugin() -> None:
    plugin = _RecordingCommentDocPlugin()
    di = _DIWithCommentDocFactory(plugin)

    with _prefer_fsrc_prism_on_sys_path():
        plugin_defaults = importlib.import_module("prism.scanner_plugins.defaults")
        result = plugin_defaults.extract_role_notes_from_comments(
            role_path="/tmp/fake-role",
            exclude_paths=["tasks/ignored.yml"],
            marker_prefix="opsdoc",
            di=di,
        )

    assert result["notes"] == ["plugin note"]
    assert plugin.calls == [("/tmp/fake-role", ["tasks/ignored.yml"], "opsdoc")]


def test_extract_role_notes_default_plugin_preserves_existing_behavior(
    tmp_path: Path,
) -> None:
    role_path = tmp_path / "role"
    tasks_dir = role_path / "tasks"
    defaults_fragment_dir = role_path / "defaults" / "main"
    tasks_dir.mkdir(parents=True)
    defaults_fragment_dir.mkdir(parents=True)
    (tasks_dir / "main.yml").write_text(
        "# prism~warning: check rollback path\n"
        "# prism~note: verify service dependencies\n"
        "- name: Example task\n"
        "  debug:\n"
        "    msg: ok\n",
        encoding="utf-8",
    )
    (defaults_fragment_dir / "extra.yml").write_text(
        "# prism~note: fragment defaults note\n",
        encoding="utf-8",
    )

    with _prefer_fsrc_prism_on_sys_path():
        plugin_defaults = importlib.import_module("prism.scanner_plugins.defaults")
        result = plugin_defaults.extract_role_notes_from_comments(str(role_path))

    assert "check rollback path" in result["warnings"]
    assert "verify service dependencies" in result["notes"]
    assert "fragment defaults note" in result["notes"]


def test_extract_role_notes_prefers_di_over_registry_default() -> None:
    plugin = _RecordingCommentDocPlugin()
    di = _DIWithCommentDocFactory(plugin)

    with _prefer_fsrc_prism_on_sys_path():
        plugin_defaults = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_comment_driven_doc_plugin("default")
        try:
            plugin_registry.register_comment_driven_doc_plugin(
                "default",
                _RegistryOnlyCommentDocPlugin,
            )
            result = plugin_defaults.extract_role_notes_from_comments(
                role_path="/tmp/di-wins",
                marker_prefix="di",
                di=di,
            )
        finally:
            if original is None:
                plugin_registry._comment_driven_doc_plugins.pop("default", None)
            else:
                plugin_registry.register_comment_driven_doc_plugin("default", original)

    assert result["notes"] == ["plugin note"]
    assert plugin.calls == [("/tmp/di-wins", None, "di")]


def test_extract_role_notes_uses_registry_default_when_di_absent() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        plugin_defaults = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_comment_driven_doc_plugin("default")
        try:
            plugin_registry.register_comment_driven_doc_plugin(
                "default",
                _RegistryOnlyCommentDocPlugin,
            )
            result = plugin_defaults.extract_role_notes_from_comments(
                role_path="/tmp/registry-wins",
                marker_prefix="registry",
            )
        finally:
            if original is None:
                plugin_registry._comment_driven_doc_plugins.pop("default", None)
            else:
                plugin_registry.register_comment_driven_doc_plugin("default", original)

    assert result["warnings"] == ["registry:/tmp/registry-wins"]
    assert result["notes"] == ["registry:registry"]


def test_extract_role_notes_uses_class_fallback_when_di_and_registry_unavailable(
    tmp_path: Path,
) -> None:
    role_path = tmp_path / "role"
    tasks_dir = role_path / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "main.yml").write_text(
        "# prism~note: fallback engaged\n"
        "- name: Example task\n"
        "  debug:\n"
        "    msg: ok\n",
        encoding="utf-8",
    )

    with _prefer_fsrc_prism_on_sys_path():
        plugin_defaults = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        had_default = "default" in plugin_registry.list_comment_driven_doc_plugins()
        original = plugin_registry.get_comment_driven_doc_plugin("default")
        try:
            plugin_registry._comment_driven_doc_plugins.pop("default", None)
            result = plugin_defaults.extract_role_notes_from_comments(str(role_path))
        finally:
            if had_default and original is not None:
                plugin_registry.register_comment_driven_doc_plugin("default", original)

    assert "fallback engaged" in result["notes"]


def test_run_scan_metadata_role_notes_uses_comment_doc_plugin_seam(
    tmp_path: Path,
) -> None:
    role_path = tmp_path / "role"
    (role_path / "defaults").mkdir(parents=True)
    (role_path / "tasks").mkdir(parents=True)
    (role_path / "defaults" / "main.yml").write_text(
        "---\nexample_name: prism\n",
        encoding="utf-8",
    )
    (role_path / "tasks" / "main.yml").write_text(
        "- name: Example task\n" "  debug:\n" '    msg: "{{ example_name }}"\n',
        encoding="utf-8",
    )

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        class _Plugin:
            def extract_role_notes_from_comments(
                self,
                role_path: str,
                exclude_paths: list[str] | None = None,
                marker_prefix: str = "prism",
            ) -> dict[str, list[str]]:
                del role_path
                del exclude_paths
                return {
                    "warnings": [],
                    "deprecations": [],
                    "notes": [f"from-plugin:{marker_prefix}"],
                    "additionals": [],
                }

        original_container = api_module.DIContainer

        class _DIContainerWithCommentDocPlugin(original_container):
            def factory_comment_driven_doc_plugin(self):
                return _Plugin()

        api_module.DIContainer = _DIContainerWithCommentDocPlugin
        try:
            payload = api_module.run_scan(str(role_path), include_vars_main=True)
        finally:
            api_module.DIContainer = original_container

    role_notes = payload["metadata"].get("role_notes")
    assert isinstance(role_notes, dict)
    assert role_notes.get("notes") == ["from-plugin:prism"]


def test_task_annotation_policy_resolver_prefers_di_over_registry() -> None:
    class _DI:
        def factory_task_annotation_policy_plugin(self) -> _TaskAnnotationPluginFromDI:
            return _TaskAnnotationPluginFromDI()

    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_extract_policy_plugin("task_annotation_parsing")
        try:
            plugin_registry.register_extract_policy_plugin(
                "task_annotation_parsing",
                _TaskAnnotationPluginFromRegistry,
            )
            plugin = defaults_module.resolve_task_annotation_policy_plugin(_DI())
        finally:
            if original is None:
                plugin_registry._extract_policy_plugins.pop(
                    "task_annotation_parsing", None
                )
            else:
                plugin_registry.register_extract_policy_plugin(
                    "task_annotation_parsing", original
                )

    assert plugin.split_task_annotation_label("x") == ("di", "x")


def test_task_annotation_policy_resolver_uses_registry_before_fallback() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_extract_policy_plugin("task_annotation_parsing")
        try:
            plugin_registry.register_extract_policy_plugin(
                "task_annotation_parsing",
                _TaskAnnotationPluginFromRegistry,
            )
            plugin = defaults_module.resolve_task_annotation_policy_plugin(None)
        finally:
            if original is None:
                plugin_registry._extract_policy_plugins.pop(
                    "task_annotation_parsing", None
                )
            else:
                plugin_registry.register_extract_policy_plugin(
                    "task_annotation_parsing", original
                )

    assert plugin.split_task_annotation_label("x") == ("registry", "x")


def test_task_line_parsing_policy_resolver_prefers_di_over_registry() -> None:
    class _DI:
        def factory_task_line_parsing_policy_plugin(
            self,
        ) -> _TaskLineParsingPluginFromDI:
            return _TaskLineParsingPluginFromDI()

    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_extract_policy_plugin("task_line_parsing")
        try:
            plugin_registry.register_extract_policy_plugin(
                "task_line_parsing",
                _TaskLineParsingPluginFromRegistry,
            )
            plugin = defaults_module.resolve_task_line_parsing_policy_plugin(_DI())
        finally:
            if original is None:
                plugin_registry._extract_policy_plugins.pop("task_line_parsing", None)
            else:
                plugin_registry.register_extract_policy_plugin(
                    "task_line_parsing", original
                )

    assert plugin.TASK_INCLUDE_KEYS == {"di.include"}


def test_task_line_parsing_policy_resolver_uses_registry_before_fallback() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_extract_policy_plugin("task_line_parsing")
        try:
            plugin_registry.register_extract_policy_plugin(
                "task_line_parsing",
                _TaskLineParsingPluginFromRegistry,
            )
            plugin = defaults_module.resolve_task_line_parsing_policy_plugin(None)
        finally:
            if original is None:
                plugin_registry._extract_policy_plugins.pop("task_line_parsing", None)
            else:
                plugin_registry.register_extract_policy_plugin(
                    "task_line_parsing", original
                )

    assert plugin.TASK_INCLUDE_KEYS == {"registry.include"}


def test_task_line_parsing_policy_resolver_uses_fallback_when_unavailable() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_extract_policy_plugin("task_line_parsing")
        try:
            plugin_registry._extract_policy_plugins.pop("task_line_parsing", None)
            plugin = defaults_module.resolve_task_line_parsing_policy_plugin(None)
        finally:
            if original is not None:
                plugin_registry.register_extract_policy_plugin(
                    "task_line_parsing", original
                )

    assert "include_tasks" in plugin.TASK_INCLUDE_KEYS


def test_task_traversal_policy_resolver_prefers_di_over_registry() -> None:
    class _DI:
        def factory_task_traversal_policy_plugin(self) -> _TaskTraversalPluginFromDI:
            return _TaskTraversalPluginFromDI()

    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_extract_policy_plugin("task_traversal")
        try:
            plugin_registry.register_extract_policy_plugin(
                "task_traversal",
                _TaskTraversalPluginFromRegistry,
            )
            plugin = defaults_module.resolve_task_traversal_policy_plugin(_DI())
        finally:
            if original is None:
                plugin_registry._extract_policy_plugins.pop("task_traversal", None)
            else:
                plugin_registry.register_extract_policy_plugin(
                    "task_traversal", original
                )

    assert plugin.iter_task_include_targets([]) == ["di.yml"]


def test_task_traversal_policy_resolver_uses_registry_before_fallback() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_extract_policy_plugin("task_traversal")
        try:
            plugin_registry.register_extract_policy_plugin(
                "task_traversal",
                _TaskTraversalPluginFromRegistry,
            )
            plugin = defaults_module.resolve_task_traversal_policy_plugin(None)
        finally:
            if original is None:
                plugin_registry._extract_policy_plugins.pop("task_traversal", None)
            else:
                plugin_registry.register_extract_policy_plugin(
                    "task_traversal", original
                )

    assert plugin.iter_task_include_targets([]) == ["registry.yml"]


def test_task_traversal_policy_resolver_uses_fallback_when_unavailable() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_extract_policy_plugin("task_traversal")
        try:
            plugin_registry._extract_policy_plugins.pop("task_traversal", None)
            plugin = defaults_module.resolve_task_traversal_policy_plugin(None)
        finally:
            if original is not None:
                plugin_registry.register_extract_policy_plugin(
                    "task_traversal", original
                )

    assert plugin.iter_task_include_targets([{"include_tasks": "main.yml"}]) == [
        "main.yml"
    ]


def test_variable_extractor_policy_resolver_prefers_di_over_registry() -> None:
    class _DI:
        def factory_variable_extractor_policy_plugin(
            self,
        ) -> _VariableExtractorPluginFromDI:
            return _VariableExtractorPluginFromDI()

    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_extract_policy_plugin("variable_extractor")
        try:
            plugin_registry.register_extract_policy_plugin(
                "variable_extractor",
                _VariableExtractorPluginFromRegistry,
            )
            plugin = defaults_module.resolve_variable_extractor_policy_plugin(_DI())
        finally:
            if original is None:
                plugin_registry._extract_policy_plugins.pop("variable_extractor", None)
            else:
                plugin_registry.register_extract_policy_plugin(
                    "variable_extractor", original
                )

    result = plugin.collect_include_vars_files()
    assert [path.name for path in result] == ["di-vars.yml"]


def test_variable_extractor_policy_resolver_uses_registry_before_fallback() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_extract_policy_plugin("variable_extractor")
        try:
            plugin_registry.register_extract_policy_plugin(
                "variable_extractor",
                _VariableExtractorPluginFromRegistry,
            )
            plugin = defaults_module.resolve_variable_extractor_policy_plugin(None)
        finally:
            if original is None:
                plugin_registry._extract_policy_plugins.pop("variable_extractor", None)
            else:
                plugin_registry.register_extract_policy_plugin(
                    "variable_extractor", original
                )

    result = plugin.collect_include_vars_files()
    assert [path.name for path in result] == ["registry-vars.yml"]


def test_variable_extractor_policy_resolver_uses_fallback_when_unavailable() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_extract_policy_plugin("variable_extractor")
        try:
            plugin_registry._extract_policy_plugins.pop("variable_extractor", None)
            plugin = defaults_module.resolve_variable_extractor_policy_plugin(None)
        finally:
            if original is not None:
                plugin_registry.register_extract_policy_plugin(
                    "variable_extractor", original
                )

    assert hasattr(plugin, "collect_include_vars_files")


def test_yaml_parsing_policy_resolver_prefers_di_over_registry() -> None:
    class _DI:
        def factory_yaml_parsing_policy_plugin(self) -> _YAMLParsingPluginFromDI:
            return _YAMLParsingPluginFromDI()

    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_yaml_parsing_policy_plugin("yaml_parsing")
        try:
            plugin_registry.register_yaml_parsing_policy_plugin(
                "yaml_parsing",
                _YAMLParsingPluginFromRegistry,
            )
            plugin = defaults_module.resolve_yaml_parsing_policy_plugin(_DI())
        finally:
            if original is None:
                plugin_registry._yaml_parsing_policy_plugins.pop("yaml_parsing", None)
            else:
                plugin_registry.register_yaml_parsing_policy_plugin(
                    "yaml_parsing", original
                )

    assert plugin.load_yaml_file(Path("ignored.yml")) == {"source": "di"}


def test_yaml_parsing_policy_resolver_uses_registry_before_fallback() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_yaml_parsing_policy_plugin("yaml_parsing")
        try:
            plugin_registry.register_yaml_parsing_policy_plugin(
                "yaml_parsing",
                _YAMLParsingPluginFromRegistry,
            )
            plugin = defaults_module.resolve_yaml_parsing_policy_plugin(None)
        finally:
            if original is None:
                plugin_registry._yaml_parsing_policy_plugins.pop("yaml_parsing", None)
            else:
                plugin_registry.register_yaml_parsing_policy_plugin(
                    "yaml_parsing", original
                )

    assert plugin.load_yaml_file(Path("ignored.yml")) == {"source": "registry"}


def test_jinja_analysis_policy_resolver_prefers_di_over_registry() -> None:
    class _DI:
        def factory_jinja_analysis_policy_plugin(self) -> _JinjaAnalysisPluginFromDI:
            return _JinjaAnalysisPluginFromDI()

    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_jinja_analysis_policy_plugin("jinja_analysis")
        try:
            plugin_registry.register_jinja_analysis_policy_plugin(
                "jinja_analysis",
                _JinjaAnalysisPluginFromRegistry,
            )
            plugin = defaults_module.resolve_jinja_analysis_policy_plugin(_DI())
        finally:
            if original is None:
                plugin_registry._jinja_analysis_policy_plugins.pop(
                    "jinja_analysis", None
                )
            else:
                plugin_registry.register_jinja_analysis_policy_plugin(
                    "jinja_analysis", original
                )

    assert plugin.collect_undeclared_jinja_variables("{{ ignored }}") == {
        "from_di_jinja_plugin"
    }


def test_jinja_analysis_policy_resolver_uses_registry_before_fallback() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_jinja_analysis_policy_plugin("jinja_analysis")
        try:
            plugin_registry.register_jinja_analysis_policy_plugin(
                "jinja_analysis",
                _JinjaAnalysisPluginFromRegistry,
            )
            plugin = defaults_module.resolve_jinja_analysis_policy_plugin(None)
        finally:
            if original is None:
                plugin_registry._jinja_analysis_policy_plugins.pop(
                    "jinja_analysis", None
                )
            else:
                plugin_registry.register_jinja_analysis_policy_plugin(
                    "jinja_analysis", original
                )

    assert plugin.collect_undeclared_jinja_variables("{{ ignored }}") == {
        "from_registry_jinja_plugin"
    }


def test_task_line_parsing_raises_without_prepared_policy() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.task_line_parsing")
        with pytest.raises(
            ValueError, match="prepared_policy_bundle.task_line_parsing"
        ):
            module._extract_constrained_when_values({}, "x")


def test_task_line_parsing_prefers_prepared_policy_bundle() -> None:
    class _PreparedPolicy:
        @staticmethod
        def extract_constrained_when_values(_task: dict, _variable: str) -> list[str]:
            return ["prepared"]

    class _DI:
        scan_options = {
            "prepared_policy_bundle": {"task_line_parsing": _PreparedPolicy()}
        }

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.task_line_parsing")
        result = module._extract_constrained_when_values({}, "x", di=_DI())

    assert result == ["prepared"]


def test_task_line_parsing_constants_require_prepared_policy() -> None:
    class _Policy:
        TASK_INCLUDE_KEYS = {"include_test"}

    class _DI:
        scan_options = {"prepared_policy_bundle": {"task_line_parsing": _Policy()}}

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.task_line_parsing")

        with pytest.raises(
            ValueError, match="prepared_policy_bundle.task_line_parsing"
        ):
            list(module.TASK_INCLUDE_KEYS)

        result = module.get_task_include_keys(di=_DI())
        assert result == {"include_test"}


def test_task_line_parsing_templated_include_regex_requires_prepared_policy() -> None:
    import re as _re

    class _Policy:
        TEMPLATED_INCLUDE_RE = _re.compile(r"^test_pattern$")

    class _DI:
        scan_options = {"prepared_policy_bundle": {"task_line_parsing": _Policy()}}

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.task_line_parsing")

        with pytest.raises(
            ValueError, match="prepared_policy_bundle.task_line_parsing"
        ):
            module.TEMPLATED_INCLUDE_RE.match("test_pattern")

        pattern = module.get_templated_include_re(di=_DI())
        assert bool(pattern.match("test_pattern"))


def test_task_file_traversal_raises_without_prepared_policy() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.task_file_traversal")
        with pytest.raises(ValueError, match="prepared_policy_bundle.task_traversal"):
            module._iter_task_include_targets([])


def test_task_file_traversal_prefers_prepared_policy_bundle() -> None:
    class _PreparedPolicy:
        @staticmethod
        def iter_task_include_targets(_data: object) -> list[str]:
            return ["prepared.yml"]

    class _DI:
        scan_options = {"prepared_policy_bundle": {"task_traversal": _PreparedPolicy()}}

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.task_file_traversal")
        result = module._iter_task_include_targets([], di=_DI())

    assert result == ["prepared.yml"]


def test_task_annotation_parsing_raises_without_prepared_policy() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module(
            "prism.scanner_extract.task_annotation_parsing"
        )
        with pytest.raises(
            ValueError, match="prepared_policy_bundle.task_annotation_parsing"
        ):
            module._split_task_annotation_label("x")


def test_task_annotation_parsing_prefers_prepared_policy_bundle() -> None:
    class _PreparedPolicy:
        @staticmethod
        def split_task_annotation_label(text: str) -> tuple[str, str]:
            return "prepared", text

    class _DI:
        scan_options = {
            "prepared_policy_bundle": {"task_annotation_parsing": _PreparedPolicy()}
        }

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module(
            "prism.scanner_extract.task_annotation_parsing"
        )
        result = module._split_task_annotation_label("x", di=_DI())

    assert result == ("prepared", "x")


def test_variable_extractor_reads_prepared_policy_bundle(tmp_path: Path) -> None:
    role_path = tmp_path / "role"
    (role_path / "tasks").mkdir(parents=True)
    (role_path / "tasks" / "main.yml").write_text("- name: Example\n", encoding="utf-8")

    class _PolicyA:
        @staticmethod
        def collect_include_vars_files(**_kwargs):
            return [Path("a.yml")]

    class _PolicyB:
        @staticmethod
        def collect_include_vars_files(**_kwargs):
            return [Path("b.yml")]

    bundle: dict = {"variable_extractor": _PolicyA()}

    class _DI:
        scan_options = {"prepared_policy_bundle": bundle}

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.variable_extractor")
        first = module.collect_include_vars_files(str(role_path), di=_DI())
        bundle["variable_extractor"] = _PolicyB()
        second = module.collect_include_vars_files(str(role_path), di=_DI())

    assert [path.name for path in first] == ["a.yml"]
    assert [path.name for path in second] == ["b.yml"]


def test_variable_extractor_raises_without_prepared_policy() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.variable_extractor")
        with pytest.raises(
            ValueError, match="prepared_policy_bundle.variable_extractor"
        ):
            module.collect_include_vars_files("/nonexistent")


def test_task_catalog_assembly_raises_without_prepared_policy() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.task_catalog_assembly")
        with pytest.raises(
            ValueError, match="prepared_policy_bundle.task_line_parsing"
        ):
            module._detect_task_module({})


def test_task_catalog_assembly_uses_dynamic_task_include_keys(
    tmp_path: Path,
) -> None:
    role_root = tmp_path / "role"
    tasks_dir = role_root / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "main.yml").write_text(
        "- name: Include nested\n" "  include_a: nested.yml\n",
        encoding="utf-8",
    )
    (tasks_dir / "nested.yml").write_text(
        "- name: Nested task\n" "  debug:\n" "    msg: nested\n",
        encoding="utf-8",
    )

    class _PolicyA:
        TASK_INCLUDE_KEYS = {"include_a"}

        @staticmethod
        def detect_task_module(_task: dict) -> str | None:
            return "debug"

    class _PolicyB:
        TASK_INCLUDE_KEYS = {"include_b"}

        @staticmethod
        def detect_task_module(_task: dict) -> str | None:
            return "debug"

    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        catalog_module = importlib.import_module(
            "prism.scanner_extract.task_catalog_assembly"
        )

        def _make_di(task_line_policy):
            options: dict = {
                "prepared_policy_bundle": {
                    "task_line_parsing": task_line_policy,
                    "task_annotation_parsing": defaults_module.resolve_task_annotation_policy_plugin(
                        None
                    ),
                    "task_traversal": defaults_module.resolve_task_traversal_policy_plugin(
                        None
                    ),
                    "yaml_parsing": defaults_module.resolve_yaml_parsing_policy_plugin(
                        None
                    ),
                    "jinja_analysis": defaults_module.resolve_jinja_analysis_policy_plugin(
                        None
                    ),
                }
            }

            class _DI:
                scan_options = options

            return _DI()

        first, _ = catalog_module._collect_task_handler_catalog(
            str(role_root), di=_make_di(_PolicyA())
        )
        second, _ = catalog_module._collect_task_handler_catalog(
            str(role_root), di=_make_di(_PolicyB())
        )

    assert [entry["name"] for entry in first] == ["Include nested", "Nested task"]
    assert [entry["name"] for entry in second] == ["Include nested"]


def test_variable_discovery_uses_prepared_jinja_analysis_bundle(
    monkeypatch,
    tmp_path: Path,
) -> None:
    role_root = tmp_path / "role"
    tasks_dir = role_root / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "main.yml").write_text(
        "- name: Example task\n"
        "  ansible.builtin.debug:\n"
        "    msg: '{{ fallback_token }}'\n",
        encoding="utf-8",
    )

    calls: list[str] = []

    class _Plugin:
        @staticmethod
        def collect_undeclared_jinja_variables(text: str) -> set[str]:
            calls.append(text)
            return {"plugin_only_token"}

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module(
            "prism.scanner_plugins.ansible.variable_discovery"
        )
        names = module._collect_referenced_variable_names(
            role_root,
            exclude_paths=None,
            options={"prepared_policy_bundle": {"jinja_analysis": _Plugin()}},
        )

    assert calls
    assert "plugin_only_token" in names


def test_yaml_parsing_loader_uses_resolver_traversal_uses_prepared_bundle(
    monkeypatch,
    tmp_path: Path,
) -> None:
    yaml_file = tmp_path / "main.yml"
    yaml_file.write_text("k: v\n", encoding="utf-8")

    loader_calls: list[Path] = []
    traversal_calls: list[Path] = []

    class _LoaderPlugin:
        @staticmethod
        def load_yaml_file(path: Path) -> object:
            loader_calls.append(path)
            return {"loader": "yes"}

    class _TraversalPlugin:
        @staticmethod
        def load_yaml_file(path: Path) -> object:
            traversal_calls.append(path)
            return {"traversal": "yes"}

    class _DI:
        scan_options = {"prepared_policy_bundle": {"yaml_parsing": _TraversalPlugin()}}

    with _prefer_fsrc_prism_on_sys_path():
        loader_module = importlib.import_module("prism.scanner_io.loader")
        traversal_module = importlib.import_module(
            "prism.scanner_extract.task_file_traversal"
        )

        monkeypatch.setattr(
            loader_module,
            "_get_yaml_parsing_policy",
            lambda _di=None: _LoaderPlugin(),
        )

        loader_payload = loader_module.load_yaml_file(yaml_file)
        traversal_payload = traversal_module._load_yaml_file(yaml_file, di=_DI())

    assert loader_payload == {"loader": "yes"}
    assert traversal_payload == {"traversal": "yes"}
    assert loader_calls == [yaml_file]
    assert traversal_calls == [yaml_file]


def test_task_file_traversal_yaml_parsing_prefers_prepared_policy_bundle(
    tmp_path: Path,
) -> None:
    yaml_file = tmp_path / "main.yml"
    yaml_file.write_text("k: v\n", encoding="utf-8")

    class _PreparedPolicy:
        @staticmethod
        def load_yaml_file(path: Path) -> object:
            return {"prepared": path.name}

    class _DI:
        scan_options = {"prepared_policy_bundle": {"yaml_parsing": _PreparedPolicy()}}

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.task_file_traversal")
        payload = module._load_yaml_file(yaml_file, di=_DI())

    assert payload == {"prepared": "main.yml"}


def test_comment_doc_plugin_validation_raises_on_malformed_plugin_in_strict_mode() -> (
    None
):
    class _BadPlugin:
        pass

    class _DI:
        def factory_comment_driven_doc_plugin(self) -> _BadPlugin:
            return _BadPlugin()

    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        errors_module = importlib.import_module("prism.errors")

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            defaults_module.resolve_comment_driven_documentation_plugin(
                _DI(),
                strict_mode=True,
            )

    assert "malformed" in str(exc_info.value).lower()


def test_comment_doc_plugin_validation_falls_back_in_non_strict_mode() -> None:
    class _BadPlugin:
        pass

    class _DI:
        def factory_comment_driven_doc_plugin(self) -> _BadPlugin:
            return _BadPlugin()

    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin = defaults_module.resolve_comment_driven_documentation_plugin(
            _DI(),
            strict_mode=False,
        )

    assert callable(getattr(plugin, "extract_role_notes_from_comments", None))


def test_task_annotation_plugin_validation_raises_on_malformed_plugin_in_strict_mode() -> (
    None
):
    class _BadPlugin:
        pass

    class _DI:
        def factory_task_annotation_policy_plugin(self) -> _BadPlugin:
            return _BadPlugin()

    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        errors_module = importlib.import_module("prism.errors")

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            defaults_module.resolve_task_annotation_policy_plugin(
                _DI(),
                strict_mode=True,
            )

    assert "malformed" in str(exc_info.value).lower()


def test_task_annotation_plugin_validation_falls_back_in_non_strict_mode() -> None:
    class _BadPlugin:
        pass

    class _DI:
        def factory_task_annotation_policy_plugin(self) -> _BadPlugin:
            return _BadPlugin()

    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin = defaults_module.resolve_task_annotation_policy_plugin(
            _DI(),
            strict_mode=False,
        )

    assert plugin.split_task_annotation_label("note") == ("note", "note")


def test_task_line_plugin_validation_raises_on_malformed_plugin_in_strict_mode() -> (
    None
):
    class _MalformedTaskLinePlugin:
        @staticmethod
        def detect_task_module(_task: dict) -> str:
            return "debug"

    class _DI:
        def factory_task_line_parsing_policy_plugin(self) -> _MalformedTaskLinePlugin:
            return _MalformedTaskLinePlugin()

    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        errors_module = importlib.import_module("prism.errors")

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            defaults_module.resolve_task_line_parsing_policy_plugin(
                _DI(),
                strict_mode=True,
            )

    assert "malformed" in str(exc_info.value).lower()


def test_task_line_plugin_validation_falls_back_in_non_strict_mode() -> None:
    class _MalformedTaskLinePlugin:
        pass

    class _DI:
        def factory_task_line_parsing_policy_plugin(self) -> _MalformedTaskLinePlugin:
            return _MalformedTaskLinePlugin()

    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin = defaults_module.resolve_task_line_parsing_policy_plugin(
            _DI(),
            strict_mode=False,
        )

    assert "include_tasks" in plugin.TASK_INCLUDE_KEYS


def test_task_traversal_plugin_validation_raises_on_malformed_plugin_in_strict_mode() -> (
    None
):
    class _MalformedTaskTraversalPlugin:
        @staticmethod
        def iter_task_include_targets(_data: object) -> list[str]:
            return []

    class _DI:
        def factory_task_traversal_policy_plugin(self) -> _MalformedTaskTraversalPlugin:
            return _MalformedTaskTraversalPlugin()

    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        errors_module = importlib.import_module("prism.errors")

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            defaults_module.resolve_task_traversal_policy_plugin(
                _DI(),
                strict_mode=True,
            )

    assert "malformed" in str(exc_info.value).lower()


def test_task_traversal_plugin_validation_falls_back_in_non_strict_mode() -> None:
    class _MalformedTaskTraversalPlugin:
        pass

    class _DI:
        def factory_task_traversal_policy_plugin(self) -> _MalformedTaskTraversalPlugin:
            return _MalformedTaskTraversalPlugin()

    with _prefer_fsrc_prism_on_sys_path():
        defaults_module = importlib.import_module("prism.scanner_plugins.defaults")
        plugin = defaults_module.resolve_task_traversal_policy_plugin(
            _DI(),
            strict_mode=False,
        )

    assert plugin.iter_task_include_targets([{"include_tasks": "main.yml"}]) == [
        "main.yml"
    ]


def test_task_extract_adapters_marker_prefix_bundle_only_and_fail_closed(
    monkeypatch,
) -> None:
    captured_prefixes: list[str] = []
    captured_catalog_prefixes: list[str] = []

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_core.task_extract_adapters")

        def _capture_extract(
            _raw_lines,
            *,
            marker_prefix: str = "prism",
            include_task_index: bool = False,
            di=None,
        ):
            del include_task_index, di
            captured_prefixes.append(marker_prefix)
            return [], {}

        monkeypatch.setattr(
            module, "_extract_task_annotations_for_file", _capture_extract
        )

        def _capture_catalog(
            _role_path,
            exclude_paths=None,
            marker_prefix: str = "prism",
            *,
            di=None,
        ):
            del exclude_paths, di
            captured_catalog_prefixes.append(marker_prefix)
            return [], []

        monkeypatch.setattr(module, "_collect_task_handler_catalog", _capture_catalog)

        class _CanonicalContextDI:
            scan_options = {
                "comment_doc_marker_prefix": "canonical.value",
                "prepared_policy_bundle": {
                    "comment_doc_marker_prefix": "canonical.value",
                },
                "policy_context": {
                    "comment_doc": {
                        "marker": {"prefix": "nested.ignore"},
                    },
                },
            }

        module.extract_task_annotations_for_file(
            ["# comment"], di=_CanonicalContextDI()
        )
        assert captured_prefixes[-1] == "canonical.value"
        module.collect_task_handler_catalog("/tmp/role", di=_CanonicalContextDI())
        assert captured_catalog_prefixes[-1] == "canonical.value"

        class _NoBundleDI:
            scan_options = {
                "policy_context": {
                    "comment_doc_marker_prefix": "flat.alias",
                    "comment_doc": {
                        "marker_prefix": "nested.alias",
                    },
                }
            }

        with pytest.raises(ValueError, match="prepared_policy_bundle"):
            module.extract_task_annotations_for_file(["# comment"], di=_NoBundleDI())


def test_resolve_marker_prefix_reads_from_prepared_policy_bundle() -> None:
    """_resolve_marker_prefix reads only from prepared_policy_bundle (fail-closed)."""
    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_core.task_extract_adapters")

        class _BundleDI:
            scan_options = {
                "comment_doc_marker_prefix": "direct.scan.option.ignored",
                "prepared_policy_bundle": {
                    "comment_doc_marker_prefix": "bundle.value",
                },
            }

        result = module._resolve_marker_prefix(_BundleDI())
        assert result == "bundle.value"

        class _NoBundleDI:
            scan_options = {
                "comment_doc_marker_prefix": "direct.option.ignored",
            }

        with pytest.raises(ValueError, match="prepared_policy_bundle"):
            module._resolve_marker_prefix(_NoBundleDI())

        class _EmptyBundleDI:
            scan_options = {
                "prepared_policy_bundle": {},
            }

        with pytest.raises(ValueError, match="comment_doc_marker_prefix"):
            module._resolve_marker_prefix(_EmptyBundleDI())


def test_ensure_prepared_policy_bundle_sets_marker_prefix() -> None:
    """ensure_prepared_policy_bundle projects comment_doc_marker_prefix into the bundle."""
    with _prefer_fsrc_prism_on_sys_path():
        bundle_resolver = importlib.import_module(
            "prism.scanner_plugins.bundle_resolver"
        )
        di_module = importlib.import_module("prism.scanner_core.di")

        options: dict = {
            "role_path": "/tmp/role",
            "comment_doc_marker_prefix": "ingress.marker",
        }
        container = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options=options,
        )
        bundle = bundle_resolver.ensure_prepared_policy_bundle(
            scan_options=options, di=container
        )
        assert bundle["comment_doc_marker_prefix"] == "ingress.marker"

        options2: dict = {
            "role_path": "/tmp/role",
        }
        container2 = di_module.DIContainer(
            role_path="/tmp/role",
            scan_options=options2,
        )
        bundle2 = bundle_resolver.ensure_prepared_policy_bundle(
            scan_options=options2, di=container2
        )
        marker_utils = importlib.import_module(
            "prism.scanner_plugins.parsers.comment_doc.marker_utils"
        )
        assert (
            bundle2["comment_doc_marker_prefix"]
            == marker_utils.DEFAULT_DOC_MARKER_PREFIX
        )


def test_scan_request_ignores_deprecated_nested_marker_prefix_alias() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        scan_request = importlib.import_module("prism.scanner_core.scan_request")

        options = scan_request.build_run_scan_options_canonical(
            role_path="/tmp/role",
            role_name_override=None,
            readme_config_path=None,
            include_vars_main=True,
            exclude_path_patterns=None,
            detailed_catalog=False,
            include_task_parameters=True,
            include_task_runbooks=True,
            inline_task_runbooks=True,
            include_collection_checks=True,
            keep_unknown_style_sections=True,
            adopt_heading_mode=None,
            vars_seed_paths=None,
            style_readme_path=None,
            style_source_path=None,
            style_guide_skeleton=False,
            compare_role_path=None,
            fail_on_unconstrained_dynamic_includes=None,
            fail_on_yaml_like_task_annotations=None,
            ignore_unresolved_internal_underscore_references=None,
            policy_context={
                "comment_doc": {
                    "marker_prefix": "legacy.nested",
                }
            },
        )

    assert "comment_doc_marker_prefix" not in options
    assert options.get("scan_policy_warnings") is None


def test_build_run_scan_options_canonical_does_not_project_marker_prefix_from_policy_context() -> (
    None
):
    """After WB, scan_request no longer owns marker prefix extraction.

    The bundle resolver (scanner_plugins layer) now handles policy_context
    navigation for comment_doc.marker.prefix.
    """
    with _prefer_fsrc_prism_on_sys_path():
        scan_request = importlib.import_module("prism.scanner_core.scan_request")

        options = scan_request.build_run_scan_options_canonical(
            role_path="/tmp/role",
            role_name_override=None,
            readme_config_path=None,
            include_vars_main=True,
            exclude_path_patterns=None,
            detailed_catalog=False,
            include_task_parameters=True,
            include_task_runbooks=True,
            inline_task_runbooks=True,
            include_collection_checks=True,
            keep_unknown_style_sections=True,
            adopt_heading_mode=None,
            vars_seed_paths=None,
            style_readme_path=None,
            style_source_path=None,
            style_guide_skeleton=False,
            compare_role_path=None,
            fail_on_unconstrained_dynamic_includes=None,
            fail_on_yaml_like_task_annotations=None,
            ignore_unresolved_internal_underscore_references=None,
            policy_context={
                "comment_doc": {
                    "marker": {"prefix": "canonical.marker"},
                }
            },
        )

    assert "comment_doc_marker_prefix" not in options
    assert options.get("scan_policy_warnings") is None


def test_bundle_resolver_projects_marker_prefix_from_policy_context() -> None:
    """The bundle resolver navigates policy_context.comment_doc.marker.prefix."""
    with _prefer_fsrc_prism_on_sys_path():
        di_mod = importlib.import_module("prism.scanner_core.di")
        bundle_resolver = importlib.import_module(
            "prism.scanner_plugins.bundle_resolver"
        )

        scan_options: dict = {
            "role_path": "/tmp/role",
            "policy_context": {
                "comment_doc": {
                    "marker": {"prefix": "canonical.marker"},
                },
            },
        }
        container = di_mod.DIContainer(role_path="/tmp/role", scan_options=scan_options)
        bundle = bundle_resolver.ensure_prepared_policy_bundle(
            scan_options=scan_options, di=container
        )

    assert bundle["comment_doc_marker_prefix"] == "canonical.marker"


def test_run_scan_ignores_flat_marker_alias_in_policy_context() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        scan_request = importlib.import_module("prism.scanner_core.scan_request")
        options = scan_request.build_run_scan_options_canonical(
            role_path="/tmp/role",
            role_name_override=None,
            readme_config_path=None,
            include_vars_main=True,
            exclude_path_patterns=None,
            detailed_catalog=False,
            include_task_parameters=True,
            include_task_runbooks=True,
            inline_task_runbooks=True,
            include_collection_checks=True,
            keep_unknown_style_sections=True,
            adopt_heading_mode=None,
            vars_seed_paths=None,
            style_readme_path=None,
            style_source_path=None,
            style_guide_skeleton=False,
            compare_role_path=None,
            fail_on_unconstrained_dynamic_includes=None,
            fail_on_yaml_like_task_annotations=None,
            ignore_unresolved_internal_underscore_references=None,
            policy_context={"comment_doc_marker_prefix": "legacy-flat"},
        )

    warnings = options.get("scan_policy_warnings")
    if warnings:
        deprecated_alias_warnings = [
            w
            for w in warnings
            if isinstance(w, dict)
            and w.get("code") == "deprecated_policy_context_alias"
        ]
        assert deprecated_alias_warnings == []


def test_build_run_scan_options_canonical_preserves_alias_keys_without_resolving() -> (
    None
):
    with _prefer_fsrc_prism_on_sys_path():
        scan_request = importlib.import_module("prism.scanner_core.scan_request")
        options = scan_request.build_run_scan_options_canonical(
            role_path="/tmp/role",
            role_name_override=None,
            readme_config_path=None,
            include_vars_main=True,
            exclude_path_patterns=None,
            detailed_catalog=False,
            include_task_parameters=True,
            include_task_runbooks=True,
            inline_task_runbooks=True,
            include_collection_checks=True,
            keep_unknown_style_sections=True,
            adopt_heading_mode=None,
            vars_seed_paths=None,
            style_readme_path=None,
            style_source_path=None,
            style_guide_skeleton=False,
            compare_role_path=None,
            fail_on_unconstrained_dynamic_includes=None,
            fail_on_yaml_like_task_annotations=None,
            ignore_unresolved_internal_underscore_references=None,
            policy_context={
                "comment_doc_marker_prefix": "legacy-flat",
                "comment_doc": {
                    "marker_prefix": "legacy-nested",
                },
            },
        )

    assert "comment_doc_marker_prefix" not in options
    assert options.get("scan_policy_warnings") is None
    policy_context = options["policy_context"]
    assert isinstance(policy_context, dict)
    comment_doc = policy_context["comment_doc"]
    assert isinstance(comment_doc, dict)
    assert comment_doc.get("marker_prefix") == "legacy-nested"


@pytest.mark.parametrize(
    ("include_underscore_prefixed_references", "expected_ignore_flag"),
    [(True, False), (False, True)],
)
def test_scan_request_passes_through_raw_underscore_reference_value_without_policy_resolution(
    include_underscore_prefixed_references: bool,
    expected_ignore_flag: bool,
) -> None:
    """scan_request no longer interprets policy_context for underscore refs.

    The raw caller value (None here) should pass through unchanged.
    """
    with _prefer_fsrc_prism_on_sys_path():
        scan_request = importlib.import_module("prism.scanner_core.scan_request")

        options = scan_request.build_run_scan_options_canonical(
            role_path="/tmp/role",
            role_name_override=None,
            readme_config_path=None,
            include_vars_main=True,
            exclude_path_patterns=None,
            detailed_catalog=False,
            include_task_parameters=True,
            include_task_runbooks=True,
            inline_task_runbooks=True,
            include_collection_checks=True,
            keep_unknown_style_sections=True,
            adopt_heading_mode=None,
            vars_seed_paths=None,
            style_readme_path=None,
            style_source_path=None,
            style_guide_skeleton=False,
            compare_role_path=None,
            fail_on_unconstrained_dynamic_includes=None,
            fail_on_yaml_like_task_annotations=None,
            ignore_unresolved_internal_underscore_references=None,
            policy_context={
                "include_underscore_prefixed_references": (
                    include_underscore_prefixed_references
                )
            },
        )

    assert options["ignore_unresolved_internal_underscore_references"] is None


@pytest.mark.parametrize(
    ("include_underscore_prefixed_references", "expected_ignore_flag"),
    [(True, False), (False, True)],
)
def test_bundle_resolver_resolves_underscore_reference_policy_from_policy_context(
    include_underscore_prefixed_references: bool,
    expected_ignore_flag: bool,
) -> None:
    """bundle_resolver interprets policy_context.include_underscore_prefixed_references."""
    with _prefer_fsrc_prism_on_sys_path():
        scan_request = importlib.import_module("prism.scanner_core.scan_request")
        bundle_resolver = importlib.import_module(
            "prism.scanner_plugins.bundle_resolver"
        )

        options = scan_request.build_run_scan_options_canonical(
            role_path="/tmp/role",
            role_name_override=None,
            readme_config_path=None,
            include_vars_main=True,
            exclude_path_patterns=None,
            detailed_catalog=False,
            include_task_parameters=True,
            include_task_runbooks=True,
            inline_task_runbooks=True,
            include_collection_checks=True,
            keep_unknown_style_sections=True,
            adopt_heading_mode=None,
            vars_seed_paths=None,
            style_readme_path=None,
            style_source_path=None,
            style_guide_skeleton=False,
            compare_role_path=None,
            fail_on_unconstrained_dynamic_includes=None,
            fail_on_yaml_like_task_annotations=None,
            ignore_unresolved_internal_underscore_references=None,
            policy_context={
                "include_underscore_prefixed_references": (
                    include_underscore_prefixed_references
                )
            },
        )

        bundle = bundle_resolver.ensure_prepared_policy_bundle(
            scan_options=options, di=None
        )

    assert (
        bundle["ignore_unresolved_internal_underscore_references"]
        is expected_ignore_flag
    )
    assert (
        options["ignore_unresolved_internal_underscore_references"]
        is expected_ignore_flag
    )


def test_build_run_scan_options_canonical_ignores_deprecated_marker_aliases() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        scan_request = importlib.import_module("prism.scanner_core.scan_request")

        options = scan_request.build_run_scan_options_canonical(
            role_path="/tmp/role",
            role_name_override=None,
            readme_config_path=None,
            include_vars_main=True,
            exclude_path_patterns=None,
            detailed_catalog=False,
            include_task_parameters=True,
            include_task_runbooks=True,
            inline_task_runbooks=True,
            include_collection_checks=True,
            keep_unknown_style_sections=True,
            adopt_heading_mode=None,
            vars_seed_paths=None,
            style_readme_path=None,
            style_source_path=None,
            style_guide_skeleton=False,
            compare_role_path=None,
            fail_on_unconstrained_dynamic_includes=None,
            fail_on_yaml_like_task_annotations=None,
            ignore_unresolved_internal_underscore_references=None,
            policy_context={
                "comment_doc": {
                    "marker_prefix": "legacy.nested",
                }
            },
        )

    assert "comment_doc_marker_prefix" not in options
    assert options.get("scan_policy_warnings") is None
