from pathlib import Path
from types import SimpleNamespace

from prism import cli
from prism import errors as prism_errors
from prism.scanner_io.collection_renderer import render_collection_markdown


def test_main_returns_error_for_unknown_command(monkeypatch):
    fake_parser = SimpleNamespace(
        parse_args=lambda argv: SimpleNamespace(command="bogus")
    )
    monkeypatch.setattr(cli, "build_parser", lambda: fake_parser)

    assert cli.main([]) == 2


def test_main_maps_file_not_found_to_specific_exit_code(monkeypatch, capsys):
    fake_parser = SimpleNamespace(
        parse_args=lambda argv: SimpleNamespace(command="role")
    )
    monkeypatch.setattr(cli, "build_parser", lambda: fake_parser)
    monkeypatch.setattr(
        cli,
        "_handle_role_command",
        lambda args: (_ for _ in ()).throw(FileNotFoundError("missing role")),
    )

    assert cli.main([]) == 3
    captured = capsys.readouterr()
    assert "missing role" in captured.err


def test_main_maps_permission_error_to_specific_exit_code(monkeypatch, capsys):
    fake_parser = SimpleNamespace(
        parse_args=lambda argv: SimpleNamespace(command="collection")
    )
    monkeypatch.setattr(cli, "build_parser", lambda: fake_parser)
    monkeypatch.setattr(
        cli,
        "_handle_collection_command",
        lambda args: (_ for _ in ()).throw(PermissionError("permission denied")),
    )

    assert cli.main([]) == 4
    captured = capsys.readouterr()
    assert "permission denied" in captured.err


def test_main_maps_keyboard_interrupt_to_interrupt_exit_code(monkeypatch):
    fake_parser = SimpleNamespace(
        parse_args=lambda argv: SimpleNamespace(command="repo")
    )
    monkeypatch.setattr(cli, "build_parser", lambda: fake_parser)
    monkeypatch.setattr(
        cli,
        "_handle_repo_command",
        lambda args: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    assert cli.main([]) == 130


def test_fetch_repo_contents_payload_returns_none_for_unparseable_repo_url():
    assert cli._fetch_repo_contents_payload("not-a-repo-url") is None


def test_fetch_repo_contents_payload_returns_none_on_urlopen_errors(monkeypatch):
    class _Boom:
        def __enter__(self):
            raise cli.URLError("network down")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(cli, "urlopen", lambda *args, **kwargs: _Boom())
    payload = cli._fetch_repo_contents_payload(
        "https://github.com/example/repo.git",
        repo_path="README.md",
    )
    assert payload is None


def test_fetch_repo_file_returns_none_for_empty_repo_path(tmp_path):
    out = cli._fetch_repo_file(
        "https://github.com/example/repo.git",
        "",
        tmp_path / "README.md",
    )
    assert out is None


def test_fetch_repo_file_returns_none_when_base64_decode_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(
        cli,
        "_fetch_repo_contents_payload",
        lambda *args, **kwargs: {
            "type": "file",
            "content": "broken",
            "encoding": "base64",
        },
    )
    monkeypatch.setattr(
        cli.base64,
        "b64decode",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad b64")),
    )

    out = cli._fetch_repo_file(
        "https://github.com/example/repo.git",
        "README.md",
        tmp_path / "README.md",
    )
    assert out is None


def test_repo_path_looks_like_role_returns_false_for_empty_listing():
    assert cli._repo_path_looks_like_role(set()) is False


def test_save_style_comparison_artifacts_truncates_on_section_count_limit(
    monkeypatch, tmp_path
):
    style_readme = tmp_path / "STYLE.md"
    style_readme.write_text("# Source\n", encoding="utf-8")
    generated = tmp_path / "README.generated.md"
    generated.write_text("# Generated\n", encoding="utf-8")

    monkeypatch.setattr(
        cli,
        "parse_style_readme",
        lambda _: {
            "sections": [
                {"id": "unknown", "title": "One", "body": "a"},
                {"id": "unknown", "title": "Two", "body": "b"},
            ]
        },
    )
    monkeypatch.setattr(cli, "_CAPTURE_MAX_SECTIONS", 1)

    _, demo_path = cli._save_style_comparison_artifacts(
        str(style_readme),
        str(generated),
        keep_unknown_style_sections=False,
    )

    cfg_text = (Path(demo_path).parent / "ROLE_README_CONFIG.yml").read_text(
        encoding="utf-8"
    )
    assert "truncated: true" in cfg_text


def test_cli_collection_writes_md_and_skips_invalid_role_entries(monkeypatch, tmp_path):
    payload = {
        "collection": {"metadata": {"namespace": "demo", "name": "toolkit"}},
        "summary": {"total_roles": 1, "scanned_roles": 1, "failed_roles": 0},
        "dependencies": {},
        "plugin_catalog": {},
        "failures": [],
        "roles": [
            "invalid",
            {},
            {"role": "", "rendered_readme": "# Empty\n"},
            {"role": "ok", "rendered_readme": "# Role OK\n"},
            {"role": "no-doc", "rendered_readme": "   "},
        ],
    }

    monkeypatch.setattr(cli, "load_feedback", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        cli,
        "apply_feedback_recommendations",
        lambda _feedback, include_checks: {
            "include_collection_checks": include_checks,
        },
    )
    monkeypatch.setattr("prism.api.scan_collection", lambda *args, **kwargs: payload)

    out = tmp_path / "collection.md"
    rc = cli.main(["collection", str(tmp_path), "-f", "md", "-o", str(out)])

    assert rc == 0
    assert out.exists()
    assert (out.parent / "roles" / "ok.md").read_text(encoding="utf-8") == "# Role OK\n"
    assert not (out.parent / "roles" / "no-doc.md").exists()


def test_cli_repo_feedback_load_error_returns_one(monkeypatch, tmp_path, capsys):
    def fake_clone_repo(*args, **kwargs):
        destination = args[1]
        destination.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(cli, "_clone_repo", fake_clone_repo)
    monkeypatch.setattr(
        cli,
        "load_feedback",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("bad feedback")),
    )

    rc = cli.main(
        [
            "repo",
            "--repo-url",
            "https://github.com/example/repo.git",
            "--create-style-guide",
            "--style-source",
            str(tmp_path / "style.md"),
            "--feedback-from-learn",
            str(tmp_path / "feedback.json"),
        ]
    )
    captured = capsys.readouterr()

    assert rc == 1
    assert "Error loading feedback" in captured.err


