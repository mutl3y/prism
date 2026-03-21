#!/usr/bin/env python3
"""API demo for Prism role and collection scanning functions."""

from __future__ import annotations

import json
from pathlib import Path

from prism.api import scan_collection, scan_role


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    role_path = root / "demos" / "fixtures" / "role_demo"
    collection_path = root / "demos" / "fixtures" / "collection_demo"

    role_payload = scan_role(str(role_path), detailed_catalog=True)
    collection_payload = scan_collection(str(collection_path), detailed_catalog=True)

    role_counters = (
        role_payload.get("metadata", {}).get("scanner_counters", {})
        if isinstance(role_payload, dict)
        else {}
    )
    collection_summary = (
        collection_payload.get("summary", {})
        if isinstance(collection_payload, dict)
        else {}
    )
    collection_roles = (
        collection_payload.get("roles", [])
        if isinstance(collection_payload, dict)
        else []
    )
    collection_meta = (
        collection_payload.get("collection", {}).get("metadata", {})
        if isinstance(collection_payload, dict)
        else {}
    )
    plugin_summary = (
        collection_payload.get("plugin_catalog", {}).get("summary", {})
        if isinstance(collection_payload, dict)
        else {}
    )
    plugin_types = (
        collection_payload.get("plugin_catalog", {})
        .get("summary", {})
        .get("types_present", [])
        if isinstance(collection_payload, dict)
        else []
    )

    summary = {
        "role_function": "scan_role",
        "collection_function": "scan_collection",
        "role_path": str(role_path),
        "collection_path": str(collection_path),
        "role_counters": {
            "task_files": role_counters.get("task_files", 0),
            "tasks": role_counters.get("tasks", 0),
            "handlers": role_counters.get("handlers", 0),
            "templates": role_counters.get("templates", 0),
        },
        "collection": {
            "namespace": collection_meta.get("namespace", "unknown"),
            "name": collection_meta.get("name", "unknown"),
            "version": collection_meta.get("version", "unknown"),
            "total_roles": collection_summary.get("total_roles", 0),
            "scanned_roles": collection_summary.get("scanned_roles", 0),
            "role_names": [
                entry.get("role", "unknown")
                for entry in collection_roles
                if isinstance(entry, dict)
            ],
            "plugins_discovered": plugin_summary.get("total_plugins", 0),
            "plugin_types": plugin_types,
        },
    }

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
