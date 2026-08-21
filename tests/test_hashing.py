"""Tests for streaming file hashing and deterministic directory manifests."""

from __future__ import annotations

import hashlib
import os
import stat
import sys
from typing import Any

import pytest
from modelmeta.errors import RaceDetectedError, UnsupportedTargetError
from modelmeta.hashing import (
    FileIdentity,
    hash_directory,
    hash_file,
    is_temp_name,
    sidecar_name_for,
)
from rfc8785 import dumps as raw_jcs_dumps

EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only filesystem semantics")


def write_file(path: str, payload: bytes) -> str:
    with open(path, "wb") as handle:
        handle.write(payload)
    return path


class TestHashFile:
    def test_empty_file_known_digest(self, tmp_path: Any) -> None:
        target = write_file(str(tmp_path / "empty.bin"), b"")
        result = hash_file(target)
        assert result.digest == EMPTY_SHA256
        assert result.size_bytes == 0

    def test_known_vector(self, tmp_path: Any) -> None:
        target = write_file(str(tmp_path / "abc.bin"), b"abc")
        assert hash_file(target).digest == ABC_SHA256

    def test_multi_megabyte_file_matches_hashlib(self, tmp_path: Any) -> None:
        payload = os.urandom(5 * 1024 * 1024 + 7)
        target = write_file(str(tmp_path / "big.bin"), payload)
        expected = hashlib.sha256(payload).hexdigest()
        assert hash_file(target).digest == expected

    def test_elapsed_time_is_reported(self, tmp_path: Any) -> None:
        target = write_file(str(tmp_path / "timed.bin"), b"abc")
        assert hash_file(target).elapsed_seconds >= 0.0

    @posix_only
    def test_symlink_rejected(self, tmp_path: Any) -> None:
        real = write_file(str(tmp_path / "real.bin"), b"abc")
        link = str(tmp_path / "link.bin")
        os.symlink(real, link)
        with pytest.raises(UnsupportedTargetError, match="symlink"):
            hash_file(link)

    @posix_only
    def test_fifo_rejected(self, tmp_path: Any) -> None:
        fifo = str(tmp_path / "pipe")
        os.mkfifo(fifo)
        with pytest.raises(UnsupportedTargetError, match="non-regular"):
            hash_file(fifo)


class TestFileIdentity:
    def test_inode_zero_degrades_to_size_and_mtime(self) -> None:
        before = FileIdentity(size=1, mtime_ns=100, inode=0, dev=1)
        after = FileIdentity(size=1, mtime_ns=100, inode=4_096, dev=1)
        from modelmeta.hashing import _check_same

        _check_same("x", before, after)

    def test_size_change_is_a_race(self) -> None:
        before = FileIdentity(size=1, mtime_ns=100, inode=7, dev=1)
        after = FileIdentity(size=2, mtime_ns=100, inode=7, dev=1)
        from modelmeta.hashing import _check_same

        with pytest.raises(RaceDetectedError):
            _check_same("x", before, after)

    def test_mtime_change_is_a_race(self) -> None:
        before = FileIdentity(size=1, mtime_ns=100, inode=7, dev=1)
        after = FileIdentity(size=1, mtime_ns=200, inode=7, dev=1)
        from modelmeta.hashing import _check_same

        with pytest.raises(RaceDetectedError):
            _check_same("x", before, after)

    def test_inode_change_is_a_race_when_meaningful(self) -> None:
        before = FileIdentity(size=1, mtime_ns=100, inode=7, dev=1)
        after = FileIdentity(size=1, mtime_ns=100, inode=8, dev=1)
        from modelmeta.hashing import _check_same

        with pytest.raises(RaceDetectedError):
            _check_same("x", before, after)


