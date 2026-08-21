"""Typed schema validation for sidecar metadata."""

from __future__ import annotations

import copy
import math
import re
from collections.abc import Mapping
from typing import Any

from modelmeta.canonical import is_valid_timestamp
from modelmeta.errors import SchemaError, UnsupportedSchemaError

SCHEMA_VERSION = "0.1"

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SECRET_KEY_PATTERN = re.compile(r"(?i)(token|secret|password|api[_-]?key)")

_CHECKPOINT_KINDS = frozenset({"file", "directory"})

_TRAINING_NUMERIC_FIELDS = frozenset(
    {"global_step", "epoch", "loss", "learning_rate", "gradient_norm"}
)
_TRAINING_INT_FIELDS = frozenset({"global_step"})
_COMPUTE_STR_FIELDS = frozenset({"framework", "framework_version", "accelerator_type", "precision"})
_COMPUTE_INT_FIELDS = frozenset({"accelerator_count"})


def assert_no_secret_keys(value: Mapping[str, Any], prefix: str = "") -> None:
    """Refuse caller-supplied mappings whose keys look like credentials.

    This is a conservative substring guard on caller input before it enters a
    sidecar; it is a safety check, not complete secret detection.
    """
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(key, str) and SECRET_KEY_PATTERN.search(key) is not None:
            raise ValueError(f"refusing caller-supplied key that looks like a credential: {path}")
        if isinstance(item, Mapping):
            assert_no_secret_keys(item, path)
        elif isinstance(item, list):
            for index, entry in enumerate(item):
                if isinstance(entry, Mapping):
                    assert_no_secret_keys(entry, f"{path}[{index}]")


def validate_metadata(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a full metadata mapping and return an independent deep copy.

    Unknown sections are preserved verbatim but must remain JSON-serializable.
    Raises UnsupportedSchemaError for a foreign schema_version and SchemaError
    for every structural violation.
    """
    if not isinstance(raw, Mapping):
        raise SchemaError("document: must be a mapping")
    data = copy.deepcopy(dict(raw))

    version = _required_str(data, "schema_version")
    if version != SCHEMA_VERSION:
        raise UnsupportedSchemaError(
            f"schema_version {version!r} is not supported by this release; refusing to parse"
        )

    created_at = _required_str(data, "created_at")
    if not is_valid_timestamp(created_at):
        raise SchemaError(
            "created_at: must be UTC 'YYYY-MM-DDTHH:MM:SSZ' with no fractional seconds"
        )

    checkpoint = data.get("checkpoint")
    if checkpoint is None:
        raise SchemaError("checkpoint: required section is missing")
    _validate_checkpoint(_as_mapping(checkpoint, "checkpoint"))

    provenance = data.get("provenance")
    if provenance is not None:
        _validate_provenance(_as_mapping(provenance, "provenance"))

    training = data.get("training")
    if training is not None:
        _validate_training(_as_mapping(training, "training"))

    compute = data.get("compute")
    if compute is not None:
        _validate_compute(_as_mapping(compute, "compute"))

    integrity = data.get("integrity")
    if integrity is not None:
        _validate_integrity(_as_mapping(integrity, "integrity"))

    _ensure_json_value(data, "")
    return data


def _validate_checkpoint(checkpoint: dict[str, Any]) -> None:
    kind = _required_str(checkpoint, "checkpoint.kind")
    if kind not in _CHECKPOINT_KINDS:
        raise SchemaError(
            f"checkpoint.kind: must be one of {sorted(_CHECKPOINT_KINDS)}, got {kind!r}"
        )

    digest = _required_str(checkpoint, "checkpoint.sha256")
    if SHA256_PATTERN.fullmatch(digest) is None:
        raise SchemaError("checkpoint.sha256: must be a lowercase 64-character hex SHA-256 digest")

    size = _required(checkpoint, "checkpoint.size_bytes")
    if type(size) is not int or size < 0:
        raise SchemaError("checkpoint.size_bytes: must be a non-negative integer")

    _required_str(checkpoint, "checkpoint.path")


def _validate_provenance(provenance: dict[str, Any]) -> None:
    git = provenance.get("git")
    if git is not None:
        git_mapping = _as_mapping(git, "provenance.git")
        dirty = git_mapping.get("dirty")
        if dirty is not None and not isinstance(dirty, bool):
            raise SchemaError("provenance.git.dirty: must be a boolean")
        commit = git_mapping.get("commit")
        if commit is not None and not isinstance(commit, str):
            raise SchemaError("provenance.git.commit: must be a string")

    dataset = provenance.get("dataset")
    if dataset is not None:
        dataset_mapping = _as_mapping(dataset, "provenance.dataset")
        digest = dataset_mapping.get("digest")
        if digest is not None and not isinstance(digest, str):
            raise SchemaError("provenance.dataset.digest: must be a string")


def _validate_training(training: dict[str, Any]) -> None:
    for field in _TRAINING_NUMERIC_FIELDS:
        value = training.get(field)
        if value is None:
            continue
        if type(value) is bool or not isinstance(value, (int, float)):
            raise SchemaError(f"training.{field}: must be a number")
        if field in _TRAINING_INT_FIELDS and type(value) is not int:
            raise SchemaError(f"training.{field}: must be an integer")


def _validate_compute(compute: dict[str, Any]) -> None:
    for field in _COMPUTE_STR_FIELDS:
        value = compute.get(field)
        if value is not None and not isinstance(value, str):
            raise SchemaError(f"compute.{field}: must be a string")
    count = compute.get("accelerator_count")
    if count is not None and (type(count) is not int or count < 0):
        raise SchemaError("compute.accelerator_count: must be a non-negative integer")
    gpu_hours = compute.get("gpu_hours")
    if gpu_hours is not None and (
        type(gpu_hours) is bool or not isinstance(gpu_hours, (int, float))
    ):
        raise SchemaError("compute.gpu_hours: must be a number")


def _validate_integrity(integrity: dict[str, Any]) -> None:
    signed = integrity.get("signed")
    if signed is not None and not isinstance(signed, bool):
        raise SchemaError("integrity.signed: must be a boolean")
    encoding = integrity.get("metadata_encoding")
    if encoding is not None and not isinstance(encoding, str):
        raise SchemaError("integrity.metadata_encoding: must be a string")


def _ensure_json_value(value: Any, path: str) -> None:
    """Fail closed on any value that would break canonical JSON encoding."""
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SchemaError(f"{path or 'document'}: NaN and Infinity are not representable")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise SchemaError(f"{path}: mapping keys must be strings, got {type(key).__name__}")
            child_path = f"{path}.{key}" if path else key
            _ensure_json_value(item, child_path)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _ensure_json_value(item, f"{path}[{index}]")
        return
    raise SchemaError(f"{path or 'document'}: unsupported value type {type(value).__name__}")


def _required(mapping: Mapping[str, Any], path: str) -> Any:
    value = mapping.get(path.rsplit(".", 1)[-1])
    if value is None:
        raise SchemaError(f"{path}: required field is missing or null")
    return value


def _required_str(mapping: Mapping[str, Any], path: str) -> str:
    value = _required(mapping, path)
    if not isinstance(value, str) or not value:
        raise SchemaError(f"{path}: must be a non-empty string")
    return value


def _as_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaError(f"{path or 'document'}: must be a mapping")
    return value if type(value) is dict else dict(value)