def test_cli_collection_feedback_load_error_returns_one(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        cli,
        "load_feedback",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("bad feedback")),
    )

    rc = cli.main(
        [
            "collection",
            str(tmp_path),
            "--feedback-from-learn",
            str(tmp_path / "feedback.json"),
        ]
    )
    captured = capsys.readouterr()

    assert rc == 1
    assert "Error loading feedback" in captured.err


def test_cli_role_feedback_load_error_returns_one(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        cli,
        "load_feedback",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("bad feedback")),
    )

    rc = cli.main(
        [
            "role",
            str(tmp_path / "role"),
            "--feedback-from-learn",
            str(tmp_path / "feedback.json"),
        ]
    )
    captured = capsys.readouterr()

    assert rc == 1
    assert "Error loading feedback" in captured.err


def test_cli_repo_dry_run_prints_scan_output(monkeypatch, tmp_path, capsys):
    def fake_clone_repo(*args, **kwargs):
        destination = args[1]
        destination.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(cli, "_clone_repo", fake_clone_repo)
    monkeypatch.setattr(cli, "load_feedback", lambda *_a, **_k: None)
    monkeypatch.setattr(
        cli,
        "apply_feedback_recommendations",
        lambda _feedback, include_checks: {
            "include_collection_checks": include_checks,
        },
    )
    monkeypatch.setattr(cli, "run_scan", lambda *args, **kwargs: "repo-preview")

    rc = cli.main(
        [
            "repo",
            "--repo-url",
            "https://github.com/example/repo.git",
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()

    assert rc == 0
    assert "repo-preview" in captured.out


def test_cli_collection_dry_run_prints_rendered_output(monkeypatch, tmp_path, capsys):
    payload = {
        "collection": {"metadata": {"namespace": "demo", "name": "toolkit"}},
        "summary": {"total_roles": 0, "scanned_roles": 0, "failed_roles": 0},
        "dependencies": {},
        "plugin_catalog": {},
        "roles": [],
        "failures": [],
    }
    monkeypatch.setattr(cli, "load_feedback", lambda *_a, **_k: None)
    monkeypatch.setattr(
        cli,
        "apply_feedback_recommendations",
        lambda _feedback, include_checks: {
            "include_collection_checks": include_checks,
        },
    )
    monkeypatch.setattr("prism.api.scan_collection", lambda *args, **kwargs: payload)

    rc = cli.main(["collection", str(tmp_path), "--dry-run", "-f", "md"])
    captured = capsys.readouterr()

    assert rc == 0
    assert "Collection Documentation" in captured.out


def test_main_prints_structured_error_context(monkeypatch, capsys):
    fake_parser = SimpleNamespace(
        parse_args=lambda argv: SimpleNamespace(command="repo")
    )
    monkeypatch.setattr(cli, "build_parser", lambda: fake_parser)
    monkeypatch.setattr(
        cli,
        "_handle_repo_command",
        lambda args: (_ for _ in ()).throw(
            prism_errors.PrismRuntimeError(
                code=prism_errors.REPO_TRANSPORT_FAILED,
                category=prism_errors.ERROR_CATEGORY_NETWORK,
                message="network down",
            )
        ),
    )

    rc = cli.main([])
    captured = capsys.readouterr()

    assert rc == cli._EXIT_CODE_NETWORK_ERROR
    assert "code=repo_transport_failed" in captured.err
    assert "category=network" in captured.err


def test_cli_build_parser_delegates_to_cli_parser(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(cli.cli_parser, "build_parser", lambda: sentinel)

    assert cli.build_parser() is sentinel


def test_cli_collection_presenter_delegates_to_cli_app_presenters(monkeypatch):
    monkeypatch.setattr(
        cli.cli_app_presenters,
        "render_collection_markdown_payload",
        lambda payload: "delegated-render",
    )

    assert cli._render_collection_markdown({"summary": {}}) == "delegated-render"


def test_collection_markdown_renderer_is_callable_outside_cli_layer():
    rendered = render_collection_markdown(
        {
            "collection": {
                "metadata": {
                    "namespace": "demo",
                    "name": "sample",
                    "version": "1.0.0",
                }
            },
            "summary": {"total_roles": 1, "scanned_roles": 1, "failed_roles": 0},
        }
    )

    assert "# demo.sample Collection Documentation" in rendered
    assert "- Total roles: 1" in rendered
