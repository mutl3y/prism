"""Collection plugin inventory helpers.

Gate 2 focuses on filter plugin extraction using Python AST while preserving
an additive payload shape for other plugin categories.
"""

from __future__ import annotations

import ast
from pathlib import Path
import re
from typing import TypedDict

PLUGIN_CATALOG_SCHEMA_VERSION = 1
PLUGIN_TYPES: tuple[str, ...] = (
    "filter",
    "modules",
    "lookup",
    "inventory",
    "callback",
    "connection",
    "strategy",
    "test",
    "doc_fragments",
    "module_utils",
)


class PluginExtraction(TypedDict):
    method: str
    ast_version: str | None
    fallback_used: bool


class PluginRecord(TypedDict, total=False):
    type: str
    name: str
    relative_path: str
    language: str
    symbols: list[str]
    summary: str
    doc_source: str
    confidence: str
    confidence_score: float
    extraction: PluginExtraction
    capability_hints: list[str]
    documentation_blocks: dict[str, str]


class PluginScanFailure(TypedDict):
    relative_path: str
    type: str
    error_type: str
    error: str
    stage: str


class PluginCatalogSummary(TypedDict):
    total_plugins: int
    types_present: list[str]
    files_scanned: int
    files_failed: int


class PluginCatalog(TypedDict):
    schema_version: int
    summary: PluginCatalogSummary
    by_type: dict[str, list[PluginRecord]]
    failures: list[PluginScanFailure]


def build_empty_plugin_catalog() -> PluginCatalog:
    """Return an empty plugin catalog with stable keys."""
    return {
        "schema_version": PLUGIN_CATALOG_SCHEMA_VERSION,
        "summary": {
            "total_plugins": 0,
            "types_present": [],
            "files_scanned": 0,
            "files_failed": 0,
        },
        "by_type": {plugin_type: [] for plugin_type in PLUGIN_TYPES},
        "failures": [],
    }


def scan_collection_plugins(collection_root: Path) -> PluginCatalog:
    """Scan collection plugin directories and return a plugin catalog payload."""
    catalog = build_empty_plugin_catalog()
    failures = catalog["failures"]
    plugin_root = collection_root / "plugins"

    for plugin_type in PLUGIN_TYPES:
        plugin_dir = plugin_root / plugin_type
        if not plugin_dir.is_dir():
            continue
        if plugin_type == "filter":
            _scan_filter_plugins(collection_root, plugin_dir, catalog)
            continue
        _scan_non_filter_plugins(collection_root, plugin_type, plugin_dir, catalog)

    catalog["summary"]["files_failed"] = len(failures)
    catalog["summary"]["total_plugins"] = sum(
        len(catalog["by_type"][plugin_type]) for plugin_type in PLUGIN_TYPES
    )
    catalog["summary"]["types_present"] = [
        plugin_type for plugin_type in PLUGIN_TYPES if catalog["by_type"][plugin_type]
    ]
    return catalog


def _scan_filter_plugins(
    collection_root: Path,
    plugin_dir: Path,
    catalog: PluginCatalog,
) -> None:
    records = catalog["by_type"]["filter"]
    failures = catalog["failures"]

    for plugin_file in sorted(
        path for path in plugin_dir.rglob("*.py") if path.is_file()
    ):
        relpath = _relative_path(plugin_file, collection_root)
        catalog["summary"]["files_scanned"] += 1
        try:
            text = plugin_file.read_text(encoding="utf-8")
        except Exception as exc:  # pragma: no cover - defensive IO guard
            failures.append(
                {
                    "relative_path": relpath,
                    "type": "filter",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "stage": "read",
                }
            )
            continue

        try:
            parsed = ast.parse(text)
        except SyntaxError as exc:
            failures.append(
                {
                    "relative_path": relpath,
                    "type": "filter",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "stage": "ast_parse",
                }
            )
            continue

        symbols, symbol_function_names, confidence, extraction_method = (
            _extract_filter_symbols(parsed, text)
        )
        summary, doc_source = _resolve_filter_summary(
            parsed,
            plugin_file.stem,
            symbol_function_names,
        )
        confidence_score = {
            "high": 0.95,
            "medium": 0.75,
            "low": 0.40,
        }[confidence]

        records.append(
            {
                "type": "filter",
                "name": plugin_file.stem,
                "relative_path": relpath,
                "language": "python",
                "symbols": sorted(set(symbols)),
                "summary": summary,
                "doc_source": doc_source,
                "confidence": confidence,
                "confidence_score": confidence_score,
                "extraction": {
                    "method": extraction_method,
                    "ast_version": "py3",
                    "fallback_used": extraction_method != "ast",
                },
                "capability_hints": sorted(set(symbols)),
            }
        )


