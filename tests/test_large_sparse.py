"""Acceptance test: hashing a checkpoint larger than available memory (spec §16.9).

Uses sparse files so the fixture allocates almost no real disk or RAM.
Marked slow; runs in pre-push and explicitly via `uv run pytest -m slow`.
"""

from __future__ import annotations

import hashlib
import os
import sys
from typing import Any

import pytest
from modelmeta.hashing import hash_file

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(sys.platform == "win32", reason="NTFS would really allocate the bytes"),
]

SIZE_BYTES = int(os.environ.get("MODELMETA_SPARSE_TEST_GB", "16")) * 1024**3


def test_sparse_checkpoint_larger_than_memory(tmp_path: Any) -> None:
    target = tmp_path / "huge.bin"
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        os.ftruncate(descriptor, SIZE_BYTES)
        os.pwrite(descriptor, b"\x01", 0)
        os.pwrite(descriptor, b"\x02", SIZE_BYTES - 1)
    finally:
        os.close(descriptor)

    assert target.stat().st_size == SIZE_BYTES

    result = hash_file(str(target))

    hasher = hashlib.sha256()
    hasher.update(b"\x01")
    zeros = bytes(8 * 1024 * 1024)
    remaining = SIZE_BYTES - 2
    while remaining > 0:
        chunk = zeros if remaining > len(zeros) else bytes(remaining)
        hasher.update(chunk)
        remaining -= len(chunk)
    hasher.update(b"\x02")
    assert result.digest == hasher.hexdigest()
    assert result.size_bytes == SIZE_BYTES
