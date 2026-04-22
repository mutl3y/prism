"""Domain-neutral default policy ownership seams for scanner plugins."""

from __future__ import annotations

from prism.scanner_plugins.parsers.jinja import JinjaAnalysisPolicyPlugin
from prism.scanner_plugins.parsers.yaml import YAMLParsingPolicyPlugin
from prism.scanner_plugins.policies.extract_defaults import (
    DefaultTaskAnnotationPolicyPlugin,
)
from prism.scanner_plugins.policies.extract_defaults import (
    DefaultTaskLineParsingPolicyPlugin,
)
from prism.scanner_plugins.policies.extract_defaults import (
    DefaultTaskTraversalPolicyPlugin,
)
from prism.scanner_plugins.policies.extract_defaults import (
    DefaultVariableExtractorPolicyPlugin,
)
from prism.scanner_plugins.policies.default_scan_pipeline import (
    DefaultScanPipelinePlugin,
)

__all__ = [
    "DefaultScanPipelinePlugin",
    "DefaultTaskAnnotationPolicyPlugin",
    "DefaultTaskLineParsingPolicyPlugin",
    "DefaultTaskTraversalPolicyPlugin",
    "DefaultVariableExtractorPolicyPlugin",
    "JinjaAnalysisPolicyPlugin",
    "YAMLParsingPolicyPlugin",
]
