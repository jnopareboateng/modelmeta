"""Strict loading of sidecar YAML files."""

from __future__ import annotations

from typing import Any

import yaml

from modelmeta.errors import SchemaError, SidecarIOError

MAX_SIDECAR_BYTES = 4 * 1024 * 1024


class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate keys, anchors, aliases, and merge syntax."""

    def compose_node(self, parent: Any, index: Any) -> Any:
        if self.check_event(yaml.AliasEvent):
            raise yaml.constructor.ConstructorError(
                None, None, "aliases are not allowed in sidecars", self.get_mark()
            )
        return super().compose_node(parent, index)

    def compose_scalar_node(self, anchor: Any) -> Any:
        if anchor is not None:
            raise yaml.constructor.ConstructorError(
                None, None, "anchors are not allowed in sidecars", self.get_mark()
            )
        return super().compose_scalar_node(anchor)  # type: ignore[arg-type]

    def compose_sequence_node(self, anchor: Any) -> Any:
        if anchor is not None:
            raise yaml.constructor.ConstructorError(
                None, None, "anchors are not allowed in sidecars", self.get_mark()
            )
        return super().compose_sequence_node(anchor)  # type: ignore[arg-type]

    def compose_mapping_node(self, anchor: Any) -> Any:
        if anchor is not None:
            raise yaml.constructor.ConstructorError(
                None, None, "anchors are not allowed in sidecars", self.get_mark()
            )
        return super().compose_mapping_node(anchor)  # type: ignore[arg-type]

    def construct_mapping(self, node: Any, deep: bool = False) -> dict[Any, Any]:
        mapping: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as error:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"unhashable key: {key!r}",
                    key_node.start_mark,
                ) from error
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"duplicate key: {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def load_sidecar(path: str) -> dict[str, Any]:
    """Parse a sidecar file into a raw mapping.

    Structural problems (size cap, malformed YAML, duplicate keys, anchors,
    aliases, non-mapping documents) raise SchemaError. Schema-level checks
    happen later in validate_metadata so the two failure classes stay distinct.
    """
    try:
        with open(path, "rb") as handle:
            payload = handle.read()
    except OSError as error:
        raise SidecarIOError(f"sidecar could not be read: {path}") from error
    if len(payload) > MAX_SIDECAR_BYTES:
        raise SchemaError(
            f"sidecar exceeds the maximum supported size of {MAX_SIDECAR_BYTES} bytes"
        )
    try:
        document = yaml.load(payload, Loader=_StrictLoader)
    except yaml.YAMLError as error:
        raise SchemaError(f"sidecar is not valid YAML: {error}") from error
    if not isinstance(document, dict):
        raise SchemaError("sidecar must contain a mapping at the top level")
    return document
