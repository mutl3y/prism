from prism.scanner_submodules import task_parser


def test_is_relpath_excluded_matches_top_level_directory_pattern():
    assert task_parser._is_relpath_excluded("tasks/main.yml", ["tasks"])


def test_is_path_excluded_returns_false_for_paths_outside_role(tmp_path):
    role_root = tmp_path / "role"
    role_root.mkdir()
    outside_file = tmp_path / "outside.yml"
    outside_file.write_text("---\n", encoding="utf-8")

    assert not task_parser._is_path_excluded(outside_file, role_root, ["tasks/**"])


def test_iter_role_include_targets_accepts_string_and_skips_non_string_ref():
    task = {
        "include_role": "demo.role",
        "import_role": {"name": 123},
    }

    assert task_parser._iter_role_include_targets(task) == ["demo.role"]


def test_iter_dynamic_role_include_targets_accepts_templated_string_only():
    task = {
        "include_role": "{{ role_ref }}",
        "import_role": {"name": 123},
    }

    assert task_parser._iter_dynamic_role_include_targets(task) == ["{{ role_ref }}"]


def test_resolve_task_include_rejects_absolute_file_outside_role(tmp_path):
    role_root = tmp_path / "role"
    current_file = role_root / "tasks" / "main.yml"
    current_file.parent.mkdir(parents=True)
    current_file.write_text("---\n", encoding="utf-8")

    outside = tmp_path / "outside.yml"
    outside.write_text("---\n", encoding="utf-8")

    assert (
        task_parser._resolve_task_include(role_root, current_file, str(outside)) is None
    )


def test_collect_task_files_skips_excluded_resolved_include(tmp_path):
    role_root = tmp_path / "role"
    tasks_dir = role_root / "tasks"
    tasks_dir.mkdir(parents=True)

    (tasks_dir / "main.yml").write_text(
        "---\n" "- name: include child\n" "  include_tasks: child.yml\n",
        encoding="utf-8",
    )
    (tasks_dir / "child.yml").write_text(
        "---\n" "- name: child task\n" "  debug:\n" "    msg: ok\n",
        encoding="utf-8",
    )

    discovered = task_parser._collect_task_files(
        role_root,
        exclude_paths=["tasks/child.yml"],
    )

    assert [str(path.relative_to(role_root)) for path in discovered] == [
        "tasks/main.yml"
    ]


def test_extract_role_notes_from_comments_short_aliases_cover_branches(tmp_path):
    role_root = tmp_path / "role"
    tasks_dir = role_root / "tasks"
    tasks_dir.mkdir(parents=True)

    (tasks_dir / "main.yml").write_text(
        "---\n" "- name: noop\n" "  debug:\n" "    msg: ok\n",
        encoding="utf-8",
    )
    (role_root / "defaults").mkdir()
    (role_root / "vars").mkdir()
    (role_root / "handlers").mkdir()
    (role_root / "defaults" / "main.yml").write_text(
        "# prism~deprecated: old setting\n"
        "# prism~additional: extra details\n"
        "# prism~notes: regular note\n",
        encoding="utf-8",
    )

    notes = task_parser._extract_role_notes_from_comments(str(role_root))

    assert "old setting" in notes["deprecations"]
    assert "extra details" in notes["additionals"]
    assert "regular note" in notes["notes"]


def test_extract_task_annotations_for_file_long_syntax_with_continuation():
    lines = [
        "# prism~task: Install package | runbook: run apt update",
        "# then install packages",
        "- name: Install package",
    ]

    implicit, explicit = task_parser._extract_task_annotations_for_file(lines)

    assert implicit == []
    assert "Install package" in explicit
    assert explicit["Install package"][0]["kind"] == "runbook"
    assert "then install packages" in explicit["Install package"][0]["text"]


def test_detect_task_module_skips_with_items_keys():
    task = {
        "with_items": ["a"],
        "ansible.builtin.copy": {"src": "a", "dest": "b"},
    }

    assert task_parser._detect_task_module(task) == "ansible.builtin.copy"


def test_compact_task_parameters_truncates_long_multiline_strings():
    long_body = "x" * 120
    task = {"shell": f"echo hi\n{long_body}"}

    rendered = task_parser._compact_task_parameters(task, "shell")

    assert "\n" not in rendered
    assert rendered.endswith("...")


def test_collect_task_handler_catalog_fallback_and_excluded_paths(tmp_path):
    role_root = tmp_path / "role"
    tasks_dir = role_root / "tasks"
    handlers_dir = role_root / "handlers"
    tasks_dir.mkdir(parents=True)
    handlers_dir.mkdir(parents=True)

    (tasks_dir / "a.yml").write_text(
        "---\n"
        "- name: include child\n"
        "  include_tasks: child.yml\n"
        "- name: include excluded\n"
        "  include_tasks: excluded.yml\n",
        encoding="utf-8",
    )
    (tasks_dir / "child.yml").write_text(
        "---\n" "- name: loop back\n" "  include_tasks: a.yml\n",
        encoding="utf-8",
    )
    (tasks_dir / "excluded.yml").write_text(
        "---\n" "- name: excluded\n" "  debug:\n" "    msg: nope\n",
        encoding="utf-8",
    )
    (handlers_dir / "main.yml").write_text(
        "---\n" "- name: restart service\n" "  debug:\n" "    msg: restart\n",
        encoding="utf-8",
    )

    task_catalog, handler_catalog = task_parser._collect_task_handler_catalog(
        str(role_root),
        exclude_paths=["tasks/excluded.yml", "handlers/main.yml"],
    )

    task_names = [entry["name"] for entry in task_catalog]
    assert "include child" in task_names
    assert "loop back" in task_names
    assert "excluded" not in task_names
    assert handler_catalog == []


def test_collect_molecule_scenarios_skips_non_dict_platform_entries(tmp_path):
    role_root = tmp_path / "role"
    scenario_dir = role_root / "molecule" / "default"
    scenario_dir.mkdir(parents=True)
    (scenario_dir / "molecule.yml").write_text(
        "---\n"
        "driver:\n"
        "  name: podman\n"
        "verifier:\n"
        "  name: ansible\n"
        "platforms:\n"
        "  - invalid\n"
        "  - name: instance\n"
        "    image: quay.io/example/image:latest\n",
        encoding="utf-8",
    )

    scenarios = task_parser._collect_molecule_scenarios(str(role_root))

    assert len(scenarios) == 1
    assert scenarios[0]["platforms"] == ["instance (quay.io/example/image:latest)"]


def test_extract_role_features_ignores_non_string_notify_items(tmp_path):
    role_root = tmp_path / "role"
    tasks_dir = role_root / "tasks"
    tasks_dir.mkdir(parents=True)

    (tasks_dir / "main.yml").write_text(
        "---\n"
        "- name: notify mixed list\n"
        "  ansible.builtin.debug:\n"
        "    msg: hello\n"
        "  notify:\n"
        "    - restart app\n"
        "    - 123\n",
        encoding="utf-8",
    )

    features = task_parser.extract_role_features(str(role_root))

    assert features["handlers_notified"] == "restart app"
