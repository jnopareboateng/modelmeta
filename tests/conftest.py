"""Shared fixtures and metadata builders for the test suite."""

from __future__ import annotations

from typing import Any

import pytest


def file_metadata(**overrides: Any) -> dict[str, Any]:
    """A minimal valid single-file sidecar mapping, overridable per test."""
    metadata: dict[str, Any] = {
        "schema_version": "0.1",
        "created_at": "2026-07-20T00:00:00Z",
        "checkpoint": {
            "kind": "file",
            "path": "step_042000.safetensors",
            "size_bytes": 16,
            "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        },
    }
    metadata.update(overrides)
    return metadata


@pytest.fixture
def valid_file_metadata() -> dict[str, Any]:
    return file_metadata()
