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
    (role / ".ansible_role_doc.yml").write_text(
        "readme:\n  include_sections:\n    - Requirements\n",
        encoding="utf-8",
    )

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
    cfg_sidecar = tmp_path / "style_readme" / "ROLE_README_CONFIG.yml"
    assert source_sidecar.exists()
    assert source_sidecar.read_text(encoding="utf-8") == "# Guide\n"
    assert demo_sidecar.exists()
    assert demo_sidecar.read_text(encoding="utf-8") == "generated"
    assert cfg_sidecar.exists()
    assert "include_sections" in cfg_sidecar.read_text(encoding="utf-8")


def test_cli_style_guide_skeleton_defaults_to_local_style_source(monkeypatch, tmp_path):
    calls: dict = {}

    role = tmp_path / "role"
    role.mkdir()

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        calls["style_guide_skeleton"] = kwargs.get("style_guide_skeleton")
        calls["style_readme_path"] = kwargs.get("style_readme_path")
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "skeleton.md"
    rc = cli.main([str(role), "--create-style-guide", "-o", str(out)])

    assert rc == 0
    assert calls["style_guide_skeleton"] is True
    assert calls["style_readme_path"].endswith("STYLE_GUIDE_SOURCE.md")


def test_cli_style_guide_skeleton_prefers_cwd_source(monkeypatch, tmp_path):
    calls: dict = {}

    role = tmp_path / "role"
    role.mkdir()
    cwd_style = tmp_path / "STYLE_GUIDE_SOURCE.md"
    cwd_style.write_text("# CWD guide\n", encoding="utf-8")

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        calls["style_guide_skeleton"] = kwargs.get("style_guide_skeleton")
        calls["style_readme_path"] = kwargs.get("style_readme_path")
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)
    monkeypatch.chdir(tmp_path)

    out = tmp_path / "skeleton-cwd.md"
    rc = cli.main([str(role), "--create-style-guide", "-o", str(out)])

    assert rc == 0
    assert calls["style_guide_skeleton"] is True
    assert calls["style_readme_path"] == str(cwd_style.resolve())


def test_cli_style_guide_skeleton_prefers_env_source(monkeypatch, tmp_path):
    calls: dict = {}

    role = tmp_path / "role"
    role.mkdir()

    env_style = tmp_path / "env-style.md"
    env_style.write_text("# ENV guide\n", encoding="utf-8")

    cwd_style = tmp_path / "STYLE_GUIDE_SOURCE.md"
    cwd_style.write_text("# CWD guide\n", encoding="utf-8")

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        calls["style_guide_skeleton"] = kwargs.get("style_guide_skeleton")
        calls["style_readme_path"] = kwargs.get("style_readme_path")
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANSIBLE_ROLE_DOC_STYLE_SOURCE", str(env_style))

    out = tmp_path / "skeleton-env.md"
    rc = cli.main([str(role), "--create-style-guide", "-o", str(out)])

    assert rc == 0
    assert calls["style_guide_skeleton"] is True
    assert calls["style_readme_path"] == str(env_style.resolve())


def test_cli_vars_seed_is_forwarded(monkeypatch, tmp_path):
    calls: dict = {}

    role = tmp_path / "role"
    seed_file = tmp_path / "group_vars.yml"
    role.mkdir()
    seed_file.write_text("---\nexample: value\n", encoding="utf-8")

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        calls["vars_seed_paths"] = kwargs.get("vars_seed_paths")
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "seeded.md"
    rc = cli.main(
        [
            str(role),
            "--vars-seed",
            str(seed_file),
            "--vars-seed",
            str(tmp_path),
            "-o",
            str(out),
        ]
    )

    assert rc == 0
    assert calls["vars_seed_paths"] == [str(seed_file), str(tmp_path)]


