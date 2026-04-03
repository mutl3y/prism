"""Guide section/body rendering helpers extracted from scanner."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token

from prism.scanner_readme.style import (
    _render_role_notes_section,
    _render_role_variables_for_style,
    _render_template_overrides_section,
    _render_variable_summary_section,
)
from prism.scanner_readme.doc_insights import parse_comma_values
from prism.scanner_extract.requirements import normalize_requirements
from prism.scanner_config.patterns import load_pattern_config

_POLICY = load_pattern_config()
_VARIABLE_GUIDANCE_KEYWORDS: tuple[str, ...] = tuple(
    _POLICY["variable_guidance"]["priority_keywords"]
)
_VARIABLE_GUIDANCE_KEYWORDS_OVERRIDE: ContextVar[tuple[str, ...] | None] = ContextVar(
    "prism_readme_variable_guidance_keywords_override",
    default=None,
)


@contextmanager
def variable_guidance_keywords_scope(
    variable_guidance_keywords: tuple[str, ...] | None,
):
    """Apply request-scoped variable-guidance keywords for README rendering."""

    token: Token[tuple[str, ...] | None] = _VARIABLE_GUIDANCE_KEYWORDS_OVERRIDE.set(
        variable_guidance_keywords
    )
    try:
        yield
    finally:
        _VARIABLE_GUIDANCE_KEYWORDS_OVERRIDE.reset(token)


def refresh_policy_derived_state(policy: dict) -> None:
    """Refresh default variable-guidance keywords for legacy in-process callers."""

    global _POLICY
    global _VARIABLE_GUIDANCE_KEYWORDS

    _POLICY = policy
    _VARIABLE_GUIDANCE_KEYWORDS = tuple(
        policy.get("variable_guidance", {}).get("priority_keywords") or ()
    )


def _render_guide_identity_sections(
    section_id: str,
    role_name: str,
    description: str,
    requirements: list,
    galaxy: dict,
    metadata: dict,
) -> str | None:
    """Render style-guide sections focused on role identity and metadata."""
    if section_id == "galaxy_info":
        return _render_identity_galaxy_info_section(role_name, description, galaxy)
    if section_id == "requirements":
        return _render_identity_requirements_section(requirements)
    if section_id == "installation":
        return _render_identity_installation_section(role_name, galaxy)
    if section_id == "license":
        return _render_identity_license_section(galaxy)
    if section_id == "author_information":
        return _render_identity_author_section(galaxy)
    if section_id == "license_author":
        return _render_identity_license_author_section(galaxy)
    if section_id == "sponsors":
        return "No sponsorship metadata detected for this role."
    if section_id == "purpose":
        return _render_identity_purpose_section(metadata)
    if section_id == "role_notes":
        return _render_role_notes_section(metadata.get("role_notes"))
    return None


def _render_identity_galaxy_info_section(
    role_name: str,
    description: str,
    galaxy: dict,
) -> str:
    """Render Galaxy metadata section details."""
    if not galaxy:
        return "No Galaxy metadata found."
    lines = [
        f"- **Role name**: {galaxy.get('role_name', role_name)}",
        f"- **Description**: {galaxy.get('description', description)}",
        f"- **License**: {galaxy.get('license', 'N/A')}",
        f"- **Min Ansible Version**: {galaxy.get('min_ansible_version', 'N/A')}",
    ]
    tags = galaxy.get("galaxy_tags")
    if tags:
        lines.append(f"- **Tags**: {', '.join(tags)}")
    return "\n".join(lines)


def _render_identity_requirements_section(requirements: list) -> str:
    """Render normalized requirements bullet list."""
    requirement_lines = normalize_requirements(requirements)
    if not requirement_lines:
        return "No additional requirements."
    return "\n".join(f"- {line}" for line in requirement_lines)


def _render_identity_installation_section(role_name: str, galaxy: dict) -> str:
    """Render installation guidance using Ansible Galaxy and requirements.yml."""
    install_name = str(galaxy.get("role_name") or role_name)
    return (
        "Install the role with Ansible Galaxy:\n\n"
        "```bash\n"
        f"ansible-galaxy install {install_name}\n"
        "```\n\n"
        "Or pin it in `requirements.yml`:\n\n"
        "```yaml\n"
        f"- src: {install_name}\n"
        "```"
    )


def _render_identity_license_section(galaxy: dict) -> str:
    """Render license value from Galaxy metadata when present."""
    if galaxy and galaxy.get("license"):
        return str(galaxy.get("license"))
    return "N/A"


def _render_identity_author_section(galaxy: dict) -> str:
    """Render author value from Galaxy metadata when present."""
    if galaxy and galaxy.get("author"):
        return str(galaxy.get("author"))
    return "N/A"


def _render_identity_license_author_section(galaxy: dict) -> str:
    """Render combined license/author identity section."""
    license_value = str(galaxy.get("license", "N/A")) if galaxy else "N/A"
    author_value = str(galaxy.get("author", "N/A")) if galaxy else "N/A"
    return f"License: {license_value}\n\nAuthor: {author_value}"


def _render_identity_purpose_section(metadata: dict) -> str:
    """Render inferred purpose and capabilities from doc insights."""
    insights = metadata.get("doc_insights") or {}
    lines = [insights.get("purpose_summary", "No inferred role summary available.")]
    capabilities = insights.get("capabilities", [])
    if capabilities:
        lines.extend(["", "Capabilities:"])
        lines.extend(f"- {capability}" for capability in capabilities)
    return "\n".join(lines)


def _render_guide_variable_sections(
    section_id: str,
    variables: dict,
    metadata: dict,
    variable_guidance_keywords: tuple[str, ...] | None = None,
) -> str | None:
    """Render style-guide sections focused on variable inventory and guidance."""
    if section_id == "variable_summary":
        return _render_variable_summary_section(metadata)
    if section_id == "variable_guidance":
        return _render_variable_guidance_section(
            metadata,
            variable_guidance_keywords=variable_guidance_keywords,
        )
    if section_id == "template_overrides":
        return _render_template_overrides_section(metadata)
    if section_id == "role_variables":
        return _render_role_variables_for_style(variables, metadata)
    return None


def _render_variable_guidance_section(
    metadata: dict,
    variable_guidance_keywords: tuple[str, ...] | None = None,
) -> str:
    """Render recommended variable override candidates."""
    rows = metadata.get("variable_insights") or []
    if not rows:
        return "No variable guidance available because no variable defaults were discovered."

    keywords = variable_guidance_keywords
    if keywords is None:
        keywords = _VARIABLE_GUIDANCE_KEYWORDS_OVERRIDE.get()
    if keywords is None:
        keywords = _VARIABLE_GUIDANCE_KEYWORDS
    priority = [
        row for row in rows if any(keyword in row["name"] for keyword in keywords)
    ]
    if not priority:
        priority = rows[:5]
    lines = ["Recommended variables to tune:"]
    for row in priority[:8]:
        lines.append(
            f"- `{row['name']}` (default: `{str(row['default']).replace('`', "'")}`)"
        )
    lines.append("")
    lines.append("Use these as initial overrides for environment-specific behavior.")
    return "\n".join(lines)


def _render_guide_task_sections(
    section_id: str,
    default_filters: list,
    metadata: dict,
) -> str | None:
    """Render style-guide sections focused on task, handler, and test activity."""
    if section_id == "task_summary":
        return _render_task_summary_section(metadata)
    if section_id == "example_usage":
        return _render_example_usage_section(metadata)
    if section_id == "local_testing":
        return _render_local_testing_section(metadata)
    if section_id == "handlers":
        return _render_handlers_section(metadata)
    if section_id == "faq_pitfalls":
        return _render_faq_pitfalls_section(default_filters, metadata)
    return None


def _render_task_summary_section(metadata: dict) -> str:
    """Render task-summary section details including optional parse failures/catalog."""
    summary = (metadata.get("doc_insights") or {}).get("task_summary", {})
    if not summary:
        return "No task summary available."

    yaml_parse_failures = metadata.get("yaml_parse_failures") or []
    unconstrained_dynamic_task_includes = (
        metadata.get("unconstrained_dynamic_task_includes") or []
    )
    unconstrained_dynamic_role_includes = (
        metadata.get("unconstrained_dynamic_role_includes") or []
    )
    unconstrained_dynamic_includes = [
        *unconstrained_dynamic_task_includes,
        *unconstrained_dynamic_role_includes,
    ]
    lines = [
        f"- **Task files scanned**: {summary.get('task_files_scanned', 0)}",
        f"- **Tasks scanned**: {summary.get('tasks_scanned', 0)}",
        f"- **Recursive includes**: {summary.get('recursive_task_includes', 0)}",
        f"- **Unique modules**: {summary.get('module_count', 0)}",
        f"- **Handlers referenced**: {summary.get('handler_count', 0)}",
        f"- **YAML parse failures**: {len(yaml_parse_failures)}",
        f"- **Unconstrained dynamic task includes**: {len(unconstrained_dynamic_task_includes)}",
        f"- **Unconstrained dynamic role includes**: {len(unconstrained_dynamic_role_includes)}",
    ]
    if yaml_parse_failures:
        lines.extend(["", "Parse failures detected:"])
        for item in yaml_parse_failures[:5]:
            file_name = str(item.get("file") or "<unknown>")
            line = item.get("line")
            column = item.get("column")
            location = (
                f"{file_name}:{line}:{column}"
                if line is not None and column is not None
                else file_name
            )
            error_text = str(item.get("error") or "parse error")
            lines.append(f"- `{location}`: {error_text}")
        if len(yaml_parse_failures) > 5:
            lines.append(
                f"- ... and {len(yaml_parse_failures) - 5} additional parse failures"
            )

    if unconstrained_dynamic_includes:
        lines.extend(["", "Unconstrained dynamic include hazards detected:"])
        for item in unconstrained_dynamic_includes[:5]:
            if not isinstance(item, dict):
                continue
            file_name = str(item.get("file") or "<unknown>")
            task_name = str(item.get("task") or "(unnamed task)")
            target = str(item.get("target") or "")
            lines.append(f"- `{file_name}` / {task_name}: `{target}`")
        if len(unconstrained_dynamic_includes) > 5:
            lines.append(
                "- ... and "
                f"{len(unconstrained_dynamic_includes) - 5} additional unconstrained dynamic includes"
            )

    task_catalog = metadata.get("task_catalog") or []
    if metadata.get("detailed_catalog") and task_catalog:
        lines.extend(
            [
                "",
                "Detailed task catalog:",
                "",
                "| File | Task | Module | Parameters |",
                "| --- | --- | --- | --- |",
            ]
        )
        for entry in task_catalog:
            if not isinstance(entry, dict):
                continue
            lines.append(
                f"| `{entry.get('file', '')}` | {entry.get('name', '')} | `{entry.get('module', '')}` | {entry.get('parameters', '')} |"
            )

    return "\n".join(lines)


def _render_example_usage_section(metadata: dict) -> str:
    """Render inferred example playbook block for style guide output."""
    example = (metadata.get("doc_insights") or {}).get("example_playbook")
    if not example:
        return "No inferred example available."
    return f"```yaml\n{example}\n```"


def _build_molecule_scenario_lines(metadata: dict) -> list[str]:
    """Render optional molecule scenario bullet list for testing guidance."""
    molecule_scenarios = metadata.get("molecule_scenarios") or []
    scenario_lines: list[str] = []
    if molecule_scenarios:
        scenario_lines.extend(["", "Molecule scenarios detected:"])
        for scenario in molecule_scenarios:
            if not isinstance(scenario, dict):
                continue
            name = str(scenario.get("name") or "default")
            driver = str(scenario.get("driver") or "unknown")
            verifier = str(scenario.get("verifier") or "unknown")
            platforms = scenario.get("platforms") or []
            platform_summary = ", ".join(
                str(item) for item in platforms if isinstance(item, str)
            )
            if not platform_summary:
                platform_summary = "unspecified"
            scenario_lines.append(
                f"- `{name}` (driver: `{driver}`, verifier: `{verifier}`, platforms: {platform_summary})"
            )
    return scenario_lines


def _render_local_testing_section(metadata: dict) -> str:
    """Render local testing guidance including role-test and molecule hints."""
    role_tests = metadata.get("tests") or []
    scenario_lines = _build_molecule_scenario_lines(metadata)

    if role_tests:
        inventory = next(
            (item for item in role_tests if "inventory" in item), role_tests[0]
        )
        playbook = next(
            (
                item
                for item in role_tests
                if item.endswith(".yml") or item.endswith(".yaml")
            ),
            role_tests[0],
        )
        guidance = (
            "Run a quick local validation using bundled role tests:\n\n"
            "```bash\n"
            f"ansible-playbook -i {inventory} {playbook}\n"
            "```"
        )
        if scenario_lines:
            guidance += "\n" + "\n".join(scenario_lines)
        return guidance

    fallback = "Run `tox` or `pytest -q` locally to validate scanner behavior and generated output."
    if scenario_lines:
        fallback += "\n" + "\n".join(scenario_lines)
    return fallback


def _render_handlers_section(metadata: dict) -> str:
    """Render handler summary and optional handler catalog for style output."""
    features = metadata.get("features") or {}
    handler_names = parse_comma_values(str(features.get("handlers_notified", "none")))
    handler_files = metadata.get("handlers") or []
    summary = (metadata.get("doc_insights") or {}).get("task_summary", {})
    if not handler_names and not handler_files and not summary:
        return "No handler activity was detected."

    lines = [
        f"- **Handler files detected**: {len(handler_files)}",
        f"- **Handlers referenced by tasks**: {summary.get('handler_count', len(handler_names))}",
    ]
    if handler_names:
        lines.append("- **Named handlers**: " + ", ".join(handler_names))
    if handler_files:
        lines.append("")
        lines.append("Handler definition files:")
        lines.extend(f"- `{path}`" for path in handler_files)

    handler_catalog = metadata.get("handler_catalog") or []
    if metadata.get("detailed_catalog") and handler_catalog:
        lines.extend(
            [
                "",
                "Detailed handler catalog:",
                "",
                "| File | Handler | Module | Parameters |",
                "| --- | --- | --- | --- |",
            ]
        )
        for entry in handler_catalog:
            if not isinstance(entry, dict):
                continue
            lines.append(
                f"| `{entry.get('file', '')}` | {entry.get('name', '')} | `{entry.get('module', '')}` | {entry.get('parameters', '')} |"
            )

    return "\n".join(lines)


def _render_faq_pitfalls_section(default_filters: list, metadata: dict) -> str:
    """Render common scanner-detected pitfalls for role docs."""
    features = metadata.get("features") or {}
    lines = [
        "- Ensure default values are defined in `defaults/main.yml` so they are discoverable.",
        "- Keep task includes file-based when possible for better recursive scanning.",
    ]
    if int(features.get("recursive_task_includes", 0) or 0) > 0:
        lines.append(
            "- Nested include chains are detected; avoid heavily dynamic include paths when possible."
        )
    if default_filters:
        lines.append(
            "- `default()` usages are captured from source files; keep expressions readable for better docs."
        )
    return "\n".join(lines)


def _render_guide_operations_sections(section_id: str, metadata: dict) -> str | None:
    """Render style-guide sections for operational guidance."""
    if section_id == "basic_authorization":
        return (
            "Use custom vhost or directory directives to add HTTP Basic Authentication where needed.\n\n"
            "- Provide credential files such as `.htpasswd` from your playbook or a companion role.\n"
            "- Prefer explicit configuration blocks or custom templates over editing generated files in place.\n"
            "- Keep authentication settings alongside the related virtual host configuration so the access policy remains reviewable."
        )

    if section_id == "contributing":
        return (
            "Contributions are welcome.\n\n"
            "- Run `pytest -q` before submitting changes.\n"
            "- Run `tox` for full local validation and review artifact generation.\n"
            "- Update docs/templates when scanner behavior changes."
        )

    return None


def _render_guide_section_body(
    section_id: str,
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
    *,
    variable_guidance_keywords: tuple[str, ...] | None = None,
) -> str:
    """Render one canonical section body for guided README output."""
    galaxy = (
        metadata.get("meta", {}).get("galaxy_info", {}) if metadata.get("meta") else {}
    )

    rendered = _render_guide_identity_sections(
        section_id,
        role_name,
        description,
        requirements,
        galaxy,
        metadata,
    )
    if rendered is not None:
        return rendered

    rendered = _render_guide_variable_sections(
        section_id,
        variables,
        metadata,
        variable_guidance_keywords=variable_guidance_keywords,
    )
    if rendered is not None:
        return rendered

    rendered = _render_guide_task_sections(section_id, default_filters, metadata)
    if rendered is not None:
        return rendered

    rendered = _render_guide_operations_sections(section_id, metadata)
    if rendered is not None:
        return rendered

    rendered = _render_guide_misc_sections(section_id, default_filters, metadata)
    if rendered is not None:
        return rendered

    return ""


def _render_guide_misc_sections(
    section_id: str,
    default_filters: list,
    metadata: dict,
) -> str | None:
    """Render remaining style-guide sections not covered by other groups."""
    renderers = {
        "role_contents": lambda: _render_role_contents_section(metadata),
        "features": lambda: _render_features_section(metadata),
        "comparison": lambda: _render_comparison_section(metadata),
        "default_filters": lambda: _render_default_filters_section(default_filters),
    }
    renderer = renderers.get(section_id)
    return renderer() if renderer else None


def _render_role_contents_section(metadata: dict) -> str:
    """Render a compact count summary of discovered role subdirectories."""
    lines = ["The scanner collected these role subdirectories (counts):", ""]
    for key, items in metadata.items():
        if key in {
            "meta",
            "features",
            "comparison",
            "variable_insights",
            "doc_insights",
            "style_guide",
            "role_notes",
            "scanner_counters",
        }:
            continue
        if isinstance(items, list):
            lines.append(f"- **{key}**: {len(items)} files")
    return "\n".join(lines)


def _render_features_section(metadata: dict) -> str:
    """Render extracted role feature heuristics."""
    features = metadata.get("features") or {}
    if not features:
        return "No role features detected."
    return "\n".join(f"- **{key}**: {value}" for key, value in features.items())


def _render_comparison_section(metadata: dict) -> str:
    """Render baseline comparison metrics when available."""
    comparison = metadata.get("comparison")
    if not comparison:
        return "No comparison baseline provided."
    lines = [
        f"- **Baseline path**: {comparison['baseline_path']}",
        f"- **Target score**: {comparison['target_score']}/100",
        f"- **Baseline score**: {comparison['baseline_score']}/100",
        f"- **Score delta**: {comparison['score_delta']}",
        "",
    ]
    for metric, values in comparison["metrics"].items():
        lines.append(
            f"- **{metric}**: target={values['target']}, baseline={values['baseline']}, delta={values['delta']}"
        )
    return "\n".join(lines)


def _render_default_filters_section(default_filters: list) -> str:
    """Render undocumented default() findings in bullet-list form."""
    if not default_filters:
        return "No undocumented variables using `default()` were detected."
    lines = [
        "The scanner found undocumented variables using `default()` in role files:",
        "",
    ]
    for occ in default_filters:
        match = occ["match"].replace("`", "'")
        args = occ["args"].replace("`", "'")
        lines.append(f"- {occ['file']}:{occ['line_no']} - `{match}`")
        lines.append(f"  args: `{args}`")
    return "\n".join(lines)
