"""Convenience glue for raw PyTorch training loops.

This adapter never imports torch: it only captures repository state and
delegates to MetaWriter, so it can live in any environment.
"""

from __future__ import annotations

import subprocess
from typing import Any


def capture_git_state(repo_path: str = ".") -> dict[str, Any] | None:
    """Collect repository/commit/dirty state; returns None outside a git repo."""
    if not _git_success(["git", "-C", repo_path, "rev-parse", "--is-inside-work-tree"]):
        return None
    commit = _git_output(["git", "-C", repo_path, "rev-parse", "HEAD"])
    if commit is None:
        return None
    dirty = bool(_git_output(["git", "-C", repo_path, "status", "--porcelain"]))
    repository = _git_output(["git", "-C", repo_path, "config", "--get", "remote.origin.url"])
    state: dict[str, Any] = {"commit": commit, "dirty": dirty}
    if repository:
        state["repository"] = repository
    return state


def stamp_checkpoint(
    checkpoint_path: str,
    *,
    run_context: dict[str, Any] | None = None,
    training_state: dict[str, Any] | None = None,
    compute_state: dict[str, Any] | None = None,
    repo_path: str = ".",
) -> str:
    """Capture git provenance from `repo_path` and write the sidecar."""
    provenance = dict(run_context) if run_context else {}
    git_state = capture_git_state(repo_path)
    if git_state is not None and "git" not in provenance:
        provenance["git"] = git_state
    from modelmeta.writer import MetaWriter

    writer = MetaWriter(run_context=provenance or None)
    return writer.on_checkpoint_saved(
        checkpoint_path,
        training_state=training_state,
        compute_state=compute_state,
    )


def _git_output(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    return output or None


def _git_success(command: list[str]) -> bool:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0 and completed.stdout.strip() == "true"