def _scan_non_filter_plugins(
    collection_root: Path,
    plugin_type: str,
    plugin_dir: Path,
    catalog: PluginCatalog,
) -> None:
    records = catalog["by_type"][plugin_type]
    for plugin_file in _iter_plugin_files(plugin_dir):
        relpath = _relative_path(plugin_file, collection_root)
        catalog["summary"]["files_scanned"] += 1
        name = _plugin_name_from_path(plugin_file)
        language = _plugin_language(plugin_file)
        record: PluginRecord = {
            "type": plugin_type,
            "name": name,
            "relative_path": relpath,
            "language": language,
            "symbols": [],
            "summary": f"{plugin_type} plugin `{name}`.",
            "doc_source": "path_inventory",
            "confidence": "low",
            "confidence_score": 0.30,
            "extraction": {
                "method": "path_inventory",
                "ast_version": None,
                "fallback_used": False,
            },
        }
        if language == "python":
            extracted = _extract_python_plugin_summary(plugin_file, plugin_type)
            if extracted is not None:
                (
                    summary,
                    doc_source,
                    method,
                    confidence,
                    score,
                    symbols,
                    capability_hints,
                    documentation_blocks,
                ) = extracted
                record["summary"] = summary
                record["doc_source"] = doc_source
                record["confidence"] = confidence
                record["confidence_score"] = score
                record["symbols"] = symbols
                if capability_hints:
                    record["capability_hints"] = capability_hints
                if documentation_blocks:
                    record["documentation_blocks"] = documentation_blocks
                record["extraction"] = {
                    "method": method,
                    "ast_version": "py3",
                    "fallback_used": method != "ast",
                }
        records.append(record)


def _iter_plugin_files(plugin_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in plugin_dir.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )


def _plugin_name_from_path(path: Path) -> str:
    if path.suffix:
        return path.stem
    return path.name


def _plugin_language(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".py": "python",
        ".ps1": "powershell",
        ".sh": "shell",
        ".rb": "ruby",
        ".pl": "perl",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".j2": "jinja",
    }.get(suffix, "unknown")


def _extract_filter_symbols(
    parsed: ast.Module,
    text: str,
) -> tuple[list[str], dict[str, str | None], str, str]:
    """Extract filter symbol names from common ``FilterModule.filters`` patterns."""
    for node in parsed.body:
        if not isinstance(node, ast.ClassDef) or node.name != "FilterModule":
            continue
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "filters":
                direct = _extract_direct_return_dict_keys(item)
                if direct:
                    symbols = sorted(set(direct.keys()))
                    return symbols, direct, "high", "ast"
                indirect = _extract_named_dict_return_keys(item)
                if indirect:
                    symbols = sorted(set(indirect.keys()))
                    return symbols, indirect, "medium", "ast"

    fallback = _fallback_extract_symbols(text)
    if fallback:
        return fallback, {symbol: None for symbol in fallback}, "low", "mixed"
    return [], {}, "low", "mixed"


def _extract_direct_return_dict_keys(func: ast.FunctionDef) -> dict[str, str | None]:
    for stmt in func.body:
        if not isinstance(stmt, ast.Return):
            continue
        if isinstance(stmt.value, ast.Dict):
            return _dict_string_key_to_function_name(stmt.value)
    return {}


def _extract_named_dict_return_keys(func: ast.FunctionDef) -> dict[str, str | None]:
    dict_assignments: dict[str, ast.Dict] = {}
    for stmt in func.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if isinstance(target, ast.Name) and isinstance(stmt.value, ast.Dict):
                dict_assignments[target.id] = stmt.value
        if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Name):
            ref = dict_assignments.get(stmt.value.id)
            if ref is not None:
                return _dict_string_key_to_function_name(ref)
    return {}


def _dict_string_key_to_function_name(node: ast.Dict) -> dict[str, str | None]:
    key_map: dict[str, str | None] = {}
    for key, value in zip(node.keys, node.values):
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            key_map[key.value] = _function_name_from_ast_value(value)
    return key_map


