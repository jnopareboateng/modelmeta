"""Tests for atomic sidecar writing."""

from __future__ import annotations

import os
from typing import Any

import pytest
import yaml
from modelmeta.errors import UnsupportedTargetError
from modelmeta.hashing import hash_file, sidecar_name_for
from modelmeta.writer import MetaWriter


@pytest.fixture
def checkpoint(tmp_path: Any) -> str:
    target = tmp_path / "step_042000.safetensors"
    target.write_bytes(b"checkpoint-bytes")
    return str(target)


class TestHappyPath:
    def test_sidecar_is_written_next_to_checkpoint(self, checkpoint: str) -> None:
        sidecar = MetaWriter().on_checkpoint_saved(checkpoint)
        assert sidecar == checkpoint + ".modelmeta.yaml"
        assert os.path.exists(sidecar)

    def test_metadata_content(self, checkpoint: str) -> None:
        MetaWriter().on_checkpoint_saved(checkpoint)
        with open(checkpoint + ".modelmeta.yaml", encoding="utf-8") as handle:
            metadata = yaml.safe_load(handle)
        assert metadata["schema_version"] == "0.1"
        assert metadata["checkpoint"]["kind"] == "file"
        assert metadata["checkpoint"]["path"] == "step_042000.safetensors"
        assert metadata["checkpoint"]["size_bytes"] == 16
        assert metadata["checkpoint"]["sha256"] == hash_file(checkpoint).digest
        assert metadata["integrity"] == {
            "metadata_encoding": "yaml+canonical-json-v1",
            "signed": False,
        }

    def test_created_at_shape(self, checkpoint: str) -> None:
        MetaWriter().on_checkpoint_saved(checkpoint)
        with open(checkpoint + ".modelmeta.yaml", encoding="utf-8") as handle:
            metadata = yaml.safe_load(handle)
        assert isinstance(metadata["created_at"], str)
        assert metadata["created_at"].endswith("Z")
        assert "." not in metadata["created_at"]

    def test_caller_sections_are_included(self, checkpoint: str) -> None:
        writer = MetaWriter(
            run_context={"run_id": "run_001", "git": {"commit": "abc123", "dirty": False}}
        )
        writer.on_checkpoint_saved(
            checkpoint,
            training_state={"global_step": 42000, "loss": 1.25},
            compute_state={"framework": "torch", "precision": "bf16"},
            optimizer_state={"included": True},
            lineage={"parent_checkpoint": None},
        )
        with open(checkpoint + ".modelmeta.yaml", encoding="utf-8") as handle:
            metadata = yaml.safe_load(handle)
        assert metadata["provenance"]["run_id"] == "run_001"
        assert metadata["training"]["global_step"] == 42000
        assert metadata["compute"]["framework"] == "torch"
        assert metadata["optimizer_state"]["included"] is True

    def test_hashing_cost_is_reported(self, checkpoint: str) -> None:
        writer = MetaWriter()
        writer.on_checkpoint_saved(checkpoint)
        assert writer.last_hash_seconds is not None
        assert writer.last_hash_seconds >= 0.0


class TestCallerSafety:
    def test_caller_dicts_are_not_mutated(self, checkpoint: str) -> None:
        training = {"global_step": 1, "loss": 0.5}
        compute = {"framework": "torch"}
        MetaWriter().on_checkpoint_saved(checkpoint, training_state=training, compute_state=compute)
        assert training == {"global_step": 1, "loss": 0.5}
        assert compute == {"framework": "torch"}

    def test_secret_looking_keys_are_refused(self, checkpoint: str) -> None:
        with pytest.raises(ValueError, match="api_key"):
            MetaWriter(run_context={"dataset": {"api_key": "hunter2"}}).on_checkpoint_saved(
                checkpoint
            )

    def test_secret_keys_in_training_state_are_refused(self, checkpoint: str) -> None:
        with pytest.raises(ValueError, match="training_state"):
            MetaWriter().on_checkpoint_saved(checkpoint, training_state={"hf_token": "ghp_x"})

    def test_missing_checkpoint_raises(self, tmp_path: Any) -> None:
        with pytest.raises(FileNotFoundError):
            MetaWriter().on_checkpoint_saved(str(tmp_path / "missing.pt"))

    def test_temp_named_target_is_rejected(self, tmp_path: Any) -> None:
        target = tmp_path / "step.modelmeta.yaml.tmpabc"
        target.write_bytes(b"partial")
        with pytest.raises(UnsupportedTargetError, match="temporary"):
            MetaWriter().on_checkpoint_saved(str(target))


