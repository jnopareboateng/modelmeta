# modelmeta

**One-line problem:** Training saves `model.safetensors` but forgets *how long it took, what data, what code, and what loss* made it — so you need a separate W&B/MLflow setup just to look it up later. `modelmeta` puts that info right next to the checkpoint so you can see it and verify it anywhere, offline, with no tracking server.

```text
checkpoints/
├── step_042000.safetensors
└── step_042000.safetensors.modelmeta.yaml  <- travels with the checkpoint (SHA-256 linked)
```

No tracking backend. No network. Just two files you copy together. `modelmeta verify` checks the bytes match, `modelmeta inspect` shows the story behind the checkpoint.

> **Beginner in 30 seconds:**
> 1. Create one `MetaWriter` when training starts — it starts a timer automatically.
> 2. After each `torch.save()` call `writer.on_checkpoint_saved("ckpt.safetensors", training_state={...})` — it adds `wall_hours`/`gpu_hours` for you.
> 3. Run `modelmeta inspect ckpt.safetensors` — you see step, loss, dataset, commit, *and how long training has run so far* without W&B.

**What v0.1 guarantees:** integrity (these bytes are exactly what the sidecar described) and traceability (what step, loss, dataset, commit, and elapsed time produced them — as self-asserted by the training process).

**What v0.1 does not guarantee:** that the metadata is *true*. Anyone who controls both files can regenerate a matching pair. Unsigned metadata is not proof — signed attestations are planned for v0.2.

## Install

```bash
pip install modelmeta          # or: uv pip install modelmeta
```

Requires Python ≥ 3.11. Core has two runtime dependencies (PyYAML, rfc8785) and never imports PyTorch.

## Verify before you load

The pickle deserializer behind `torch.load` executes code, and malicious checkpoints are an active attack vector. Make hash verification a pre-load gate:

```bash
$ modelmeta verify checkpoints/step_042000.safetensors
checkpoint integrity verified; metadata remains self-asserted

$ echo $?   # 0
```

If a single byte of the checkpoint changed in transit:

```bash
$ modelmeta verify checkpoints/step_042000.safetensors
verify failed: digest_mismatch: checkpoint bytes do not match the digest recorded in the sidecar

$ echo $?   # 12
```

Scripted use:

```bash
modelmeta verify --json checkpoints/step_042000.safetensors
```

```json
{
  "cli_output_version": "1",
  "command": "verify",
  "exit_code": 0,
  "status": "match",
  "checkpoint_path": "checkpoints/step_042000.safetensors",
  "sidecar_path": "checkpoints/step_042000.safetensors.modelmeta.yaml",
  "detail": {"message": "...", "sha256": "...", "size_bytes": 1843200000, "hash_seconds": 3.1}
}
```

## Stamp after saving

In a raw PyTorch loop, create **one** writer when the run starts and reuse it — the timer starts automatically. Call it immediately after a successful save:

```python
from modelmeta import MetaWriter

# Timer starts here at run start — no manual clock needed
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
    training_state={"global_step": 42000, "loss": 1.2384, "learning_rate": 2e-05},
    compute_state={"framework": "torch", "precision": "bf16", "accelerator_count": 8},
    # you don't need to pass gpu_hours — it's auto-filled as wall_hours * accelerator_count
    # pass it only if you want to override: compute_state={"gpu_hours": 12.5}
)

# Inspect will now show:
#   wall_hours: 1.2345 (~74.1 min)
#   gpu_hours: 9.8760
# If you call it again 30 min later, the next checkpoint shows ~1.73 wall_hours automatically.
```

Need to reset the timer (e.g. you created the writer earlier)? Call `writer.reset_timer()` when training actually starts. For a quick one-off without reusing a writer:

```python
from modelmeta.adapters import stamp_checkpoint

stamp_checkpoint("ckpt.pt", training_state={"global_step": 100}, repo_path=".")
# Note: stamp_checkpoint creates a fresh writer, so elapsed time will be ~0.
# For real run duration, reuse one MetaWriter as above.
```

Writes are atomic: the sidecar appears complete or not at all; a crash mid-write leaves the previous sidecar untouched. Unavailable values are omitted, never invented.

## Inspect and diff (beginner-friendly)

```bash
modelmeta inspect checkpoints/step_042000.safetensors   # human-readable summary
# shows: step, loss, wall_hours/gpu_hours, dataset, commit — no JSON needed

modelmeta inspect --json checkpoints/step_042000.safetensors  # for scripts

modelmeta diff old.safetensors new.safetensors          # what changed between two checkpoints
```

Example `inspect` output:
```text
sidecar: step_042000.safetensors.modelmeta.yaml
checkpoint.sha256: 0123...abcdef
training.global_step: 42000
training.loss: 1.2384
wall_hours: 1.2345 (~74.1 min)
gpu_hours: 9.8760
dataset.name: curated-corpus
```

`diff` groups changes into artifact / training / provenance / compute buckets. It compares claims, not quality — a lower loss in the sidecar does not mean a better model.

## Keeping pairs together

The sidecar is useless without its checkpoint. Copy and upload them as one operation:

```bash
cp step_042000.safetensors step_042000.safetensors.modelmeta.yaml destination/
```

Directory checkpoints embed the sidecar inside the directory; copy the directory whole. If only the checkpoint is uploaded, the metadata is intentionally absent — modelmeta will not try to recover it from anywhere.

## Exit codes

| Code | Status | Meaning |
|---|---|---|
| 0 | `match` | Checkpoint and sidecar agree |
| 2 | — | CLI usage error |
| 10 | `missing_sidecar` | No metadata available |
| 11 | `invalid_schema` | Sidecar structurally untrustworthy |
| 12 | `digest_mismatch` | Checkpoint bytes differ from sidecar |
| 13 | `unsupported_target` / `unsupported_schema` | v0.1 cannot safely proceed |
| 14 | `io_error` / `race_detected` | Verification could not complete |

An unrecognized `schema_version` fails closed. Verification output never describes provenance as verified.

## Development

```bash
uv sync --extra dev
git config core.hooksPath .githooks
uv run pytest -m "not slow"     # fast suite
uv run pytest -m slow           # >memory streaming acceptance test (minutes)
```

Branching: `main` ← `dev` ← `feat/*`. Gates: ruff, mypy strict, pytest. See [CONTRIBUTING.md](CONTRIBUTING.md).

Design and threat model: [docs/architecture.md](docs/architecture.md) · [spec](docs/specs/modelmeta-spec-v0.1.md)

## License

MIT
