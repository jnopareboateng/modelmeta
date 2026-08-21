# modelmeta — market, landscape, and technical research synthesis

**Date:** 2026-08-21
**Method:** Three parallel research tracks (competitive landscape, PMF/demand, technical feasibility), web-sourced.
**Purpose:** Decide whether v0.1 ships as specced, with what positioning, and which spec decisions change.

## 1. Verdict

**Build it — as a narrow integrity tool, not a provenance standard.**

- The niche (unsigned, human-readable, hash-linked checkpoint sidecar) is **empty**: trackers keep metadata behind backends, embedded format metadata can't be added post-hoc without mutating bytes, signing tools operate a tier above, storage pointers stop at hashes. No packaged competitor found on PyPI/GitHub as of Aug 2026.
- PMF is **weak-to-moderate (~30% confidence)** as a "standard" play. The wedge that converts: `modelmeta verify` positioned as a **pre-load integrity gate** on the pickle-CVE timeline (CVE-2025-32434, CVE-2026-24747 — RCEs against `torch.load` within 24 months). Integrity has a forcing event; provenance-recording does not.
- Strategic hedge: design the canonical metadata payload so v0.2 can emit **Sigstore/OpenSSF Model Signing (OMS)-compatible statements** — ride the incumbent rather than race it.

## 2. Competitive landscape (what exists, what it means)

| Layer | Tools | Gap modelmeta fills |
|---|---|---|
| Trackers | MLflow (`MLmodel` YAML), W&B artifacts, Neptune, Aim | Metadata lives in backend DBs; nothing portable beside the file. MLflow's YAML is right shape, wrong binding (no byte digest). |
| Embedded format metadata | safetensors `__metadata__`, GGUF KV, ONNX `metadata_props` | Writing = rewriting gigabytes → invalidates LFS OIDs/pins; needs framework cooperation at save time; can't annotate existing files. Complementary, not competitive. |
| Signing/provenance | sigstore/model-transparency v1.1 (Google/NVIDIA/OpenSSF), google/model-signing, SPDX 3.0 AI, CycloneDX ML-BOM, C2PA | All answer "are these bytes authentic?" (keys, bundles, PKI). None occupies the unsigned, cat-able layer below. OMS explicitly plans signed metadata → future integration point, also future competitor. |
| Storage pointers | DVC `.dvc` (md5+size+path), git-lfs pointer (sha256+size) | Prove the sidecar pattern at scale; capture zero training semantics. |
| Direct competitors | none packaged; ad-hoc per-team scripts; `hanfei-fa` (Mar 2026, Merkle sidecars, sign/verify/diff) is nearest new entrant | Win on simplicity/offline/no-key UX, not first-mover. |

Steelman rebutted: "just use safetensors metadata" fails because mutation breaks content-addressability; "sigstore covers it" fails because unsigned tamper-*evident* ≠ signed tamper-*proof* and most labs haven't adopted signing infra; "it's a 50-line script" concedes the pattern but ignores that the value is the shared convention + atomic-write/verify discipline.

## 3. PMF

### Segments (ranked)

| Segment | Pain | Notes |
|---|---|---|
| Indie/open-source fine-tuners publishing to HF | 4/5 | Hit directly by malicious-model incidents + pickle CVEs; already hand-roll sidecars |
| Small teams on raw PyTorch loops, no MLOps backend | 3–4/5 | Documented silent resume/corruption incidents (optimizer-state loss, Megatron corrupt checkpoints) |
| Academic reproducibility | 3/5 | Real pain, misaligned incentives, slow channel |
| Enterprise MLOps (MLflow/W&B) | 2/5 | Already solved server-side; unreachable |
| Marketplaces/authenticity | 3/5 for them | Converging on *signed* provenance; not reachable by an unsigned tool |

