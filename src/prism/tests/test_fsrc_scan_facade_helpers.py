"""Tests for fsrc/src/prism/scanner_core/scan_facade_helpers.py."""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _noop_is_path_excluded(path, role_root, exclude_paths):
    return False


def _noop_load_meta(role_path, *, warning_collector=None):
    return {}


def _noop_extract_role_features(role_path, *, exclude_paths=None):
    return {}


def _noop_load_variables(*, role_path, exclude_paths=None, **kw):
    return {}


def _noop_scan_for_default_filters(role_path, exclude_paths):
    return []


# ---------------------------------------------------------------------------
# collect_role_contents
# ---------------------------------------------------------------------------


class TestCollectRoleContents:
    def test_returns_dict_with_all_sections(self, tmp_path):
        from prism.scanner_core.scan_facade_helpers import collect_role_contents

        (tmp_path / "tasks").mkdir()
        (tmp_path / "tasks" / "main.yml").write_text("")
        (tmp_path / "defaults").mkdir()
        (tmp_path / "defaults" / "main.yml").write_text("")

        result = collect_role_contents(
            role_path=str(tmp_path),
            exclude_paths=None,
            is_path_excluded=_noop_is_path_excluded,
            load_meta=_noop_load_meta,
            extract_role_features=_noop_extract_role_features,
        )

        assert "tasks" in result
        assert "defaults" in result
        assert "handlers" in result
        assert "templates" in result
        assert "files" in result
        assert "tests" in result
        assert "vars" in result
        assert "meta" in result
        assert "features" in result
        assert result["tasks"] == ["tasks/main.yml"]
        assert result["defaults"] == ["defaults/main.yml"]
        assert result["handlers"] == []

    def test_empty_role_dir_produces_empty_lists(self, tmp_path):
        from prism.scanner_core.scan_facade_helpers import collect_role_contents

        result = collect_role_contents(
            role_path=str(tmp_path),
            exclude_paths=None,
            is_path_excluded=_noop_is_path_excluded,
            load_meta=_noop_load_meta,
            extract_role_features=_noop_extract_role_features,
        )

        for section in (
            "handlers",
            "tasks",
            "templates",
            "files",
            "tests",
            "defaults",
            "vars",
        ):
            assert result[section] == []

    def test_load_meta_exception_adds_meta_load_warnings(self, tmp_path):
        from prism.scanner_core.scan_facade_helpers import collect_role_contents

        def _failing_load_meta(role_path, *, warning_collector=None):
            raise RuntimeError("boom")

        result = collect_role_contents(
            role_path=str(tmp_path),
            exclude_paths=None,
            is_path_excluded=_noop_is_path_excluded,
            load_meta=_failing_load_meta,
            extract_role_features=_noop_extract_role_features,
        )

        assert result["meta"] == {}
        assert "meta_load_warnings" in result
        assert any(
            "ROLE_METADATA_LOAD_FAILED" in w for w in result["meta_load_warnings"]
        )

    def test_excluded_paths_are_skipped(self, tmp_path):
        from prism.scanner_core.scan_facade_helpers import collect_role_contents

        (tmp_path / "tasks").mkdir()
        (tmp_path / "tasks" / "main.yml").write_text("")
        (tmp_path / "tasks" / "skip.yml").write_text("")

        def _excluding(path, role_root, exclude_paths):
            return path.name == "skip.yml"

        result = collect_role_contents(
            role_path=str(tmp_path),
            exclude_paths=None,
            is_path_excluded=_excluding,
            load_meta=_noop_load_meta,
            extract_role_features=_noop_extract_role_features,
        )

        assert "tasks/main.yml" in result["tasks"]
        assert not any("skip.yml" in p for p in result["tasks"])

    def test_features_key_contains_extract_role_features_output(self, tmp_path):
        from prism.scanner_core.scan_facade_helpers import collect_role_contents

        def _features(role_path, *, exclude_paths=None):
            return {"tasks_scanned": 5}

        result = collect_role_contents(
            role_path=str(tmp_path),
            exclude_paths=None,
            is_path_excluded=_noop_is_path_excluded,
            load_meta=_noop_load_meta,
            extract_role_features=_features,
        )

        assert result["features"] == {"tasks_scanned": 5}


# ---------------------------------------------------------------------------
# compute_quality_metrics
# ---------------------------------------------------------------------------


