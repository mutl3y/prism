from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from ansible_role_doc import cli


def test_cli_scans_from_repo_url(monkeypatch, tmp_path):
    calls: dict = {}

    def fake_clone_run(cmd, check, stdout, stderr, text, timeout, env):
        destination = Path(cmd[-1])
        (destination / "tasks").mkdir(parents=True, exist_ok=True)
        (destination / "tasks" / "main.yml").write_text(
            "---\n- name: Task\n  debug:\n    msg: \"{{ demo | default('x') }}\"\n",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        calls["role_path"] = role_path
        calls["output"] = output
        calls["template"] = template
        calls["format"] = output_format
        calls["role_name_override"] = kwargs.get("role_name_override")
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli.subprocess, "run", fake_clone_run)
    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "repo-out.md"
    rc = cli.main(["--repo-url", "https://github.com/example/role.git", "-o", str(out)])

    assert rc == 0
    assert out.exists()
    assert calls["format"] == "md"
    assert calls["role_path"].endswith("repo")
    assert calls["role_name_override"] == "role"


def test_cli_repo_ref_is_used_for_clone(monkeypatch, tmp_path):
    clone_cmd: dict = {}

    def fake_clone_run(cmd, check, stdout, stderr, text, timeout, env):
        clone_cmd["cmd"] = cmd
        clone_cmd["timeout"] = timeout
        clone_cmd["prompt"] = env.get("GIT_TERMINAL_PROMPT")
        destination = Path(cmd[-1])
        destination.mkdir(parents=True, exist_ok=True)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli.subprocess, "run", fake_clone_run)
    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "repo-ref.md"
    rc = cli.main(
        [
            "--repo-url",
            "https://github.com/example/role.git",
            "--repo-ref",
            "main",
            "--repo-role-path",
            ".",
            "-o",
            str(out),
        ]
    )

    assert rc == 0
    assert out.exists()
    assert "--branch" in clone_cmd["cmd"]
    assert "main" in clone_cmd["cmd"]
    assert clone_cmd["timeout"] == 60
    assert clone_cmd["prompt"] == "0"


def test_cli_repo_timeout_is_forwarded(monkeypatch, tmp_path):
    clone_timeout: dict = {}

    def fake_clone_run(cmd, check, stdout, stderr, text, timeout, env):
        clone_timeout["value"] = timeout
        destination = Path(cmd[-1])
        destination.mkdir(parents=True, exist_ok=True)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli.subprocess, "run", fake_clone_run)
    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "repo-timeout.md"
    rc = cli.main(
        [
            "--repo-url",
            "https://github.com/example/role.git",
            "--repo-timeout",
            "5",
            "-o",
            str(out),
        ]
    )

    assert rc == 0
    assert clone_timeout["value"] == 5


def test_cli_github_https_url_is_converted_to_ssh(monkeypatch, tmp_path):
    clone_cmd: dict = {}

    def fake_clone_run(cmd, check, stdout, stderr, text, timeout, env):
        clone_cmd["cmd"] = cmd
        destination = Path(cmd[-1])
        destination.mkdir(parents=True, exist_ok=True)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli.subprocess, "run", fake_clone_run)
    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "repo-ssh-url.md"
    rc = cli.main(
        [
            "--repo-url",
            "https://github.com/example/role",
            "-o",
            str(out),
        ]
    )

    assert rc == 0
    assert clone_cmd["cmd"][-2] == "git@github.com:example/role.git"


def test_cli_ssh_repo_url_is_preserved(monkeypatch, tmp_path):
    clone_cmd: dict = {}

    def fake_clone_run(cmd, check, stdout, stderr, text, timeout, env):
        clone_cmd["cmd"] = cmd
        destination = Path(cmd[-1])
        destination.mkdir(parents=True, exist_ok=True)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli.subprocess, "run", fake_clone_run)
    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "repo-ssh-preserved.md"
    rc = cli.main(
        [
            "--repo-url",
            "git@github.com:example/role.git",
            "-o",
            str(out),
        ]
    )

    assert rc == 0
    assert clone_cmd["cmd"][-2] == "git@github.com:example/role.git"


def test_cli_requires_single_input_source():
    assert cli.main([]) == 2
    assert (
        cli.main(["some/role", "--repo-url", "https://github.com/example/role.git"])
        == 2
    )