### Demand signals
1. Pickle RCE recurrence: CVE-2025-32434 (bypassed `weights_only=True`, fixed torch 2.6.0); CVE-2026-24747 (fixed 2.10.0).
2. Practitioners prescribe exactly this design in practitioner guides ("attach a sidecar JSON/YAML for every checkpoint… shouldn't need a VPN to know what this file is") — reinvented per team, no standard.
3. Corruption/resume incident write-ups are routine (kroonen.ai optimizer-state bug; Megatron issues #4378/#5281).

### Anti-signals (honest)
1. Sigstore model-signing v1.0+ is the signed superset with Google/NVIDIA backing and explicit plans for tamper-proof metadata records.
2. DIY cost is ~15 lines (`json.dump` + `sha256sum`); HF Trainer already writes `training_args.bin`/`trainer_state.json`.
3. Discipline-tool adoption is historically thin (study of 56 OSS projects: 85.7% use DVC only for basic versioning).

### Wedge
**ICP:** solo/small-team PyTorch fine-tuners publishing checkpoints to Hugging Face who want one command proving "these bytes = this commit + dataset + metrics" without adopting W&B/MLflow or a signing PKI.
**Trigger feature:** `verify` as cheap pre-load gate before `torch.load`. `stamp`/`diff` are retention; `verify` is acquisition.

### Distribution (ranked)
1. PyPI + README 60-second verify-before-load snippet (ruff/pre-commit pattern).
2. HF-ecosystem content framed on the CVE timeline ("what `weights_only=True` does not protect you from").
3. Framework integrations (Trainer callback / `save_pretrained`) last — requires ecosystem buy-in.

### Kill criteria (decide by, don't hope past)
- <500 PyPI downloads/month AND <10 non-author GitHub interactions within 8 weeks of launch → kill or pivot.
- No unsolicited framework-integration ask within 12 weeks → demand isn't converting → kill.
- OpenSSF OMS ships friendly keyless hash+metadata+verify flow before ~1k users → pivot to OMS frontend (emit OMS payloads from modelmeta sidecars).

## 4. Technical decisions validated/amended

| Topic | Decision |
|---|---|
| Canonical JSON | Use **`rfc8785`** (Trail of Bits, zero-dep, Apache-2.0). Hand-rolling ES6 number serialization is the trap; sorted-keys shortcut diverges on `1e-08` vs `1e-8`. Run RFC Appendix B vectors in tests. Pin exact version; pre-decide vendoring trigger. |
| Python floor | **≥3.11** (amended from ≥3.10): 3.10 EOL Oct 2026; native `hashlib.file_digest`; `tomllib`. |
| YAML | PyYAML ≥6.0.3, custom SafeLoader: duplicate-key rejection **plus anchor/alias rejection** (billion-laughs unfixed upstream, #235 open since 2018) + input size cap (4 MiB). Dump args fixed: `sort_keys=True, default_flow_style=False, allow_unicode=True, width=10**6`. |
| Atomic write | mkstemp same dir (`<sidecar>.tmp*` naming matches exclusion rules) → write → flush → fsync → close → `os.replace` (retry ×3 on Windows `PermissionError`) → parent-dir fsync POSIX-only. Documented Windows durability gap. |
| Hashing | `hashlib.file_digest` (256 KiB internal buffer). SHA-NI ≈2–3 GB/s compute; disk-bound on NVMe. No mmap. Document cost honestly. |
| Race detection | `os.lstat` snapshot `(size, mtime_ns, inode, dev)` pre/post; degrade gracefully when `st_ino == 0` (FAT/WebDAV); never false-positive on inode-less filesystems. Race error maps to exit 14 (could-not-complete), distinct from digest mismatch. |
| Sparse test | `os.ftruncate` sparse files for >memory acceptance test; POSIX-only gate (NTFS would really allocate). |
| Toolchain | hatchling ≥1.31, ruff, mypy strict (+`py.typed`), pytest+cov. No runtime deps beyond PyYAML + rfc8785. CLI on argparse (stdlib). |
| Names | PyPI `modelmeta` **free** (404 on registry API) — register at first publish. GitHub org `modelmeta` squatted by dormant unrelated project; repo stays `jnopareboateng/modelmeta`. |

Top implementation risks (ranked): Windows `os.replace` fragility; PyYAML alias-bomb DoS (closed by our loader); `rfc8785` single-vendor beta (mitigated by vectors + vendoring plan); race-detection portability; Python-floor timing (resolved by ≥3.11).

## 5. Spec amendments

Folded into `docs/specs/modelmeta-spec-v0.1.md` §19. Summary: Python ≥3.11; strict loader rejects anchors/aliases + size cap; rfc8785 pinned with RFC vectors in CI; Windows retry/durability notes; graceful inode degradation; unrecognized `schema_version` → `unsupported_schema` (exit 13); schema payload kept extractable for future OMS/Sigstore signing; embedded safetensors/GGUF metadata surfacing in `inspect` deferred to roadmap (compose, don't compete).

## 6. Sources

Primary URLs captured inline above; key anchors:
- https://github.com/sigstore/model-transparency · https://openssf.org/blog/2025/07/23/case-study-google-secures-machine-learning-models-with-sigstore/ · https://github.com/ossf/model-signing-spec
- https://jfrog.com/blog/data-scientists-targeted-by-malicious-hugging-face-ml-models-with-silent-backdoor/ · https://github.com/pytorch/pytorch/security/advisories/GHSA-53q9-r3pm-6pq6 · https://github.com/pytorch/pytorch/security/advisories/GHSA-63cw-57p8-fm3p
- https://pypi.org/project/rfc8785 · https://www.rfc-editor.org/info/rfc8785 · https://github.com/yaml/pyyaml/issues/235
- https://docs.python.org/3/library/hashlib.html · https://doc.dvc.org/user-guide/project-structure/dvc-files
- https://digital-strategy.ec.europa.eu/en/faqs/template-general-purpose-ai-model-providers-summarise-their-training-content