class TestComputeQualityMetrics:
    def test_score_is_zero_when_all_mocks_return_empty(self, tmp_path):
        from prism.scanner_core.scan_facade_helpers import compute_quality_metrics

        result = compute_quality_metrics(
            role_path=str(tmp_path),
            exclude_paths=None,
            collect_role_contents=lambda rp, ep: {
                **{
                    s: []
                    for s in (
                        "tasks",
                        "defaults",
                        "vars",
                        "handlers",
                        "templates",
                        "files",
                        "tests",
                    )
                },
                "features": {},
            },
            load_variables=_noop_load_variables,
            scan_for_default_filters=_noop_scan_for_default_filters,
        )

        assert result["score"] == 0
        assert result["present_dirs"] == 0
        assert result["variable_count"] == 0
        assert result["task_count"] == 0
        assert result["module_count"] == 0
        assert result["default_filter_count"] == 0

    def test_score_is_positive_when_sections_populated(self, tmp_path):
        from prism.scanner_core.scan_facade_helpers import compute_quality_metrics

        def _collect(rp, ep):
            return {
                "tasks": ["tasks/main.yml"],
                "defaults": ["defaults/main.yml"],
                "vars": [],
                "handlers": [],
                "templates": [],
                "files": [],
                "tests": [],
                "features": {
                    "tasks_scanned": 3,
                    "unique_modules": "ansible.builtin.debug,ansible.builtin.copy",
                },
            }

        result = compute_quality_metrics(
            role_path=str(tmp_path),
            exclude_paths=None,
            collect_role_contents=_collect,
            load_variables=lambda *, role_path, exclude_paths=None, **kw: {
                "var1": "v",
                "var2": "v",
            },
            scan_for_default_filters=lambda rp, ep: [{"file": "f", "line_no": 1}],
        )

        assert result["score"] > 0
        assert result["present_dirs"] == 2
        assert result["variable_count"] == 2
        assert result["task_count"] == 3
        assert result["module_count"] == 2
        assert result["default_filter_count"] == 1

    def test_score_capped_at_100(self, tmp_path):
        from prism.scanner_core.scan_facade_helpers import compute_quality_metrics

        many_modules = ",".join(f"mod{i}" for i in range(50))

        def _collect(rp, ep):
            return {
                s: [f"{s}/main.yml"]
                for s in (
                    "tasks",
                    "defaults",
                    "vars",
                    "handlers",
                    "templates",
                    "files",
                    "tests",
                )
            } | {"features": {"tasks_scanned": 100, "unique_modules": many_modules}}

        result = compute_quality_metrics(
            role_path=str(tmp_path),
            exclude_paths=None,
            collect_role_contents=_collect,
            load_variables=lambda *, role_path, exclude_paths=None, **kw: {
                str(i): i for i in range(50)
            },
            scan_for_default_filters=lambda rp, ep: [{}] * 20,
        )

        assert result["score"] == 100


# ---------------------------------------------------------------------------
# build_comparison_report
# ---------------------------------------------------------------------------


class TestBuildComparisonReport:
    def test_score_delta_is_computed_correctly(self, tmp_path):
        from prism.scanner_core.scan_facade_helpers import build_comparison_report

        target_dir = str(tmp_path / "target")
        baseline_dir = str(tmp_path / "baseline")

        call_count = {"n": 0}

        def _metrics(rp, ep):
            call_count["n"] += 1
            if rp == target_dir:
                return {
                    "score": 70,
                    "present_dirs": 4,
                    "variable_count": 5,
                    "task_count": 3,
                    "module_count": 2,
                    "default_filter_count": 1,
                }
            return {
                "score": 50,
                "present_dirs": 2,
                "variable_count": 3,
                "task_count": 1,
                "module_count": 1,
                "default_filter_count": 0,
            }

        result = build_comparison_report(
            target_role_path=target_dir,
            baseline_role_path=baseline_dir,
            exclude_paths=None,
            compute_quality_metrics=_metrics,
        )

        assert result["target_score"] == 70
        assert result["baseline_score"] == 50
        assert result["score_delta"] == 20
        assert result["metrics"]["present_dirs"]["delta"] == 2
        assert result["metrics"]["variable_count"]["delta"] == 2
        assert result["metrics"]["task_count"]["delta"] == 2
        assert result["metrics"]["module_count"]["delta"] == 1
        assert result["metrics"]["default_filter_count"]["delta"] == 1
        assert call_count["n"] == 2

    def test_baseline_path_is_resolved(self, tmp_path):
        from prism.scanner_core.scan_facade_helpers import build_comparison_report

        baseline_dir = str(tmp_path / "baseline")

        def _metrics(rp, ep):
            return {
                "score": 0,
                "present_dirs": 0,
                "variable_count": 0,
                "task_count": 0,
                "module_count": 0,
                "default_filter_count": 0,
            }

        result = build_comparison_report(
            target_role_path=str(tmp_path / "target"),
            baseline_role_path=baseline_dir,
            exclude_paths=None,
            compute_quality_metrics=_metrics,
        )

        assert result["baseline_path"] == str(Path(baseline_dir).resolve())


# ---------------------------------------------------------------------------
# API importability
# ---------------------------------------------------------------------------


class TestApiImportability:
    def test_collect_role_contents_is_importable(self):
        from prism.api import collect_role_contents  # noqa: F401

        assert callable(collect_role_contents)

    def test_compute_quality_metrics_is_importable(self):
        from prism.api import compute_quality_metrics  # noqa: F401

        assert callable(compute_quality_metrics)

    def test_build_comparison_report_is_importable(self):
        from prism.api import build_comparison_report  # noqa: F401

        assert callable(build_comparison_report)
