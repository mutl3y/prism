"""MarkerPrefixContract: Enforces marker-prefix ownership and validation.

This module defines the MarkerPrefixContract class, which ensures that the
marker-prefix is validated at runtime and is read-only once set in the
PreparedPolicyBundle.
"""

from typing import Any


class MarkerPrefixContract:
    """Validation class for enforcing marker-prefix ownership.

    This helper accepts either the concrete `PreparedPolicyBundle` object or a
    dict-like projection (legacy/prepared dict). Tests and some callsites pass
    a dict with the key `comment_doc_marker_prefix`, while other callsites may
    use an object with attribute `marker_prefix`. To preserve the MP1 ValueError
    contract, this class normalizes both shapes and raises `ValueError` on any
    invalid or missing value.
    """

    @staticmethod
    def validate(bundle: Any) -> str:
        """Validate that the marker-prefix exists and return it as a string.

        Args:
            bundle: Either a PreparedPolicyBundle or a dict-like projection
                containing the marker-prefix under `comment_doc_marker_prefix`.

        Returns:
            str: The marker-prefix value.

        Raises:
            ValueError: If the marker-prefix is missing or invalid.
        """
        # Accept dict-like bundles produced by bundle_resolver tests
        if isinstance(bundle, dict):
            if "comment_doc_marker_prefix" not in bundle:
                raise ValueError(
                    "PreparedPolicyBundle missing required comment_doc_marker_prefix"
                )
            marker = bundle.get("comment_doc_marker_prefix")
        else:
            # Try object attribute (PreparedPolicyBundle-like)
            try:
                marker = getattr(bundle, "marker_prefix")
            except Exception:
                raise ValueError(
                    "PreparedPolicyBundle missing required marker_prefix attribute"
                )

        # Validate type and content
        if not isinstance(marker, str):
            raise ValueError(
                f"marker_prefix must be a string, got {type(marker).__name__}"
            )
        if marker.strip() == "":
            raise ValueError("marker_prefix must be a non-empty string")
        if any(c in marker for c in "\n\t\r"):
            raise ValueError("marker_prefix contains invalid control characters")

        return marker

    @staticmethod
    def enforce_marker_prefix_available(marker_prefix: str) -> None:
        """Ensure the marker-prefix is a valid non-empty string.

        Raises ValueError when the value is invalid; preserved for MP1 tests.
        """
        if not marker_prefix or not isinstance(marker_prefix, str):
            raise ValueError(
                f"marker_prefix must be a non-empty string, got {marker_prefix!r}"
            )
        if marker_prefix.strip() == "":
            raise ValueError("marker_prefix cannot be empty or whitespace-only.")
        if any(char in marker_prefix for char in "\n\t\r"):
            raise ValueError("marker_prefix contains invalid control characters.")
