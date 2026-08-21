"""Tests for schema validation rules."""

from __future__ import annotations

from typing import Any

import pytest
from modelmeta.errors import SchemaError, UnsupportedSchemaError
from modelmeta.schema import assert_no_secret_keys, validate_metadata

from tests.conftest import file_metadata


class TestValidMetadata:
    def test_minimal_file_metadata_passes(self, valid_file_metadata: dict[str, Any]) -> None:
        validated = validate_metadata(valid_file_metadata)
        assert validated["checkpoint"]["sha256"].startswith("0123456789abcdef")

    def test_full_example_passes(self) -> None:
        metadata = file_metadata(
            provenance={
                "run_id": "run_20260720_001",
                "git": {
                    "repository": "https://github.com/example/project",
                    "commit": "abc123",
                    "dirty": False,
                },
                "dataset": {
                    "name": "curated-corpus",
                    "version": "2026-07-18",
                    "digest": "sha256:abc",
                },
            },
            training={"global_step": 42000, "loss": 1.2384, "learning_rate": 2e-05},
            compute={
                "framework": "torch",
                "framework_version": "2.7.0",
                "accelerator_type": "NVIDIA A100",
                "accelerator_count": 8,
                "precision": "bf16",
                "gpu_hours": None,
            },
            optimizer_state={"included": True, "name": "AdamW"},
            lineage={"parent_checkpoint": None},
            integrity={"metadata_encoding": "yaml+canonical-json-v1", "signed": False},
        )
        assert validate_metadata(metadata)["training"]["global_step"] == 42000

    def test_returns_independent_copy(self, valid_file_metadata: dict[str, Any]) -> None:
        validated = validate_metadata(valid_file_metadata)
        valid_file_metadata["checkpoint"]["size_bytes"] = 999
        assert validated["checkpoint"]["size_bytes"] == 16

    def test_unknown_sections_are_preserved(self, valid_file_metadata: dict[str, Any]) -> None:
        metadata = file_metadata(custom_section={"nested": [1, 2, {"x": "y"}]})
        validated = validate_metadata(metadata)
        assert validated["custom_section"] == {"nested": [1, 2, {"x": "y"}]}

    def test_explicit_null_on_optional_known_field_is_accepted(self) -> None:
        metadata = file_metadata(compute={"gpu_hours": None})
        assert validate_metadata(metadata)["compute"]["gpu_hours"] is None


class TestRequiredFields:
    @pytest.mark.parametrize(
        ("mutation", "message_part"),
        [
            ({"schema_version": None}, "schema_version"),
            ({"created_at": None}, "created_at"),
            ({"checkpoint": None}, "checkpoint"),
        ],
    )
    def test_missing_required_top_level_fields(
        self, valid_file_metadata: dict[str, Any], mutation: dict[str, Any], message_part: str
    ) -> None:
        metadata = {**valid_file_metadata, **mutation}
        with pytest.raises(SchemaError, match=message_part):
            validate_metadata(metadata)

    def test_missing_checkpoint_sha256(self, valid_file_metadata: dict[str, Any]) -> None:
        del valid_file_metadata["checkpoint"]["sha256"]
        with pytest.raises(SchemaError, match=r"checkpoint\.sha256"):
            validate_metadata(valid_file_metadata)