class TestHashDirectory:
    def make_tree(self, root: str) -> str:
        os.makedirs(os.path.join(root, "shards"))
        write_file(os.path.join(root, "shards", "model-00001.safetensors"), b"one")
        write_file(os.path.join(root, "shards", "model-00002.safetensors"), b"two")
        write_file(os.path.join(root, "optimizer.pt"), b"opt")
        return root

    def test_manifest_digest_matches_independent_computation(self, tmp_path: Any) -> None:
        tree = self.make_tree(str(tmp_path / "ckpt"))
        result = hash_directory(tree, sidecar_name_for("ckpt"))
        files: list[dict[str, Any]] = [
            {"path": "optimizer.pt", "sha256": hashlib.sha256(b"opt").hexdigest(), "size_bytes": 3},
            {
                "path": "shards/model-00001.safetensors",
                "sha256": hashlib.sha256(b"one").hexdigest(),
                "size_bytes": 3,
            },
            {
                "path": "shards/model-00002.safetensors",
                "sha256": hashlib.sha256(b"two").hexdigest(),
                "size_bytes": 3,
            },
        ]
        expected = hashlib.sha256(raw_jcs_dumps({"files": files})).hexdigest()
        assert result.digest == expected
        assert result.size_bytes == 9
        assert result.manifest is not None
        assert [entry["path"] for entry in result.manifest["files"]] == [
            "optimizer.pt",
            "shards/model-00001.safetensors",
            "shards/model-00002.safetensors",
        ]

    def test_digest_is_creation_order_independent(self, tmp_path: Any) -> None:
        first = self.make_tree(str(tmp_path / "a"))
        second_root = str(tmp_path / "b")
        os.makedirs(os.path.join(second_root, "shards"))
        write_file(os.path.join(second_root, "optimizer.pt"), b"opt")
        write_file(os.path.join(second_root, "shards", "model-00002.safetensors"), b"two")
        write_file(os.path.join(second_root, "shards", "model-00001.safetensors"), b"one")
        assert hash_directory(first, "a").digest == hash_directory(second_root, "b").digest

    def test_sidecar_and_temp_files_are_excluded(self, tmp_path: Any) -> None:
        tree = self.make_tree(str(tmp_path / "ckpt"))
        write_file(os.path.join(tree, sidecar_name_for("ckpt")), b"sidecar")
        write_file(os.path.join(tree, f"{sidecar_name_for('ckpt')}.tmpabc123"), b"temp")
        write_file(os.path.join(tree, "notes.modelmeta.yaml"), b"not-excluded")
        result = hash_directory(tree, sidecar_name_for("ckpt"))
        paths = [entry["path"] for entry in (result.manifest or {})["files"]]
        assert sidecar_name_for("ckpt") not in paths
        assert not any(path.startswith(sidecar_name_for("ckpt")) for path in paths)
        assert "notes.modelmeta.yaml" in paths

    def test_orphan_temps_are_removed(self, tmp_path: Any) -> None:
        tree = self.make_tree(str(tmp_path / "ckpt"))
        orphan = os.path.join(tree, f"{sidecar_name_for('ckpt')}.tmpdeadbeef")
        write_file(orphan, b"orphan")
        hash_directory(tree, sidecar_name_for("ckpt"))
        assert not os.path.exists(orphan)

    def test_unremovable_orphan_fails_hashing(self, tmp_path: Any) -> None:
        if os.geteuid() == 0:
            pytest.skip("permissions do not block root")
        tree = self.make_tree(str(tmp_path / "ckpt"))
        orphan = os.path.join(tree, f"{sidecar_name_for('ckpt')}.tmpstuck")
        write_file(orphan, b"stuck")
        os.chmod(tree, stat.S_IRUSR | stat.S_IXUSR)
        try:
            with pytest.raises(UnsupportedTargetError, match="temporary file"):
                hash_directory(tree, sidecar_name_for("ckpt"))
        finally:
            os.chmod(tree, stat.S_IRWXU)

    @posix_only
    def test_nested_symlinked_directory_rejected(self, tmp_path: Any) -> None:
        tree = self.make_tree(str(tmp_path / "ckpt"))
        outside = str(tmp_path / "outside")
        os.makedirs(outside)
        os.symlink(outside, os.path.join(tree, "shady-link"))
        with pytest.raises(UnsupportedTargetError, match="symlinked directory"):
            hash_directory(tree, sidecar_name_for("ckpt"))

    @posix_only
    def test_symlinked_file_inside_directory_rejected(self, tmp_path: Any) -> None:
        tree = self.make_tree(str(tmp_path / "ckpt"))
        outside_file = write_file(str(tmp_path / "outside.bin"), b"x")
        os.symlink(outside_file, os.path.join(tree, "link.bin"))
        with pytest.raises(UnsupportedTargetError, match="symlink"):
            hash_directory(tree, sidecar_name_for("ckpt"))

    def test_mutated_file_during_hashing_raises_race(self, tmp_path: Any, monkeypatch: Any) -> None:
        tree = self.make_tree(str(tmp_path / "ckpt"))
        victim = os.path.join(tree, "optimizer.pt")
        original = hashlib.file_digest

        def mutating_digest(handle: Any, algorithm: str) -> Any:
            os.utime(victim, ns=(1_500_000_000, 1_500_000_000))
            return original(handle, algorithm)

        monkeypatch.setattr(hashlib, "file_digest", mutating_digest)
        with pytest.raises(RaceDetectedError):
            hash_directory(tree, sidecar_name_for("ckpt"))
        monkeypatch.undo()
        result = hash_directory(tree, sidecar_name_for("ckpt"))
        assert result.digest


class TestNamingRules:
    def test_sidecar_name(self) -> None:
        assert sidecar_name_for("step_042000.safetensors") == (
            "step_042000.safetensors.modelmeta.yaml"
        )

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("step_042000.modelmeta.yaml.tmpabc", True),
            ("step_042000.modelmeta.yaml", False),
            ("other.modelmeta.yaml.tmp", True),
            ("model.yaml.tmpbackup", False),
            ("step.safetensors", False),
        ],
    )
    def test_temp_name_detection(self, name: str, expected: bool) -> None:
        assert is_temp_name(name) is expected
