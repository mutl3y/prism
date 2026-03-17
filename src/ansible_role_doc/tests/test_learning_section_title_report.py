import importlib.util
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "learning_section_title_report.py"
)


def _load_report_module():
    spec = importlib.util.spec_from_file_location(
        "learning_section_title_report", SCRIPT_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_render_markdown_reports_backtick_title_candidates():
    mod = _load_report_module()
    report = {
        "selection": {
            "source": "raw",
            "latest_per_target": True,
            "run_label": None,
            "batch_id": None,
        },
        "snapshot_count": 2,
        "distinct_targets": 2,
        "total_sections": 4,
        "known_sections": 3,
        "unknown_sections": 1,
        "sections": [
            {
                "known": True,
                "section_id": "role_variables",
                "display_title": "Role Variables",
                "count": 2,
                "distinct_targets": 2,
                "titles": [
                    {"title": "Role Variables", "count": 1},
                    {"title": "`Role Variables`", "count": 1},
                ],
            }
        ],
        "unknown_titles": [
            {
                "normalized_title": "extra config",
                "count": 1,
                "distinct_targets": 1,
                "titles": [{"title": "`Extra Config`", "count": 1}],
                "sample_targets": ["owner/repo"],
            }
        ],
    }

    md = mod.render_markdown(report, top_variants=5)

    assert "- Backtick title variants detected: 2" in md
    assert "## Backtick Title Variant Checks" in md
    assert "known_section_variant" in md
    assert "unknown_title_variant" in md
    assert "Role Variables" in md
    assert "Extra Config" in md
    assert "`Role Variables`" not in md
    assert "`Extra Config`" not in md


def test_render_markdown_omits_backtick_table_when_none_detected():
    mod = _load_report_module()
    report = {
        "selection": {
            "source": "raw",
            "latest_per_target": True,
            "run_label": None,
            "batch_id": None,
        },
        "snapshot_count": 1,
        "distinct_targets": 1,
        "total_sections": 1,
        "known_sections": 1,
        "unknown_sections": 0,
        "sections": [
            {
                "known": True,
                "section_id": "requirements",
                "display_title": "Requirements",
                "count": 1,
                "distinct_targets": 1,
                "titles": [{"title": "Requirements", "count": 1}],
            }
        ],
        "unknown_titles": [],
    }

    md = mod.render_markdown(report, top_variants=5)

    assert "- Backtick title variants detected: 0" in md
    assert "## Backtick Title Variant Checks" not in md
