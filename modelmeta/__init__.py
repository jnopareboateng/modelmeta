"""modelmeta: portable, hash-linked metadata sidecars for model checkpoints."""

from __future__ import annotations

from modelmeta.canonical import canonical_bytes, is_valid_timestamp, normalize, utc_now
from modelmeta.errors import (
    ModelMetaError,
    RaceDetectedError,
    SchemaError,
    SidecarIOError,
    UnsupportedSchemaError,
    UnsupportedTargetError,
)
from modelmeta.schema import SCHEMA_VERSION, assert_no_secret_keys, validate_metadata

__version__ = "0.1.0"

__all__ = [
    "SCHEMA_VERSION",
    "ModelMetaError",
    "RaceDetectedError",
    "SchemaError",
    "SidecarIOError",
    "UnsupportedSchemaError",
    "UnsupportedTargetError",
    "assert_no_secret_keys",
    "canonical_bytes",
    "is_valid_timestamp",
    "normalize",
    "utc_now",
    "validate_metadata",
]
