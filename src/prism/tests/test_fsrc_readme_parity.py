"""Focused parity checks for fsrc README style parsing and rendering foundations."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import jinja2


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_LANE_ROOT = PROJECT_ROOT / "src"
FSRC_LANE_ROOT = PROJECT_ROOT / "src"


@contextmanager
def _prefer_prism_lane(lane_root: Path) -> Iterator[None]:
    original_path = list(sys.path)
    original_modules = {
        key: value
        for key, value in sys.modules.items()
        if key == "prism" or key.startswith("prism.")
    }
    lane_roots = {SRC_LANE_ROOT.resolve(), FSRC_LANE_ROOT.resolve()}

    try:
        sys.path[:] = [str(lane_root.resolve())] + [
            path for path in original_path if Path(path).resolve() not in lane_roots
        ]
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


def _render_with_lane(
    lane_root: Path,
    *,
    output: str,
    role_name: str,
    description: str,
    variables: dict[str, Any],
    metadata: dict[str, Any],
    template_path: str,
) -> str:
    with _prefer_prism_lane(lane_root):
        render_module = importlib.import_module("prism.scanner_readme.render")
        rendered = render_module.render_readme(
            output=output,
            role_name=role_name,
            description=description,
            variables=variables,
            requirements=[],
            default_filters=[],
            template=template_path,
            metadata=metadata,
            write=False,
        )
    return str(rendered)


def test_w3_t03_style_parser_foundational_parity(tmp_path: Path) -> None:
    style_path = tmp_path / "STYLE_GUIDE.md"
    style_path.write_text(
        """Role style
==========

Role Variables
--------------

Intro text for variables.

| Name | Description |
| --- | --- |
| demo_var | Demo variable |
""",
        encoding="utf-8",
    )

    with _prefer_prism_lane(FSRC_LANE_ROOT):
        style_module = importlib.import_module("prism.scanner_readme.style")
        fsrc_parsed = style_module.parse_style_readme(str(style_path))

    assert isinstance(fsrc_parsed["title_style"], str)
    assert isinstance(fsrc_parsed["section_style"], str)
    assert isinstance(fsrc_parsed["section_level"], int)
    assert isinstance(fsrc_parsed["variable_style"], str)
    assert fsrc_parsed.get("variable_intro") == "Intro text for variables."
    section_rows = [
        (section["id"], section["title"], section["normalized_title"])
        for section in fsrc_parsed["sections"]
    ]
    assert section_rows
    assert any(title == "Role Variables" for _, title, _ in section_rows)


def test_w3_t03_render_readme_template_and_style_foundational_parity(
    tmp_path: Path,
) -> None:
    template_path = tmp_path / "README.md.j2"
    template_path.write_text(
        """# {{ role_name }}

{{ description }}

Variables: {{ variables | length }}
""",
        encoding="utf-8",
    )

    style_path = tmp_path / "STYLE_GUIDE.md"
    style_path.write_text(
        """Guide title
===========

Role Variables
--------------
""",
        encoding="utf-8",
    )

    with _prefer_prism_lane(FSRC_LANE_ROOT):
        style_module = importlib.import_module("prism.scanner_readme.style")
        fsrc_style = style_module.parse_style_readme(str(style_path))

    template_rendered = _render_with_lane(
        FSRC_LANE_ROOT,
        output=str(tmp_path / "fsrc.md"),
        role_name="demo_role",
        description="demo description",
        variables={"demo_var": {"default": "x"}},
        metadata={},
        template_path=str(template_path),
    )

    style_skeleton_rendered = _render_with_lane(
        FSRC_LANE_ROOT,
        output=str(tmp_path / "fsrc-styled.md"),
        role_name="demo_role",
        description="demo description",
        variables={"demo_var": {"default": "x"}},
        metadata={
            "style_guide": fsrc_style,
            "style_guide_skeleton": True,
        },
        template_path=str(template_path),
    )

    assert "demo_role" in template_rendered
    assert "demo description" in template_rendered
    assert "Variables: 1" in template_rendered
    assert "demo_role" in style_skeleton_rendered


def test_w3_t03_style_parser_treats_yaml_fence_case_insensitively_fsrc(
    tmp_path: Path,
) -> None:
    style_path = tmp_path / "STYLE_GUIDE.md"
    style_path.write_text(
        """Role style
==========

Role Variables
--------------

Intro paragraph.

