"""Helpers for inferred README narrative and examples."""

from __future__ import annotations


def parse_comma_values(raw_value: str) -> list[str]:
    """Parse a comma-separated feature value into a list."""
    raw = (raw_value or "").strip()
    if not raw or raw == "none":
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def build_doc_insights(
    role_name: str,
    description: str,
    metadata: dict,
    variables: dict,
    variable_insights: list[dict],
) -> dict:
    """Build inferred purpose/capability/examples for richer README output."""
    features = metadata.get("features", {}) if isinstance(metadata, dict) else {}
    modules = parse_comma_values(str(features.get("unique_modules", "none")))
    handlers = parse_comma_values(str(features.get("handlers_notified", "none")))

    capability_rules = (
        (
            ("template", "ansible.builtin.template", "copy", "ansible.builtin.copy"),
            "Deploy configuration or content files",
        ),
        (
            (
                "service",
                "ansible.builtin.service",
                "systemd",
                "ansible.builtin.systemd",
            ),
            "Manage service lifecycle and state",
        ),
        (
            ("package", "ansible.builtin.package", "apt", "yum", "dnf"),
            "Install and manage packages",
        ),
        (
            ("user", "ansible.builtin.user", "group", "ansible.builtin.group"),
            "Manage users and groups",
        ),
        (
            (
                "lineinfile",
                "ansible.builtin.lineinfile",
                "replace",
                "ansible.builtin.replace",
            ),
            "Modify existing configuration files in-place",
        ),
    )
    capabilities: list[str] = []
    module_set = set(modules)
    for keys, sentence in capability_rules:
        if any(key in module_set for key in keys):
            capabilities.append(sentence)
    if int(features.get("recursive_task_includes", 0) or 0) > 0:
        capabilities.append("Uses nested task includes for modular orchestration")
    if handlers:
        capabilities.append("Triggers role handlers based on task changes")
    if not capabilities:
        capabilities.append("Provides reusable Ansible automation tasks")

    purpose_summary = (
        description.strip()
        if description
        else (
            f"The role `{role_name}` automates setup and configuration tasks with Ansible best-practice structure."
        )
    )

    example_vars = variable_insights[:3]
    example_lines = ["- hosts: all", "  roles:", f"    - role: {role_name}"]
    if example_vars:
        example_lines.append("      vars:")
        for row in example_vars:
            example_lines.append(f"        {row['name']}: {row['default']}")
    elif variables:
        example_lines.append("      vars: {}")

    return {
        "purpose_summary": purpose_summary,
        "capabilities": capabilities,
        "task_summary": {
            "task_files_scanned": int(features.get("task_files_scanned", 0) or 0),
            "tasks_scanned": int(features.get("tasks_scanned", 0) or 0),
            "recursive_task_includes": int(
                features.get("recursive_task_includes", 0) or 0
            ),
            "module_count": len(modules),
            "handler_count": len(handlers),
        },
        "example_playbook": "\n".join(example_lines),
    }
