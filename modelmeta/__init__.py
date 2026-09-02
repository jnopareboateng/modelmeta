"""modelmeta: portable, hash-linked metadata sidecars for model checkpoints."""

from __future__ import annotations

from modelmeta.adapters.torch_loop import capture_git_state, stamp_checkpoint
from modelmeta.canonical import canonical_bytes, is_valid_timestamp, normalize, utc_now
from modelmeta.detect import detect_accelerators
from modelmeta.errors import (
    ModelMetaError,
    RaceDetectedError,
    SchemaError,
    SidecarIOError,
    UnsupportedSchemaError,
    UnsupportedTargetError,
)
from modelmeta.reader import load_sidecar
from modelmeta.schema import SCHEMA_VERSION, assert_no_secret_keys, validate_metadata
from modelmeta.verify import SUCCESS_MESSAGE, VerificationOutcome, verify_checkpoint
from modelmeta.writer import MetaWriter

__version__ = "0.1.0"

__all__ = [
    "SCHEMA_VERSION",
    "SUCCESS_MESSAGE",
    "MetaWriter",
    "ModelMetaError",
    "RaceDetectedError",
    "SchemaError",
    "SidecarIOError",
    "UnsupportedSchemaError",
    "UnsupportedTargetError",
    "VerificationOutcome",
    "assert_no_secret_keys",
    "canonical_bytes",
    "capture_git_state",
    "detect_accelerators",
    "is_valid_timestamp",
    "load_sidecar",
    "normalize",
    "stamp_checkpoint",
    "utc_now",
    "validate_metadata",
    "verify_checkpoint",
]
