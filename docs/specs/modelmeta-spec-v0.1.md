# modelmeta — realistic specification v0.1

**Status:** Amended after adversarial review; implementation-ready pending design approval
**Audience:** Engineers building or operating training pipelines
**Primary decision:** Ship a portable, hash-linked metadata sidecar first. Do not describe v0.1 as independently verified provenance.

## 1. Executive summary

`modelmeta` writes machine-readable metadata next to a model checkpoint and binds the metadata to the checkpoint through a cryptographic digest.

The first release provides:

- portable checkpoint metadata that does not require MLflow, W&B, or another tracking backend;
- byte-integrity verification through SHA-256;
- human-readable inspection and metadata comparison;
- framework-neutral integration through a small dictionary-based API;
- safe sidecar writes that survive normal process crashes.

The first release does **not** prove that the metadata is truthful. A user who controls the checkpoint and sidecar can edit both. It provides traceability and integrity, not authenticated provenance. Signed attestations are a separate release.

## 2. Problem

Training metadata is usually stored in an experiment tracker while checkpoint bytes are stored elsewhere. When a checkpoint is copied to another machine, uploaded to a model registry, or handed to another team, the association between the bytes and the training run is easily lost.

The required primitive is a portable metadata artifact that travels with the checkpoint and can be inspected offline.

## 3. Goals

### 3.1 Required goals

1. Write metadata after a checkpoint has been completely and successfully saved.
2. Record a cryptographic digest of the exact checkpoint artifact being described.
3. Read and verify metadata without network access or a tracking backend.
4. Work with raw PyTorch training loops without requiring a framework-specific dependency.
5. Fail safely when metadata is incomplete rather than inventing values.
6. Make the sidecar easy to copy, upload, archive, and review with the checkpoint.
7. Provide deterministic output suitable for future signing and reproducible comparisons.

### 3.2 Secondary goals

- Provide thin adapters for common training frameworks later.
- Record optional training, compute, and lineage information supplied by the caller.
- Support a directory checkpoint through a deterministic manifest rather than assuming every checkpoint is one file.

## 4. Non-goals

v0.1 is not:

- a replacement for MLflow, W&B, TensorBoard, or a model registry;
- a live telemetry system or dashboard;
- a reproducibility guarantee;
- a proof that a claimed dataset, code revision, or hardware configuration was actually used;
- a signing, identity, trust, or attestation system;
- a new checkpoint format;
- a distributed-training coordinator;
- a GPU utilisation profiler;
- a storage or upload service.

## 5. Correct security and trust model

### 5.1 What v0.1 guarantees

If `modelmeta verify` succeeds, then:

1. the checkpoint bytes currently being verified match the digest recorded in the sidecar; and
2. the sidecar is structurally valid according to its schema.

This detects accidental corruption, incomplete copying, and mismatch between a checkpoint and its sidecar.

### 5.2 What v0.1 does not guarantee

The following claims remain self-asserted:

- which code produced the checkpoint;
- which dataset was used;
- whether the recorded loss or learning rate is accurate;
- whether the stated GPU-hours are accurate;
- whether a particular person or organisation wrote the metadata.

An attacker or careless operator who can replace both files can create a new valid-looking pair. SHA-256 alone cannot solve this.

### 5.3 Future authenticated provenance

Signed provenance is planned for v0.2 or later. The signing design should sign a canonical representation of the metadata and checkpoint digest using an established envelope format such as DSSE or an equivalent well-specified format. It must define:

- signer identity;
- key distribution and rotation;
- trust roots;
- revocation and expiry;
- whether the signature is attached, detached, or stored in a transparency log.

Until that exists, documentation and CLI output must use terms such as **self-asserted metadata**, **traceability**, and **integrity-linked metadata**, not **proof** or **verified provenance**.

## 6. Artifact model

### 6.1 Single-file checkpoint

For a checkpoint at:

```text
checkpoints/step_042000.safetensors
```

the sidecar is:

```text
checkpoints/step_042000.safetensors.modelmeta.yaml
```

The sidecar is never included in the checkpoint digest.

### 6.2 Directory checkpoint

Many systems save a checkpoint as a directory containing model shards, optimizer state, scheduler state, tokenizer files, and a manifest. In that case:

```text
checkpoints/step_042000/
├── model-00001-of-00004.safetensors
├── model-00002-of-00004.safetensors
├── optimizer.pt
└── step_042000.modelmeta.yaml
```

The directory digest is calculated from a deterministic manifest containing the relative POSIX path and SHA-256 digest of every regular file included in the checkpoint. The sidecar itself and temporary files are excluded by exact, versioned rules: for a directory named `step_042000`, the reserved sidecar name is `step_042000.modelmeta.yaml`, and writer temporary files match `step_042000.modelmeta.yaml.tmp*`. No other `.yaml`, `.tmp`, or similarly named file is excluded. Orphaned reserved temporary files from a prior interrupted write are removed before hashing; if they cannot be removed, hashing fails.

The reserved sidecar name belongs to `modelmeta`. A writer must refuse to overwrite a non-regular object at that path and must fail clearly if the reserved name is occupied in a way that cannot be treated as the prior modelmeta sidecar.

v0.1 must reject symlinks in the target path, including a symlink target or symlink path component, as well as symlinks, sockets, device files, and other non-regular objects inside a directory checkpoint. File and directory hashing records a pre-hash and post-hash `(size, mtime_ns, inode)` identity; a change raises a documented race error. This is best-effort accidental-mutation detection, not protection against an adversarial writer that controls the filesystem. The caller remains responsible for invoking the writer only after the directory is quiescent.

### 6.3 Distributed checkpoints

v0.1 does not coordinate FSDP, DCP, ZeRO, or multi-node checkpoint writes. A caller may invoke the writer after its own save-completion barrier, but `modelmeta` must not pretend to establish that barrier. Native distributed-checkpoint support is a future feature.

## 7. Sidecar format

YAML is the human-facing format. Canonical JSON is the internal representation used for deterministic comparison and future signatures. The YAML parser must preserve the same data model and must reject duplicate keys through a custom `SafeLoader` mapping implementation; duplicate keys are a schema error, never last-write-wins.

### 7.1 Example

```yaml
schema_version: "0.1"
created_at: "2026-07-20T00:00:00Z"

checkpoint:
  kind: file
  path: "step_042000.safetensors"
  size_bytes: 1843200000
  sha256: "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
  hash_scope: bytes

provenance:
  run_id: "run_20260720_001"
  experiment_name: "biomed-pretraining"
  git:
    repository: "https://github.com/example/project"
    commit: "abc123..."
    dirty: false
  dataset:
    name: "curated-corpus"
    version: "2026-07-18"
    digest: "sha256:..."

training:
  global_step: 42000
  epoch: 2.5
  loss: 1.2384
  learning_rate: 0.00002
  gradient_norm: 0.91

compute:
  framework: "torch"
  framework_version: "2.7.0"
  accelerator_type: "NVIDIA A100"
  accelerator_count: 8
  precision: "bf16"
  gpu_hours: null

optimizer_state:
  included: true
  name: "AdamW"
  scheduler_included: true

lineage:
  parent_checkpoint: null

integrity:
  metadata_encoding: "yaml+canonical-json-v1"
  signed: false
```

### 7.2 Schema rules

