# Contributing

## Setup

```bash
uv sync --extra dev
git config core.hooksPath .githooks
```

## Workflow

- Branch model: `main` (releases) <- `dev` (integration) <- `feat/*`.
- Commits go to `feat/*`, merge into `dev` with `--no-ff`, integrate to `main` when the release slice is complete.

## Gates

`pre-commit` runs ruff (lint + format check), mypy strict, and the fast unit suite.
`pre-push` runs the full suite including tests marked `slow`.

Run everything locally:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy modelmeta tests
uv run pytest
```

## Rules

- The core package must not import PyTorch or any ML framework.
- Runtime dependencies stay minimal; justify any addition in the PR description.
- No fabricated metadata: unavailable optional values are omitted, never invented.
- Verification output must never describe provenance as verified.
