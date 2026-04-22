"""Collection plugin inventory helpers for the fsrc package lane."""

from __future__ import annotations

import ast
from pathlib import Path
import re
from typing import Any, NamedTuple


PLUGIN_CATALOG_SCHEMA_VERSION = 1
PLUGIN_EXTRACTION_METHOD_AST = "ast"
PLUGIN_EXTRACTION_METHOD_PATH_INVENTORY = "path_inventory"
PLUGIN_EXTRACTION_METHOD_BEST_EFFORT = "best_effort"
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

_PLUGIN_SUPPORT_FILE_STEMS: frozenset[str] = frozenset(
    {"readme", "license", "copying", "changelog", "changes", "notes"}
)


class PluginSummaryExtraction(NamedTuple):
    """Structured result of an individual plugin summary extraction attempt."""

    description: str
    source_kind: str
    extraction_method: str
    confidence_label: str
    confidence_score: float
    symbols: list[str]
    capability_hints: list[str]
    documentation_blocks: dict[str, str]


def build_empty_plugin_catalog() -> dict[str, Any]:
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


def scan_collection_plugins(collection_root: Path) -> dict[str, Any]:
    catalog = build_empty_plugin_catalog()
    plugin_root = collection_root / "plugins"

    for plugin_type in PLUGIN_TYPES:
        plugin_dir = plugin_root / plugin_type
        if not plugin_dir.is_dir():
            continue
        if plugin_type == "filter":
            _scan_filter_plugins(collection_root, plugin_dir, catalog)
            continue
        _scan_non_filter_plugins(collection_root, plugin_type, plugin_dir, catalog)

    catalog["summary"]["files_failed"] = len(catalog["failures"])
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
    catalog: dict[str, Any],
) -> None:
    records = catalog["by_type"]["filter"]
    failures = catalog["failures"]

    for plugin_file in _iter_plugin_files(plugin_dir):
        if plugin_file.suffix.lower() != ".py":
            continue
        relpath = _relative_path(plugin_file, collection_root)
        catalog["summary"]["files_scanned"] += 1
        try:
            text = plugin_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            failures.append(
                {
                    "relative_path": relpath,
                    "type": "filter",
                    "category": "io",
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
                    "category": "parse",
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
        confidence_score = {"high": 0.95, "medium": 0.75, "low": 0.40}[confidence]

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
                    "fallback_used": extraction_method != PLUGIN_EXTRACTION_METHOD_AST,
                },
                "capability_hints": sorted(set(symbols)),
            }
        )


def _scan_non_filter_plugins(
    collection_root: Path,
    plugin_type: str,
    plugin_dir: Path,
    catalog: dict[str, Any],
) -> None:
    records = catalog["by_type"][plugin_type]
    failures = catalog["failures"]
    for plugin_file in _iter_plugin_files(plugin_dir):
        relpath = _relative_path(plugin_file, collection_root)
        catalog["summary"]["files_scanned"] += 1
        record: dict[str, Any] = {
            "type": plugin_type,
            "name": _plugin_name_from_path(plugin_file),
            "relative_path": relpath,
            "language": _plugin_language(plugin_file),
            "symbols": [],
            "summary": f"{plugin_type} plugin `{_plugin_name_from_path(plugin_file)}`.",
            "doc_source": "path_inventory",
            "confidence": "low",
            "confidence_score": 0.30,
            "extraction": {
                "method": PLUGIN_EXTRACTION_METHOD_PATH_INVENTORY,
                "ast_version": None,
                "fallback_used": False,
            },
        }
        if record["language"] == "python":
            extracted, failure = _extract_python_plugin_summary_with_failure(
                plugin_file,
                plugin_type,
                relpath,
            )
            if failure is not None:
                failures.append(failure)
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
                    "fallback_used": method != PLUGIN_EXTRACTION_METHOD_AST,
                }
        records.append(record)


