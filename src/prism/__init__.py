"""Prism package root (canonical src/ lane)."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("prism")
except PackageNotFoundError:
    __version__ = "0.1.0"
