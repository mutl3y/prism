"""Package-owned repository intake and metadata helpers.

`prism.repo_services` remains the stable shared facade for API and CLI repo
flows. Internal repo-intake extension work should land here first.

Current capability ownership:
- `prism.repo_layer.intake`: clone, sparse checkout, workspace lifecycle,
  checkout-target resolution, and repo scan preparation
- `prism.repo_layer.metadata`: repo path normalization, metadata fetch
  helpers, style README candidate discovery, and scan metadata normalization
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