- `schema_version` is required and is a string.
- `created_at` is required and must use the exact UTC representation `YYYY-MM-DDTHH:MM:SSZ`: literal `Z`, no numeric offset, and no fractional seconds.
- `checkpoint.kind` is `file` or `directory`.
- `checkpoint.sha256` is required and must be a lowercase 64-character hexadecimal SHA-256 digest.
- `checkpoint.path` is relative to the sidecar directory and is informational only. `inspect` and `verify` must operate exclusively on the checkpoint path supplied by the caller; they must never open, join, resolve, or otherwise follow a path read from sidecar contents.
- Numeric fields use SI units and explicit names. GPU time is in decimal `gpu_hours`, not hours per device unless stated otherwise.
- Unknown fields are preserved by the reader but ignored by v0.1 verification.
- The writer omits unavailable optional values and never fabricates them. Readers may accept explicit `null` for optional known fields, but canonical comparison normalizes an explicit optional `null` to omission so semantically identical sidecars do not produce phantom differences.
- Dataset names and versions are descriptive only. A dataset `digest` is required for content identity; a version string alone is not sufficient.
- Git commit identifies source history but does not capture uncommitted changes. `dirty: true` must be recorded when known.

### 7.3 Training metrics

Training metrics are snapshots supplied by the caller. `modelmeta` does not infer a loss curve from one checkpoint and does not claim that a metric represents the whole run. A future version may support a separate metrics file, but the sidecar should remain small.

### 7.4 Canonical JSON v1

Canonical JSON is defined by RFC 8785 JSON Canonicalization Scheme (JCS), encoded as UTF-8. Implementations must use lexicographic property ordering, JCS number serialization, no insignificant whitespace, and must reject NaN and Infinity. The canonical representation is independent of YAML formatting, mapping insertion order, and operating system. The `integrity.metadata_encoding` value is `yaml+canonical-json-v1`.

## 8. Writer API

```python
from modelmeta import MetaWriter

writer = MetaWriter(
    run_context={
        "run_id": "run_20260720_001",
        "experiment_name": "biomed-pretraining",
        "git": {
            "repository": "https://github.com/example/project",
            "commit": "abc123",
            "dirty": False,
        },
        "dataset": {
            "name": "curated-corpus",
            "version": "2026-07-18",
            "digest": "sha256:...",
        },
    }
)

sidecar_path = writer.on_checkpoint_saved(
    checkpoint_path="checkpoints/step_042000.safetensors",
    training_state={
        "global_step": 42000,
        "loss": 1.2384,
        "learning_rate": 2e-5,
        "gradient_norm": 0.91,
    },
    compute_state={
        "framework": "torch",
        "framework_version": "2.7.0",
        "accelerator_type": "NVIDIA A100",
        "accelerator_count": 8,
        "precision": "bf16",
    },
)
```

The public method should:

1. validate the target path;
2. confirm the target exists and is not a temporary file;
3. hash the complete target using streaming I/O;
4. construct the metadata object without mutating caller-owned dictionaries;
5. validate the schema;
6. write the sidecar to a temporary file in the same directory;
7. flush and `fsync` the temporary file;
8. atomically replace the final sidecar path;
9. return the final sidecar path.

If hashing or writing fails, the method must raise an error and leave the previous valid sidecar untouched. It must not write a partial sidecar.

### 8.1 Idempotency

Writing metadata for the same checkpoint more than once is allowed. The operation replaces the sidecar atomically. The writer must not silently merge old fields into new metadata because that creates stale claims.

### 8.2 Concurrent calls

Concurrent writers targeting the same checkpoint are unsupported in v0.1. The last atomic replacement wins, and the CLI should make this visible through the sidecar timestamp. A future version may use a lock or immutable sidecar names.

## 9. Hashing and verification

### 9.1 File hashing

Read the file in bounded chunks, for example 8 MiB, and calculate SHA-256 over the exact bytes. Do not load the entire checkpoint into memory.

### 9.2 Directory hashing

For a directory checkpoint, create an in-memory manifest with entries sorted by UTF-8 encoded relative POSIX path:

```json
{
  "files": [
    {"path": "model-00001-of-00004.safetensors", "sha256": "...", "size_bytes": 123}
  ]
}
```

The checkpoint digest is SHA-256 of the canonical JSON representation of that manifest. The manifest should be exposed by `inspect` so users can understand what was hashed.

### 9.3 Verification outcomes

`verify` must return distinct statuses and exit codes. Exit code `2` remains reserved for CLI usage/argument errors; domain results use the following stable block:

| Condition | Exit code | Meaning |
|---|---:|---|
| Match | 0 | Checkpoint and sidecar agree |
| Missing sidecar | 10 | No metadata is available |
| Invalid schema | 11 | Sidecar cannot be trusted structurally |
| Digest mismatch | 12 | Checkpoint bytes differ from the sidecar |
| Unsupported target | 13 | v0.1 cannot safely hash the target |
| I/O or permission error | 14 | Verification could not complete |

An unrecognized `schema_version` is an unsupported-schema result. A v0.1 reader must fail closed rather than attempting best-effort parsing. Verification must never report provenance as verified; the success message is `checkpoint integrity verified; metadata remains self-asserted`.

Verification must never report “provenance verified”. Its success message should say “checkpoint integrity verified; metadata remains self-asserted”.

## 10. CLI

### 10.1 Inspect

```bash
modelmeta inspect checkpoints/step_042000.safetensors
```

Displays the sidecar in a readable form, including whether it is signed, the checkpoint digest, training step, dataset identity, Git commit, and any missing high-value fields.

### 10.2 Verify

```bash
modelmeta verify checkpoints/step_042000.safetensors
```

Recomputes the checkpoint digest and compares it to the sidecar. It must support `--json` for automation and must use the exit codes defined above.

### 10.3 Diff

```bash
modelmeta diff checkpoints/step_040000.safetensors \
  checkpoints/step_042000.safetensors
```

Compares metadata fields only. It must clearly separate:

- training changes: step, epoch, loss, learning rate;
- provenance changes: run, Git, dataset;
- compute changes: hardware, precision, GPU count;
- artifact changes: size and digest.

It must not imply that a lower loss means a better model.

The `--json` output has a stable, independently versioned envelope. v0.1 uses this shape for `inspect`, `verify`, and `diff`:

```json
{
  "cli_output_version": "1",
  "command": "verify",
  "exit_code": 0,
  "status": "match",
  "checkpoint_path": "checkpoints/step_042000.safetensors",
  "sidecar_path": "checkpoints/step_042000.safetensors.modelmeta.yaml",
  "detail": {}
}
```

Future changes may add fields, but must not remove or rename v1 fields without incrementing `cli_output_version`. Human-readable output and JSON output must remain separate.

### 10.4 Create or repair metadata

The initial release should not provide a command that invents provenance from incomplete information. A future `modelmeta create` command may accept an explicit metadata file, but it must label all manually supplied fields as self-asserted.

## 11. GPU-hours decision

GPU-hours should not be implemented as a cumulative read-modify-write field in the sidecar for v0.1.

The sidecar is a snapshot tied to one checkpoint, not a durable run ledger. Using it as the ledger creates failure modes when:

- an older checkpoint is copied over a newer one;
- a sidecar is missing or edited;
- training restarts from a checkpoint;
- multiple ranks write simultaneously;
- a checkpoint save fails after the timer is updated;
- a process is killed between computation and sidecar replacement.

For v0.1, `compute.gpu_hours` is optional and must be supplied by the caller. If implemented later, use a separate append-only run ledger or durable training-run state, then copy a snapshot into each checkpoint sidecar.

The future timer must define whether it measures:

- wall-clock accelerator allocation time;
- active CUDA execution time;
- the sum across devices;
- the sum across ranks and nodes.

Those quantities are not interchangeable. `torch.cuda.Event` measures GPU stream elapsed time, not complete infrastructure cost or wall-clock training duration.

## 12. Performance requirements

- Hashing must be streaming and bounded-memory.
- Sidecar generation must not duplicate checkpoint bytes.
- The writer should expose a synchronous implementation first; asynchronous hashing can be added only if completion and failure semantics are explicit.
- The writer must report elapsed hashing time so users can measure its cost.
- A future optimisation may cache digests by inode, size, modification time, and device-specific file identity, but such caching must never weaken correctness.

## 13. Packaging and portability