```YAML
demo_var: value
```
""",
        encoding="utf-8",
    )

    with _prefer_prism_lane(FSRC_LANE_ROOT):
        style_module = importlib.import_module("prism.scanner_readme.style")
        parsed = style_module.parse_style_readme(str(style_path))

    assert parsed["variable_style"] == "yaml_block"
    assert parsed["variable_intro"] == "Intro paragraph."


def test_w3_t03_merge_label_can_be_configured_via_metadata_with_stable_default(
    tmp_path: Path,
) -> None:
    with _prefer_prism_lane(FSRC_LANE_ROOT):
        render_module = importlib.import_module("prism.scanner_readme.render")

        metadata = {
            "style_guide": {
                "title_style": "setext",
                "section_style": "setext",
                "section_level": 2,
                "sections": [
                    {
                        "id": "requirements",
                        "title": "Requirements",
                        "body": "Keep this context.",
                        "level": 2,
                    }
                ],
            },
            "merge_generated_content_label": "Scanner synthesis",
        }

        rendered = render_module.render_readme(
            output=str(tmp_path / "README.md"),
            role_name="demo_role",
            description="demo description",
            variables={},
            requirements=["ansible-core"],
            default_filters=[],
            metadata=metadata,
            write=False,
        )

    assert "Scanner synthesis:" in rendered
    assert "Generated content:" not in rendered


def test_w3_t03_readme_and_runbook_use_shared_jinja_environment_factory(
    tmp_path: Path,
) -> None:
    readme_template = tmp_path / "README.md.j2"
    readme_template.write_text("# {{ role_name }}\n", encoding="utf-8")
    runbook_template = tmp_path / "RUNBOOK.md.j2"
    runbook_template.write_text("# Runbook for {{ role_name }}\n", encoding="utf-8")

    factory_calls: list[str] = []

    def _factory(template_dir: Path, *, metadata: dict[str, Any] | None = None):
        _ = metadata
        factory_calls.append(str(template_dir))
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    metadata = {"jinja_environment_factory": _factory}

    with _prefer_prism_lane(FSRC_LANE_ROOT):
        render_module = importlib.import_module("prism.scanner_readme.render")
        runbook_module = importlib.import_module("prism.scanner_reporting.runbook")

        readme_output = render_module.render_readme(
            output=str(tmp_path / "README.out.md"),
            role_name="demo_role",
            description="demo description",
            variables={},
            requirements=[],
            default_filters=[],
            template=str(readme_template),
            metadata=metadata,
            write=False,
        )
        runbook_output = runbook_module.render_runbook(
            role_name="demo_role",
            metadata=metadata,
            template=str(runbook_template),
        )

    assert "demo_role" in readme_output
    assert "demo_role" in runbook_output
    assert factory_calls == [
        str(readme_template.parent),
        str(runbook_template.parent),
    ]


def test_fsrc_parse_style_readme_respects_scoped_style_section_aliases(
    tmp_path: Path,
) -> None:
    style_path = tmp_path / "STYLE_GUIDE.md"
    style_path.write_text(
        """Role style
==========

Custom Variables
----------------
""",
        encoding="utf-8",
    )

    with _prefer_prism_lane(FSRC_LANE_ROOT):
        style_module = importlib.import_module("prism.scanner_readme.style")

        parsed_without_scope = style_module.parse_style_readme(str(style_path))
        parsed_with_scope = style_module.parse_style_readme(
            str(style_path),
            section_aliases={"custom variables": "role_variables"},
        )

    assert parsed_without_scope["sections"][0]["id"] == "unknown"
    assert parsed_with_scope["sections"][0]["id"] == "role_variables"


def test_fsrc_style_alias_defaults_are_single_source() -> None:
    with _prefer_prism_lane(FSRC_LANE_ROOT):
        style_config_module = importlib.import_module(
            "prism.scanner_readme.style_config"
        )
        parser_module = importlib.import_module(
            "prism.scanner_plugins.parsers.markdown.style_parser"
        )
        shared_alias_module = importlib.import_module(
            "prism.scanner_data.style_aliases"
        )

        config_snapshot = style_config_module.get_style_section_aliases_snapshot()
        parser_snapshot = parser_module.get_default_style_section_aliases_snapshot()
        shared_snapshot = (
            shared_alias_module.get_default_style_section_aliases_snapshot()
        )

    assert config_snapshot == shared_snapshot
    assert parser_snapshot == shared_snapshot
