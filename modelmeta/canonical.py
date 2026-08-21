"""Canonical JSON (RFC 8785 JCS) bytes, null normalization, and timestamp rules."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import rfc8785

TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def utc_now() -> str:
    """Current UTC time in the exact sidecar timestamp representation."""
    return datetime.now(UTC).strftime(_TIMESTAMP_FORMAT)


def is_valid_timestamp(value: Any) -> bool:
    """True when value is a real calendar instant in `YYYY-MM-DDTHH:MM:SSZ` form."""
    if not isinstance(value, str) or TIMESTAMP_PATTERN.fullmatch(value) is None:
        return False
    try:
        datetime.strptime(value, _TIMESTAMP_FORMAT)
    except ValueError:
        return False
    return True


def normalize(value: Any) -> Any:
    """Return a copy with explicit-null mapping values removed at every depth.

    List items are preserved verbatim except for nested mappings, so ordered
    collections never silently lose entries.
    """
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def canonical_bytes(value: Any) -> bytes:
    """RFC 8785 canonical JSON encoding of the normalized value.

    Raises ValueError/TypeError for values that cannot be represented
    (NaN, Infinity, non-string keys); schema validation guarantees these
    never reach this function for sidecar content.
    """
    return rfc8785.dumps(normalize(value))
