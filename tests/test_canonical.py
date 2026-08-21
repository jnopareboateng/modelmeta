"""Tests for RFC 8785 canonicalization, null normalization, and timestamp rules."""

from __future__ import annotations

from typing import Any

import pytest
from modelmeta.canonical import canonical_bytes, is_valid_timestamp, normalize, utc_now
from rfc8785 import dumps as raw_jcs_dumps

RFC8785_SORTING_VECTOR = (
    {
        "\u20ac": "Euro Sign",
        "\r": "Carriage Return",
        "\ufb33": "Hebrew Letter Dalet With Dagesh",
        "1": "One",
        "\U0001f600": "Emoji: Grinning Face",
        "\u0080": "Control",
        "\u00f6": "Latin Small Letter O With Diaeresis",
    },
    '{"\\r":"Carriage Return","1":"One","\u0080":"Control",'
    '"ö":"Latin Small Letter O With Diaeresis","€":"Euro Sign",'
    '"😀":"Emoji: Grinning Face","\ufb33":"Hebrew Letter Dalet With Dagesh"}',
)

RFC8785_NUMBER_VECTOR = (
    {"numbers": [333333333.33333329, 1e30, 4.50, 2e-3, 0.000000000000000000000000001]},
    '{"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27]}',
)

RFC8785_NULL_VECTOR = (
    {"true": True, "false": False, "null": None, "int": 1, "float": 1.5},
    '{"false":false,"float":1.5,"int":1,"null":null,"true":true}',
)


class TestRfc8785Vectors:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [RFC8785_SORTING_VECTOR, RFC8785_NUMBER_VECTOR],
        ids=["sorting", "numbers"],
    )
    def test_official_vectors(self, value: Any, expected: str) -> None:
        assert canonical_bytes(value).decode("utf-8") == expected

    def test_list_literals_preserve_null(self) -> None:
        assert (
            canonical_bytes({"literals": [None, True, False]}) == b'{"literals":[null,true,false]}'
        )

    def test_official_null_vector_via_raw_jcs(self) -> None:
        value, expected = RFC8785_NULL_VECTOR
        assert raw_jcs_dumps(value).decode("utf-8") == expected

    def test_string_escaping_rules(self) -> None:
        assert canonical_bytes({"s": 'a"b\\c\nd\x01'}) == b'{"s":"a\\"b\\\\c\\nd\\u0001"}'


class TestNumberSerialization:
    def test_learning_rate_style_floats_are_jcs_stable(self) -> None:
        assert canonical_bytes({"lr": 2e-05}) == b'{"lr":0.00002}'

    def test_trailing_zero_exponent_is_normalized(self) -> None:
        assert canonical_bytes({"wd": 1e-08}) == b'{"wd":1e-8}'

    def test_negative_zero_becomes_zero(self) -> None:
        assert canonical_bytes({"x": -0.0}) == b'{"x":0}'

    def test_nan_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            canonical_bytes({"loss": float("nan")})

    def test_infinity_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            canonical_bytes({"loss": float("inf")})


class TestNullNormalization:
    def test_explicit_nulls_are_removed_from_mappings(self) -> None:
        value = {"a": 1, "b": None, "c": {"d": None, "e": 2}}
        assert normalize(value) == {"a": 1, "c": {"e": 2}}

    def test_list_items_are_preserved(self) -> None:
        value = {"metrics": [1, None, 2]}
        assert normalize(value) == {"metrics": [1, None, 2]}

    def test_normalization_feeds_canonical_equality(self) -> None:
        assert canonical_bytes({"a": 1, "b": None}) == canonical_bytes({"a": 1})

    def test_input_is_not_mutated(self) -> None:
        value: dict[str, Any] = {"a": 1, "b": None}
        normalize(value)
        assert value == {"a": 1, "b": None}


class TestTimestamps:
    def test_utc_now_matches_required_shape(self) -> None:
        assert is_valid_timestamp(utc_now())

    @pytest.mark.parametrize(
        "value",
        [
            "2026-07-20T00:00:00Z",
            "2024-02-29T23:59:59Z",
        ],
    )
    def test_valid_timestamps(self, value: str) -> None:
        assert is_valid_timestamp(value)

    @pytest.mark.parametrize(
        "value",
        [
            "2026-07-20T00:00:00+00:00",
            "2026-07-20T00:00:00.123Z",
            "2026-13-01T00:00:00Z",
            "2026-07-20 00:00:00Z",
            "2026-07-20T00:00:00z",
            "",
            20260720,
            None,
        ],
    )
    def test_invalid_timestamps(self, value: Any) -> None:
        assert not is_valid_timestamp(value)
