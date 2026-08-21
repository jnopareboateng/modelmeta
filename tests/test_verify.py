"""End-to-end verification tests covering every documented outcome."""

from __future__ import annotations

import os
from typing import Any

import pytest
from modelmeta.verify import (
    EXIT_DIGEST_MISMATCH,
    EXIT_INCOMPLETE,
    EXIT_INVALID_SCHEMA,
    EXIT_MATCH,
    EXIT_MISSING_SIDECAR,
    EXIT_UNSUPPORTED,
    SUCCESS_MESSAGE,
    sidecar_path_for,
    verify_checkpoint,
)
from modelmeta.writer import MetaWriter


@pytest.fixture
def checkpoint(tmp_path: Any) -> str:
    target = tmp_path / "step_001.safetensors"
    target.write_bytes(b"model-weights")
    MetaWriter().on_checkpoint_saved(str(target))
    return str(target)


class TestOutcomes:
    def test_match(self, checkpoint: str) -> None:
        outcome = verify_checkpoint(checkpoint)
        assert (outcome.status, outcome.exit_code) == ("match", EXIT_MATCH)
        assert outcome.detail["message"] == SUCCESS_MESSAGE
        assert "self-asserted" in SUCCESS_MESSAGE

    def test_missing_sidecar(self, tmp_path: Any) -> None:
        target = tmp_path / "lonely.pt"
        target.write_bytes(b"x")
        outcome = verify_checkpoint(str(target))
        assert (outcome.status, outcome.exit_code) == ("missing_sidecar", EXIT_MISSING_SIDECAR)

    def test_single_byte_flip_is_digest_mismatch(self, checkpoint: str) -> None:
        with open(checkpoint, "rb") as handle:
            payload = bytearray(handle.read())
        payload[0] ^= 0xFF
        with open(checkpoint, "wb") as handle:
            handle.write(payload)
        outcome = verify_checkpoint(checkpoint)
        assert (outcome.status, outcome.exit_code) == ("digest_mismatch", EXIT_DIGEST_MISMATCH)
        assert outcome.detail["recorded_sha256"] != outcome.detail["computed_sha256"]

    def test_truncated_checkpoint_is_mismatch(self, checkpoint: str) -> None:
        with open(checkpoint, "wb") as handle:
            handle.write(b"model-weight")
        outcome = verify_checkpoint(checkpoint)
        assert outcome.status == "digest_mismatch"

    def test_corrupt_sidecar_is_invalid_schema(self, checkpoint: str) -> None:
        with open(checkpoint + ".modelmeta.yaml", "w", encoding="utf-8") as handle:
            handle.write("{not: [valid")
        outcome = verify_checkpoint(checkpoint)
        assert (outcome.status, outcome.exit_code) == ("invalid_schema", EXIT_INVALID_SCHEMA)

    def test_uppercase_digest_in_sidecar_is_invalid_schema(self, checkpoint: str) -> None:
        import re

        path = checkpoint + ".modelmeta.yaml"
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
        content = re.sub(
            r"sha256: [0-9a-f]{64}",
            "sha256: " + "ABCDEF0123456789" * 4,
            content,
        )
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        outcome = verify_checkpoint(checkpoint)
        assert outcome.status == "invalid_schema"

    def test_foreign_schema_version_fails_closed(self, checkpoint: str) -> None:
        import re

        path = checkpoint + ".modelmeta.yaml"
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
        content = re.sub(r"schema_version: .+", "schema_version: '9.9'", content)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        outcome = verify_checkpoint(checkpoint)
        assert (outcome.status, outcome.exit_code) == ("unsupported_schema", EXIT_UNSUPPORTED)

    def test_lying_checkpoint_path_field_is_ignored(self, checkpoint: str) -> None:
        path = checkpoint + ".modelmeta.yaml"
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content.replace("step_001.safetensors", "../../etc/passwd"))
        outcome = verify_checkpoint(checkpoint)
        assert outcome.status == "match"


class TestDirectoryVerification:
    def test_directory_roundtrip_matches(self, tmp_path: Any) -> None:
        tree = tmp_path / "ckpt"
        (tree / "shards").mkdir(parents=True)
        (tree / "shards" / "m1.safetensors").write_bytes(b"a" * 1024)
        (tree / "shards" / "m2.safetensors").write_bytes(b"b" * 2048)
        (tree / "optimizer.pt").write_bytes(b"c" * 16)
        MetaWriter(run_context={"run_id": "r"}).on_checkpoint_saved(str(tree))
        outcome = verify_checkpoint(str(tree))
        assert outcome.status == "match"

    def test_directory_inner_mutation_is_mismatch(self, tmp_path: Any) -> None:
        tree = tmp_path / "ckpt"
        tree.mkdir()
        (tree / "m.safetensors").write_bytes(b"original")
        MetaWriter().on_checkpoint_saved(str(tree))
        (tree / "m.safetensors").write_bytes(b"mutated!")
        outcome = verify_checkpoint(str(tree))
        assert outcome.status == "digest_mismatch"

    def test_directory_orphan_temp_does_not_break_verification(self, tmp_path: Any) -> None:
        tree = tmp_path / "ckpt"
        tree.mkdir()
        (tree / "m.safetensors").write_bytes(b"data")
        MetaWriter().on_checkpoint_saved(str(tree))
        orphan = tree / f"{sidecar_path_for(str(tree)).rsplit(os.sep, 1)[-1]}.tmpjunk"
        orphan.write_bytes(b"junk")
        outcome = verify_checkpoint(str(tree))
        assert outcome.status == "match"


class TestLibraryContract:
    def test_missing_checkpoint_raises_file_not_found(self, tmp_path: Any) -> None:
        with pytest.raises(FileNotFoundError):
            verify_checkpoint(str(tmp_path / "nope.pt"))

    def test_outcome_never_raises_for_domain_failures(self, tmp_path: Any) -> None:
        target = tmp_path / "x.pt"
        target.write_bytes(b"x")
        for corrupt_content in ("", "- list\n", "a: &anc\n"):
            (tmp_path / "x.pt.modelmeta.yaml").write_text(corrupt_content, encoding="utf-8")
            outcome = verify_checkpoint(str(target))
            assert isinstance(outcome.exit_code, int)

    def test_race_maps_to_incomplete_not_mismatch(self, tmp_path: Any, monkeypatch: Any) -> None:
        from modelmeta.hashing import _identity

        target = tmp_path / "y.pt"
        target.write_bytes(b"data")
        MetaWriter().on_checkpoint_saved(str(target))

        real_identity = _identity
        calls = {"n": 0}

        def shifting_identity(path: str) -> Any:
            calls["n"] += 1
            identity = real_identity(path)
            if os.fspath(path) == os.fspath(target):
                return type(identity)(
                    size=identity.size + 1,
                    mtime_ns=identity.mtime_ns,
                    inode=identity.inode,
                    dev=identity.dev,
                )
            return identity

        monkeypatch.setattr("modelmeta.hashing._identity", shifting_identity)
        outcome = verify_checkpoint(str(target))
        assert (outcome.status, outcome.exit_code) == ("race_detected", EXIT_INCOMPLETE)
