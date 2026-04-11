"""Registry for scanner extension loading and version-gated lookup."""

from __future__ import annotations

import importlib
from abc import ABC
from abc import abstractmethod


class ExtensionInterface(ABC):
    """Interface implemented by scanner extensions."""

    @abstractmethod
    def get_name(self) -> str:
        """Return extension name."""

    @abstractmethod
    def get_version(self) -> str:
        """Return extension semantic version string."""

    @abstractmethod
    def execute(self, data: dict) -> dict:
        """Execute extension behavior."""


class ExtensionRegistry:
    """Registry for extension registration and dynamic loading."""

    def __init__(self) -> None:
        self._extensions: dict[str, ExtensionInterface] = {}

    def register(self, extension: ExtensionInterface) -> None:
        name = extension.get_name()
        if name in self._extensions:
            raise ValueError(f"Extension '{name}' already registered")
        self._extensions[name] = extension

    def get_extension(
        self,
        name: str,
        required_version: str | None = None,
    ) -> ExtensionInterface:
        if name not in self._extensions:
            raise ValueError(f"Extension '{name}' not found")

        extension = self._extensions[name]
        if required_version and not self._is_version_compatible(
            extension.get_version(),
            required_version,
        ):
            raise ValueError(
                f"Extension '{name}' version {extension.get_version()} does not satisfy {required_version}"
            )
        return extension

    def load_from_module(self, module_path: str) -> None:
        module = importlib.import_module(module_path)
        extensions = getattr(module, "extensions", None)
        if not isinstance(extensions, list):
            return
        for extension_class in extensions:
            self.register(extension_class())

    def list_extensions(self) -> list[str]:
        return list(self._extensions.keys())

    def _is_version_compatible(self, ext_version: str, required: str) -> bool:
        ext_parsed = _parse_semver(ext_version)
        required_parsed = _parse_semver(required.lstrip("^"))
        if ext_parsed is None or required_parsed is None:
            return ext_version == required

        if required.startswith("^"):
            ext_major, ext_minor, ext_patch = ext_parsed
            req_major, req_minor, req_patch = required_parsed

            if ext_major != req_major:
                return False
            return (ext_major, ext_minor, ext_patch) >= (
                req_major,
                req_minor,
                req_patch,
            )

        return ext_parsed == required_parsed


def _parse_semver(version: str) -> tuple[int, int, int] | None:
    parts = version.strip().split(".")
    if not 1 <= len(parts) <= 3 or not all(part.isdigit() for part in parts):
        return None
    normalized_parts = parts + ["0"] * (3 - len(parts))
    major, minor, patch = (int(part) for part in normalized_parts)
    return (major, minor, patch)