The sidecar is useful only if it travels with the checkpoint. Documentation must define copy and upload conventions:

```bash
cp step_042000.safetensors step_042000.safetensors.modelmeta.yaml destination/
```

Registry and Hub adapters should upload the checkpoint and sidecar as one logical operation when possible. If only the checkpoint is uploaded, the metadata is intentionally absent; `modelmeta` must not try to recover it from a tracking backend.

The sidecar must contain no secrets, access tokens, private filesystem paths, or raw environment variables by default. Repository URLs, dataset names, and hostnames may be sensitive and should be opt-in or sanitised by the caller.

The writer must not capture process environments or discover secrets implicitly. A small denylist guard for caller-supplied keys matching `token`, `secret`, `password`, or `api[_-]?key` may be added as a v0.1 hardening item; it must be documented as a caller-input safety check rather than a claim of complete secret detection.

## 14. Repository layout

```text
modelmeta/
├── __init__.py
├── schema.py          # Typed model and validation
├── canonical.py       # Canonical JSON and timestamp rules
├── hashing.py         # File and directory hashing
├── writer.py          # Atomic sidecar creation
├── reader.py          # YAML parsing and canonical representation
├── verify.py          # Digest and schema verification
├── cli.py             # inspect, verify, diff
└── adapters/
    └── torch_loop.py  # Optional convenience adapter
tests/
├── test_hashing.py
├── test_canonical.py
├── test_writer.py
├── test_verify.py
├── test_cli.py
└── fixtures/
README.md
CONTRIBUTING.md
pyproject.toml
.githooks/
├── pre-commit          # Fast formatting, lint, type, and unit checks
└── pre-push            # Full suite including streaming-memory coverage
```

Avoid importing PyTorch in the core package. The raw PyTorch adapter may depend on PyTorch, but `inspect`, `verify`, and metadata parsing should work in a minimal installation.

## 15. v0.1 scope

### Must ship

- [ ] Typed schema with explicit required and optional fields
- [ ] YAML reader and writer with duplicate-key rejection
- [ ] Canonical internal representation
- [ ] Exact directory sidecar/temp-file exclusion and sidecar collision handling
- [ ] Streaming SHA-256 for files
- [ ] Deterministic directory manifest hashing
- [ ] Symlink rejection and best-effort hash race detection
- [ ] Atomic sidecar writes with temporary-file cleanup
- [ ] `MetaWriter` framework-neutral API
- [ ] Raw PyTorch loop adapter with no framework callback dependency
- [ ] `inspect`, `verify`, and `diff` commands
- [ ] JSON CLI output mode and documented exit codes
- [ ] Tests for corruption, missing sidecars, partial writes, directories, and unknown fields
- [ ] Documentation that distinguishes integrity from provenance

### Should ship if small

- [ ] Optional caller-supplied compute metadata
- [ ] Optional caller-supplied GPU-hours value with documented semantics
- [ ] A `modelmeta version` command
- [ ] A pre-upload checklist for keeping checkpoint and sidecar together
- [ ] Secret-looking caller-key warning or rejection
- [ ] Explicit unsupported-schema-version handling

### Explicitly defer

- [ ] Sigstore, DSSE, or any signing implementation
- [ ] Trust-root and identity management
- [ ] FSDP, DCP, ZeRO, and multi-node coordination
- [ ] Cumulative GPU-hour accounting
- [ ] MLflow, W&B, Hugging Face Trainer, and Lightning adapters
- [ ] Remote registry upload integration
- [ ] Background hashing and digest caches
- [ ] Full loss curves and event streams

The project is developed in sprints. The v0.1 boundary defines the first shippable slice; deferred items remain on the roadmap for later sprints rather than being abandoned.

## 16. Acceptance criteria

The release is acceptable when all of the following are true:

