"""CLI contract tests: envelope stability, exit codes, output separation."""

from __future__ import annotations

import json
from typing import Any

import pytest
from modelmeta import __version__
from modelmeta.cli import CLI_OUTPUT_VERSION, main

ENVELOPE_KEYS = [
    "cli_output_version",
    "command",
    "exit_code",
    "status",
    "checkpoint_path",
    "sidecar_path",
    "detail",
]


@pytest.fixture
def stamped_checkpoint(tmp_path: Any) -> str:
    from modelmeta.writer import MetaWriter

    target = tmp_path / "step_010.safetensors"
    target.write_bytes(b"weights-010")
    MetaWriter(
        run_context={"run_id": "run_1", "git": {"commit": "abc", "dirty": False}}
    ).on_checkpoint_saved(
        str(target),
        training_state={"global_step": 10, "loss": 2.0},
        compute_state={"framework": "torch"},
    )
    return str(target)


def run_json(capsys: Any, *argv: str) -> tuple[dict[str, Any], int]:
    code = main(list(argv))
    out = capsys.readouterr().out
    envelope: dict[str, Any] = json.loads(out)
    return envelope, code


class TestVerifyCommand:
    def test_json_envelope_shape_is_stable(self, capsys: Any, stamped_checkpoint: str) -> None:
        envelope, code = run_json(capsys, "verify", "--json", stamped_checkpoint)
        assert list(envelope) == ENVELOPE_KEYS
        assert envelope["cli_output_version"] == CLI_OUTPUT_VERSION == "1"
        assert envelope["command"] == "verify"
        assert envelope["exit_code"] == code == 0
        assert envelope["status"] == "match"
        assert envelope["detail"]["message"].endswith("metadata remains self-asserted")

    def test_human_output_mentions_self_asserted(
        self, capsys: Any, stamped_checkpoint: str
    ) -> None:
        code = main(["verify", stamped_checkpoint])
        captured = capsys.readouterr()
        assert code == 0
        assert "self-asserted" in captured.out
        assert "{" not in captured.out

    def test_mismatch_exit_code(self, capsys: Any, stamped_checkpoint: str) -> None:
        with open(stamped_checkpoint, "ab") as handle:
            handle.write(b"corruption")
        envelope, code = run_json(capsys, "verify", "--json", stamped_checkpoint)
        assert (envelope["status"], envelope["exit_code"], code) == ("digest_mismatch", 12, 12)

    def test_missing_sidecar_exit_code(self, capsys: Any, tmp_path: Any) -> None:
        target = tmp_path / "no-sidecar.pt"
        target.write_bytes(b"x")
        envelope, code = run_json(capsys, "verify", "--json", str(target))
        assert envelope["status"] == "missing_sidecar"
        assert envelope["exit_code"] == code == 10

    def test_nonexistent_checkpoint_is_usage_error(self, capsys: Any, tmp_path: Any) -> None:
        code = main(["verify", str(tmp_path / "ghost.pt")])
        captured = capsys.readouterr()
        assert code == 2
        assert "does not exist" in captured.err
        assert captured.out == ""

    def test_bad_subcommand_is_usage_error(self, capsys: Any) -> None:
        with pytest.raises(SystemExit) as exit_info:
            main(["frobnicate"])
        assert exit_info.value.code == 2


class TestInspectCommand:
    def test_inspect_json(self, capsys: Any, stamped_checkpoint: str) -> None:
        envelope, code = run_json(capsys, "inspect", "--json", stamped_checkpoint)
        assert envelope["status"] == "ok"
        assert code == 0
        assert envelope["detail"]["metadata"]["provenance"]["run_id"] == "run_1"
        missing = envelope["detail"]["missing_high_value_fields"]
        assert "dataset_digest" in missing

    def test_inspect_human_lists_missing_fields(self, capsys: Any, stamped_checkpoint: str) -> None:
        code = main(["inspect", stamped_checkpoint])
        captured = capsys.readouterr()
        assert code == 0
        assert "missing high-value fields" in captured.out
        assert "dataset_digest" in captured.out


class TestDiffCommand:
    def make_second(self, tmp_path: Any) -> str:
        from modelmeta.writer import MetaWriter

        target = tmp_path / "step_020.safetensors"
        target.write_bytes(b"weights-020-longer")
        MetaWriter(
            run_context={"run_id": "run_2", "git": {"commit": "def", "dirty": True}}
        ).on_checkpoint_saved(
            str(target),
            training_state={"global_step": 20, "loss": 1.5},
            compute_state={"framework": "torch", "precision": "bf16"},
        )
        return str(target)

    def test_groups_are_semantic(self, capsys: Any, tmp_path: Any, stamped_checkpoint: str) -> None:
        second = self.make_second(tmp_path)
        envelope, code = run_json(capsys, "diff", "--json", stamped_checkpoint, second)
        detail = envelope["detail"]
        assert set(detail) <= {"artifact", "training", "provenance", "compute", "other"}
        assert "training.global_step" in detail["training"]["changed"]
        assert "provenance.run_id" in detail["provenance"]["changed"]
        assert "compute.precision" in detail["compute"]["added"]
        assert "checkpoint.sha256" in detail["artifact"]["changed"]
        assert code == 0
        assert envelope["status"] == "differences_found"

    def test_identical_sidecars_report_identical(
        self, capsys: Any, tmp_path: Any, stamped_checkpoint: str
    ) -> None:
        envelope, _ = run_json(capsys, "diff", "--json", stamped_checkpoint, stamped_checkpoint)
        assert envelope["status"] == "identical"
        assert envelope["detail"] == {}

    def test_human_output_separated(
        self, capsys: Any, tmp_path: Any, stamped_checkpoint: str
    ) -> None:
        second = self.make_second(tmp_path)
        code = main(["diff", stamped_checkpoint, second])
        captured = capsys.readouterr()
        assert code == 0
        assert "training:" in captured.out
        assert '"cli_output_version"' not in captured.out


class TestVersionCommand:
    def test_version_plain(self, capsys: Any) -> None:
        code = main(["version"])
        assert capsys.readouterr().out.strip() == __version__
        assert code == 0

    def test_version_json(self, capsys: Any) -> None:
        envelope, code = run_json(capsys, "version", "--json")
        assert envelope["detail"]["version"] == __version__
        assert code == 0