class TestAtomicity:
    def test_idempotent_replace_does_not_merge(self, checkpoint: str) -> None:
        writer = MetaWriter()
        writer.on_checkpoint_saved(checkpoint, training_state={"global_step": 1})
        writer.on_checkpoint_saved(checkpoint, training_state={"global_step": 2})
        with open(checkpoint + ".modelmeta.yaml", encoding="utf-8") as handle:
            metadata = yaml.safe_load(handle)
        assert metadata["training"]["global_step"] == 2

    def test_failed_replace_leaves_previous_sidecar_intact(
        self, checkpoint: str, monkeypatch: Any
    ) -> None:
        sidecar = checkpoint + ".modelmeta.yaml"
        MetaWriter().on_checkpoint_saved(checkpoint, training_state={"global_step": 1})
        with open(sidecar, "rb") as handle:
            before = handle.read()

        def failing_replace(source: Any, destination: Any) -> None:
            raise OSError("simulated crash")

        monkeypatch.setattr(os, "replace", failing_replace)
        with pytest.raises(OSError, match="simulated crash"):
            MetaWriter().on_checkpoint_saved(checkpoint, training_state={"global_step": 2})
        monkeypatch.undo()
        with open(sidecar, "rb") as handle:
            assert handle.read() == before

    def test_failed_write_leaves_no_temp_files(self, checkpoint: str, monkeypatch: Any) -> None:
        def failing_fsync(fd: int) -> None:
            raise OSError("simulated fsync failure")

        monkeypatch.setattr(os, "fsync", failing_fsync)
        with pytest.raises(OSError, match="fsync"):
            MetaWriter().on_checkpoint_saved(checkpoint)
        monkeypatch.undo()
        parent = os.path.dirname(checkpoint)
        assert not [name for name in os.listdir(parent) if ".tmp" in name]

    def test_fsync_precedes_replace(self, checkpoint: str, monkeypatch: Any) -> None:
        events: list[str] = []
        real_fsync = os.fsync
        real_replace = os.replace

        def tracking_fsync(fd: int) -> None:
            events.append("fsync")
            real_fsync(fd)

        def tracking_replace(source: Any, destination: Any) -> None:
            events.append("replace")
            real_replace(source, destination)

        monkeypatch.setattr(os, "fsync", tracking_fsync)
        monkeypatch.setattr(os, "replace", tracking_replace)
        MetaWriter().on_checkpoint_saved(checkpoint)
        assert events.index("fsync") < events.index("replace")

    def test_reserved_sidecar_occupied_by_directory_is_refused(self, tmp_path: Any) -> None:
        target = tmp_path / "model.safetensors"
        target.write_bytes(b"x")
        (tmp_path / "model.safetensors.modelmeta.yaml").mkdir()
        with pytest.raises(UnsupportedTargetError, match="non-regular"):
            MetaWriter().on_checkpoint_saved(str(target))


class TestDirectoryCheckpoints:
    def make_tree(self, root: str) -> str:
        os.makedirs(root, exist_ok=True)
        with open(os.path.join(root, "model.safetensors"), "wb") as handle:
            handle.write(b"weights")
        return root

    def test_sidecar_lives_inside_directory(self, tmp_path: Any) -> None:
        tree = self.make_tree(str(tmp_path / "ckpt"))
        sidecar = MetaWriter(run_context={"run_id": "r1"}).on_checkpoint_saved(tree)
        expected = os.path.join(tree, sidecar_name_for("ckpt"))
        assert sidecar == expected
        assert os.path.exists(sidecar)

    def test_directory_metadata_kind_and_size(self, tmp_path: Any) -> None:
        tree = self.make_tree(str(tmp_path / "ckpt"))
        MetaWriter().on_checkpoint_saved(tree)
        with open(os.path.join(tree, sidecar_name_for("ckpt")), encoding="utf-8") as handle:
            metadata = yaml.safe_load(handle)
        assert metadata["checkpoint"]["kind"] == "directory"
        assert metadata["checkpoint"]["path"] == "ckpt"
        assert metadata["checkpoint"]["size_bytes"] == 7

    def test_stale_orphans_cleaned_before_hashing(self, tmp_path: Any) -> None:
        tree = self.make_tree(str(tmp_path / "ckpt"))
        orphan = os.path.join(tree, f"{sidecar_name_for('ckpt')}.tmpold")
        with open(orphan, "wb") as handle:
            handle.write(b"stale")
        MetaWriter().on_checkpoint_saved(tree)
        assert not os.path.exists(orphan)