def test_cli_compare_role_path_is_forwarded(monkeypatch, tmp_path):
    calls: dict = {}

    role = tmp_path / "role"
    baseline = tmp_path / "baseline"
    role.mkdir()
    baseline.mkdir()

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        calls["role_path"] = role_path
        calls["compare_role_path"] = kwargs.get("compare_role_path")
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "compare.md"
    rc = cli.main(
        [
            str(role),
            "--compare-role-path",
            str(baseline),
            "-o",
            str(out),
        ]
    )

    assert rc == 0
    assert calls["role_path"] == str(role)
    assert calls["compare_role_path"] == str(baseline)


def test_cli_style_readme_is_forwarded(monkeypatch, tmp_path):
    calls: dict = {}

    role = tmp_path / "role"
    style = tmp_path / "STYLE_README.md"
    role.mkdir()
    style.write_text("# Guide\n", encoding="utf-8")

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        calls["style_readme_path"] = kwargs.get("style_readme_path")
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "styled.md"
    rc = cli.main([str(role), "--style-readme", str(style), "-o", str(out)])

    assert rc == 0
    assert calls["style_readme_path"] == str(style)
    source_sidecar = tmp_path / "style_readme" / "SOURCE_STYLE_GUIDE.md"
    demo_sidecar = tmp_path / "style_readme" / "DEMO_GENERATED.md"
    assert source_sidecar.exists()
    assert source_sidecar.read_text(encoding="utf-8") == "# Guide\n"
    assert demo_sidecar.exists()
    assert demo_sidecar.read_text(encoding="utf-8") == "generated"


def test_cli_repo_style_readme_path_is_resolved(monkeypatch, tmp_path):
    calls: dict = {}

    def fake_clone_run(cmd, check, stdout, stderr, text, timeout, env):
        destination = Path(cmd[-1])
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "README.md").write_text("# Guide\n", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        calls["style_readme_path"] = kwargs.get("style_readme_path")
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli.subprocess, "run", fake_clone_run)
    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "repo-style.md"
    rc = cli.main(
        [
            "--repo-url",
            "https://github.com/example/role.git",
            "--repo-style-readme-path",
            "README.md",
            "-o",
            str(out),
        ]
    )

    assert rc == 0
    assert calls["style_readme_path"].endswith("README.md")
    source_sidecar = tmp_path / "style_role" / "SOURCE_STYLE_GUIDE.md"
    demo_sidecar = tmp_path / "style_role" / "DEMO_GENERATED.md"
    assert source_sidecar.exists()
    assert source_sidecar.read_text(encoding="utf-8") == "# Guide\n"
    assert demo_sidecar.exists()
    assert demo_sidecar.read_text(encoding="utf-8") == "generated"


def test_clone_repo_timeout_raises_runtime_error(monkeypatch, tmp_path):
    def fake_clone_run(cmd, check, stdout, stderr, text, timeout, env):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

    monkeypatch.setattr(cli.subprocess, "run", fake_clone_run)

    with pytest.raises(RuntimeError, match="repository clone timed out"):
        cli._clone_repo(
            "https://github.com/example/role.git", tmp_path / "repo", timeout=5
        )


def test_clone_repo_failure_raises_runtime_error(monkeypatch, tmp_path):
    def fake_clone_run(cmd, check, stdout, stderr, text, timeout, env):
        raise subprocess.CalledProcessError(
            returncode=1, cmd=cmd, stderr="fatal: denied"
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_clone_run)

    with pytest.raises(RuntimeError, match="repository clone failed: fatal: denied"):
        cli._clone_repo("https://github.com/example/role.git", tmp_path / "repo")


def test_save_style_comparison_artifacts_requires_existing_source(tmp_path):
    with pytest.raises(FileNotFoundError, match="style README not found"):
        cli._save_style_comparison_artifacts(
            str(tmp_path / "missing.md"),
            str(tmp_path / "generated.md"),
        )


def test_save_style_comparison_artifacts_handles_same_source_path(tmp_path):
    style_dir = tmp_path / "style_demo"
    style_dir.mkdir()
    source = style_dir / "SOURCE_STYLE_GUIDE.md"
    source.write_text("# Guide\n", encoding="utf-8")
    generated = tmp_path / "generated.html"
    generated.write_text("<html></html>", encoding="utf-8")

    source_path, demo_path = cli._save_style_comparison_artifacts(
        str(source),
        str(generated),
        "style_demo",
    )

    assert Path(source_path) == source
    assert Path(demo_path) == style_dir / "DEMO_GENERATED.html"
    assert Path(demo_path).read_text(encoding="utf-8") == "<html></html>"


