"""Streaming SHA-256 hashing for single-file and directory checkpoints."""

from __future__ import annotations

import hashlib
import os
import stat
import time
from dataclasses import dataclass
from typing import Any

from modelmeta.canonical import canonical_bytes
from modelmeta.errors import RaceDetectedError, UnsupportedTargetError

SIDECAR_SUFFIX = ".modelmeta.yaml"
TEMP_MARKER = ".tmp"


@dataclass(frozen=True)
class FileIdentity:
    """Best-effort identity snapshot used to detect mutation during hashing."""

    size: int
    mtime_ns: int
    inode: int
    dev: int


@dataclass(frozen=True)
class DigestResult:
    """Outcome of a hashing operation."""

    digest: str
    elapsed_seconds: float
    size_bytes: int
    manifest: dict[str, Any] | None = None


def sidecar_name_for(target_name: str) -> str:
    """Reserved sidecar filename for a checkpoint named `target_name`."""
    return f"{target_name}{SIDECAR_SUFFIX}"


def is_temp_name(name: str) -> bool:
    """True for writer temporary files matching the versioned `<sidecar>.tmp*` rule."""
    return SIDECAR_SUFFIX + TEMP_MARKER in name


def _identity(path: str) -> FileIdentity:
    info = os.lstat(path)
    return FileIdentity(info.st_size, info.st_mtime_ns, info.st_ino, info.st_dev)


def _check_same(path: str, before: FileIdentity, after: FileIdentity) -> None:
    if before.size != after.size or before.mtime_ns != after.mtime_ns:
        raise RaceDetectedError(f"target changed while being hashed: {path}")
    inode_meaningful = before.inode != 0 and after.inode != 0
    if inode_meaningful and (before.inode != after.inode or before.dev != after.dev):
        raise RaceDetectedError(f"target was replaced while being hashed: {path}")


def _require_regular_file(path: str) -> FileIdentity:
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode):
        raise UnsupportedTargetError(f"refusing to hash a symlink: {path}")
    if not stat.S_ISREG(info.st_mode):
        raise UnsupportedTargetError(f"refusing to hash a non-regular file: {path}")
    return FileIdentity(info.st_size, info.st_mtime_ns, info.st_ino, info.st_dev)


def _hash_stream(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def hash_file(path: str | os.PathLike[str]) -> DigestResult:
    """Stream-hash a regular file with pre/post race detection."""
    target = os.fspath(path)
    before = _require_regular_file(target)
    started = time.perf_counter()
    digest = _hash_stream(target)
    elapsed = time.perf_counter() - started
    _check_same(target, before, _identity(target))
    return DigestResult(digest=digest, elapsed_seconds=elapsed, size_bytes=before.size)


def hash_directory(path: str | os.PathLike[str], sidecar_name: str) -> DigestResult:
    """Hash a directory checkpoint through its deterministic manifest.

    The reserved sidecar file and writer temporaries are excluded by exact,
    versioned rules; orphaned temporaries are removed before hashing.
    """
    target = os.fspath(path)
    info = os.lstat(target)
    if stat.S_ISLNK(info.st_mode):
        raise UnsupportedTargetError(f"refusing to hash a symlink: {target}")
    if not stat.S_ISDIR(info.st_mode):
        raise UnsupportedTargetError(f"directory checkpoint expected, got: {target}")

    _remove_orphan_temps(target, sidecar_name)
    dir_before = _identity(target)
    started = time.perf_counter()

    relatives: list[str] = []
    absolute_by_relative: dict[str, str] = {}
    for root, dirs, files in os.walk(target, followlinks=False):
        for name in dirs:
            absolute_dir = os.path.join(root, name)
            if os.path.islink(absolute_dir):
                raise UnsupportedTargetError(
                    f"symlinked directory inside checkpoint is unsupported: {absolute_dir}"
                )
        for name in files:
            relative = os.path.relpath(os.path.join(root, name), target).replace(os.sep, "/")
            if relative == sidecar_name or is_temp_name(relative):
                continue
            relatives.append(relative)
            absolute_by_relative[relative] = os.path.join(root, name)

    relatives.sort(key=lambda item: item.encode("utf-8"))

    manifest_files: list[dict[str, Any]] = []
    identities: list[tuple[str, FileIdentity]] = []
    total_bytes = 0
    for relative in relatives:
        absolute = absolute_by_relative[relative]
        before = _require_regular_file(absolute)
        digest = _hash_stream(absolute)
        total_bytes += before.size
        manifest_files.append({"path": relative, "sha256": digest, "size_bytes": before.size})
        identities.append((absolute, before))

    elapsed = time.perf_counter() - started
    for absolute, before in identities:
        _check_same(absolute, before, _identity(absolute))
    _check_same(target, dir_before, _identity(target))

    manifest = {"files": manifest_files}
    digest = hashlib.sha256(canonical_bytes(manifest)).hexdigest()
    return DigestResult(
        digest=digest, elapsed_seconds=elapsed, size_bytes=total_bytes, manifest=manifest
    )


def _remove_orphan_temps(directory: str, sidecar_name: str) -> None:
    prefix = sidecar_name + TEMP_MARKER
    with os.scandir(directory) as entries:
        orphans = [entry.path for entry in entries if entry.name.startswith(prefix)]
    for orphan in orphans:
        try:
            os.unlink(orphan)
        except OSError as error:
            raise UnsupportedTargetError(
                f"orphaned temporary file could not be removed: {orphan}"
            ) from error
