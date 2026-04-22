"""Tests verifying extract_defaults.py is free of Ansible-specific module names."""

from __future__ import annotations

import inspect


def _source_text():
    from prism.scanner_plugins.policies import extract_defaults

    return inspect.getsource(extract_defaults)


class TestExtractDefaultsDomainNeutrality:
    """Ensure extract_defaults stays domain-neutral (no ansible.builtin refs)."""

    def test_no_ansible_builtin_in_module_constants(self):
        from prism.scanner_plugins.policies.extract_defaults import (
            TASK_INCLUDE_KEYS,
            ROLE_INCLUDE_KEYS,
            INCLUDE_VARS_KEYS,
            SET_FACT_KEYS,
        )

        all_keys = (
            TASK_INCLUDE_KEYS | ROLE_INCLUDE_KEYS | INCLUDE_VARS_KEYS | SET_FACT_KEYS
        )
        ansible_hits = {k for k in all_keys if "ansible.builtin" in k}
        assert (
            ansible_hits == set()
        ), f"Found ansible.builtin entries in defaults: {ansible_hits}"

    def test_generic_keys_present(self):
        from prism.scanner_plugins.policies.extract_defaults import (
            TASK_INCLUDE_KEYS,
            ROLE_INCLUDE_KEYS,
            INCLUDE_VARS_KEYS,
            SET_FACT_KEYS,
        )

        assert "include_tasks" in TASK_INCLUDE_KEYS
        assert "import_tasks" in TASK_INCLUDE_KEYS
        assert "include_role" in ROLE_INCLUDE_KEYS
        assert "import_role" in ROLE_INCLUDE_KEYS
        assert "include_vars" in INCLUDE_VARS_KEYS
        assert "set_fact" in SET_FACT_KEYS

    def test_default_policy_plugin_uses_generic_keys_only(self):
        from prism.scanner_plugins.policies.extract_defaults import (
            DefaultTaskLineParsingPolicyPlugin,
        )

        plugin = DefaultTaskLineParsingPolicyPlugin()
        all_keys = (
            plugin.TASK_INCLUDE_KEYS
            | plugin.ROLE_INCLUDE_KEYS
            | plugin.INCLUDE_VARS_KEYS
            | plugin.SET_FACT_KEYS
        )
        ansible_hits = {k for k in all_keys if "ansible.builtin" in k}
        assert (
            ansible_hits == set()
        ), f"Default plugin contains ansible.builtin: {ansible_hits}"

    def test_docstring_not_domain_neutral(self):
        from prism.scanner_plugins.policies import extract_defaults

        doc = extract_defaults.__doc__ or ""
        assert (
            "Domain-neutral" not in doc
        ), "Docstring should not claim 'Domain-neutral'"

    def test_ansible_plugin_has_builtin_variants(self):
        from prism.scanner_plugins.ansible.extract_policies import (
            AnsibleTaskLineParsingPolicyPlugin,
        )

        plugin = AnsibleTaskLineParsingPolicyPlugin()
        assert "ansible.builtin.include_tasks" in plugin.TASK_INCLUDE_KEYS
        assert "ansible.builtin.import_tasks" in plugin.TASK_INCLUDE_KEYS
        assert "ansible.builtin.include_role" in plugin.ROLE_INCLUDE_KEYS
        assert "ansible.builtin.import_role" in plugin.ROLE_INCLUDE_KEYS
        assert "ansible.builtin.include_vars" in plugin.INCLUDE_VARS_KEYS
        assert "ansible.builtin.set_fact" in plugin.SET_FACT_KEYS

    def test_ansible_plugin_superset_of_defaults(self):
        from prism.scanner_plugins.policies.extract_defaults import (
            DefaultTaskLineParsingPolicyPlugin,
        )
        from prism.scanner_plugins.ansible.extract_policies import (
            AnsibleTaskLineParsingPolicyPlugin,
        )

        default_p = DefaultTaskLineParsingPolicyPlugin()
        ansible_p = AnsibleTaskLineParsingPolicyPlugin()

        assert default_p.TASK_INCLUDE_KEYS <= ansible_p.TASK_INCLUDE_KEYS
        assert default_p.ROLE_INCLUDE_KEYS <= ansible_p.ROLE_INCLUDE_KEYS
        assert default_p.INCLUDE_VARS_KEYS <= ansible_p.INCLUDE_VARS_KEYS
        assert default_p.SET_FACT_KEYS <= ansible_p.SET_FACT_KEYS
