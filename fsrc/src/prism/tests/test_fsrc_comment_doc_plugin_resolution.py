"""Focused tests for comment-driven documentation plugin resolution in fsrc."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
FSRC_SOURCE_ROOT = PROJECT_ROOT / "fsrc" / "src"


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
        scanner_extract = importlib.import_module("prism.scanner_extract")
        result = scanner_extract.extract_role_notes_from_comments(
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
        scanner_extract = importlib.import_module("prism.scanner_extract")
        result = scanner_extract.extract_role_notes_from_comments(str(role_path))

    assert "check rollback path" in result["warnings"]
    assert "verify service dependencies" in result["notes"]
    assert "fragment defaults note" in result["notes"]


def test_extract_role_notes_prefers_di_over_registry_default() -> None:
    plugin = _RecordingCommentDocPlugin()
    di = _DIWithCommentDocFactory(plugin)

    with _prefer_fsrc_prism_on_sys_path():
        scanner_extract = importlib.import_module("prism.scanner_extract")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_comment_driven_doc_plugin("default")
        try:
            plugin_registry.register_comment_driven_doc_plugin(
                "default",
                _RegistryOnlyCommentDocPlugin,
            )
            result = scanner_extract.extract_role_notes_from_comments(
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
        scanner_extract = importlib.import_module("prism.scanner_extract")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        original = plugin_registry.get_comment_driven_doc_plugin("default")
        try:
            plugin_registry.register_comment_driven_doc_plugin(
                "default",
                _RegistryOnlyCommentDocPlugin,
            )
            result = scanner_extract.extract_role_notes_from_comments(
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
        scanner_extract = importlib.import_module("prism.scanner_extract")
        plugin_registry = importlib.import_module(
            "prism.scanner_plugins.registry"
        ).plugin_registry
        had_default = "default" in plugin_registry.list_comment_driven_doc_plugins()
        original = plugin_registry.get_comment_driven_doc_plugin("default")
        try:
            plugin_registry._comment_driven_doc_plugins.pop("default", None)
            result = scanner_extract.extract_role_notes_from_comments(str(role_path))
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


def test_task_line_parsing_calls_resolver_each_time(monkeypatch) -> None:
    class _PolicyA:
        @staticmethod
        def extract_constrained_when_values(_task: dict, _variable: str) -> list[str]:
            return ["a"]

    class _PolicyB:
        @staticmethod
        def extract_constrained_when_values(_task: dict, _variable: str) -> list[str]:
            return ["b"]

    state = {"value": "a"}

    def _resolver(_di=None):
        return _PolicyA() if state["value"] == "a" else _PolicyB()

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.task_line_parsing")
        monkeypatch.setattr(
            module, "resolve_task_line_parsing_policy_plugin", _resolver
        )
        first = module._extract_constrained_when_values({}, "x")
        state["value"] = "b"
        second = module._extract_constrained_when_values({}, "x")

    assert first == ["a"]
    assert second == ["b"]


def test_task_line_parsing_prefers_prepared_policy_bundle(monkeypatch) -> None:
    class _PreparedPolicy:
        @staticmethod
        def extract_constrained_when_values(_task: dict, _variable: str) -> list[str]:
            return ["prepared"]

    class _DI:
        _scan_options = {
            "prepared_policy_bundle": {"task_line_parsing": _PreparedPolicy()}
        }

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.task_line_parsing")
        monkeypatch.setattr(
            module,
            "resolve_task_line_parsing_policy_plugin",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("task-line resolver should not be called")
            ),
        )

        result = module._extract_constrained_when_values({}, "x", di=_DI())

    assert result == ["prepared"]


def test_task_line_parsing_policy_backed_constants_are_dynamic(monkeypatch) -> None:
    class _PolicyA:
        TASK_INCLUDE_KEYS = {"include_a"}

    class _PolicyB:
        TASK_INCLUDE_KEYS = {"include_b"}

    state = {"value": "a"}

    def _resolver(_di=None):
        return _PolicyA() if state["value"] == "a" else _PolicyB()

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.task_line_parsing")
        monkeypatch.setattr(
            module, "resolve_task_line_parsing_policy_plugin", _resolver
        )
        first = sorted(module.TASK_INCLUDE_KEYS)
        state["value"] = "b"
        second = sorted(module.TASK_INCLUDE_KEYS)

    assert first == ["include_a"]
    assert second == ["include_b"]


def test_task_line_parsing_templated_include_regex_is_dynamic(monkeypatch) -> None:
    class _PolicyA:
        TEMPLATED_INCLUDE_RE = __import__("re").compile(r"^a$")

    class _PolicyB:
        TEMPLATED_INCLUDE_RE = __import__("re").compile(r"^b$")

    state = {"value": "a"}

    def _resolver(_di=None):
        return _PolicyA() if state["value"] == "a" else _PolicyB()

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.task_line_parsing")
        monkeypatch.setattr(
            module, "resolve_task_line_parsing_policy_plugin", _resolver
        )
        first = bool(module.TEMPLATED_INCLUDE_RE.match("a"))
        state["value"] = "b"
        second = bool(module.TEMPLATED_INCLUDE_RE.match("b"))

    assert first is True
    assert second is True


def test_task_file_traversal_calls_resolver_each_time(monkeypatch) -> None:
    class _PolicyA:
        @staticmethod
        def iter_task_include_targets(_data: object) -> list[str]:
            return ["a.yml"]

    class _PolicyB:
        @staticmethod
        def iter_task_include_targets(_data: object) -> list[str]:
            return ["b.yml"]

    state = {"value": "a"}

    def _resolver(_di=None):
        return _PolicyA() if state["value"] == "a" else _PolicyB()

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.task_file_traversal")
        monkeypatch.setattr(module, "resolve_task_traversal_policy_plugin", _resolver)
        first = module._iter_task_include_targets([])
        state["value"] = "b"
        second = module._iter_task_include_targets([])

    assert first == ["a.yml"]
    assert second == ["b.yml"]


def test_task_file_traversal_prefers_prepared_policy_bundle(monkeypatch) -> None:
    class _PreparedPolicy:
        @staticmethod
        def iter_task_include_targets(_data: object) -> list[str]:
            return ["prepared.yml"]

    class _DI:
        _scan_options = {
            "prepared_policy_bundle": {"task_traversal": _PreparedPolicy()}
        }

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.task_file_traversal")
        monkeypatch.setattr(
            module,
            "resolve_task_traversal_policy_plugin",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("task-traversal resolver should not be called")
            ),
        )

        result = module._iter_task_include_targets([], di=_DI())

    assert result == ["prepared.yml"]


def test_task_annotation_parsing_calls_resolver_each_time(monkeypatch) -> None:
    class _PolicyA:
        @staticmethod
        def split_task_annotation_label(text: str) -> tuple[str, str]:
            return "a", text

    class _PolicyB:
        @staticmethod
        def split_task_annotation_label(text: str) -> tuple[str, str]:
            return "b", text

    state = {"value": "a"}

    def _resolver(_di=None):
        return _PolicyA() if state["value"] == "a" else _PolicyB()

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module(
            "prism.scanner_extract.task_annotation_parsing"
        )
        monkeypatch.setattr(module, "resolve_task_annotation_policy_plugin", _resolver)
        first = module._split_task_annotation_label("x")
        state["value"] = "b"
        second = module._split_task_annotation_label("x")

    assert first == ("a", "x")
    assert second == ("b", "x")


def test_task_annotation_parsing_prefers_prepared_policy_bundle(
    monkeypatch,
) -> None:
    class _PreparedPolicy:
        @staticmethod
        def split_task_annotation_label(text: str) -> tuple[str, str]:
            return "prepared", text

    class _DI:
        _scan_options = {
            "prepared_policy_bundle": {"task_annotation_parsing": _PreparedPolicy()}
        }

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module(
            "prism.scanner_extract.task_annotation_parsing"
        )
        monkeypatch.setattr(
            module,
            "resolve_task_annotation_policy_plugin",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("task-annotation resolver should not be called")
            ),
        )

        result = module._split_task_annotation_label("x", di=_DI())

    assert result == ("prepared", "x")


def test_variable_extractor_calls_resolver_each_time(
    monkeypatch, tmp_path: Path
) -> None:
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

    state = {"value": "a"}

    def _resolver(_di=None):
        return _PolicyA() if state["value"] == "a" else _PolicyB()

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.variable_extractor")
        monkeypatch.setattr(
            module, "resolve_variable_extractor_policy_plugin", _resolver
        )
        first = module.collect_include_vars_files(str(role_path))
        state["value"] = "b"
        second = module.collect_include_vars_files(str(role_path))

    assert [path.name for path in first] == ["a.yml"]
    assert [path.name for path in second] == ["b.yml"]


def test_task_catalog_assembly_calls_resolver_each_time(monkeypatch) -> None:
    class _PolicyA:
        @staticmethod
        def detect_task_module(_task: dict) -> str | None:
            return "a.module"

    class _PolicyB:
        @staticmethod
        def detect_task_module(_task: dict) -> str | None:
            return "b.module"

    state = {"value": "a"}

    def _resolver(_di=None):
        return _PolicyA() if state["value"] == "a" else _PolicyB()

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.task_catalog_assembly")
        monkeypatch.setattr(
            module, "resolve_task_line_parsing_policy_plugin", _resolver
        )
        first = module._detect_task_module({})
        state["value"] = "b"
        second = module._detect_task_module({})

    assert first == "a.module"
    assert second == "b.module"


def test_task_catalog_assembly_uses_dynamic_task_include_keys(
    monkeypatch, tmp_path: Path
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

    state = {"value": "a"}

    def _resolver(_di=None):
        return _PolicyA() if state["value"] == "a" else _PolicyB()

    with _prefer_fsrc_prism_on_sys_path():
        catalog_module = importlib.import_module(
            "prism.scanner_extract.task_catalog_assembly"
        )
        task_line_module = importlib.import_module(
            "prism.scanner_extract.task_line_parsing"
        )
        monkeypatch.setattr(
            catalog_module,
            "resolve_task_line_parsing_policy_plugin",
            _resolver,
        )
        monkeypatch.setattr(
            task_line_module,
            "resolve_task_line_parsing_policy_plugin",
            _resolver,
        )
        first, _ = catalog_module._collect_task_handler_catalog(str(role_root))
        state["value"] = "b"
        second, _ = catalog_module._collect_task_handler_catalog(str(role_root))

    assert [entry["name"] for entry in first] == ["Include nested", "Nested task"]
    assert [entry["name"] for entry in second] == ["Include nested"]


def test_extract_role_features_threads_optional_di_into_helper_path(
    monkeypatch, tmp_path: Path
) -> None:
    role_root = tmp_path / "role"
    tasks_dir = role_root / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "main.yml").write_text(
        "- name: Example task\n" "  ansible.builtin.debug:\n" "    msg: hi\n",
        encoding="utf-8",
    )

    di_token = object()
    detect_di_calls: list[object | None] = []
    annotation_di_calls: list[object | None] = []

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.task_catalog_assembly")

        def _detect_task_module_with_di(
            _task: dict,
            *,
            di: object | None = None,
        ) -> str:
            detect_di_calls.append(di)
            return "ansible.builtin.debug"

        def _extract_task_annotations_with_di(
            _lines: list[str],
            marker_prefix: str = "prism",
            include_task_index: bool = False,
            *,
            di: object | None = None,
        ) -> tuple[list[dict[str, object]], dict[str, list[dict[str, object]]]]:
            del marker_prefix, include_task_index
            annotation_di_calls.append(di)
            return [], {}

        monkeypatch.setattr(module, "_detect_task_module", _detect_task_module_with_di)
        monkeypatch.setattr(
            module.tap,
            "_extract_task_annotations_for_file",
            _extract_task_annotations_with_di,
        )

        features = module.extract_role_features(str(role_root), di=di_token)

    assert features["tasks_scanned"] == 1
    assert detect_di_calls == [di_token]
    assert annotation_di_calls == [di_token]


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
        module = importlib.import_module("prism.scanner_core.variable_discovery")
        monkeypatch.setattr(
            module,
            "scan_request",
            type(
                "_ScanRequest",
                (),
                {
                    "ensure_prepared_policy_bundle": staticmethod(
                        lambda *, scan_options, di: scan_options.setdefault(
                            "prepared_policy_bundle",
                            {"jinja_analysis": _Plugin()},
                        )
                    )
                },
            ),
            raising=False,
        )
        names = module._collect_referenced_variable_names(
            role_root,
            exclude_paths=None,
            options={},
        )

    assert calls
    assert "plugin_only_token" in names


def test_yaml_parsing_policy_resolver_used_in_loader_and_task_traversal(
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

    with _prefer_fsrc_prism_on_sys_path():
        loader_module = importlib.import_module("prism.scanner_io.loader")
        traversal_module = importlib.import_module(
            "prism.scanner_extract.task_file_traversal"
        )

        monkeypatch.setattr(
            loader_module,
            "resolve_yaml_parsing_policy_plugin",
            lambda _di=None: _LoaderPlugin(),
        )
        monkeypatch.setattr(
            traversal_module,
            "resolve_yaml_parsing_policy_plugin",
            lambda _di=None: _TraversalPlugin(),
        )

        loader_payload = loader_module.load_yaml_file(yaml_file)
        traversal_payload = traversal_module._load_yaml_file(yaml_file)

    assert loader_payload == {"loader": "yes"}
    assert traversal_payload == {"traversal": "yes"}
    assert loader_calls == [yaml_file]
    assert traversal_calls == [yaml_file]


def test_task_file_traversal_yaml_parsing_prefers_prepared_policy_bundle(
    monkeypatch,
    tmp_path: Path,
) -> None:
    yaml_file = tmp_path / "main.yml"
    yaml_file.write_text("k: v\n", encoding="utf-8")

    class _PreparedPolicy:
        @staticmethod
        def load_yaml_file(path: Path) -> object:
            return {"prepared": path.name}

    class _DI:
        _scan_options = {"prepared_policy_bundle": {"yaml_parsing": _PreparedPolicy()}}

    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_extract.task_file_traversal")
        monkeypatch.setattr(
            module,
            "resolve_yaml_parsing_policy_plugin",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("yaml-parsing resolver should not be called")
            ),
        )

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


def test_task_extract_adapters_resolve_marker_prefix_from_policy_context(
    monkeypatch,
) -> None:
    captured_prefixes: list[str] = []

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

        class _CanonicalContextDI:
            _scan_options = {
                "policy_context": {
                    "comment_doc": {
                        "marker": {"prefix": "team.docs"},
                    }
                }
            }

        module.extract_task_annotations_for_file(
            ["# comment"], di=_CanonicalContextDI()
        )
        assert captured_prefixes[-1] == "team.docs"


def test_task_extract_adapters_marker_prefix_precedence_and_canonical_boundary(
    monkeypatch,
) -> None:
    captured_prefixes: list[str] = []

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

        class _CanonicalContextDI:
            _scan_options = {
                "policy_context": {
                    "comment_doc": {
                        "marker": {"prefix": "canonical.value"},
                    },
                }
            }

        module.extract_task_annotations_for_file(
            ["# comment"], di=_CanonicalContextDI()
        )
        assert captured_prefixes[-1] == "canonical.value"

        module.extract_task_annotations_for_file(
            ["# comment"],
            marker_prefix="explicit.value",
            di=_CanonicalContextDI(),
        )
        assert captured_prefixes[-1] == "explicit.value"

        class _LegacyAliasOnlyDI:
            _scan_options = {
                "policy_context": {
                    "comment_doc_marker_prefix": "flat.alias",
                    "comment_doc": {
                        "marker_prefix": "nested.alias",
                    },
                }
            }

        module.extract_task_annotations_for_file(["# comment"], di=_LegacyAliasOnlyDI())
        assert captured_prefixes[-1] == module.DEFAULT_DOC_MARKER_PREFIX


def test_scan_request_normalizes_comment_doc_marker_alias_and_emits_warning() -> None:
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

    assert (
        options["policy_context"]["comment_doc"]["marker"]["prefix"] == "legacy.nested"
    )
    warnings = options.get("scan_policy_warnings")
    assert isinstance(warnings, list)
    assert warnings
    assert warnings[0]["code"] == "deprecated_policy_context_alias"
    assert warnings[0]["detail"] == {
        "alias_key": "policy_context.comment_doc.marker_prefix"
    }


def test_run_scan_surfaces_marker_alias_warning_in_scan_policy_warnings(
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
        payload = api_module.run_scan(
            str(role_path),
            include_vars_main=True,
            policy_context={"comment_doc_marker_prefix": "legacy-flat"},
        )

    warnings = payload["metadata"].get("scan_policy_warnings")
    assert isinstance(warnings, list)
    deprecated_alias_warnings = [
        warning
        for warning in warnings
        if isinstance(warning, dict)
        and warning.get("code") == "deprecated_policy_context_alias"
        and warning.get("detail")
        == {"alias_key": "policy_context.comment_doc_marker_prefix"}
    ]
    assert deprecated_alias_warnings == [
        {
            "code": "deprecated_policy_context_alias",
            "message": "Deprecated marker-prefix policy alias used.",
            "detail": {"alias_key": "policy_context.comment_doc_marker_prefix"},
        }
    ]


def test_build_run_scan_options_canonical_policy_context_strips_marker_alias_keys() -> (
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

    policy_context = options["policy_context"]
    assert isinstance(policy_context, dict)
    assert "comment_doc_marker_prefix" not in policy_context
    comment_doc = policy_context["comment_doc"]
    assert isinstance(comment_doc, dict)
    assert "marker_prefix" not in comment_doc
    assert comment_doc["marker"] == {"prefix": "legacy-nested"}


@pytest.mark.parametrize(
    ("include_underscore_prefixed_references", "expected_ignore_flag"),
    [(True, False), (False, True)],
)
def test_scan_request_normalizes_underscore_reference_policy_into_canonical_ignore_flag(
    include_underscore_prefixed_references: bool,
    expected_ignore_flag: bool,
) -> None:
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

    assert (
        options["ignore_unresolved_internal_underscore_references"]
        is expected_ignore_flag
    )
