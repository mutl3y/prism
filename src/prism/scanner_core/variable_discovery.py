"""VariableDiscovery orchestrator for role variable discovery and analysis.

This module consolidates variable-extraction logic currently spread across:
- variable_extractor.py — variable tokenization from task files/README
- task_parser.py — task/include file parsing
- scanner_dataload.py — YAML loading and preparation
- scan_discovery.py — variable discovery orchestration
- scanner_analysis/metrics.py — uncertainty tracking and error reasoning

The VariableDiscovery class provides a cohesive interface for discovering,
extracting, typing, and resolving all variables in a role.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .di import DIContainer
from ..scanner_data.builders import VariableRowBuilder
from ..scanner_data.contracts_variables import VariableRow
from ..scanner_extract.dataload import (
    iter_role_argument_spec_entries,
    load_role_variable_maps,
    map_argument_spec_type,
)
from ..scanner_extract.discovery import iter_role_variable_map_candidates
from ..scanner_extract.task_parser import _format_inline_yaml
from ..scanner_extract.task_parser import _load_yaml_file
from ..scanner_extract.variable_extractor import (
    _collect_referenced_variable_names,
    _collect_set_fact_names,
    _find_variable_line_in_yaml,
    _infer_variable_type,
    _is_sensitive_variable,
)


class VariableDiscovery:
    """Orchestrator for discovering and analyzing variables in a role.

    Consolidates:
    - Static discovery: defaults/, vars/, meta/argument_spec
    - Referenced discovery: task files, README sections
    - Type inference: string, list, dict, bool, etc.
    - Secret detection: password, token, key patterns
    - Uncertainty tracking: unresolved variables with reasons

    Uses immutable TypedDict for all data structures.
    Builders handle mutable construction; discovery returns immutable tuples.
    All discovery methods return Final immutable data structures."""

    def __init__(
        self,
        di: DIContainer,
        role_path: str,
        options: dict[str, Any],
    ) -> None:
        """Initialize discovery with DI container and scan options.

        Args:
            di: Dependency Injection container for orchestration.
            role_path: Path to the role directory.
            options: Scan configuration dictionary containing:
                - role_path: Role directory path
                - include_vars_main: Whether to include vars/ directory
                - exclude_path_patterns: List of paths to exclude
                - vars_seed_paths: External variable seed files
                - ignore_unresolved_internal_underscore_references: Policy flag
        """
        self._di = di
        self._role_path = role_path
        self._options = options
        self._role_root = Path(role_path).resolve()

    def discover_static(self) -> tuple[VariableRow, ...]:
        """Discover static variables from defaults, vars, meta, include_vars, set_fact.

        Returns immutable tuple of VariableRow dicts after building complete metadata.

        Returns:
            Immutable tuple[VariableRow, ...] of discovered variables with complete metadata:
            - name, type, default, source, required
            - provenance_source_file, provenance_line, provenance_confidence
        """
        rows: list[VariableRow] = []
        seen_names: frozenset[str] = frozenset()

        # Phase 1: Load defaults/main.yml and fragments
        defaults_data, vars_data, defaults_sources, vars_sources = (
            load_role_variable_maps(
                self._role_path,
                include_vars_main=self._options.get("include_vars_main", True),
                iter_variable_map_candidates_fn=iter_role_variable_map_candidates,
                load_yaml_file_fn=_load_yaml_file,
            )
        )

        # Process defaults
        for var_name, var_value in defaults_data.items():
            if not isinstance(var_name, str):
                continue
            if var_name in seen_names:
                continue
            seen_names = frozenset([*seen_names, var_name])

            source_file = defaults_sources.get(var_name)
            line_no = None
            source_file_path = "defaults/main.yml"
            if source_file:
                line_no = _find_variable_line_in_yaml(source_file, var_name)
                try:
                    source_file_path = str(source_file.relative_to(self._role_root))
                except ValueError:
                    source_file_path = str(source_file)

            is_secret = _is_sensitive_variable(var_name, var_value)
            inferred_type = _infer_variable_type(var_value)

            row = (
                VariableRowBuilder()
                .name(var_name)
                .type(inferred_type)
                .default(
                    _format_inline_yaml(var_value) if var_value is not None else ""
                )
                .source("defaults/main.yml")
                .required(False)
                .secret(is_secret)
                .provenance_source_file(source_file_path)
                .provenance_line(line_no)
                .provenance_confidence(0.95)
                .is_unresolved(False)
                .is_ambiguous(False)
                .build()
            )
            rows.append(row)

        # Process vars (if enabled)
        if self._options.get("include_vars_main", True):
            for var_name, var_value in vars_data.items():
                if not isinstance(var_name, str):
                    continue
                if var_name in seen_names:
                    continue
                seen_names = frozenset([*seen_names, var_name])

                source_file = vars_sources.get(var_name)
                line_no = None
                source_file_path = "vars/main.yml"
                if source_file:
                    line_no = _find_variable_line_in_yaml(source_file, var_name)
                    try:
                        source_file_path = str(source_file.relative_to(self._role_root))
                    except ValueError:
                        source_file_path = str(source_file)

                is_secret = _is_sensitive_variable(var_name, var_value)
                inferred_type = _infer_variable_type(var_value)

                row = (
                    VariableRowBuilder()
                    .name(var_name)
                    .type(inferred_type)
                    .default(
                        _format_inline_yaml(var_value) if var_value is not None else ""
                    )
                    .source("vars/main.yml")
                    .required(False)
                    .secret(is_secret)
                    .provenance_source_file(source_file_path)
                    .provenance_line(line_no)
                    .provenance_confidence(0.95)
                    .is_unresolved(False)
                    .is_ambiguous(False)
                    .build()
                )
                rows.append(row)

        # Phase 2: Load meta/argument_specs.yml
        for source_file, var_name, spec in iter_role_argument_spec_entries(
            self._role_path,
            load_yaml_file_fn=_load_yaml_file,
            load_meta_fn=lambda role_path: _load_yaml_file(
                Path(role_path) / "meta" / "main.yml"
            )
            or {},
        ):
            if var_name in seen_names:
                continue

            seen_names = frozenset([*seen_names, var_name])

            # Get metadata from argument spec
            spec_type = spec.get("type", "documented")
            var_default = spec.get("default", "")

            # Type from argument spec
            if isinstance(spec_type, str):
                inferred_type = map_argument_spec_type(spec_type)
            else:
                inferred_type = "documented"

            # Try to infer from default if present
            if var_default != "":
                inferred_type = _infer_variable_type(var_default)

            is_secret = _is_sensitive_variable(var_name, var_default)

            row = (
                VariableRowBuilder()
                .name(var_name)
                .type(inferred_type)
                .default(_format_inline_yaml(var_default) if var_default else "")
                .source("meta/argument_specs")
                .documented(True)
                .required(bool(spec.get("required", False)))
                .secret(is_secret)
                .provenance_source_file("meta/argument_specs.yml")
                .provenance_line(None)
                .provenance_confidence(0.9)
                .is_unresolved(False)
                .is_ambiguous(False)
                .build()
            )
            rows.append(row)

        # Phase 3: Collect set_fact assignments
        set_fact_names = _collect_set_fact_names(
            self._role_path,
            exclude_paths=self._options.get("exclude_path_patterns"),
        )
        for var_name in set_fact_names:
            if var_name in seen_names:
                continue
            seen_names = frozenset([*seen_names, var_name])

            row = (
                VariableRowBuilder()
                .name(var_name)
                .type("dynamic")
                .default("")
                .source("set_fact")
                .required(False)
                .secret(False)
                .provenance_source_file("tasks/")
                .provenance_line(None)
                .provenance_confidence(0.7)
                .is_unresolved(False)
                .is_ambiguous(True)
                .build()
            )
            rows.append(row)

        return tuple(rows)

    def discover_referenced(self) -> frozenset[str]:
        """Discover referenced variable names from task files and README.

        Returns immutable frozenset of variable names that appear in the role.

        Returns:
            Immutable frozenset[str] of referenced variable names.
        """
        # Collect from task files, templates, handlers
        referenced = _collect_referenced_variable_names(
            self._role_path,
            exclude_paths=self._options.get("exclude_path_patterns"),
        )

        # Collect from README sections
        readme_path = self._role_root / "README.md"
        if readme_path.exists():
            try:
                readme_text = readme_path.read_text(encoding="utf-8")
                # Find {{ variable }} patterns in README
                import re

                pattern = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)")
                for match in pattern.finditer(readme_text):
                    referenced.add(match.group(1))
            except (OSError, UnicodeDecodeError):
                pass

        return frozenset(referenced)

    def resolve_unresolved(
        self,
        *,
        static_names: frozenset[str] | None = None,
        referenced: frozenset[str] | None = None,
    ) -> dict[str, str]:
        """Return mapping of unresolved variable names → uncertainty reasons.

        Returns immutable mapping of unresolved variable names and their reasons.

        Returns:
            Dictionary mapping unresolved variable names to uncertainty reason text
            explaining why the variable couldn't be resolved.
        """
        # Get static and referenced
        effective_static_names = static_names
        if effective_static_names is None:
            static = self.discover_static()
            effective_static_names = frozenset(v["name"] for v in static)

        effective_referenced = referenced or self.discover_referenced()

        # Find unresolved (referenced but not defined) - build as new dict
        unresolved: dict[str, str] = {}
        for var_name in effective_referenced:
            if var_name not in effective_static_names:
                # Build uncertainty reason
                reason = self._build_uncertainty_reason(
                    var_name,
                    referenced_names=effective_referenced,
                )
                unresolved[var_name] = reason

        return unresolved

    def discover(self) -> tuple[VariableRow, ...]:
        """Main entry point: discover all variables (static + referenced).

        Returns immutable tuple of all variables (static + referenced + unresolved).

        Returns:
            Immutable tuple[VariableRow, ...] with complete metadata:
            - name, type, default, description, provenance
            - required, source, line_number, confidence, uncertainty_reason
        """
        # Get static and referenced
        static_rows = self.discover_static()
        static_names: frozenset[str] = frozenset(v["name"] for v in static_rows)

        referenced = self.discover_referenced()
        unresolved = self.resolve_unresolved(
            static_names=static_names,
            referenced=referenced,
        )

        # Build list during construction (mutable intermediate)
        all_rows: list[VariableRow] = list(static_rows)

        # Add referenced-but-unresolved variables
        for var_name in referenced:
            if var_name not in static_names:
                # This is a referenced but not defined variable
                uncertainty_reason = unresolved.get(var_name, "")

                row = (
                    VariableRowBuilder()
                    .name(var_name)
                    .type("dynamic")
                    .default("")
                    .source("referenced")
                    .documented(False)
                    .required(False)
                    .secret(False)
                    .provenance_source_file("tasks/")
                    .provenance_line(None)
                    .provenance_confidence(0.5)
                    .uncertainty_reason(uncertainty_reason)
                    .is_unresolved(True)
                    .is_ambiguous(False)
                    .build()
                )
                all_rows.append(row)

        return tuple(all_rows)

    def _build_uncertainty_reason(
        self,
        var_name: str,
        *,
        referenced_names: frozenset[str],
    ) -> str:
        """Build uncertainty reason text for unresolved variable."""
        # Check for dynamic indicators
        if var_name.startswith("_"):
            return "Dynamic or internal variable (underscore prefix)"

        # Check if it might come from complex expressions
        if var_name in referenced_names:
            return "Referenced but not defined in role"

        return "Unresolved reference"
