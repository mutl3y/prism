"""KubernetesFeatureDetectionPlugin — Kubernetes-specific feature detection logic."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import yaml

from prism.scanner_data.contracts_request import FeaturesContext
from prism.scanner_plugins.interfaces import TaskCatalog


@dataclass(frozen=True)
class _ManifestInventory:
    file_count: int
    document_count: int
    resource_kinds: tuple[str, ...]
    operational_notes: tuple[str, ...]
    secret_reference_count: int


_MANIFEST_IGNORED_DIRS = frozenset(
    {
        ".git",
        ".tox",
        ".venv",
        "__pycache__",
        "node_modules",
        "venv",
    }
)


def _relative_manifest_path(path: Path, role_root: Path) -> str:
    relative_path = path.relative_to(role_root)
    return relative_path.as_posix()


def _catalog_entry_name(path: Path, role_root: Path) -> str:
    relative_path = _relative_manifest_path(path, role_root)
    return path.name if "/" not in relative_path else relative_path


def _iter_manifest_files(role_root: Path) -> tuple[Path, ...]:
    if not role_root.is_dir():
        return ()
    manifest_files: list[Path] = []
    for root, dirs, files in os.walk(role_root):
        dirs[:] = sorted(
            directory for directory in dirs if directory not in _MANIFEST_IGNORED_DIRS
        )
        for file_name in sorted(files):
            candidate = Path(root) / file_name
            if candidate.suffix.lower() not in {".yaml", ".yml"}:
                continue
            manifest_files.append(candidate)

    return tuple(
        sorted(
            manifest_files,
            key=lambda path: _relative_manifest_path(path, role_root),
        )
    )


def _safe_mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _iter_mapping_documents(path: Path) -> tuple[dict[str, object], ...]:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        loaded = tuple(yaml.safe_load_all(content))
    except OSError, yaml.YAMLError:
        return ()
    return tuple(item for item in loaded if isinstance(item, dict))


def _container_specs(document: dict[str, object]) -> tuple[dict[str, object], ...]:
    spec = _safe_mapping(document.get("spec"))
    template = _safe_mapping(spec.get("template"))
    template_spec = _safe_mapping(template.get("spec"))
    containers = template_spec.get("containers")
    if not isinstance(containers, list):
        return ()
    return tuple(item for item in containers if isinstance(item, dict))


def _manifest_operational_notes(document: dict[str, object]) -> tuple[str, ...]:
    notes: list[str] = []
    kind = document.get("kind")
    if not isinstance(kind, str):
        return ()

    spec = _safe_mapping(document.get("spec"))
    metadata = _safe_mapping(document.get("metadata"))
    resource_name = metadata.get("name")

    if kind == "Service" and spec.get("type") == "LoadBalancer":
        notes.append("Service uses LoadBalancer exposure")

    if kind != "Deployment":
        return tuple(notes)

    containers = _container_specs(document)
    if any("livenessProbe" in container for container in containers):
        notes.append("Deployment configures a liveness probe")

    for container in containers:
        env_items = container.get("env")
        if not isinstance(env_items, list):
            continue
        for env_item in env_items:
            if not isinstance(env_item, dict):
                continue
            value_from = _safe_mapping(env_item.get("valueFrom"))
            secret_key_ref = _safe_mapping(value_from.get("secretKeyRef"))
            secret_name = secret_key_ref.get("name")
            if isinstance(secret_name, str) and secret_name:
                prefix = "Deployment" if resource_name else kind
                notes.append(f"{prefix} references Secret {secret_name} via env")
                return tuple(notes)

    return tuple(notes)


def collect_manifest_inventory(role_path: str) -> _ManifestInventory:
    role_root = Path(role_path).resolve()
    manifest_files = _iter_manifest_files(role_root)
    resource_kinds: set[str] = set()
    operational_notes: set[str] = set()
    document_count = 0
    secret_reference_count = 0

    for manifest_file in manifest_files:
        for document in _iter_mapping_documents(manifest_file):
            document_count += 1
            kind = document.get("kind")
            if isinstance(kind, str) and kind:
                resource_kinds.add(kind)

            notes = _manifest_operational_notes(document)
            operational_notes.update(notes)
            secret_reference_count += sum(
                1 for note in notes if "references Secret" in note
            )

    return _ManifestInventory(
        file_count=len(manifest_files),
        document_count=document_count,
        resource_kinds=tuple(sorted(resource_kinds)),
        operational_notes=tuple(sorted(operational_notes)),
        secret_reference_count=secret_reference_count,
    )


class KubernetesFeatureDetectionPlugin:
    """Kubernetes-specific feature detection plugin.

    Implements contract-valid, stateless feature detection for Kubernetes
    manifests. Currently provides bootstrap-level detection with explicit
    fail-closed behavior for unimplemented capabilities.
    """

    PLUGIN_IS_STATELESS = True

    def __init__(self, di: object | None = None) -> None:
        self._di = di

    def detect_features(
        self,
        role_path: str,
        options: dict[str, Any],
    ) -> FeaturesContext:
        """Detect Kubernetes-specific features in target path.

        For bootstrap phase, returns minimal feature detection context.
        Kubernetes does not have the same task-centric feature model
        as Ansible, so detection is limited to manifest presence.

        Args:
            role_path: Path to target Kubernetes manifests
            options: Detection options (unused in bootstrap phase)

        Returns:
            FeaturesContext dict with detected features
        """
        del options

        inventory = collect_manifest_inventory(role_path)
        features: FeaturesContext = {
            "task_files_scanned": inventory.file_count,
            "tasks_scanned": inventory.document_count,
            "recursive_task_includes": 0,
            "unique_modules": (
                ", ".join(inventory.resource_kinds)
                if inventory.resource_kinds
                else "none"
            ),
            "external_collections": "none",
            "handlers_notified": "none",
            "privileged_tasks": inventory.secret_reference_count,
            "conditional_tasks": 0,
            "tagged_tasks": 0,
            "included_role_calls": 0,
            "included_roles": "none",
            "dynamic_included_role_calls": 0,
            "dynamic_included_roles": "none",
            "disabled_task_annotations": 0,
            "yaml_like_task_annotations": 0,
        }

        return features

    def analyze_task_catalog(
        self,
        role_path: str,
        options: dict[str, Any],
    ) -> TaskCatalog:
        """Analyze task catalog for Kubernetes manifests.

        For bootstrap phase, returns empty catalog since Kubernetes
        manifest scanning is not yet implemented.

        Args:
            role_path: Path to target Kubernetes manifests
            options: Catalog analysis options (unused in bootstrap)

        Returns:
            TaskCatalog dict (empty for bootstrap)
        """
        del options

        role_root = Path(role_path).resolve()
        result: TaskCatalog = {}
        for manifest_file in _iter_manifest_files(role_root):
            documents = _iter_mapping_documents(manifest_file)
            resource_kinds = sorted(
                {
                    kind
                    for document in documents
                    for kind in [document.get("kind")]
                    if isinstance(kind, str) and kind
                }
            )
            secret_reference_count = sum(
                1
                for document in documents
                for note in _manifest_operational_notes(document)
                if "references Secret" in note
            )
            result[_catalog_entry_name(manifest_file, role_root)] = {
                "task_count": len(documents),
                "async_count": 0,
                "modules_used": resource_kinds,
                "collections_used": [],
                "handlers_notified": [],
                "privileged_tasks": secret_reference_count,
                "conditional_tasks": 0,
                "tagged_tasks": 0,
            }

        return result
