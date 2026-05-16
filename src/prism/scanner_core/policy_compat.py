"""Backward compatibility wrappers for policy resolver functions.

This module provides deprecated wrapper functions for the original scattered
policy resolution functions, delegating to PolicyManager while logging
deprecation warnings for external callers.

Phase 2 Wave 3: Integration & Deprecation Wrappers
---------------------------------------------------
Task 3.2 implements a deprecation wrapper layer that:
- Maintains 100% backward compatibility
- Routes all calls to PolicyManager
- Logs warnings for external callers only (internal calls migrate silently)
- Documents migration paths
"""

from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prism.scanner_core.di import DIContainer
    from prism.scanner_data.contracts_request import (
        PreparedTaskLineParsingPolicy,
        PreparedTaskAnnotationPolicy,
        PreparedTaskTraversalPolicy,
        PreparedVariableExtractorPolicy,
        PreparedYAMLParsingPolicy,
        PreparedJinjaAnalysisPolicy,
    )

logger = logging.getLogger(__name__)

# Migration guide URL (points to documentation)
MIGRATION_GUIDE_URL = "https://docs.prism.local/migration/policy-resolver-deprecation"


def resolve_task_line_parsing_policy(
    di: DIContainer,
    scan_options: dict[str, object],
) -> PreparedTaskLineParsingPolicy:
    """Deprecated wrapper for resolve_task_line_parsing_policy.

    This function is DEPRECATED. Use `di.policy_manager.resolve_task_line_parsing_policy()` instead.

    Args:
        di: DIContainer for policy manager access.
        scan_options: Scan options including platform key.

    Returns:
        PreparedTaskLineParsingPolicy implementation.

    Raises:
        ValueError: If policy cannot be resolved.

    .. deprecated:: Wave 3
        Use :meth:`DIContainer.policy_manager` to access PolicyManager directly.
        See {MIGRATION_GUIDE_URL} for migration guide.
    """
    warnings.warn(
        "resolve_task_line_parsing_policy() is deprecated and will be removed in a future release. "
        f"Use di.policy_manager.resolve_task_line_parsing_policy() instead. "
        f"See {MIGRATION_GUIDE_URL} for migration guide.",
        DeprecationWarning,
        stacklevel=2,
    )
    logger.warning(
        "Deprecated function resolve_task_line_parsing_policy() called. "
        f"Migrate to di.policy_manager.resolve_task_line_parsing_policy(). "
        f"See {MIGRATION_GUIDE_URL}"
    )

    policy_manager = di.policy_manager
    return policy_manager.resolve_task_line_parsing_policy(di, scan_options)


def resolve_task_annotation_policy(
    di: DIContainer,
    scan_options: dict[str, object],
) -> PreparedTaskAnnotationPolicy:
    """Deprecated wrapper for resolve_task_annotation_policy.

    This function is DEPRECATED. Use `di.policy_manager.resolve_task_annotation_policy()` instead.

    Args:
        di: DIContainer for policy manager access.
        scan_options: Scan options including platform key.

    Returns:
        PreparedTaskAnnotationPolicy implementation.

    Raises:
        ValueError: If policy cannot be resolved.

    .. deprecated:: Wave 3
        Use :meth:`DIContainer.policy_manager` to access PolicyManager directly.
    """
    warnings.warn(
        "resolve_task_annotation_policy() is deprecated and will be removed in a future release. "
        f"Use di.policy_manager.resolve_task_annotation_policy() instead. "
        f"See {MIGRATION_GUIDE_URL} for migration guide.",
        DeprecationWarning,
        stacklevel=2,
    )
    logger.warning(
        "Deprecated function resolve_task_annotation_policy() called. "
        f"Migrate to di.policy_manager.resolve_task_annotation_policy(). "
        f"See {MIGRATION_GUIDE_URL}"
    )

    policy_manager = di.policy_manager
    return policy_manager.resolve_task_annotation_policy(di, scan_options)


def resolve_task_traversal_policy(
    di: DIContainer,
    scan_options: dict[str, object],
) -> PreparedTaskTraversalPolicy:
    """Deprecated wrapper for resolve_task_traversal_policy.

    This function is DEPRECATED. Use `di.policy_manager.resolve_task_traversal_policy()` instead.

    Args:
        di: DIContainer for policy manager access.
        scan_options: Scan options including platform key.

    Returns:
        PreparedTaskTraversalPolicy implementation.

    Raises:
        ValueError: If policy cannot be resolved.

    .. deprecated:: Wave 3
        Use :meth:`DIContainer.policy_manager` to access PolicyManager directly.
    """
    warnings.warn(
        "resolve_task_traversal_policy() is deprecated and will be removed in a future release. "
        f"Use di.policy_manager.resolve_task_traversal_policy() instead. "
        f"See {MIGRATION_GUIDE_URL} for migration guide.",
        DeprecationWarning,
        stacklevel=2,
    )
    logger.warning(
        "Deprecated function resolve_task_traversal_policy() called. "
        f"Migrate to di.policy_manager.resolve_task_traversal_policy(). "
        f"See {MIGRATION_GUIDE_URL}"
    )

    policy_manager = di.policy_manager
    return policy_manager.resolve_task_traversal_policy(di, scan_options)