def test_cli_concise_and_scanner_report_flags_are_forwarded(monkeypatch, tmp_path):
    calls: dict = {}

    role = tmp_path / "role"
    report = tmp_path / "SCAN_REPORT.md"
    role.mkdir()

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        calls["concise_readme"] = kwargs.get("concise_readme")
        calls["scanner_report_output"] = kwargs.get("scanner_report_output")
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "concise.md"
    rc = cli.main(
        [
            str(role),
            "--concise-readme",
            "--scanner-report-output",
            str(report),
            "-o",
            str(out),
        ]
    )

    assert rc == 0
    assert calls["concise_readme"] is True
    assert calls["scanner_report_output"] == str(report)


def test_cli_variable_sources_defaults_only_is_forwarded(monkeypatch, tmp_path):
    calls: dict = {}

    role = tmp_path / "role"
    role.mkdir()

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        calls["include_vars_main"] = kwargs.get("include_vars_main")
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "defaults-only.md"
    rc = cli.main(
        [
            str(role),
            "--variable-sources",
            "defaults-only",
            "-o",
            str(out),
        ]
    )

    assert rc == 0
    assert calls["include_vars_main"] is False


def test_cli_variable_sources_default_excludes_vars(monkeypatch, tmp_path):
    calls: dict = {}

    role = tmp_path / "role"
    role.mkdir()

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        calls["include_vars_main"] = kwargs.get("include_vars_main")
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "default-sources.md"
    rc = cli.main([str(role), "-o", str(out)])

    assert rc == 0
    assert calls["include_vars_main"] is False


def test_cli_scanner_report_link_flag_is_forwarded(monkeypatch, tmp_path):
    calls: dict = {}

    role = tmp_path / "role"
    role.mkdir()

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        calls["include_scanner_report_link"] = kwargs.get("include_scanner_report_link")
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "no-link.md"
    rc = cli.main(
        [
            str(role),
            "--concise-readme",
            "--no-include-scanner-report-link",
            "-o",
            str(out),
        ]
    )

    assert rc == 0
    assert calls["include_scanner_report_link"] is False


def test_cli_adopt_style_headings_flag_is_forwarded(monkeypatch, tmp_path):
    calls: dict = {}

    role = tmp_path / "role"
    role.mkdir()

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        calls["adopt_style_headings"] = kwargs.get("adopt_style_headings")
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "adopt-headings.md"
    rc = cli.main([str(role), "--adopt-style-headings", "-o", str(out)])

    assert rc == 0
    assert calls["adopt_style_headings"] is True


def test_cli_keep_unknown_style_sections_flag_is_forwarded(monkeypatch, tmp_path):
    calls: dict = {}

    role = tmp_path / "role"
    role.mkdir()

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        calls["keep_unknown_style_sections"] = kwargs.get(
            "keep_unknown_style_sections"
        )
        Path(output).write_text("generated", encoding="utf-8")
        return str(Path(output).resolve())

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "keep-unknown.md"
    rc = cli.main([str(role), "--keep-unknown-style-sections", "-o", str(out)])

    assert rc == 0
    assert calls["keep_unknown_style_sections"] is True


def test_cli_repo_style_readme_path_is_resolved(monkeypatch, tmp_path):
    calls: dict = {}

    def fake_clone_run(cmd, check, stdout, stderr, text, timeout, env):
        destination = Path(cmd[-1])
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "README.md").write_text(
            "Guide\n"
            "=====\n\n"
            "Unknown Custom Notes\n"
            "--------------------\n\n"
            "Human-authored unknown section body.\n",
            encoding="utf-8",
        )
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
    keep_demo_sidecar = tmp_path / "style_role" / "DEMO_GENERATED_KEEP_UNKNOWN.md"
    cfg_sidecar = tmp_path / "style_role" / "ROLE_README_CONFIG.yml"
    assert source_sidecar.exists()
    assert "Unknown Custom Notes" in source_sidecar.read_text(encoding="utf-8")
    assert demo_sidecar.exists()
    assert demo_sidecar.read_text(encoding="utf-8") == "generated"
    assert keep_demo_sidecar.exists()
    assert keep_demo_sidecar.read_text(encoding="utf-8") == "generated"
    assert cfg_sidecar.exists()
    cfg_text = cfg_sidecar.read_text(encoding="utf-8")
    assert "unknown_style_sections" in cfg_text
    assert "title: Unknown Custom Notes" in cfg_text
    assert "Human-authored unknown section body." in cfg_text


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


