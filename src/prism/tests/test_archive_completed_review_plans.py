from __future__ import annotations

import runpy
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "archive_completed_review_plans.py"


def _load_script(plan_root: Path) -> dict[str, object]:
    script = runpy.run_path(str(SCRIPT_PATH), run_name="archive_completed_review_plans")
    repo_root = plan_root.parents[1]
    globals_dict = script["main"].__globals__
    globals_dict["REPO_ROOT"] = repo_root
    globals_dict["PLAN_ROOT"] = plan_root
    globals_dict["ARCHIVE_ROOT"] = plan_root / "archive"
    return script


def _run_main(script: dict[str, object], args: list[str]) -> int:
    main = script["main"]
    assert callable(main)
    previous_argv = sys.argv[:]
    try:
        sys.argv = [str(SCRIPT_PATH), *args]
        return main()
    finally:
        sys.argv = previous_argv


def _write_yaml(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_plan(plan_dir: Path, *, status: str) -> None:
    _write_yaml(
        plan_dir / "plan.yaml",
        {
            "plan_id": plan_dir.name,
            "cycle": plan_dir.name,
            "status": status,
            "resumption_pointer": {
                "current_phase": "P7",
                "next_action": "Archived.",
                "blocking_issues": [],
            },
            "artifacts": {
                "closure_summary": str(plan_dir / "artifacts" / "closure-summary.yaml"),
            },
        },
    )
    _write_yaml(plan_dir / "artifacts" / "closure-summary.yaml", {"status": status})


def test_archive_completed_review_plans_archives_complete_and_completed_checkpoint(
    tmp_path: Path,
) -> None:
    plan_root = tmp_path / "docs" / "plan"
    archive_root = plan_root / "archive"
    plan_root.mkdir(parents=True)
    archive_root.mkdir()

    complete_dir = plan_root / "mutl3y-review-20260504-g65"
    checkpoint_dir = plan_root / "mutl3y-review-20260504-g72"
    active_dir = plan_root / "mutl3y-review-20260504-g73"
    _write_plan(complete_dir, status="complete")
    _write_plan(checkpoint_dir, status="completed_checkpoint")
    _write_plan(active_dir, status="implementation_in_progress")

    script = _load_script(plan_root)
    exit_code = _run_main(
        script,
        [str(complete_dir), str(checkpoint_dir), str(active_dir)],
    )

    assert exit_code == 0
    assert not complete_dir.exists()
    assert not checkpoint_dir.exists()
    assert active_dir.exists()
    assert (archive_root / complete_dir.name).exists()
    assert (archive_root / checkpoint_dir.name).exists()


def test_archive_completed_review_plans_keeps_latest_prefix_family(
    tmp_path: Path,
) -> None:
    plan_root = tmp_path / "docs" / "plan"
    archive_root = plan_root / "archive"
    plan_root.mkdir(parents=True)
    archive_root.mkdir()

    older_dir = plan_root / "gilfoyle-review-20260501-g46"
    latest_dir = plan_root / "gilfoyle-review-20260502-g47"
    _write_plan(older_dir, status="completed")
    _write_plan(latest_dir, status="completed")

    script = _load_script(plan_root)
    exit_code = _run_main(
        script,
        [
            "--keep-latest-prefix",
            "gilfoyle-review-",
            str(older_dir),
            str(latest_dir),
        ],
    )

    assert exit_code == 0
    assert not older_dir.exists()
    assert latest_dir.exists()
    assert (archive_root / older_dir.name).exists()
