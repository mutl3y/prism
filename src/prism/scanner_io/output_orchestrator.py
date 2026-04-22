"""Output orchestrator — canonical home for output emission coordination."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, cast

from prism.scanner_data.contracts_output import (
    RunScanOutputPayload,
    ScanMetadata,
    validate_output_orchestrator_inputs,
    validate_run_scan_output_payload,
    validate_runbook_sidecar_inputs,
)
from prism.scanner_io.emit_output import (
    ScanOutputRenderer,
    ScanReportRenderer,
    build_output_emission_context as _build_output_emission_context,
    orchestrate_output_emission as _orchestrate_output_emission,
)


class OutputOrchestrator:
    """Coordinate primary output and sidecar emission with injectable renderers."""

    def __init__(
        self,
        di: Any,
        output_path: str,
        options: dict[str, Any],
    ) -> None:
        validate_output_orchestrator_inputs(output_path=output_path, options=options)
        self._di = di
        self._output_path = output_path
        self._options = options

    def render_and_emit(
        self,
        payload: RunScanOutputPayload,
        dry_run: bool = False,
        *,
        render_and_write: ScanOutputRenderer,
        render_scanner_report: ScanReportRenderer,
        render_runbook: Callable[[str, dict[str, Any] | None], str],
        render_runbook_csv: Callable[[dict[str, Any] | None], str],
    ) -> str | bytes:
        """Render primary output and emit sidecars with injected renderer callables."""
        validated_payload = validate_run_scan_output_payload(payload)

        emission_args = _build_output_emission_context(
            output_payload={
                **validated_payload,
                "metadata": cast(ScanMetadata, dict(validated_payload["metadata"])),
            },
            output=self._output_path,
            output_format=self._options.get("output_format", "md"),
            template=self._options.get("template"),
            dry_run=dry_run,
            concise_readme=self._options.get("concise_readme", False),
            scanner_report_output=self._options.get("scanner_report_output"),
            include_scanner_report_link=self._options.get(
                "include_scanner_report_link", False
            ),
            runbook_output=self._options.get("runbook_output"),
            runbook_csv_output=self._options.get("runbook_csv_output"),
        )

        return _orchestrate_output_emission(
            args=emission_args,
            render_and_write=render_and_write,
            render_scanner_report=render_scanner_report,
            render_runbook=render_runbook,
            render_runbook_csv=render_runbook_csv,
        )

    def emit_runbook_sidecars(
        self,
        md_path: str,
        csv_path: str,
        *,
        role_name: str = "role",
        metadata: dict[str, Any] | None = None,
        render_runbook: Callable[[str, dict[str, Any] | None], str],
        render_runbook_csv: Callable[[dict[str, Any] | None], str],
    ) -> dict[str, int]:
        """Emit runbook markdown and CSV sidecars to specified paths."""
        validate_runbook_sidecar_inputs(
            md_path=md_path,
            csv_path=csv_path,
            role_name=role_name,
            metadata=metadata,
        )

        result: dict[str, int] = {}
        sidecar_metadata: dict[str, Any] = metadata or {}

        md_path_obj = Path(md_path)
        md_path_obj.parent.mkdir(parents=True, exist_ok=True)
        md_content = render_runbook(role_name, sidecar_metadata)
        md_path_obj.write_text(md_content, encoding="utf-8")
        result[md_path] = len(md_content.encode("utf-8"))

        csv_path_obj = Path(csv_path)
        csv_path_obj.parent.mkdir(parents=True, exist_ok=True)
        csv_content = render_runbook_csv(sidecar_metadata)
        csv_path_obj.write_text(csv_content, encoding="utf-8")
        result[csv_path] = len(csv_content.encode("utf-8"))

        return result
