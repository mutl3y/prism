# Mock Projects for Plugin Development

This directory contains realistic example projects for Terraform and Kubernetes plugin testing and development.

## Structure

- `terraform/` - Mock Terraform project with sample configurations
- `kubernetes/` - Mock Kubernetes project with sample manifests

## Purpose

These mock projects are used to:
1. Test plugin parsing and analysis capabilities
2. Validate error detection and classification
3. Test unified error provenance across platforms
4. Provide reference implementations for plugin developers
5. Support integration testing and parity tests

## Usage

When developing plugins:

```python
# Terraform plugin testing
from prism.scanner_plugins.terraform import scanner
tf_scanner = scanner.TerraformScanner()
result = tf_scanner.scan_configs(['docs/plan/.../mock-projects/terraform/'])

# Kubernetes plugin testing
from prism.scanner_plugins.kubernetes import scanner
k8s_scanner = scanner.KubernetesScanner()
result = k8s_scanner.scan_manifests(['docs/plan/.../mock-projects/kubernetes/'])
```

## Contents

See individual directories for detailed documentation.
