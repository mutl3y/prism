"""Prism next-generation package root hosted under fsrc/src."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("prism")
except PackageNotFoundError:
    __version__ = "0.1.0"