def _function_name_from_ast_value(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _resolve_filter_summary(
    parsed: ast.Module,
    plugin_stem: str,
    symbol_function_names: dict[str, str | None],
) -> tuple[str, str]:
    function_docs = _module_function_docstrings(parsed)
    for function_name in symbol_function_names.values():
        if not function_name:
            continue
        doc = function_docs.get(function_name)
        if doc:
            return doc, "filter_function_docstring"
    module_doc = ast.get_docstring(parsed)
    if module_doc:
        return module_doc, "module_docstring"
    return f"Filter plugin `{plugin_stem}`.", "fallback"


def _module_function_docstrings(parsed: ast.Module) -> dict[str, str]:
    docs: dict[str, str] = {}
    for node in parsed.body:
        if isinstance(node, ast.FunctionDef):
            doc = ast.get_docstring(node)
            if doc:
                docs[node.name] = doc
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    doc = ast.get_docstring(item)
                    if doc:
                        docs[item.name] = doc
    return docs


def _extract_python_plugin_summary(
    plugin_file: Path,
    plugin_type: str,
) -> (
    tuple[
        str,
        str,
        str,
        str,
        float,
        list[str],
        list[str],
        dict[str, str],
    ]
    | None
):
    try:
        text = plugin_file.read_text(encoding="utf-8")
    except Exception:
        return None
    try:
        parsed = ast.parse(text)
    except SyntaxError:
        return None

    documentation_blocks = _extract_documentation_literals(parsed)
    short_description = _extract_short_description_from_documentation(
        documentation_blocks.get("DOCUMENTATION")
    )
    capability_hints = _extract_class_method_capability_hints(parsed, plugin_type)
    symbols = _extract_python_symbol_names(parsed)

    if short_description:
        return (
            short_description,
            "documentation_short_description",
            "ast",
            "medium",
            0.70,
            symbols,
            capability_hints,
            documentation_blocks,
        )

    if capability_hints:
        hint_text = ", ".join(capability_hints[:4])
        return (
            f"Capability hints: {hint_text}.",
            "class_method_hints",
            "ast",
            "medium",
            0.65,
            symbols,
            capability_hints,
            documentation_blocks,
        )

    module_doc = ast.get_docstring(parsed)
    if module_doc:
        return (
            module_doc,
            "module_docstring",
            "ast",
            "medium",
            0.65,
            symbols,
            capability_hints,
            documentation_blocks,
        )

    return None


def _extract_documentation_literals(parsed: ast.Module) -> dict[str, str]:
    blocks: dict[str, str] = {}
    for node in parsed.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id in {
            "DOCUMENTATION",
            "EXAMPLES",
            "RETURN",
        }:
            if isinstance(node.value, ast.Constant) and isinstance(
                node.value.value, str
            ):
                blocks[target.id] = node.value.value
    return blocks


def _extract_class_method_capability_hints(
    parsed: ast.Module,
    plugin_type: str,
) -> list[str]:
    if plugin_type not in {"lookup", "inventory", "callback", "strategy", "connection"}:
        return []
    hints: list[str] = []
    for node in parsed.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not isinstance(item, ast.FunctionDef):
                continue
            if item.name.startswith("__") and item.name.endswith("__"):
                continue
            hints.append(f"{node.name}.{item.name}")
    return sorted(set(hints))


def _extract_python_symbol_names(parsed: ast.Module) -> list[str]:
    symbols: set[str] = set()
    for node in parsed.body:
        if isinstance(node, ast.FunctionDef):
            symbols.add(node.name)
        elif isinstance(node, ast.ClassDef):
            symbols.add(node.name)
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    symbols.add(item.name)
    return sorted(symbols)


def _extract_short_description_from_documentation(
    documentation: str | None,
) -> str | None:
    if not documentation:
        return None
    match = re.search(
        r"(?im)^\s*short_description\s*:\s*(.+?)\s*$",
        documentation,
    )
    if not match:
        return None
    return match.group(1).strip().strip("\"'")


def _fallback_extract_symbols(text: str) -> list[str]:
    """Best-effort fallback for quoted mapping keys in filter plugins."""
    matches = re.findall(r"['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*:", text)
    return sorted(set(matches))


def _relative_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")