class TestFieldValueRules:
    def test_uppercase_digest_rejected(self, valid_file_metadata: dict[str, Any]) -> None:
        valid_file_metadata["checkpoint"]["sha256"] = "ABCDEF" + "0" * 58
        with pytest.raises(SchemaError, match="lowercase 64-character"):
            validate_metadata(valid_file_metadata)

    def test_short_digest_rejected(self, valid_file_metadata: dict[str, Any]) -> None:
        valid_file_metadata["checkpoint"]["sha256"] = "abcd"
        with pytest.raises(SchemaError, match="lowercase 64-character"):
            validate_metadata(valid_file_metadata)

    def test_unknown_kind_rejected(self, valid_file_metadata: dict[str, Any]) -> None:
        valid_file_metadata["checkpoint"]["kind"] = "tarball"
        with pytest.raises(SchemaError, match=r"checkpoint\.kind"):
            validate_metadata(valid_file_metadata)

    def test_negative_size_rejected(self, valid_file_metadata: dict[str, Any]) -> None:
        valid_file_metadata["checkpoint"]["size_bytes"] = -1
        with pytest.raises(SchemaError, match="size_bytes"):
            validate_metadata(valid_file_metadata)

    def test_bool_where_int_expected_rejected(self, valid_file_metadata: dict[str, Any]) -> None:
        valid_file_metadata["checkpoint"]["size_bytes"] = True
        with pytest.raises(SchemaError, match="size_bytes"):
            validate_metadata(valid_file_metadata)

    @pytest.mark.parametrize(
        "created_at",
        [
            "2026-07-20T00:00:00+00:00",
            "2026-07-20T00:00:00.123Z",
            "not-a-timestamp",
        ],
    )
    def test_bad_timestamps_rejected(
        self, valid_file_metadata: dict[str, Any], created_at: str
    ) -> None:
        valid_file_metadata["created_at"] = created_at
        with pytest.raises(SchemaError, match="created_at"):
            validate_metadata(valid_file_metadata)

    def test_foreign_schema_version_fails_closed(self, valid_file_metadata: dict[str, Any]) -> None:
        valid_file_metadata["schema_version"] = "0.2"
        with pytest.raises(UnsupportedSchemaError):
            validate_metadata(valid_file_metadata)

    def test_non_string_schema_version_rejected(self, valid_file_metadata: dict[str, Any]) -> None:
        valid_file_metadata["schema_version"] = 0.1
        with pytest.raises((SchemaError, UnsupportedSchemaError)):
            validate_metadata(valid_file_metadata)

    def test_training_step_must_be_int(self, valid_file_metadata: dict[str, Any]) -> None:
        valid_file_metadata["training"] = {"global_step": 42.5}
        with pytest.raises(SchemaError, match=r"training\.global_step"):
            validate_metadata(valid_file_metadata)

    def test_git_dirty_must_be_bool(self, valid_file_metadata: dict[str, Any]) -> None:
        valid_file_metadata["provenance"] = {"git": {"dirty": "yes"}}
        with pytest.raises(SchemaError, match="dirty"):
            validate_metadata(valid_file_metadata)

    def test_top_level_must_be_mapping(self) -> None:
        with pytest.raises(SchemaError, match="mapping"):
            validate_metadata([1, 2, 3])  # type: ignore[arg-type]


class TestJsonRepresentability:
    def test_nan_anywhere_is_rejected(self, valid_file_metadata: dict[str, Any]) -> None:
        valid_file_metadata["mystery_section"] = {"value": float("nan")}
        with pytest.raises(SchemaError, match="NaN"):
            validate_metadata(valid_file_metadata)

    def test_non_string_keys_are_rejected(self, valid_file_metadata: dict[str, Any]) -> None:
        valid_file_metadata["mystery_section"] = {1: "one"}
        with pytest.raises(SchemaError, match="string"):
            validate_metadata(valid_file_metadata)

    def test_arbitrary_objects_are_rejected(self, valid_file_metadata: dict[str, Any]) -> None:
        valid_file_metadata["mystery_section"] = {object()}
        with pytest.raises(SchemaError):
            validate_metadata(valid_file_metadata)


class TestSecretKeyGuard:
    def test_matching_key_is_refused(self) -> None:
        with pytest.raises(ValueError, match="api_key"):
            assert_no_secret_keys({"dataset": {"api_key": "hunter2"}})

    @pytest.mark.parametrize("key", ["token", "SECRET", "db_password", "api-key", "apiKey"])
    def test_pattern_variants(self, key: str) -> None:
        with pytest.raises(ValueError):
            assert_no_secret_keys({key: "x"})

    def test_nested_list_entries_are_scanned(self) -> None:
        with pytest.raises(ValueError):
            assert_no_secret_keys({"sources": [{"secret_path": "/x"}]})

    def test_benign_keys_pass(self) -> None:
        assert_no_secret_keys({"dataset": {"name": "corpus"}, "git": {"commit": "abc"}})
