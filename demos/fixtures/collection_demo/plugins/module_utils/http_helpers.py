"""Shared helper utilities for demo modules."""


def build_demo_response(message: str) -> dict:
    return {
        "changed": False,
        "message": message,
    }
