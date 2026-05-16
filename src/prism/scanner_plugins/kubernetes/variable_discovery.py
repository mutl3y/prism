"""KubernetesVariableDiscoveryPlugin — Kubernetes-specific variable discovery logic."""

from __future__ import annotations

from prism.scanner_data import VariableRow


class KubernetesVariableDiscoveryPlugin:
    """Kubernetes-specific variable discovery plugin.

    Implements contract-valid, stateless variable discovery for Kubernetes
    manifests. Kubernetes does not have variables like Ansible does, so
    discovery is minimal and fail-closed. This plugin exists for API
    compatibility and future extensibility.
    """

    PLUGIN_IS_STATELESS = True

    def __init__(self, di: object | None = None) -> None:
        self._di = di

    def discover_static_variables(
        self,
        role_path: str,
        options: dict[str, object],
    ) -> tuple[VariableRow, ...]:
        """Discover static variables in Kubernetes manifests.

        For bootstrap phase, returns empty tuple because Kubernetes
        manifests do not have a variable model equivalent to Ansible roles.

        Args:
            role_path: Path to target Kubernetes manifests
            options: Discovery options (unused in bootstrap phase)

        Returns:
            Empty tuple (no static variables for Kubernetes)
        """
        del role_path, options  # Unused in bootstrap

        return ()

    def discover_referenced_variables(
        self,
        role_path: str,
        options: dict[str, object],
        readme_content: str | None = None,
    ) -> frozenset[str]:
        """Discover referenced variables in Kubernetes manifests.

        For bootstrap phase, returns empty frozenset because Kubernetes
        does not have a variable reference model.

        Args:
            role_path: Path to target Kubernetes manifests
            options: Discovery options (unused in bootstrap)
            readme_content: README content (unused in bootstrap)

        Returns:
            Empty frozenset (no referenced variables for Kubernetes)
        """
        del role_path, options, readme_content  # Unused in bootstrap

        return frozenset()

    def resolve_unresolved_variables(
        self,
        static_names: frozenset[str],
        referenced: frozenset[str],
        options: dict[str, object],
    ) -> dict[str, str]:
        """Resolve unresolved variables in Kubernetes manifests.

        For bootstrap phase, returns empty dict because Kubernetes
        does not have variables to resolve.

        Args:
            static_names: Static variable names (unused)
            referenced: Referenced variable names (unused)
            options: Resolution options (unused)

        Returns:
            Empty dict (no resolutions for Kubernetes)
        """
        del static_names, referenced, options  # Unused in bootstrap

        return {}
