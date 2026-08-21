"""Digest and schema verification with stable outcomes."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from modelmeta.errors import (
    RaceDetectedError,
    SchemaError,
    SidecarIOError,
    UnsupportedSchemaError,
    UnsupportedTargetError,
)
from modelmeta.hashing import DigestResult, hash_directory, hash_file, sidecar_name_for
from modelmeta.reader import load_sidecar
from modelmeta.schema import validate_metadata

STATUS_MATCH = "match"
STATUS_MISSING_SIDECAR = "missing_sidecar"
STATUS_INVALID_SCHEMA = "invalid_schema"
STATUS_DIGEST_MISMATCH = "digest_mismatch"
STATUS_UNSUPPORTED_TARGET = "unsupported_target"
STATUS_UNSUPPORTED_SCHEMA = "unsupported_schema"
STATUS_IO_ERROR = "io_error"
STATUS_RACE_DETECTED = "race_detected"

EXIT_MATCH = 0
EXIT_MISSING_SIDECAR = 10
EXIT_INVALID_SCHEMA = 11
EXIT_DIGEST_MISMATCH = 12
EXIT_UNSUPPORTED = 13
EXIT_INCOMPLETE = 14

SUCCESS_MESSAGE = "checkpoint integrity verified; metadata remains self-asserted"


@dataclass(frozen=True)
class VerificationOutcome:
    """Domain result of a verification attempt; never raised."""

    status: str
    exit_code: int
    detail: dict[str, Any] = field(default_factory=dict)


def sidecar_path_for(checkpoint_path: str) -> str:
    """Sidecar location derived from the caller-supplied checkpoint path only."""
    if os.path.isdir(checkpoint_path):
        directory_name = os.path.basename(os.path.normpath(checkpoint_path))
        return os.path.join(checkpoint_path, sidecar_name_for(directory_name))
    return checkpoint_path + ".modelmeta.yaml"


def verify_checkpoint(checkpoint_path: str | os.PathLike[str]) -> VerificationOutcome:
    """Recompute the checkpoint digest and compare it against the sidecar.

    The checkpoint must exist; the sidecar need not. All domain failures are
    returned as VerificationOutcome values with the documented exit codes.
    """
    target = os.fspath(checkpoint_path)
    if not os.path.exists(target):
        raise FileNotFoundError(f"checkpoint does not exist: {target}")
    sidecar_path = sidecar_path_for(target)
    try:
        return _verify(target, sidecar_path)
    except (UnsupportedSchemaError, SchemaError) as error:
        status = (
            STATUS_UNSUPPORTED_SCHEMA
            if isinstance(error, UnsupportedSchemaError)
            else STATUS_INVALID_SCHEMA
        )
        code = (
            EXIT_UNSUPPORTED if isinstance(error, UnsupportedSchemaError) else EXIT_INVALID_SCHEMA
        )
        return VerificationOutcome(status, code, {"message": str(error)})
    except RaceDetectedError as error:
        return VerificationOutcome(STATUS_RACE_DETECTED, EXIT_INCOMPLETE, {"message": str(error)})
    except UnsupportedTargetError as error:
        return VerificationOutcome(
            STATUS_UNSUPPORTED_TARGET, EXIT_UNSUPPORTED, {"message": str(error)}
        )
    except (SidecarIOError, OSError) as error:
        return VerificationOutcome(STATUS_IO_ERROR, EXIT_INCOMPLETE, {"message": str(error)})


def _verify(target: str, sidecar_path: str) -> VerificationOutcome:
    if not os.path.lexists(sidecar_path):
        return VerificationOutcome(
            STATUS_MISSING_SIDECAR,
            EXIT_MISSING_SIDECAR,
            {"sidecar_path": sidecar_path},
        )
    metadata = load_sidecar(sidecar_path)
    validated = validate_metadata(metadata)
    result = _hash_target(target)
    recorded = validated["checkpoint"]["sha256"]
    if result.digest != recorded:
        return VerificationOutcome(
            STATUS_DIGEST_MISMATCH,
            EXIT_DIGEST_MISMATCH,
            {
                "message": "checkpoint bytes do not match the digest recorded in the sidecar",
                "recorded_sha256": recorded,
                "computed_sha256": result.digest,
            },
        )
    return VerificationOutcome(
        STATUS_MATCH,
        EXIT_MATCH,
        {
            "message": SUCCESS_MESSAGE,
            "sha256": result.digest,
            "size_bytes": result.size_bytes,
            "hash_seconds": round(result.elapsed_seconds, 6),
        },
    )


def _hash_target(target: str) -> DigestResult:
    if os.path.isdir(target):
        directory_name = os.path.basename(os.path.normpath(target))
        return hash_directory(target, sidecar_name_for(directory_name))
    return hash_file(target)
