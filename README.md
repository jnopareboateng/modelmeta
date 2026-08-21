# modelmeta

A small offline tool that creates and verifies portable, hash-linked metadata for model checkpoint artifacts.

`modelmeta` writes a machine-readable sidecar next to a model checkpoint and binds it to the checkpoint bytes with a SHA-256 digest. Sidecars travel with checkpoints and can be inspected and verified offline — no MLflow, W&B, or tracking backend required.

v0.1 provides **integrity and traceability**, not authenticated provenance: metadata is self-asserted unless separately signed.

- Spec: [`docs/specs/modelmeta-spec-v0.1.md`](docs/specs/modelmeta-spec-v0.1.md)
- Status: pre-release, under active development
- License: MIT
