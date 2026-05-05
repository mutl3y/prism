"""Kernel plugin lifecycle runner for phase-based execution."""

from __future__ import annotations

import copy
import logging
from typing import Literal, Mapping, Protocol, TypeAlias, cast

from prism.scanner_core.protocols_runtime import (
    KernelPhaseFailure,
    KernelPhaseOutput,
    KernelRequest,
    KernelResponse,
    PluginLoader,
)
from prism.scanner_data.contracts_request import ScanMetadata, ScanOptionsDict

logger = logging.getLogger(__name__)


class _UnaryPhaseCallable(Protocol):
    def __call__(self, request: KernelRequest) -> KernelPhaseOutput | None: ...


class _BinaryPhaseCallable(Protocol):
    def __call__(
        self, request: KernelRequest, response: KernelResponse
    ) -> KernelPhaseOutput | None: ...


_PhaseHandler: TypeAlias = _BinaryPhaseCallable
_ResponseListKey: TypeAlias = Literal["warnings", "errors", "provenance"]
_RESPONSE_LIST_KEYS: tuple[_ResponseListKey, ...] = (
    "warnings",
    "errors",
    "provenance",
)


def run_kernel_plugin_orchestrator(
    *,
    platform: str,
    target_path: str,
    scan_options: dict[str, object],
    load_plugin_fn: PluginLoader,
    scan_id: str = "kernel-scan",
    fail_fast: bool = True,
    context: dict[str, object] | None = None,
) -> KernelResponse:
    """Execute baseline lifecycle phases on a loaded kernel plugin.

    Phase Execution Contract:
    -------------------------
    Plugin lifecycle phases are ORDERED and STATEFUL:
    - prepare → scan → analyze → finalize
    - Each phase depends on successful completion of upstream phases
    - Failed phase blocks downstream execution to prevent corrupt state

    Phase State Transitions:
    ------------------------
    - "completed": Phase executed successfully
    - "skipped": Handler not implemented (hasattr check)
    - "failed": Handler raised exception
    - "skipped_due_to_upstream_failure": Downstream phase not executed because
      an upstream phase failed (respects phase dependencies)

    Fail-Fast Semantics:
    -------------------
    - fail_fast=True: Break immediately on first phase failure (strict mode)
    - fail_fast=False: Skip downstream phases for this plugin, mark errors as
      recoverable; allows multi-plugin orchestration to continue (fail-per-plugin)

    Args:
        platform: Platform identifier (e.g., "ansible")
        target_path: Path to scan target
        scan_options: Scan configuration options
        load_plugin_fn: Function to load plugin by platform
        scan_id: Unique scan identifier
        fail_fast: If True, break on first failure; if False, skip downstream
        context: Optional execution context

    Returns:
        Response dict with phase_results, metadata, errors, and payload
    """
    logger.info(
        "Kernel orchestrator started: scan_id=%s platform=%s target=%s fail_fast=%s",
        scan_id,
        platform,
        target_path,
        fail_fast,
    )

    request: KernelRequest = {
        "scan_id": scan_id,
        "platform": platform,
        "target_path": target_path,
        "options": cast(ScanOptionsDict, copy.copy(scan_options)),
    }
    if isinstance(context, dict):
        request["context"] = cast(ScanMetadata, copy.copy(context))

    response: KernelResponse = {
        "scan_id": scan_id,
        "platform": platform,
        "phase_results": {},
        "metadata": {"kernel_orchestrator": "fsrc-v1"},
    }

    plugin = load_plugin_fn(platform)
    phase_handlers: list[tuple[str, _PhaseHandler | None]] = [
        ("prepare", _resolve_phase_handler(plugin, "prepare")),
        ("scan", _resolve_phase_handler(plugin, "scan")),
        ("analyze", _resolve_phase_handler(plugin, "analyze")),
        ("finalize", _resolve_phase_handler(plugin, "finalize")),
    ]

    upstream_phase_failed = False

    for phase, handler in phase_handlers:
        if handler is None:
            logger.debug("Phase %s: skipped (handler not implemented)", phase)
            response["phase_results"][phase] = {
                "phase": phase,
                "status": "skipped",
            }
            continue

        if upstream_phase_failed:
            logger.warning(
                "Phase %s: skipped due to upstream failure in previous phase",
                phase,
            )
            response["phase_results"][phase] = {
                "phase": phase,
                "status": "skipped_due_to_upstream_failure",
                "reason": "Upstream phase failed; phase dependencies require successful prior execution",
            }
            continue

        logger.info("Phase %s: executing", phase)
        try:
            phase_output = handler(request, response)
        except Exception as exc:
            logger.error("Phase %s: FAILED with exception: %s", phase, exc)
            error_envelope: KernelPhaseFailure = {
                "code": "KERNEL_PLUGIN_PHASE_FAILED",
                "message": str(exc),
                "phase": phase,
                "recoverable": not fail_fast,
            }
            _response_list(response, "errors").append(error_envelope)
            response["phase_results"][phase] = {
                "phase": phase,
                "status": "failed",
                "error": error_envelope,
            }

            upstream_phase_failed = True

            if fail_fast:
                logger.error(
                    "Phase %s: fail_fast=True, breaking plugin execution", phase
                )
                break

            logger.warning(
                "Phase %s: fail_fast=False, marking downstream phases as skipped",
                phase,
            )
            continue

        logger.info("Phase %s: completed successfully", phase)
        _merge_phase_output(response=response, phase=phase, phase_output=phase_output)
        response["phase_results"][phase] = {"phase": phase, "status": "completed"}

    logger.info(
        "Kernel orchestrator finished: scan_id=%s phases_completed=%d",
        scan_id,
        sum(
            1
            for result in response["phase_results"].values()
            if result.get("status") == "completed"
        ),
    )

    return response


