"""Kubernetes sanitization fixtures.

Provides fixtures for testing secret sanitization including kubeconfig
tokens and sensitive data removal.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def k8s_kubeconfig_with_token() -> str:
    """Kubeconfig file with bearer token."""
    return """
apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: LS0tLS1CRUdJTi...
    server: https://prod-cluster.k8s.local
  name: prod-cluster
contexts:
- context:
    cluster: prod-cluster
    user: admin
  name: prod-context
current-context: prod-context
kind: Config
preferences: {}
users:
- name: admin
  user:
    token: eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3Nlcn...
"""


@pytest.fixture
def k8s_kubeconfig_with_client_cert() -> str:
    """Kubeconfig with client certificate data."""
    return """
apiVersion: v1
clusters:
- cluster:
    server: https://secure-cluster.k8s.local
  name: secure-cluster
users:
- name: cert-user
  user:
    client-certificate-data: LS0tLS1CRUdJTi...
    client-key-data: LS0tLS1CRUdJTiBSU0...
"""


@pytest.fixture
def k8s_secret_with_credentials() -> dict[str, str]:
    """K8s Secret with credentials."""
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": "db-creds", "namespace": "production"},
        "type": "Opaque",
        "data": {
            "username": "YWRtaW4=",  # base64: admin
            "password": "c3VwZXJzZWNyZXRwYXNzd29yZA==",  # base64: supersecretpassword
        },
    }


@pytest.fixture
def k8s_error_with_token() -> str:
    """Error message containing bearer token."""
    return (
        "Authentication failed: invalid token eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9."
        "eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9z"
    )


@pytest.fixture
def k8s_error_with_api_key() -> str:
    """Error message containing API key."""
    return "API authentication failed: key sk-proj-abcd1234efgh5678ijkl9012"
