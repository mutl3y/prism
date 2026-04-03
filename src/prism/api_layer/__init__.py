"""Package-owned implementation layer for Prism's public API facade.

`prism.api` remains the stable public import surface.
New API orchestration and helper logic should land in this package first and
be re-exported from `prism.api` only when intentionally public.
"""
