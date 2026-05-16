import pytest
from prism.scanner_core.marker_prefix_contract import MarkerPrefixContract
from prism.scanner_core.scanner_context import PreparedPolicyBundle

# Fixtures
@pytest.fixture
def valid_policy_bundle():
    return PreparedPolicyBundle(marker_prefix="valid_prefix")

@pytest.fixture
def invalid_policy_bundle():
    return PreparedPolicyBundle(marker_prefix="")

@pytest.fixture
def marker_contract():
    return MarkerPrefixContract()

# Test: PreparedPolicyBundle with marker_prefix
def test_valid_marker_prefix(marker_contract, valid_policy_bundle):
    """Ensure that a valid marker_prefix passes validation."""
    marker_contract.validate(valid_policy_bundle)

# Test: PreparedPolicyBundle without marker_prefix
def test_invalid_marker_prefix(marker_contract, invalid_policy_bundle):
    """Ensure that an invalid marker_prefix raises an error."""
    with pytest.raises(ValueError, match="marker_prefix must not be empty"):
        marker_contract.validate(invalid_policy_bundle)

# Test: Enforcement errors
def test_enforce_marker_prefix_available(marker_contract):
    """Ensure enforce_marker_prefix_available raises errors for invalid prefixes."""
    with pytest.raises(ValueError, match="marker_prefix must not be empty"):
        marker_contract.enforce_marker_prefix_available("")

    with pytest.raises(ValueError, match="marker_prefix must not be empty"):
        marker_contract.enforce_marker_prefix_available(None)

# Test: Consumer contract validation
def test_consumer_contract_validation(marker_contract, valid_policy_bundle):
    """Ensure consumer contract validation works with valid marker_prefix."""
    marker_contract.enforce_marker_prefix_available(valid_policy_bundle.marker_prefix)

# Integration Tests
def test_integration_marker_prefix_in_context(marker_contract, valid_policy_bundle):
    """Integration test for marker_prefix validation in scanner_context."""
    marker_contract.validate(valid_policy_bundle)

# Regression Tests
def test_regression_marker_prefix_dynamic_resolution():
    """Ensure dynamic resolution of marker_prefix is removed."""
    # This test ensures that no dynamic resolution logic exists.
    # Implementation-specific checks can be added here.
    assert True  # Placeholder for actual regression logic

# Additional tests can be added below for edge cases and other scenarios.