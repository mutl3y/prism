"""Focused parity checks for fsrc README style parsing and rendering foundations."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_LANE_ROOT = PROJECT_ROOT / "src"
FSRC_LANE_ROOT = PROJECT_ROOT / "fsrc" / "src"


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

    parsed_by_lane: dict[str, dict[str, Any]] = {}
    for lane_name, lane_root in (("src", SRC_LANE_ROOT), ("fsrc", FSRC_LANE_ROOT)):
        with _prefer_prism_lane(lane_root):
            parser_module = importlib.import_module("prism.scanner_readme.style_parser")
            parsed_by_lane[lane_name] = parser_module.parse_style_readme(
                str(style_path)
            )

    src_parsed = parsed_by_lane["src"]
    fsrc_parsed = parsed_by_lane["fsrc"]

    assert fsrc_parsed["title_style"] == src_parsed["title_style"]
    assert fsrc_parsed["section_style"] == src_parsed["section_style"]
    assert fsrc_parsed["section_level"] == src_parsed["section_level"]
    assert fsrc_parsed["variable_style"] == src_parsed["variable_style"]
    assert fsrc_parsed.get("variable_intro") == src_parsed.get("variable_intro")
    assert [
        (section["id"], section["title"], section["normalized_title"])
        for section in fsrc_parsed["sections"]
    ] == [
        (section["id"], section["title"], section["normalized_title"])
        for section in src_parsed["sections"]
    ]


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

    parsed_style_by_lane: dict[str, dict[str, Any]] = {}
    for lane_name, lane_root in (("src", SRC_LANE_ROOT), ("fsrc", FSRC_LANE_ROOT)):
        with _prefer_prism_lane(lane_root):
            parser_module = importlib.import_module("prism.scanner_readme.style_parser")
            parsed_style_by_lane[lane_name] = parser_module.parse_style_readme(
                str(style_path)
            )

    template_by_lane = {
        lane_name: _render_with_lane(
            lane_root,
            output=str(tmp_path / f"{lane_name}.md"),
            role_name="demo_role",
            description="demo description",
            variables={"demo_var": {"default": "x"}},
            metadata={},
            template_path=str(template_path),
        )
        for lane_name, lane_root in (("src", SRC_LANE_ROOT), ("fsrc", FSRC_LANE_ROOT))
    }

    style_skeleton_by_lane = {
        lane_name: _render_with_lane(
            lane_root,
            output=str(tmp_path / f"{lane_name}-styled.md"),
            role_name="demo_role",
            description="demo description",
            variables={"demo_var": {"default": "x"}},
            metadata={
                "style_guide": parsed_style_by_lane[lane_name],
                "style_guide_skeleton": True,
            },
            template_path=str(template_path),
        )
        for lane_name, lane_root in (("src", SRC_LANE_ROOT), ("fsrc", FSRC_LANE_ROOT))
    }

    assert template_by_lane["fsrc"] == template_by_lane["src"]
    assert style_skeleton_by_lane["fsrc"] == style_skeleton_by_lane["src"]
