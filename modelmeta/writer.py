"""Atomic creation of hash-linked metadata sidecars."""

from __future__ import annotations

import contextlib
import copy
import os
import re
import stat
import tempfile
import time
from collections.abc import Mapping
from typing import Any

import yaml

from modelmeta.canonical import utc_now
from modelmeta.errors import UnsupportedTargetError
from modelmeta.hashing import (
    SIDECAR_SUFFIX,
    DigestResult,
    hash_directory,
    hash_file,
    is_temp_name,
    sidecar_name_for,
)
from modelmeta.schema import SCHEMA_VERSION, assert_no_secret_keys, validate_metadata

_METADATA_ENCODING = "yaml+canonical-json-v1"
_YAML_DUMPS: dict[str, Any] = {
    "sort_keys": True,
    "default_flow_style": False,
    "allow_unicode": True,
    "width": 10**6,
}
_TEMP_TARGET_PATTERN = re.compile(r"\.modelmeta\.yaml\.tmp")
_REPLACE_ATTEMPTS = 3


class MetaWriter:
    """Writes metadata sidecars next to checkpoints.

    The writer never mutates caller-owned dictionaries and never merges into
    an existing sidecar: every write fully replaces it atomically.
    """

    def __init__(self, run_context: Mapping[str, Any] | None = None) -> None:
        self._run_context: dict[str, Any] = copy.deepcopy(dict(run_context)) if run_context else {}
        self.last_hash_seconds: float | None = None

    def on_checkpoint_saved(
        self,
        checkpoint_path: str | os.PathLike[str],
        *,
        training_state: Mapping[str, Any] | None = None,
        compute_state: Mapping[str, Any] | None = None,
        lineage: Mapping[str, Any] | None = None,
        optimizer_state: Mapping[str, Any] | None = None,
    ) -> str:
        """Hash the checkpoint and atomically write its sidecar.

        Returns the final sidecar path. On any failure the previous valid
        sidecar is left untouched and no partial sidecar exists.
        """
        target = os.fspath(checkpoint_path)
        if not os.path.exists(target):
            raise FileNotFoundError(f"checkpoint does not exist: {target}")
        if is_temp_name(os.path.basename(target)) or _TEMP_TARGET_PATTERN.search(target):
            raise UnsupportedTargetError(f"refusing to describe a temporary file: {target}")

        caller_sections = {
            "run_context": self._run_context or None,
            "training_state": training_state,
            "compute_state": compute_state,
            "lineage": lineage,
            "optimizer_state": optimizer_state,
        }
        for name, section in caller_sections.items():
            if section:
                try:
                    assert_no_secret_keys(section)
                except ValueError as error:
                    raise ValueError(f"{name}: {error}") from error

        result = self._hash_target(target)
        self.last_hash_seconds = result.elapsed_seconds

        metadata = self._build_metadata(target, result, caller_sections)
        validated = validate_metadata(metadata)
        payload = yaml.safe_dump(validated, **_YAML_DUMPS).encode("utf-8")

        sidecar_path = self._sidecar_path_for(target)
        _require_writable_sidecar_location(sidecar_path)
        _atomic_write(sidecar_path, payload)
        return sidecar_path

    def _hash_target(self, target: str) -> DigestResult:
        if os.path.isdir(target):
            directory_name = os.path.basename(os.path.normpath(target))
            return hash_directory(target, sidecar_name_for(directory_name))
        return hash_file(target)

    def _build_metadata(
        self, target: str, result: DigestResult, sections: dict[str, Mapping[str, Any] | None]
    ) -> dict[str, Any]:
        is_directory = os.path.isdir(target)
        display_path = (
            os.path.basename(os.path.normpath(target)) if is_directory else os.path.basename(target)
        )
        metadata: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "created_at": utc_now(),
            "checkpoint": {
                "kind": "directory" if is_directory else "file",
                "path": display_path,
                "size_bytes": result.size_bytes,
                "sha256": result.digest,
            },
        }
        if sections["run_context"]:
            metadata["provenance"] = copy.deepcopy(dict(sections["run_context"]))
        if sections["training_state"]:
            metadata["training"] = copy.deepcopy(dict(sections["training_state"]))
        if sections["compute_state"]:
            metadata["compute"] = copy.deepcopy(dict(sections["compute_state"]))
        if sections["lineage"]:
            metadata["lineage"] = copy.deepcopy(dict(sections["lineage"]))
        if sections["optimizer_state"]:
            metadata["optimizer_state"] = copy.deepcopy(dict(sections["optimizer_state"]))
        metadata["integrity"] = {"metadata_encoding": _METADATA_ENCODING, "signed": False}
        return metadata

    def _sidecar_path_for(self, target: str) -> str:
        if os.path.isdir(target):
            directory_name = os.path.basename(os.path.normpath(target))
            return os.path.join(target, sidecar_name_for(directory_name))
        return target + SIDECAR_SUFFIX


def _require_writable_sidecar_location(sidecar_path: str) -> None:
    if not os.path.lexists(sidecar_path):
        return
    info = os.lstat(sidecar_path)
    if not stat.S_ISREG(info.st_mode):
        raise UnsupportedTargetError(
            f"reserved sidecar path is occupied by a non-regular object: {sidecar_path}"
        )


def _atomic_write(final_path: str, payload: bytes) -> None:
    parent = os.path.dirname(final_path)
    descriptor, temp_path = tempfile.mkstemp(
        prefix=os.path.basename(final_path) + ".tmp", dir=parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        _replace_with_retry(temp_path, final_path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temp_path)
        raise
    _fsync_parent_posix(parent)


def _replace_with_retry(source: str, destination: str) -> None:
    for attempt in range(_REPLACE_ATTEMPTS):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if os.name != "nt" or attempt == _REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(0.05 * (attempt + 1))


def _fsync_parent_posix(directory: str) -> None:
    if os.name != "posix":
        return
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)