def _resolve_phase_handler(plugin: object, phase: str) -> _PhaseHandler | None:
    candidate = getattr(plugin, phase, None)
    if not callable(candidate):
        return None

    if phase in {"prepare", "scan"}:
        unary_handler = cast(_UnaryPhaseCallable, candidate)

        def _invoke_unary(
            request: KernelRequest,
            response: KernelResponse,
        ) -> KernelPhaseOutput | None:
            del response
            return unary_handler(request)

        return _invoke_unary

    binary_handler = cast(_BinaryPhaseCallable, candidate)

    def _invoke_binary(
        request: KernelRequest,
        response: KernelResponse,
    ) -> KernelPhaseOutput | None:
        return binary_handler(request, response)

    return _invoke_binary


def _response_list(
    response: KernelResponse,
    key: _ResponseListKey,
) -> list[object]:
    values = response.get(key)
    if isinstance(values, list):
        return values
    values = []
    response[key] = values
    return values


def _merge_phase_output(
    *,
    response: KernelResponse,
    phase: str,
    phase_output: KernelPhaseOutput | None,
) -> None:
    if not isinstance(phase_output, dict):
        return

    if phase == "scan" and "payload" not in phase_output:
        response["payload"] = _copy_mapping(phase_output)

    payload = phase_output.get("payload")
    if isinstance(payload, dict):
        response["payload"] = _copy_mapping(payload)

    metadata = phase_output.get("metadata")
    if isinstance(metadata, dict):
        response_metadata = response.get("metadata")
        existing_metadata = (
            _copy_mapping(response_metadata)
            if isinstance(response_metadata, dict)
            else {}
        )
        existing_metadata.update(_copy_mapping(metadata))
        response["metadata"] = cast(ScanMetadata, existing_metadata)

    for key in _RESPONSE_LIST_KEYS:
        value = phase_output.get(key)
        if isinstance(value, list):
            _response_list(response, key).extend(value)


def _copy_mapping(mapping: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in mapping.items()}