1. A checkpoint can be written, copied, inspected, and verified on a machine with no tracking backend.
2. Modifying one checkpoint byte causes verification to fail with the digest-mismatch exit code.
3. Modifying metadata without changing the checkpoint is detectable as a metadata change, but is explicitly described as possible for unsigned metadata.
4. Killing the process during sidecar writing does not leave a syntactically valid but truncated sidecar in place.
5. Directory hashing is deterministic across operating systems that expose the same file bytes and relative paths.
6. The core package can be installed without PyTorch.
7. No field is silently populated from an unreliable heuristic.
8. The README explains exactly what v0.1 can and cannot establish.
9. Tests cover at least one checkpoint larger than available memory to confirm streaming behaviour.
10. CLI output is stable enough for scripts, with human-readable output kept separate from `--json` output.
11. The local validation hooks are documented and reproducible without hosted CI minutes.

## 17. Implementation order

1. Freeze the schema and canonicalisation rules.
2. Implement hashing and tests before the writer.
3. Implement atomic sidecar writing and crash-oriented tests.
4. Implement reader, verification, and exit codes.
5. Implement `inspect` and `diff`.
6. Add the raw PyTorch adapter as a thin translation layer.
7. Write the README around concrete copy, corruption, and missing-sidecar examples.
8. Only after this is stable, design signed attestations and durable run accounting.

The repository uses committed local hooks rather than GitHub Actions. Contributors install them with `git config core.hooksPath .githooks`; `pre-commit` runs fast checks and `pre-push` runs the complete suite. This provides local enforcement only and does not create a server-side gate for external pull requests.

## 18. Final product definition

The correct v0.1 product is:

> A small offline tool that creates and verifies portable, hash-linked metadata for model checkpoint artifacts.

It is not yet:

> A system that proves where model weights came from.

That stronger claim requires authenticated signing, a trusted identity, durable run records, and a defined trust model. Keeping that distinction explicit is what prevents the project from becoming a decorative YAML generator with misleading security language.

## 19. Amendments after market and technical research (2026-08-21)

Research synthesis: `docs/research/2026-08-21-pmf-and-landscape.md`. The v0.1 scope is unchanged; the following decisions are amended or pinned.

1. **Python floor is `>=3.11`** (was implicitly 3.10). Rationale: 3.10 upstream EOL is 2026-10-31; native `hashlib.file_digest`; `tomllib` in stdlib.
2. **Canonical JSON uses the `rfc8785` library (pinned)** rather than a hand-rolled serializer; RFC 8785 Appendix B vectors are part of the test suite. Vendoring trigger: library abandoned AND a release blocks on it.
3. **The YAML loader must reject anchors and aliases** in addition to duplicate keys, and enforce an input size cap (default 4 MiB). PyYAML's alias-expansion DoS is unfixed upstream (issue #235); sidecars are semi-trusted input.
4. **Atomic write hardening:** temporary files are created with `mkstemp` in the sidecar directory using the `<sidecar>.tmp*` naming already excluded from directory hashing; `os.replace` is retried up to three times on Windows `PermissionError`; parent-directory fsync is POSIX-only and its omission on Windows is documented as a durability gap.
5. **Race detection degrades gracefully:** when `(size, mtime_ns, inode)` identity cannot include a meaningful inode (`st_ino == 0` on FAT/WebDAV-class filesystems), comparison falls back to size + mtime only. A detected race raises a documented race error mapped to exit code 14 (verification could not complete), distinct from digest mismatch.
6. **Unrecognized `schema_version` produces status `unsupported_schema` with exit code 13**, sharing the "cannot safely proceed" block with unsupported targets. The reader fails closed.
7. **Strategic positioning:** `verify` is the acquisition feature — a pre-load integrity gate before `torch.load`, framed against the pickle-RCE CVE timeline. The canonical metadata payload must remain extractable so v0.2 can emit Sigstore/OpenSSF Model Signing-compatible statements instead of inventing a rival envelope.
8. **Roadmap note:** surfacing embedded safetensors/GGUF metadata during `inspect` (composition, not competition) is deferred; it must not enter v0.1 scope.