def test_build_sparse_clone_paths_returns_empty_for_repo_root():
    assert cli._build_sparse_clone_paths(".", None) == []
    assert cli._build_sparse_clone_paths("", "README.md") == []


def test_build_sparse_clone_paths_collects_role_and_style_path():
    assert cli._build_sparse_clone_paths("roles/demo", "README.md") == [
        "roles/demo",
        "README.md",
    ]
    assert cli._build_sparse_clone_paths("roles/demo", "roles/demo") == [
        "roles/demo"
    ]


def test_clone_repo_uses_sparse_checkout_when_paths_provided(monkeypatch, tmp_path):
    commands: list[list[str]] = []

    def fake_clone_run(cmd, check, stdout, stderr, text, timeout, env):
        commands.append(cmd)
        if cmd[:2] == ["git", "clone"]:
            destination = Path(cmd[-1])
            destination.mkdir(parents=True, exist_ok=True)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_clone_run)

    cli._clone_repo(
        "https://github.com/example/role.git",
        tmp_path / "repo",
        sparse_paths=["roles/demo", "README.md"],
    )

    assert len(commands) == 2
    assert "--filter=blob:none" in commands[0]
    assert "--sparse" in commands[0]
    assert commands[1][:5] == [
        "git",
        "-C",
        str(tmp_path / "repo"),
        "sparse-checkout",
        "set",
    ]
    assert "--no-cone" in commands[1]
    assert "roles/demo" in commands[1]
    assert "README.md" in commands[1]


def test_clone_repo_falls_back_when_sparse_checkout_fails(monkeypatch, tmp_path):
    commands: list[list[str]] = []

    def fake_clone_run(cmd, check, stdout, stderr, text, timeout, env):
        commands.append(cmd)
        if cmd[:2] == ["git", "clone"]:
            destination = Path(cmd[-1])
            destination.mkdir(parents=True, exist_ok=True)
        if "sparse-checkout" in cmd:
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="boom")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_clone_run)

    cli._clone_repo(
        "https://github.com/example/role.git",
        tmp_path / "repo",
        sparse_paths=["roles/demo"],
    )

    clone_commands = [cmd for cmd in commands if cmd[:2] == ["git", "clone"]]
    assert len(clone_commands) == 2
    assert "--sparse" in clone_commands[0]
    assert "--filter=blob:none" in clone_commands[0]
    assert "--sparse" not in clone_commands[1]
    assert "--filter=blob:none" not in clone_commands[1]


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


def test_cli_dry_run_and_json_are_forwarded(monkeypatch, tmp_path, capsys):
    calls: dict = {}

    role = tmp_path / "role"
    role.mkdir()

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        calls["role_path"] = role_path
        calls["output_format"] = output_format
        calls["dry_run"] = kwargs.get("dry_run")
        return '{"role_name":"demo"}\n'

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "dry-run-json"
    rc = cli.main([str(role), "-f", "json", "--dry-run", "-o", str(out), "-v"])
    captured = capsys.readouterr()

    assert rc == 0
    assert calls["role_path"] == str(role)
    assert calls["output_format"] == "json"
    assert calls["dry_run"] is True
    assert not out.exists()
    assert '{"role_name":"demo"}' in captured.out
    assert "Dry run: no files written." in captured.out


def test_cli_dry_run_skips_style_comparison_artifacts(monkeypatch, tmp_path):
    role = tmp_path / "role"
    role.mkdir()
    style_guide = tmp_path / "guide.md"
    style_guide.write_text("# Style\n", encoding="utf-8")

    def fake_run_scan(role_path, output, template, output_format, **kwargs):
        return "# preview\n"

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    out = tmp_path / "dry-run-output.md"
    rc = cli.main(
        [str(role), "--style-readme", str(style_guide), "--dry-run", "-o", str(out)]
    )

    assert rc == 0
    assert not out.exists()
    assert not (tmp_path / "style_guide").exists()
