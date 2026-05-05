"""Tests verifying Ansible default-policy classes live under the ansible plugin home."""

from __future__ import annotations


class TestAnsibleDefaultPolicyOwnership:
    """Ansible default-policy classes are owned by scanner_plugins.ansible."""

    def test_canonical_import_path_is_ansible(self):
        from prism.scanner_plugins.ansible.default_policies import (
            AnsibleDefaultTaskAnnotationPolicyPlugin,
            AnsibleDefaultTaskLineParsingPolicyPlugin,
            AnsibleDefaultTaskTraversalPolicyPlugin,
            AnsibleDefaultVariableExtractorPolicyPlugin,
        )

        for cls in (
            AnsibleDefaultTaskAnnotationPolicyPlugin,
            AnsibleDefaultTaskLineParsingPolicyPlugin,
            AnsibleDefaultTaskTraversalPolicyPlugin,
            AnsibleDefaultVariableExtractorPolicyPlugin,
        ):
            assert cls.__module__ == "prism.scanner_plugins.ansible.default_policies"

    def test_ansible_vocabulary_lives_under_ansible(self):
        from prism.scanner_plugins.ansible.task_vocabulary import (
            INCLUDE_VARS_KEYS,
            ROLE_INCLUDE_KEYS,
            SET_FACT_KEYS,
            TASK_INCLUDE_KEYS,
        )

        assert "include_tasks" in TASK_INCLUDE_KEYS
        assert "import_tasks" in TASK_INCLUDE_KEYS
        assert "include_role" in ROLE_INCLUDE_KEYS
        assert "import_role" in ROLE_INCLUDE_KEYS
        assert "include_vars" in INCLUDE_VARS_KEYS
        assert "set_fact" in SET_FACT_KEYS

        all_keys = (
            TASK_INCLUDE_KEYS | ROLE_INCLUDE_KEYS | INCLUDE_VARS_KEYS | SET_FACT_KEYS
        )
        assert {k for k in all_keys if "ansible.builtin" in k} == set()

    def test_ansible_plugin_superset_extends_bare_vocabulary(self):
        from prism.scanner_plugins.ansible.default_policies import (
            AnsibleDefaultTaskLineParsingPolicyPlugin,
        )
        from prism.scanner_plugins.ansible.extract_policies import (
            AnsibleTaskLineParsingPolicyPlugin,
        )

        bare = AnsibleDefaultTaskLineParsingPolicyPlugin()
        canonical = AnsibleTaskLineParsingPolicyPlugin()

        assert "ansible.builtin.include_tasks" in canonical.TASK_INCLUDE_KEYS
        assert "ansible.builtin.import_tasks" in canonical.TASK_INCLUDE_KEYS
        assert "ansible.builtin.include_role" in canonical.ROLE_INCLUDE_KEYS
        assert "ansible.builtin.import_role" in canonical.ROLE_INCLUDE_KEYS
        assert "ansible.builtin.include_vars" in canonical.INCLUDE_VARS_KEYS
        assert "ansible.builtin.set_fact" in canonical.SET_FACT_KEYS

        assert bare.TASK_INCLUDE_KEYS <= canonical.TASK_INCLUDE_KEYS
        assert bare.ROLE_INCLUDE_KEYS <= canonical.ROLE_INCLUDE_KEYS
        assert bare.INCLUDE_VARS_KEYS <= canonical.INCLUDE_VARS_KEYS
        assert bare.SET_FACT_KEYS <= canonical.SET_FACT_KEYS