def _iter_plugin_files(plugin_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(plugin_dir.iterdir()):
        if path.name.startswith(".") or path.name == "__pycache__":
            continue
        if path.is_file():
            if _is_plugin_inventory_file(path):
                files.append(path)
            continue
        package_init = path / "__init__.py"
        if path.is_dir() and package_init.is_file():
            files.append(package_init)
    return files


def _is_plugin_inventory_file(path: Path) -> bool:
    if path.name.startswith("."):
        return False
    if path.stem.lower() in _PLUGIN_SUPPORT_FILE_STEMS:
        return False
    return path.name != "__init__.py"


def _plugin_name_from_path(path: Path) -> str:
    if path.name == "__init__.py":
        return path.parent.name
    return path.stem if path.suffix else path.name


def _plugin_language(path: Path) -> str:
    return {
        ".py": "python",
        ".ps1": "powershell",
        ".sh": "shell",
        ".rb": "ruby",
        ".pl": "perl",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".j2": "jinja",
    }.get(path.suffix.lower(), "unknown")


def _extract_filter_symbols(
    parsed: ast.Module,
    text: str,
) -> tuple[list[str], dict[str, str | None], str, str]:
    for node in parsed.body:
        if not isinstance(node, ast.ClassDef) or node.name != "FilterModule":
            continue
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "filters":
                direct = _extract_direct_return_dict_keys(item)
                if direct:
                    symbols = sorted(set(direct.keys()))
                    return symbols, direct, "high", PLUGIN_EXTRACTION_METHOD_AST
                indirect = _extract_named_dict_return_keys(item)
                if indirect:
                    symbols = sorted(set(indirect.keys()))
                    return (
                        symbols,
                        indirect,
                        "medium",
                        PLUGIN_EXTRACTION_METHOD_AST,
                    )

    fallback = _fallback_extract_symbols(text)
    if fallback:
        return (
            fallback,
            {symbol: None for symbol in fallback},
            "low",
            PLUGIN_EXTRACTION_METHOD_BEST_EFFORT,
        )
    return [], {}, "low", PLUGIN_EXTRACTION_METHOD_BEST_EFFORT


def _extract_direct_return_dict_keys(func: ast.FunctionDef) -> dict[str, str | None]:
    for stmt in func.body:
        if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Dict):
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


def _extract_python_plugin_summary_with_failure(
    plugin_file: Path,
    plugin_type: str,
    relative_path: str | None,
) -> tuple[PluginSummaryExtraction | None, dict[str, Any] | None]:
    try:
        text = plugin_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        if relative_path is None:
            return None, None
        return (
            None,
            {
                "relative_path": relative_path,
                "type": plugin_type,
                "category": "io",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "stage": "read",
            },
        )
    try:
        parsed = ast.parse(text)
    except SyntaxError as exc:
        if relative_path is None:
            return None, None
        return (
            None,
            {
                "relative_path": relative_path,
                "type": plugin_type,
                "category": "parse",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "stage": "ast_parse",
            },
        )

    documentation_blocks = _extract_documentation_literals(parsed)
    short_description = _extract_short_description_from_documentation(
        documentation_blocks.get("DOCUMENTATION")
    )
    capability_hints = _extract_class_method_capability_hints(parsed, plugin_type)
    symbols = _extract_python_symbol_names(parsed)

    if short_description:
        return (
            PluginSummaryExtraction(
                description=short_description,
                source_kind="documentation_short_description",
                extraction_method=PLUGIN_EXTRACTION_METHOD_AST,
                confidence_label="medium",
                confidence_score=0.70,
                symbols=symbols,
                capability_hints=capability_hints,
                documentation_blocks=documentation_blocks,
            ),
            None,
        )

    if capability_hints:
        hint_text = ", ".join(capability_hints[:4])
        return (
            PluginSummaryExtraction(
                description=f"Capability hints: {hint_text}.",
                source_kind="class_method_hints",
                extraction_method=PLUGIN_EXTRACTION_METHOD_AST,
                confidence_label="medium",
                confidence_score=0.65,
                symbols=symbols,
                capability_hints=capability_hints,
                documentation_blocks=documentation_blocks,
            ),
            None,
        )

    module_doc = ast.get_docstring(parsed)
    if module_doc:
        return (
            PluginSummaryExtraction(
                description=module_doc,
                source_kind="module_docstring",
                extraction_method=PLUGIN_EXTRACTION_METHOD_AST,
                confidence_label="medium",
                confidence_score=0.65,
                symbols=symbols,
                capability_hints=capability_hints,
                documentation_blocks=documentation_blocks,
            ),
            None,
        )

    return None, None


def _extract_documentation_literals(parsed: ast.Module) -> dict[str, str]:
    blocks: dict[str, str] = {}
    for node in parsed.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
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
    match = re.search(r"(?im)^\s*short_description\s*:\s*(.+?)\s*$", documentation)
    if not match:
        return None
    return match.group(1).strip().strip("\"'")


def _fallback_extract_symbols(text: str) -> list[str]:
    matches = re.findall(r"['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*:", text)
    return sorted(set(matches))


def _relative_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")
