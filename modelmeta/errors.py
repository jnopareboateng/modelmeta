"""Typed errors with stable CLI exit codes."""

from __future__ import annotations


class ModelMetaError(Exception):
    """Base class for all modelmeta domain errors."""

    exit_code = 1


class SchemaError(ModelMetaError):
    """Sidecar is structurally untrustworthy: invalid schema, duplicate keys, or parse failure."""

    exit_code = 11


class UnsupportedSchemaError(ModelMetaError):
    """Sidecar declares a schema_version this release does not support; fail closed."""

    exit_code = 13


class UnsupportedTargetError(ModelMetaError):
    """Target cannot be hashed safely in this release."""

    exit_code = 13


class RaceDetectedError(ModelMetaError):
    """Target changed while it was being hashed."""

    exit_code = 14


class SidecarIOError(ModelMetaError):
    """Verification could not complete due to I/O or permission failure."""

    exit_code = 14
