"""
PolicyManager Interface & Type Specifications (Design)

This file specifies the consolidated PolicyManager architecture for unified
policy resolution and management. It defines:
- Core protocols (PolicyManager, FallbackRegistry, ConfigLoader)
- Factory method specifications
- Type-safe wrapper types
- Initialization strategy
- Error handling contracts

NOTE: This is a DESIGN SPECIFICATION, not production code. It defines the
interface contract, not the implementation.

Plan ID: g84-remediation-mutl3y-cycle-20260509
Phase: phase-0-scout-policy-boundary
Created: 2026-05-09
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Any,
    Callable,
    ClassVar,
    Generic,
    Mapping,
    NotRequired,
    Protocol,
    TypeVar,
    runtime_checkable,
)
from typing_extensions import TypedDict

# ============================================================================
# SECTION 1: PROTOCOL DEFINITIONS (Type-Safe Contracts)
# ============================================================================


@runtime_checkable
class PreparedTaskLineParsingPolicy(Protocol):
    """Protocol for task line parsing policy implementations.
    
    Defines minimum capability surface for task-line syntax parsing,
    task module detection, and constrained when-value extraction.
    
    Implementations: AnsibleDefaultTaskLineParsingPolicyPlugin, platform-specific plugins
    """

    TASK_INCLUDE_KEYS: frozenset[str]
    ROLE_INCLUDE_KEYS: frozenset[str]
    INCLUDE_VARS_KEYS: frozenset[str]
    SET_FACT_KEYS: frozenset[str]
    TASK_BLOCK_KEYS: frozenset[str]
    TASK_META_KEYS: frozenset[str]

    def detect_task_module(self, task: Mapping[str, Any]) -> str | None:
        """Detect task module name from task dict.
        
        Args:
            task: Task dictionary from parsed YAML
            
        Returns:
            Module name (e.g., 'debug', 'set_fact') or None if not found
        """
        ...

    def extract_constrained_when_values(
        self,
        task: Mapping[str, Any],
        variable: str,
    ) -> list[str]:
        """Extract values of a variable constrained by when condition.
        
        Args:
            task: Task dictionary
            variable: Variable name to constrain
            
        Returns:
            List of constrained values for the variable
        """
        ...


@runtime_checkable
class PreparedJinjaAnalysisPolicy(Protocol):
    """Protocol for Jinja template analysis.
    
    Extracts undeclared variables from Jinja templates using meta analysis.
    
    Implementations: DefaultJinjaAnalysisPolicyPlugin
    """

    def collect_undeclared_jinja_variables(self, text: str) -> set[str]:
        """Collect undeclared variables from Jinja template text.
        
        Args:
            text: Jinja template text
            
        Returns:
            Set of undeclared variable names
        """
        ...


@runtime_checkable
class PreparedTaskTraversalPolicy(Protocol):
    """Protocol for task hierarchy traversal.
    
    Defines contract for traversing task include graphs, role includes,
    dynamic includes, and unconstrained include detection.
    
    Implementations: AnsibleDefaultTaskTraversalPolicyPlugin
    """

    def iter_task_mappings(
        self,
        data: Mapping[str, Any],
    ) -> list[Mapping[str, Any]]:
        """Iterate over task mappings in data structure.
        
        Args:
            data: Parsed YAML task data
            
        Returns:
            List of task mapping dictionaries
        """
        ...

    def iter_task_include_targets(
        self,
        data: Mapping[str, Any],
    ) -> list[str]:
        """Iterate over task include target paths.
        
        Args:
            data: Parsed YAML task data
            
        Returns:
            List of include target paths (e.g., 'tasks/common.yml')
        """
        ...

    def iter_task_include_edges(
        self,
        data: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        """Iterate over task include edges for graph construction.
        
        Args:
            data: Parsed YAML task data
            
        Returns:
            List of edge dicts with source/target/type info
        """
        ...

    def expand_include_target_candidates(
        self,
        task: Mapping[str, Any],
        target: str,
    ) -> list[str]:
        """Expand include target pattern to candidate paths.
        
        Args:
            task: Task containing include directive
            target: Include target pattern (may contain wildcards)
            
        Returns:
            List of candidate paths matching pattern
        """
        ...

    def iter_role_include_targets(
        self,
        task: Mapping[str, Any],
    ) -> list[str]:
        """Iterate over role include targets in task.
        
        Args:
            task: Task dictionary
            
        Returns:
            List of role include target paths
        """
        ...

    def iter_dynamic_role_include_targets(
        self,
        task: Mapping[str, Any],
    ) -> list[str]:
        """Iterate over dynamic role include targets.
        
        Args:
            task: Task dictionary
            
        Returns:
            List of dynamic role include target paths
        """
        ...

    def collect_unconstrained_dynamic_task_includes(
        self,
        data: Mapping[str, Any],
        task_line_parsing_policy: PreparedTaskLineParsingPolicy,
    ) -> list[dict[str, Any]]:
        """Collect unconstrained dynamic task includes.
        
        Args:
            data: Parsed YAML task data
            task_line_parsing_policy: Policy for detecting when constraints
            
        Returns:
            List of unconstrained include dicts
        """
        ...

    def collect_unconstrained_dynamic_role_includes(
        self,
        data: Mapping[str, Any],
        task_line_parsing_policy: PreparedTaskLineParsingPolicy,
    ) -> list[dict[str, Any]]:
        """Collect unconstrained dynamic role includes.
        
        Args:
            data: Parsed YAML task data
            task_line_parsing_policy: Policy for detecting when constraints
            
        Returns:
            List of unconstrained include dicts
        """
        ...


@runtime_checkable
class PreparedTaskAnnotationPolicy(Protocol):
    """Protocol for task annotation parsing.
    
    Defines contract for parsing task annotations, marker prefix handling,
    and metadata extraction from comment documentation.
    
    Implementations: AnsibleDefaultTaskAnnotationPolicyPlugin
    """

    def split_task_annotation_label(self, text: str) -> tuple[str, str]:
        """Split task annotation text into label and remainder.
        
        Args:
            text: Annotation text
            
        Returns:
            Tuple of (label, remainder)
        """
        ...

    def split_task_target_payload(self, text: str) -> tuple[str, str]:
        """Split task target and payload.
        
        Args:
            text: Target payload text
            
        Returns:
            Tuple of (target, payload)
        """
        ...

    def annotation_payload_looks_yaml(self, payload: str) -> bool:
        """Check if annotation payload looks like YAML.
        
        Args:
            payload: Annotation payload text
            
        Returns:
            True if payload appears to be YAML-like
        """
        ...

    def normalize_marker_prefix(self, prefix: str) -> str:
        """Normalize a marker prefix string.
        
        Args:
            prefix: Marker prefix to normalize
            
        Returns:
            Normalized prefix
        """
        ...

    def get_marker_line_re(self, prefix: str) -> object:
        """Get compiled regex for matching marker lines.
        
        Args:
            prefix: Marker prefix
            
        Returns:
            Compiled regex pattern object
        """
        ...

    def extract_task_annotations_for_file(
        self,
        lines: list[str],
        marker_prefix: str,
        include_task_index: bool = False,
    ) -> tuple[list[dict[str, Any]], ...]:
        """Extract task annotations from file lines.
        
        Args:
            lines: File lines
            marker_prefix: Comment marker prefix to search for
            include_task_index: Whether to include task index in results
            
        Returns:
            Tuple of (annotations, indices) or (annotations,)
        """
        ...

    def task_anchor(self, file_path: str, task_name: str, index: int) -> str:
        """Generate anchor/reference for task location.
        
        Args:
            file_path: File path containing task
            task_name: Task name
            index: Task index
            
        Returns:
            Anchor string for reference
        """
        ...


@runtime_checkable
class PreparedYAMLParsingPolicy(Protocol):
    """Protocol for YAML file parsing.
    
    Defines contract for loading YAML files and validating YAML candidates.
    
    Implementations: DefaultYAMLParsingPolicyPlugin
    """

    def load_yaml_file(self, path: Path | str) -> Any:
        """Load and parse YAML file.
        
        Args:
            path: Path to YAML file
            
        Returns:
            Parsed YAML data structure
            
        Raises:
            YAMLError: If file is invalid YAML
            FileNotFoundError: If file not found
        """
        ...

    def parse_yaml_candidate(
        self,
        candidate: str,
        role_root: Path | None = None,
    ) -> dict[str, Any] | None:
        """Parse and validate YAML candidate.
        
        Args:
            candidate: YAML candidate text
            role_root: Optional role root path for context
            
        Returns:
            Parsed candidate dict or None if invalid
        """
        ...


@runtime_checkable
class PreparedVariableExtractorPolicy(Protocol):
    """Protocol for variable file extraction.
    
    Defines contract for collecting include_vars files and variable sources.
    
    Implementations: AnsibleDefaultVariableExtractorPolicyPlugin
    """

    def collect_include_vars_files(
        self,
        role_path: Path,
        exclude_paths: list[Path] | None = None,
        collect_task_files: bool = False,
        load_yaml_file: Callable[[Path], Any] | None = None,
    ) -> list[Path]:
        """Collect include_vars files from role.
        
        Args:
            role_path: Path to role directory
            exclude_paths: Paths to exclude from collection
            collect_task_files: Whether to collect files from tasks/
            load_yaml_file: Optional YAML loader function
            
        Returns:
            List of include_vars file paths
        """
        ...


# ============================================================================
# SECTION 2: PREPARED POLICY BUNDLE TYPES (Runtime Carrier)
# ============================================================================


class PreparedPolicyBundle(TypedDict):
    """Carrier of prepared policy instances for runtime.
    
    This TypedDict is created at ingress (prepare_scan_context) and used
    throughout the scan lifetime. All fields are required except those
    marked NotRequired.
    
    Fields:
        task_line_parsing: Task line parsing policy instance
        jinja_analysis: Jinja analysis policy instance
        task_traversal: Task traversal policy (NotRequired in some contexts)
        yaml_parsing: YAML parsing policy (NotRequired in some contexts)
        variable_extractor: Variable extractor policy (NotRequired)
        task_annotation_parsing: Task annotation policy (NotRequired)
        comment_doc_marker_prefix: Marker prefix for comment doc (e.g., '@prism')
        ignore_unresolved_internal_underscore_references: Whether to ignore _ references
    """

    task_line_parsing: PreparedTaskLineParsingPolicy
    jinja_analysis: PreparedJinjaAnalysisPolicy
    task_traversal: NotRequired[PreparedTaskTraversalPolicy]
    yaml_parsing: NotRequired[PreparedYAMLParsingPolicy]
    variable_extractor: NotRequired[PreparedVariableExtractorPolicy]
    task_annotation_parsing: NotRequired[PreparedTaskAnnotationPolicy]
    comment_doc_marker_prefix: NotRequired[str]
    ignore_unresolved_internal_underscore_references: NotRequired[bool]


# ============================================================================
# SECTION 3: FALLBACK REGISTRY (Centralized Singleton Management)
# ============================================================================


class FallbackPolicyRegistry:
    """Centralized registry for platform-specific and generic fallback policies.
    
    This registry manages singleton instances of default policy implementations.
    All access is thread-safe via internal lock.
    
    Responsibilities:
    - Register fallback policy instances at bootstrap
    - Retrieve fallbacks by policy kind
    - Support snapshot iteration (for listing available policies)
    - Thread-safe access
    
    Lifecycle:
    - Created once at bootstrap via initialize_fallback_registry()
    - Injected into DIContainer
    - Passed to PolicyManager at initialization
    - Reused across all scans in a process
    
    Example:
        registry = FallbackPolicyRegistry()
        registry.register_fallback("task_line_parsing", policy_instance)
        policy = registry.get_fallback("task_line_parsing")
    """

    def __init__(self) -> None:
        """Initialize empty fallback registry."""
        self._fallbacks: dict[str, object] = {}
        self._lock = threading.RLock()

    def register_fallback(self, policy_kind: str, plugin: object) -> None:
        """Register a fallback policy instance.
        
        Args:
            policy_kind: Kind identifier (e.g., 'task_line_parsing', 'yaml_parsing')
            plugin: Policy implementation instance to register as fallback
            
        Raises:
            ValueError: If policy_kind already registered (duplicate registration)
            TypeError: If plugin is None
        """
        ...

    def get_fallback(self, policy_kind: str) -> object | None:
        """Retrieve registered fallback policy.
        
        Args:
            policy_kind: Kind identifier to look up
            
        Returns:
            Registered plugin instance or None if not registered
        """
        ...

    def get_all_fallbacks(self) -> dict[str, object]:
        """Return snapshot of all registered fallbacks.
        
        Returns:
            Dict mapping policy_kind -> plugin instance (thread-safe snapshot)
        """
        ...

    def has_fallback(self, policy_kind: str) -> bool:
        """Check if policy kind is registered.
        
        Args:
            policy_kind: Kind to check
            
        Returns:
            True if registered, False otherwise
        """
        ...

    def unregister_fallback(self, policy_kind: str) -> None:
        """Unregister a fallback policy (mainly for testing).
        
        Args:
            policy_kind: Kind to unregister
        """
        ...


# ============================================================================
# SECTION 4: POLICY MANAGER FACADE (Unified Resolution)
# ============================================================================


@dataclass
class PolicyResolutionContext:
    """Context for policy resolution request.
    
    Attributes:
        scan_platform: Platform identifier (e.g., 'ansible', 'kubernetes')
        cache_resolved: Whether to cache resolved policies for reuse
        strict_mode: If True, raise on missing policy; if False, return None
    """

    scan_platform: str = "ansible"
    cache_resolved: bool = True
    strict_mode: bool = True


class PolicyManager:
    """Unified facade for policy resolution and management.
    
    Responsibilities:
    - Central entry point for policy resolution
    - Coordinate DI factories, PluginRegistry, and FallbackRegistry
    - Cache resolved policies for performance
    - Provide factory methods for all 6 policy types
    - Handle resolution errors uniformly
    
    Lifecycle:
    - Created at scan ingress (prepare_scan_context)
    - Initialized with FallbackRegistry, PluginRegistry, DIContainer
    - Used by all policy consumer modules
    - Lifetime: scan duration or longer (can be cached)
    
    Thread Safety:
    - Policy cache is read-only after initialization
    - Internal resolution is not thread-safe (single-threaded per scan)
    - Suitable for per-scan instance or long-lived thread-local instance
    
    Example:
        fallback_registry = initialize_fallback_registry()
        manager = PolicyManager(fallback_registry, plugin_registry, di)
        task_line_policy = manager.resolve_task_line_parsing_policy()
        bundle = manager.resolve_prepared_policy_bundle()
    """

    def __init__(
        self,
        fallback_registry: FallbackPolicyRegistry,
        plugin_registry: object | None = None,
        di: object | None = None,
        context: PolicyResolutionContext | None = None,
    ) -> None:
        """Initialize PolicyManager.
        
        Args:
            fallback_registry: FallbackPolicyRegistry instance for defaults
            plugin_registry: PluginRegistry for custom implementations (optional)
            di: DIContainer for factory overrides (optional)
            context: PolicyResolutionContext with settings (optional)
        """
        self._fallback_registry = fallback_registry
        self._plugin_registry = plugin_registry
        self._di = di
        self._context = context or PolicyResolutionContext()
        self._resolved_cache: dict[str, object] = {}

    # ---- Factory Methods (8 public APIs) ----

    def resolve_task_line_parsing_policy(self) -> PreparedTaskLineParsingPolicy:
        """Resolve task line parsing policy.
        
        Resolution order:
        1. DI factory override (factory_task_line_parsing_policy_plugin)
        2. PluginRegistry lookup
        3. FallbackRegistry lookup
        4. Raise ValueError if not found (strict_mode=True)
        
        Returns:
            Task line parsing policy instance
            
        Raises:
            ValueError: If no policy resolved and strict_mode=True
        """
        ...

    def resolve_jinja_analysis_policy(self) -> PreparedJinjaAnalysisPolicy:
        """Resolve Jinja analysis policy.
        
        Returns:
            Jinja analysis policy instance
            
        Raises:
            ValueError: If no policy resolved and strict_mode=True
        """
        ...

    def resolve_task_traversal_policy(self) -> PreparedTaskTraversalPolicy:
        """Resolve task traversal policy.
        
        Returns:
            Task traversal policy instance
            
        Raises:
            ValueError: If no policy resolved and strict_mode=True
        """
        ...

    def resolve_task_annotation_parsing_policy(
        self,
    ) -> PreparedTaskAnnotationPolicy:
        """Resolve task annotation parsing policy.
        
        Returns:
            Task annotation parsing policy instance
            
        Raises:
            ValueError: If no policy resolved and strict_mode=True
        """
        ...

    def resolve_yaml_parsing_policy(self) -> PreparedYAMLParsingPolicy:
        """Resolve YAML parsing policy.
        
        Returns:
            YAML parsing policy instance
            
        Raises:
            ValueError: If no policy resolved and strict_mode=True
        """
        ...

    def resolve_variable_extractor_policy(self) -> PreparedVariableExtractorPolicy:
        """Resolve variable extractor policy.
        
        Returns:
            Variable extractor policy instance
            
        Raises:
            ValueError: If no policy resolved and strict_mode=True
        """
        ...

    def resolve_prepared_policy_bundle(self) -> PreparedPolicyBundle:
        """Resolve all policies into a PreparedPolicyBundle.
        
        Convenience method that resolves all 6 policies and packages them
        into a TypedDict for easier passing through deep call stacks.
        
        Returns:
            PreparedPolicyBundle with all resolved policies
            
        Raises:
            ValueError: If any required policy not resolved and strict_mode=True
        """
        ...

    def resolve_by_kind(self, policy_kind: str) -> object | None:
        """Generic resolution by policy kind.
        
        Used for extending PolicyManager with new policy types without
        modifying the public API.
        
        Args:
            policy_kind: Policy kind identifier (e.g., 'task_line_parsing')
            
        Returns:
            Resolved policy or None if not found and strict_mode=False
            
        Raises:
            ValueError: If not found and strict_mode=True
        """
        ...

    # ---- Cache & Debug ----

    def clear_cache(self) -> None:
        """Clear policy resolution cache.
        
        Useful for testing or if policy landscape changes mid-scan.
        """
        ...

    def get_resolved_policies(self) -> dict[str, object]:
        """Return snapshot of all resolved policies.
        
        Returns:
            Dict mapping policy_kind -> resolved instance
        """
        ...

    def resolution_trace(self) -> dict[str, Any]:
        """Return resolution trace for debugging.
        
        Returns a structure showing:
        - Which policies resolved successfully
        - Which resolution path was taken (DI, registry, fallback)
        - Any skipped/optional policies
        - Performance metrics
        
        Returns:
            Dict with resolution trace details
        """
        ...


# ============================================================================
# SECTION 5: CONFIG LOADER INTERFACES
# ============================================================================


@dataclass
class PolicyConfigSpec:
    """Specification for a policy config parameter.
    
    Attributes:
        config_key: Hierarchical key in config file (e.g., 'policy_context.dynamic_includes.fail_on_unconstrained')
        python_type: Expected Python type (bool, int, str, etc.)
        default_value: Default value if not in config
        coerce_fn: Function to coerce raw config value to python_type
        description: Human-readable description
        required: Whether this config is required (default False)
    """

    config_key: str
    python_type: type
    default_value: Any
    coerce_fn: Callable[[Any], Any]
    description: str
    required: bool = False


class PolicyConfigLoader:
    """Unified loader for all policy configuration parameters.
    
    Responsibilities:
    - Load policy config from .prism.yml
    - Validate config values match expected types
    - Apply coercion functions
    - Provide schema documentation
    - Handle missing configs with defaults
    
    Specification Registry:
    The loader maintains a class-level registry of all known config parameters.
    Each parameter is defined once with type, coercion, and default.
    
    Example:
        loader = PolicyConfigLoader()
        fail_on_unconstrained = loader.load_bool("fail_on_unconstrained")
        marker_prefix = loader.load_str("marker_prefix", default="@prism")
    """

    # Registry of all known policy config specs
    POLICY_CONFIG_SPECS: ClassVar[dict[str, PolicyConfigSpec]] = {}

    def load_all(self) -> dict[str, Any]:
        """Load all policy config parameters.
        
        Returns:
            Dict mapping config_name -> loaded_value
        """
        ...

    def load_by_key(self, key: str) -> Any:
        """Load single config parameter by key.
        
        Args:
            key: Config parameter key (e.g., 'fail_on_unconstrained')
            
        Returns:
            Loaded and coerced value
        """
        ...

    @staticmethod
    def get_schema() -> dict[str, PolicyConfigSpec]:
        """Get schema documentation for all config parameters.
        
        Returns:
            Dict mapping param_name -> PolicyConfigSpec
        """
        ...


# ============================================================================
# SECTION 6: BOOTSTRAP & INITIALIZATION
# ============================================================================


def initialize_fallback_registry() -> FallbackPolicyRegistry:
    """Bootstrap function: Create and populate default fallback registry.
    
    This function is called once at process startup to initialize the
    singleton FallbackPolicyRegistry with all default policy implementations.
    
    Returns:
        Initialized FallbackPolicyRegistry with 6 fallback policies registered
        
    Raises:
        ImportError: If any default policy plugin cannot be imported
        
    Notes:
    - Called from bootstrap.py at process startup
    - Result is injected into DIContainer
    - Thread-safe: can be called multiple times (returns same registry)
    - Includes both platform-specific (Ansible) and generic (YAML, Jinja) defaults
    """
    ...


def initialize_policy_manager(
    fallback_registry: FallbackPolicyRegistry | None = None,
    plugin_registry: object | None = None,
    di: object | None = None,
) -> PolicyManager:
    """Bootstrap function: Create PolicyManager instance.
    
    Args:
        fallback_registry: FallbackPolicyRegistry (auto-created if None)
        plugin_registry: PluginRegistry for custom policies (optional)
        di: DIContainer for factory overrides (optional)
        
    Returns:
        Initialized PolicyManager
    """
    ...


# ============================================================================
# SECTION 7: ERROR HANDLING & CONTRACTS
# ============================================================================


class PolicyResolutionError(Exception):
    """Base exception for policy resolution failures."""

    pass


class MissingPolicyError(PolicyResolutionError):
    """Raised when a required policy cannot be resolved."""

    def __init__(self, policy_kind: str, context: str = ""):
        self.policy_kind = policy_kind
        self.context = context
        super().__init__(
            f"No policy resolved for {policy_kind!r}"
            + (f" ({context})" if context else "")
        )


class PolicyTypeError(PolicyResolutionError):
    """Raised when resolved policy does not conform to protocol."""

    def __init__(self, policy_kind: str, policy_obj: object, protocol: type):
        self.policy_kind = policy_kind
        self.policy_obj = policy_obj
        self.protocol = protocol
        super().__init__(
            f"Policy {policy_kind!r} does not conform to {protocol.__name__}"
        )


# ============================================================================
# SECTION 8: MOCK/TEST SUPPORT
# ============================================================================


@dataclass
class MockPolicyConfig:
    """Configuration for creating mock policies for testing.
    
    Used to quickly set up test fixtures with controlled policy behavior.
    
    Attributes:
        include_task_detection: If True, detect_task_module returns module names
        jinja_variables: Set of jinja variables to return
        include_targets: List of include targets for traversal
        marker_prefix: Marker prefix for annotations
    """

    include_task_detection: bool = True
    jinja_variables: set[str] = field(default_factory=set)
    include_targets: list[str] = field(default_factory=list)
    marker_prefix: str = "@prism"


def create_mock_fallback_registry(
    config: MockPolicyConfig | None = None,
) -> FallbackPolicyRegistry:
    """Create fallback registry with mock policies for testing.
    
    Args:
        config: MockPolicyConfig with desired mock behavior
        
    Returns:
        FallbackPolicyRegistry populated with mock policies
    """
    ...


def create_mock_policy_manager(
    config: MockPolicyConfig | None = None,
) -> PolicyManager:
    """Create PolicyManager with mock policies for testing.
    
    Args:
        config: MockPolicyConfig with desired mock behavior
        
    Returns:
        PolicyManager using mock policies
    """
    ...
