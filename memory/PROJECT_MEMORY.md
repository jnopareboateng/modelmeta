# PROJECT_MEMORY — modelmeta

Durable facts for future sessions. Chronology in UPDATE_LOG.md.

## Identity & repo
- Repo: `jnopareboateng/modelmeta` (public), WSL path `~/projects/justjosh/modelmeta`.
- Remote uses SSH alias `github-jnopareboateng` (NOT bare `github.com`, which routes to the minoHealth key).
- Local git identity: `jnopareboateng <jnopareboateng@outlook.com>`. No AI attribution in commits, ever.
- PyPI name `modelmeta` was free as of 2026-08-21 — register at first publish. GitHub org `modelmeta` is squatted by a dormant unrelated project (modelmeta.dev).

## Product thesis (2026-08-21 research)
- v0.1 = unsigned hash-linked sidecar: integrity + traceability, NOT provenance.
- Wedge: `verify` as pre-load gate before `torch.load`, framed on pickle-RCE CVEs (CVE-2025-32434, CVE-2026-24747). ICP: indie/small-team PyTorch fine-tuners publishing to HF.
- PMF weak-to-moderate (~30%). Kill criteria: <500 dl/mo + <10 interactions at 8 weeks; no integration ask by 12 weeks; OMS keyless flow ships → pivot to OMS frontend.
- v0.2 direction: emit Sigstore/OMS-compatible signed statements from the canonical payload — ride the incumbent.

## Technical decisions (researched 2026-08-21)
- Python >=3.11 (3.10 EOL Oct 2026; `hashlib.file_digest`). hatchling, ruff, mypy strict + py.typed, pytest.
- Runtime deps ONLY: PyYAML>=6.0.3, rfc8785 (Trail of Bits) for RFC 8785 JCS. CLI = argparse stdlib.
- YAML loader: custom SafeLoader rejecting duplicate keys AND anchors/aliases (billion-laughs unfixed upstream #235) + 4 MiB input cap.
- Atomic write: mkstemp same-dir `<sidecar>.tmp*` → fsync → os.replace (retry x3 on Windows PermissionError) → parent-dir fsync POSIX-only.
- Race detection: lstat (size, mtime_ns, inode, dev); degrade when st_ino==0; race error -> exit 14, not 12.
- Unrecognized schema_version -> status unsupported_schema, exit 13.
- Large-file test: sparse files via os.ftruncate, POSIX-only gate.
- Hashing throughput ceiling ~2-3 GB/s (SHA-NI), disk-bound on NVMe; no mmap.

## Environment quirks
- Shell from Windows side must go through `wsl -d Ubuntu-22.04 -- bash -lc "..."`; PowerShell chokes on WSL UNC paths for redirection. Nested quotes/`$()` inside the bash -lc string get mangled — write script files instead of inline one-liners for anything complex.
- venv runs Python 3.14 (uv default satisfying >=3.11); system python3 is 3.10.
- `.githooks/pre-push` runs the full suite incl. 16 GiB sparse test (~5 min). Pushes through automation should use `--no-verify` after running gates manually.

## Implementation state (v0.1.0, released 2026-08-21)
- Shipped: schema validation, RFC 8785 canonicalization, strict YAML reader (dup keys + anchors + aliases rejected), streaming file hashing, deterministic directory manifests with orphan-temp cleanup, race detection, atomic sidecar writer, verify/inspect/diff/version CLI with stable JSON envelope (`cli_output_version: "1"`), torch-loop adapter (no torch import).
- Test suite: 137 tests; slow-marked sparse test is the release gate for spec acceptance #9.
- PyPI name reserved-in-plan only — NOT yet registered. Register before any public announcement.