def test_cli_repo_role_path_must_exist(monkeypatch, tmp_path, capsys):
    def fake_clone_run(cmd, check, stdout, stderr, text, timeout, env):
        destination = Path(cmd[-1])
        destination.mkdir(parents=True, exist_ok=True)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_clone_run)

    out = tmp_path / "missing-subpath.md"
    rc = cli.main(
        [
            "--repo-url",
            "https://github.com/example/role.git",
            "--repo-role-path",
            "missing-role",
            "-o",
            str(out),
        ]
    )

    captured = capsys.readouterr()
    assert rc == 2
    assert "role path not found in cloned repository" in captured.err


def test_repo_name_from_url_returns_none_for_unparseable_values():
    assert cli._repo_name_from_url("not-a-url") is None
    assert cli._repo_name_from_url("git@github.com") is None


def test_clone_repo_keeps_non_repo_github_url_as_is(monkeypatch, tmp_path):
    clone_cmd: dict = {}

    def fake_clone_run(cmd, check, stdout, stderr, text, timeout, env):
        clone_cmd["cmd"] = cmd
        destination = Path(cmd[-1])
        destination.mkdir(parents=True, exist_ok=True)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_clone_run)

    cli._clone_repo("https://github.com", tmp_path / "repo")
    assert clone_cmd["cmd"][-2] == "https://github.com"


def test_save_style_comparison_artifacts_uses_parent_name_for_readme_slug(tmp_path):
    source_dir = tmp_path / "ansible-role-demo"
    source_dir.mkdir()
    source = source_dir / "README.md"
    source.write_text("# Guide\n", encoding="utf-8")
    output = tmp_path / "generated.md"
    output.write_text("generated", encoding="utf-8")

    source_path, demo_path = cli._save_style_comparison_artifacts(
        str(source),
        str(output),
        style_source_name="readme",
    )

    assert Path(source_path).parent.name == "style_ansible_role_demo"
    assert Path(demo_path).name == "DEMO_GENERATED.md"


def test_save_style_comparison_artifacts_skips_copy_when_demo_output_already_target(
    tmp_path,
):
    style_dir = tmp_path / "style_demo"
    style_dir.mkdir()
    source = tmp_path / "guide.md"
    source.write_text("# Guide\n", encoding="utf-8")
    demo_target = style_dir / "DEMO_GENERATED.md"
    demo_target.write_text("existing", encoding="utf-8")

    _, demo_path = cli._save_style_comparison_artifacts(
        str(source),
        str(demo_target),
        style_source_name="demo",
    )

    assert Path(demo_path) == demo_target
    assert demo_target.read_text(encoding="utf-8") == "existing"


def test_cli_verbose_repo_scan_prints_clone_and_write(monkeypatch, tmp_path, capsys):
    def fake_clone_run(cmd, check, stdout, stderr, text, timeout, env):
        destination = Path(cmd[-1])
        destination.mkdir(parents=True, exist_ok=True)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli.subprocess, "run", fake_clone_run)
    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "verbose.md"
    rc = cli.main(
        ["--repo-url", "https://github.com/example/role.git", "-o", str(out), "-v"]
    )
    captured = capsys.readouterr()

    assert rc == 0
    assert "Cloning: https://github.com/example/role.git" in captured.out
    assert "Wrote:" in captured.out


def test_cli_verbose_local_scan_prints_style_and_demo_paths(
    monkeypatch, tmp_path, capsys
):
    """Covers the verbose style_source_path and style_demo_path print lines (local role path flow)."""
    role_dir = tmp_path / "role"
    role_dir.mkdir()
    style_guide = tmp_path / "guide.md"
    style_guide.write_text(
        "# Style\n\n## Role Variables\n\nsome body\n", encoding="utf-8"
    )
    out = tmp_path / "out.md"

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    rc = cli.main(
        [str(role_dir), "--style-readme", str(style_guide), "-o", str(out), "-v"]
    )
    captured = capsys.readouterr()

    assert rc == 0
    assert "Wrote:" in captured.out
    assert "Style guide source:" in captured.out
    assert "Generated demo copy:" in captured.out
