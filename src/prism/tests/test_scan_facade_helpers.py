"""Tests for extracted scanner facade helper seams."""

from __future__ import annotations

from pathlib import Path

from prism.scanner_core import scan_facade_helpers


def test_collect_role_contents_handles_exclusions_and_meta_failure(tmp_path: Path):
    role = tmp_path / "role"
    (role / "tasks").mkdir(parents=True)
    (role / "tasks" / "main.yml").write_text("---\n", encoding="utf-8")
    (role / "templates").mkdir(parents=True)
    (role / "templates" / "keep.j2").write_text("x", encoding="utf-8")
    (role / "templates" / "skip.j2").write_text("x", encoding="utf-8")

    def fail_meta(_role_path: str) -> dict:
        raise RuntimeError("meta parse failed")

    def is_path_excluded(
        path: Path, role_root: Path, _exclude_paths: list[str] | None
    ) -> bool:
        return path == role_root / "templates" / "skip.j2"

    contents = scan_facade_helpers.collect_role_contents(
        role_path=str(role),
        exclude_paths=None,
        is_path_excluded=is_path_excluded,
        load_meta=fail_meta,
        extract_role_features=lambda _role_path, **_kwargs: {"tasks_scanned": 1},
    )

    assert contents["tasks"] == ["tasks/main.yml"]
    assert contents["templates"] == ["templates/keep.j2"]
    assert contents["meta"] == {}
    assert contents["features"] == {"tasks_scanned": 1}


def test_compute_quality_metrics_and_comparison_report_use_helper_dependencies():
    def collect_role_contents(
        role_path: str, exclude_paths: list[str] | None = None
    ) -> dict:
        assert exclude_paths == ["x"]
        if role_path == "target":
            return {
                "tasks": ["tasks/main.yml"],
                "defaults": ["defaults/main.yml"],
                "vars": [],
                "handlers": [],
                "templates": [],
                "files": [],
                "tests": [],
                "features": {"tasks_scanned": 3, "unique_modules": "debug, copy"},
            }
        return {
            "tasks": [],
            "defaults": [],
            "vars": [],
            "handlers": [],
            "templates": [],
            "files": [],
            "tests": [],
            "features": {"tasks_scanned": 1, "unique_modules": "debug"},
        }

    def load_variables(role_path: str, exclude_paths: list[str] | None = None) -> dict:
        assert exclude_paths == ["x"]
        return {"a": 1, "b": 2} if role_path == "target" else {"a": 1}

    def scan_for_default_filters(
        role_path: str, exclude_paths: list[str] | None = None
    ) -> list[dict]:
        assert exclude_paths == ["x"]
        return [{"match": "default"}] if role_path == "target" else []

    report = scan_facade_helpers.build_comparison_report(
        target_role_path="target",
        baseline_role_path="baseline",
        exclude_paths=["x"],
        compute_quality_metrics=lambda role_path, exclude_paths: scan_facade_helpers.compute_quality_metrics(
            role_path=role_path,
            exclude_paths=exclude_paths,
            collect_role_contents=collect_role_contents,
            load_variables=load_variables,
            scan_for_default_filters=scan_for_default_filters,
        ),
    )

    assert report["target_score"] > report["baseline_score"]
    assert report["metrics"]["task_count"]["target"] == 3
    assert report["metrics"]["default_filter_count"]["target"] == 1


def test_collect_scan_artifacts_adds_catalog_when_requested():
    variables, requirements, found, metadata = (
        scan_facade_helpers.collect_scan_artifacts(
            role_path="/tmp/role",
            include_vars_main=True,
            exclude_path_patterns=["ignore"],
            detailed_catalog=True,
            marker_prefix="prism",
            load_variables=lambda role_path, include_vars_main, exclude_paths: {"v": 1},
            load_requirements=lambda role_path: ["req"],
            scan_for_default_filters=lambda role_path, exclude_paths: [{"target": "x"}],
            collect_role_contents=lambda role_path, exclude_paths: {"features": {}},
            collect_molecule_scenarios=lambda role_path, exclude_paths: ["default"],
            collect_unconstrained_dynamic_task_includes=lambda role_path, exclude_paths: [
                {"task": "x"}
            ],
            collect_unconstrained_dynamic_role_includes=lambda role_path, exclude_paths: [
                {"task": "y"}
            ],
            collect_task_handler_catalog=lambda role_path, exclude_paths, marker_prefix: (
                [{"name": "task"}],
                [{"name": "handler"}],
            ),
        )
    )

    assert variables == {"v": 1}
    assert requirements == ["req"]
    assert found == [{"target": "x"}]
    assert metadata["marker_prefix"] == "prism"
    assert metadata["detailed_catalog"] is True
    assert metadata["task_catalog"] == [{"name": "task"}]
    assert metadata["handler_catalog"] == [{"name": "handler"}]


def test_apply_style_and_comparison_metadata_requires_existing_style_file(
    tmp_path: Path,
):
    metadata: dict = {}

    missing_style = tmp_path / "missing-style.md"

    try:
        scan_facade_helpers.apply_style_and_comparison_metadata(
            metadata=metadata,
            style_readme_path=str(missing_style),
            style_source_path=None,
            style_guide_skeleton=False,
            compare_role_path=None,
            role_path="/tmp/role",
            exclude_path_patterns=None,
            resolve_default_style_guide_source=lambda explicit_path: str(missing_style),
            parse_style_readme=lambda path: {"sections": []},
            build_comparison_report=lambda role_path, compare_role_path, exclude_paths: {},
        )
    except FileNotFoundError as exc:
        assert "style README not found" in str(exc)
    else:
        raise AssertionError("Expected missing style README to raise FileNotFoundError")
