# modelmeta — portable, hash-linked metadata for model checkpoints

**modelmeta puts dataset, training, code, timing, and integrity metadata beside every model checkpoint. Inspect it anywhere. Verify the exact bytes offline. No W&B. No MLflow. No tracking server.**

[![Watch the modelmeta demo: offline model checkpoint metadata and integrity verification](demo/modelmeta-demo.gif)](demo/modelmeta-demo.mp4)

[Watch the full 45-second demo](demo/modelmeta-demo.mp4) · [Explore the reproducible example](demo/README.md)

## Model checkpoint metadata that travels with the artifact

```text
checkpoints/
├── step_042000.safetensors
└── step_042000.safetensors.modelmeta.yaml
```

The sidecar records the checkpoint digest plus the training, dataset, Git, compute, and elapsed-time context supplied by the training process. It is portable YAML, readable without a tracking backend, and linked to the exact checkpoint bytes with SHA-256.

## Install

```bash
pip install modelmeta
```

Requires Python 3.11 or newer. The runtime package uses PyYAML and RFC 8785 canonical JSON; it does not require PyTorch or another ML framework.

## Verify before loading a checkpoint

```bash
modelmeta verify checkpoints/step_042000.safetensors
# checkpoint integrity verified; metadata remains self-asserted
```

Exit `0` means the supplied checkpoint bytes match the digest in the adjacent sidecar. A changed byte returns exit `12` (`digest_mismatch`). JSON output is stable for automation:

```bash
modelmeta verify --json checkpoints/step_042000.safetensors
```

`verify` hashes bytes; it does not deserialize or execute the checkpoint. A matching result does not authenticate the sidecar, prove who produced the model, or make an unknown pickle safe to load. Treat untrusted `.pkl`/`torch.load` inputs as executable content and use an independent trusted source or sandbox.

## Stamp metadata after saving

Create one `MetaWriter` when the run starts and reuse it after each successful checkpoint save:

```python
from modelmeta import MetaWriter

writer = MetaWriter(
    run_context={
        "run_id": "run_20260720_001",
        "git": {"repository": "https://github.com/me/project", "commit": "abc123", "dirty": False},
        "dataset": {"name": "curated-corpus", "version": "2026-07-18", "digest": "sha256:..."},
    }
)

# ... training loop ...

sidecar = writer.on_checkpoint_saved(
    "checkpoints/step_042000.safetensors",
    training_state={"global_step": 42000, "loss": 1.2384, "learning_rate": 2e-5},
    compute_state={"framework": "torch", "precision": "bf16", "accelerator_count": 8},
)
```

The writer atomically replaces the sidecar only after hashing and validation succeed. It automatically records `wall_hours` from the monotonic run timer and estimates `gpu_hours` as `wall_hours × accelerator_count` when no explicit value is supplied. Detection describes visible/available accelerators; it is not GPU-utilisation proof. Explicit caller values win. Call `writer.reset_timer()` when training actually begins.

For a one-off integration, use the framework-neutral adapter:

```python
from modelmeta.adapters import stamp_checkpoint

stamp_checkpoint("checkpoint.pt", training_state={"global_step": 100}, repo_path=".")
```

That adapter creates a fresh writer, so its elapsed time is approximately zero. Reuse `MetaWriter` when run duration matters.

## Inspect and compare checkpoints

```bash
modelmeta inspect checkpoints/step_042000.safetensors
modelmeta inspect --json checkpoints/step_042000.safetensors
modelmeta diff checkpoints/step_040000.safetensors checkpoints/step_042000.safetensors
```

`inspect` shows the checkpoint digest, training snapshot, dataset identity, Git state, compute information, signing state, and missing high-value fields. `diff` compares metadata claims grouped by training, provenance, compute, and artifact; it does not rank model quality.

## Files and directories

For a single file, the sidecar sits beside it:

```text
step_042000.safetensors
step_042000.safetensors.modelmeta.yaml
```

For a directory checkpoint, modelmeta hashes every regular file using a deterministic relative-path manifest and writes the reserved sidecar inside the directory:

```text
step_042000/
├── model-00001-of-00004.safetensors
├── optimizer.pt
└── step_042000.modelmeta.yaml
```

Copy or upload the checkpoint and sidecar together. `modelmeta` never follows a checkpoint path read from sidecar contents and never recovers missing metadata from a tracking service.

## Integrity is not authenticated provenance

If verification succeeds, the checkpoint bytes match the sidecar digest and the sidecar passes schema validation. The metadata remains self-asserted: modelmeta does not prove the dataset, code, loss, hardware, author, or model quality claims. Anyone who can replace both files can create a new matching pair. Signed attestations and durable run identity are outside v0.1.

## Exit codes

| Code | Status | Meaning |
|---:|---|---|
| 0 | `match` | Checkpoint and sidecar agree |
| 2 | — | CLI usage error |
| 10 | `missing_sidecar` | No metadata available |
| 11 | `invalid_schema` | Sidecar is structurally invalid |
| 12 | `digest_mismatch` | Checkpoint bytes differ from the sidecar |
| 13 | `unsupported_target` / `unsupported_schema` | v0.1 cannot safely proceed |
| 14 | `io_error` / `race_detected` | Verification could not complete |

## Development

```bash
uv sync --extra dev
git config core.hooksPath .githooks
uv run pytest -m "not slow"     # fast suite
uv run pytest -m slow            # larger-than-memory streaming acceptance test
```

The project is Python 3.11+ and uses `main ← dev ← feat/*`. See [CONTRIBUTING.md](CONTRIBUTING.md) for local gates.

## Documentation

- [Reproducible demo and video source](demo/README.md)
- [System architecture](docs/architecture.md)
- [v0.1 specification](docs/specs/modelmeta-spec-v0.1.md)
- [Contribution guide](CONTRIBUTING.md)

## License

MIT