def resolve_variable_extractor_policy(
    di: DIContainer,
    scan_options: dict[str, object],
) -> PreparedVariableExtractorPolicy:
    """Deprecated wrapper for resolve_variable_extractor_policy.

    This function is DEPRECATED. Use `di.policy_manager.resolve_variable_extractor_policy()` instead.

    Args:
        di: DIContainer for policy manager access.
        scan_options: Scan options including platform key.

    Returns:
        PreparedVariableExtractorPolicy implementation.

    Raises:
        ValueError: If policy cannot be resolved.

    .. deprecated:: Wave 3
        Use :meth:`DIContainer.policy_manager` to access PolicyManager directly.
    """
    warnings.warn(
        "resolve_variable_extractor_policy() is deprecated and will be removed in a future release. "
        f"Use di.policy_manager.resolve_variable_extractor_policy() instead. "
        f"See {MIGRATION_GUIDE_URL} for migration guide.",
        DeprecationWarning,
        stacklevel=2,
    )
    logger.warning(
        "Deprecated function resolve_variable_extractor_policy() called. "
        f"Migrate to di.policy_manager.resolve_variable_extractor_policy(). "
        f"See {MIGRATION_GUIDE_URL}"
    )

    policy_manager = di.policy_manager
    return policy_manager.resolve_variable_extractor_policy(di, scan_options)


def resolve_yaml_parsing_policy(
    di: DIContainer,
    scan_options: dict[str, object],
) -> PreparedYAMLParsingPolicy:
    """Deprecated wrapper for resolve_yaml_parsing_policy.

    This function is DEPRECATED. Use `di.policy_manager.resolve_yaml_parsing_policy()` instead.

    Args:
        di: DIContainer for policy manager access.
        scan_options: Scan options including platform key.

    Returns:
        PreparedYAMLParsingPolicy implementation.

    Raises:
        ValueError: If policy cannot be resolved.

    .. deprecated:: Wave 3
        Use :meth:`DIContainer.policy_manager` to access PolicyManager directly.
    """
    warnings.warn(
        "resolve_yaml_parsing_policy() is deprecated and will be removed in a future release. "
        f"Use di.policy_manager.resolve_yaml_parsing_policy() instead. "
        f"See {MIGRATION_GUIDE_URL} for migration guide.",
        DeprecationWarning,
        stacklevel=2,
    )
    logger.warning(
        "Deprecated function resolve_yaml_parsing_policy() called. "
        f"Migrate to di.policy_manager.resolve_yaml_parsing_policy(). "
        f"See {MIGRATION_GUIDE_URL}"
    )

    policy_manager = di.policy_manager
    return policy_manager.resolve_yaml_parsing_policy(di, scan_options)


def resolve_jinja_analysis_policy(
    di: DIContainer,
    scan_options: dict[str, object],
) -> PreparedJinjaAnalysisPolicy:
    """Deprecated wrapper for resolve_jinja_analysis_policy.

    This function is DEPRECATED. Use `di.policy_manager.resolve_jinja_analysis_policy()` instead.

    Args:
        di: DIContainer for policy manager access.
        scan_options: Scan options including platform key.

    Returns:
        PreparedJinjaAnalysisPolicy implementation.

    Raises:
        ValueError: If policy cannot be resolved.

    .. deprecated:: Wave 3
        Use :meth:`DIContainer.policy_manager` to access PolicyManager directly.
    """
    warnings.warn(
        "resolve_jinja_analysis_policy() is deprecated and will be removed in a future release. "
        f"Use di.policy_manager.resolve_jinja_analysis_policy() instead. "
        f"See {MIGRATION_GUIDE_URL} for migration guide.",
        DeprecationWarning,
        stacklevel=2,
    )
    logger.warning(
        "Deprecated function resolve_jinja_analysis_policy() called. "
        f"Migrate to di.policy_manager.resolve_jinja_analysis_policy(). "
        f"See {MIGRATION_GUIDE_URL}"
    )

    policy_manager = di.policy_manager
    return policy_manager.resolve_jinja_analysis_policy(di, scan_options)
