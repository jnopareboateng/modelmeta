"""Tests for strict sidecar loading."""

from __future__ import annotations

from typing import Any

import pytest
from modelmeta.errors import SchemaError
from modelmeta.reader import load_sidecar


def write_sidecar(tmp_path: Any, content: str) -> str:
    path = tmp_path / "sidecar.modelmeta.yaml"
    path.write_text(content, encoding="utf-8")
    return str(path)


VALID_SIDECAR = """\
schema_version: "0.1"
created_at: "2026-07-20T00:00:00Z"
checkpoint:
  kind: file
  path: model.safetensors
  size_bytes: 4
  sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
"""


class TestStrictLoading:
    def test_valid_sidecar_loads(self, tmp_path: Any) -> None:
        document = load_sidecar(write_sidecar(tmp_path, VALID_SIDECAR))
        assert document["checkpoint"]["kind"] == "file"

    def test_duplicate_keys_rejected(self, tmp_path: Any) -> None:
        content = VALID_SIDECAR + "training:\n  loss: 1.0\ntraining:\n  loss: 2.0\n"
        with pytest.raises(SchemaError, match="valid YAML"):
            load_sidecar(write_sidecar(tmp_path, content))

    def test_duplicate_nested_keys_rejected(self, tmp_path: Any) -> None:
        content = (
            'schema_version: "0.1"\n'
            'created_at: "2026-07-20T00:00:00Z"\n'
            "checkpoint:\n"
            "  kind: file\n"
            "  kind: directory\n"
            "  path: m.pt\n"
            "  size_bytes: 1\n"
            "  sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\n"
        )
        with pytest.raises(SchemaError):
            load_sidecar(write_sidecar(tmp_path, content))

    def test_alias_to_anchor_rejected(self, tmp_path: Any) -> None:
        content = (
            'schema_version: "0.1"\n'
            'created_at: "2026-07-20T00:00:00Z"\n'
            "base: &base\n"
            "  loss: 1.0\n"
            "checkpoint: *base\n"
        )
        with pytest.raises(SchemaError, match="not allowed"):
            load_sidecar(write_sidecar(tmp_path, content))

    def test_scalar_anchor_rejected(self, tmp_path: Any) -> None:
        content = VALID_SIDECAR + "note: &anchor hello\n"
        with pytest.raises(SchemaError, match="anchors are not allowed"):
            load_sidecar(write_sidecar(tmp_path, content))

    def test_malformed_yaml_rejected(self, tmp_path: Any) -> None:
        with pytest.raises(SchemaError, match="valid YAML"):
            load_sidecar(write_sidecar(tmp_path, "{a: [unclosed"))

    def test_empty_document_rejected(self, tmp_path: Any) -> None:
        with pytest.raises(SchemaError, match="mapping"):
            load_sidecar(write_sidecar(tmp_path, ""))

    def test_non_mapping_document_rejected(self, tmp_path: Any) -> None:
        with pytest.raises(SchemaError, match="mapping"):
            load_sidecar(write_sidecar(tmp_path, "- a\n- b\n"))

    def test_size_cap_enforced(self, tmp_path: Any, monkeypatch: Any) -> None:
        from modelmeta import reader

        monkeypatch.setattr(reader, "MAX_SIDECAR_BYTES", 16)
        with pytest.raises(SchemaError, match="maximum supported size"):
            reader.load_sidecar(write_sidecar(tmp_path, VALID_SIDECAR))
