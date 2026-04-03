"""Package-owned implementation layer for Prism's public API facade.

`prism.api` remains the stable public import surface.
New API orchestration and helper logic should land in this package first and
be re-exported from `prism.api` only when intentionally public.

Current capability ownership:
- `prism.api_layer.common`: payload parsing, result normalization, and
  API-boundary failure shaping
- `prism.api_layer.role`: role-scan API behavior
- `prism.api_layer.collection`: collection-scan orchestration, dependency
  aggregation, and collection role README/runbook helpers
- `prism.api_layer.repo`: repo-scan API orchestration over
  `prism.repo_services`
"""

__all__: list[str] = []


def __getattr__(name: str) -> object:
    """Enforce that package-root access stays intentionally empty."""
    if name.startswith("_"):
        raise AttributeError(
            f"module '{__name__}' has no attribute '{name}' "
            f"(private member; only __all__ symbols are public)"
        )
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:
    """Expose only explicitly public package-root symbols."""
    return sorted(__all__)
