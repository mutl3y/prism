"""Runtime Protocol contracts for DI factories and orchestrator boundary surfaces.

Replaces weak `Callable[..., Any]` aliases at the scanner_core ↔ scanner_kernel
boundary. Each Protocol documents the contract that previously had to be inferred
from call sites.
"""

from __future__ import annotations

from typing import Protocol, TYPE_CHECKING, TypeAlias, TypedDict, runtime_checkable

if TYPE_CHECKING:
    from prism.scanner_core.di import DIContainer
    from prism.scanner_kernel.plugin_name_resolver import RoutePreflightRuntimeCarrier

from prism.scanner_data.contracts_output import RunScanOutputPayload
from prism.scanner_data.contracts_request import ScanMetadata, ScanOptionsDict
from prism.scanner_data.contracts_request import ScanPolicyBlockerFacts


KernelPayload: TypeAlias = dict[str, object]


class KernelPhaseFailure(TypedDict):
    code: str
    message: str
    phase: str
    recoverable: bool


class KernelPhaseStatus(TypedDict, total=False):
    phase: str
    status: str
    reason: str
    error: KernelPhaseFailure


class KernelRequest(TypedDict, total=False):
    scan_id: str
    platform: str
    target_path: str
    options: ScanOptionsDict
    context: ScanMetadata


class KernelPhaseOutput(TypedDict, total=False):
    payload: RunScanOutputPayload | KernelPayload
    metadata: KernelPayload
    warnings: list[object]
    errors: list[object]
    provenance: list[object]


class KernelResponse(TypedDict, total=False):
    scan_id: str
    platform: str
    phase_results: dict[str, KernelPhaseStatus]
    metadata: KernelPayload
    payload: RunScanOutputPayload | KernelPayload
    warnings: list[object]
    errors: list[object]
    provenance: list[object]


class PluginLoader(Protocol):
    """Loads a plugin instance by platform name (kernel-side seam)."""

    def __call__(self, platform: str) -> object: ...


class KernelOrchestrator(Protocol):
    """Invokes the kernel orchestration entrypoint with keyword args."""

    def __call__(
        self,
        *,
        role_path: str,
        scan_options: ScanOptionsDict,
        route_preflight_runtime: "RoutePreflightRuntimeCarrier" | None,
    ) -> KernelResponse: ...


class ScanPayloadBuilderFn(Protocol):
    """Builds a scan payload dict (no args, returns mapping)."""

    def __call__(self) -> RunScanOutputPayload: ...


class KernelScanPayloadOrchestrator(Protocol):
    """Builds the scan payload for the ansible kernel scan phase."""

    def __call__(
        self,
        *,
        role_path: str,
        scan_options: ScanOptionsDict | None,
    ) -> RunScanOutputPayload: ...


class DIFactoryOverride(Protocol):
    """Overrides a DI factory: receives di + role_path + scan_options, returns the produced object."""

    def __call__(
        self, di: "DIContainer", role_path: str, scan_options: ScanOptionsDict
    ) -> object: ...


class BlockerFactBuilder(Protocol):
    """Assembles scan-policy blocker facts from runtime state."""

    def __call__(
        self,
        *,
        scan_options: ScanOptionsDict,
        metadata: ScanMetadata,
        di: "DIContainer",
    ) -> ScanPolicyBlockerFacts: ...


class EnsurePreparedPolicyBundleFn(Protocol):
    """Ensures the prepared_policy_bundle is set on scan_options."""

    def __call__(self, *, scan_options: ScanOptionsDict, di: "DIContainer") -> None: ...


@runtime_checkable
class KernelLifecyclePlugin(Protocol):
    """Phase-based lifecycle contract for kernel plugins.

    prepare/scan receive only the request; analyze/finalize also receive
    the accumulated response so they can read prior phase outputs.
    """

    def prepare(self, request: KernelRequest) -> KernelPhaseOutput | None: ...

    def scan(self, request: KernelRequest) -> KernelPhaseOutput | None: ...

    def analyze(
        self, request: KernelRequest, response: KernelResponse
    ) -> KernelPhaseOutput | None: ...

    def finalize(
        self, request: KernelRequest, response: KernelResponse
    ) -> KernelPhaseOutput | None: ...
