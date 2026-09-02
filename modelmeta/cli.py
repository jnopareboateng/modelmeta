"""Command-line interface: inspect, verify, diff, version."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from modelmeta import __version__
from modelmeta.errors import (
    SchemaError,
    SidecarIOError,
    UnsupportedSchemaError,
)
from modelmeta.reader import load_sidecar
from modelmeta.schema import validate_metadata
from modelmeta.verify import (
    EXIT_MISSING_SIDECAR,
    STATUS_MISSING_SIDECAR,
    SUCCESS_MESSAGE,
    VerificationOutcome,
    sidecar_path_for,
    verify_checkpoint,
)

CLI_OUTPUT_VERSION = "1"
_HIGH_VALUE_FIELDS = (
    ("run_id", ("provenance", "run_id")),
    ("git_commit", ("provenance", "git", "commit")),
    ("dataset_digest", ("provenance", "dataset", "digest")),
    ("global_step", ("training", "global_step")),
    ("framework", ("compute", "framework")),
)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    assert args.command is not None
    return int(args.func(args))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="modelmeta",
        description="Portable, hash-linked metadata sidecars for model checkpoints.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="emit stable JSON output")

    inspect_parser = subparsers.add_parser(
        "inspect", parents=[common], help="display a checkpoint's sidecar"
    )
    inspect_parser.add_argument("checkpoint")
    inspect_parser.set_defaults(func=_cmd_inspect)

    verify_parser = subparsers.add_parser(
        "verify", parents=[common], help="recompute and compare the checkpoint digest"
    )
    verify_parser.add_argument("checkpoint")
    verify_parser.set_defaults(func=_cmd_verify)

    diff_parser = subparsers.add_parser(
        "diff", parents=[common], help="compare two checkpoints' metadata"
    )
    diff_parser.add_argument("checkpoint_a")
    diff_parser.add_argument("checkpoint_b")
    diff_parser.set_defaults(func=_cmd_diff)

    version_parser = subparsers.add_parser(
        "version", parents=[common], help="print the modelmeta version"
    )
    version_parser.set_defaults(func=_cmd_version, checkpoint=None)
    return parser


def _cmd_inspect(args: argparse.Namespace) -> int:
    if not os.path.exists(args.checkpoint):
        return _usage_error(f"checkpoint does not exist: {args.checkpoint}")
    sidecar = sidecar_path_for(args.checkpoint)
    if not os.path.lexists(sidecar):
        outcome = VerificationOutcome(
            STATUS_MISSING_SIDECAR, EXIT_MISSING_SIDECAR, {"sidecar_path": sidecar}
        )
        return _emit_inspect_failure(args, outcome, sidecar)
    try:
        metadata = validate_metadata(load_sidecar(sidecar))
    except UnsupportedSchemaError as error:
        return _emit_inspect_failure(
            args, VerificationOutcome("unsupported_schema", 13, {"message": str(error)}), sidecar
        )
    except SchemaError as error:
        return _emit_inspect_failure(
            args, VerificationOutcome("invalid_schema", 11, {"message": str(error)}), sidecar
        )
    except (SidecarIOError, OSError) as error:
        return _emit_inspect_failure(
            args, VerificationOutcome("io_error", 14, {"message": str(error)}), sidecar
        )

    missing = [name for name, path in _HIGH_VALUE_FIELDS if _dig(metadata, path) is None]
    if args.json:
        envelope = _envelope(
            "inspect",
            0,
            "ok",
            args.checkpoint,
            sidecar,
            {
                "metadata": metadata,
                "missing_high_value_fields": missing,
            },
        )
        print(json.dumps(envelope, indent=2))
        return 0
    _print_inspection(metadata, sidecar, missing)
    return 0


def _print_inspection(metadata: dict[str, Any], sidecar: str, missing: list[str]) -> None:
    checkpoint = metadata["checkpoint"]
    print(f"sidecar: {sidecar}")
    print(f"schema_version: {metadata['schema_version']}")
    print(f"created_at: {metadata['created_at']}")
    print(f"checkpoint.kind: {checkpoint['kind']}")
    print(f"checkpoint.sha256: {checkpoint['sha256']}")
    print(f"checkpoint.size_bytes: {checkpoint['size_bytes']}")
    integrity = metadata.get("integrity", {})
    print(f"signed: {bool(integrity.get('signed', False))}")
    training = metadata.get("training", {})
    if "global_step" in training:
        print(f"training.global_step: {training['global_step']}")
    if "loss" in training:
        print(f"training.loss: {training['loss']}")
    compute = metadata.get("compute", {})
    if "wall_hours" in compute:
        try:
            wh = float(compute["wall_hours"])
            print(f"wall_hours: {wh:.4f} (~{wh * 60:.1f} min)")
        except (TypeError, ValueError):
            print(f"wall_hours: {compute['wall_hours']}")
    if "gpu_hours" in compute:
        try:
            gh = float(compute["gpu_hours"])
            # Only show gpu_hours separately when it differs from wall_hours
            wh_val = compute.get("wall_hours")
            if wh_val is None or float(wh_val) != gh:
                print(f"gpu_hours: {gh:.4f}")
        except (TypeError, ValueError):
            print(f"gpu_hours: {compute['gpu_hours']}")
    if "framework" in compute:
        print(f"compute.framework: {compute['framework']}")
    if "accelerator_type" in compute:
        print(f"compute.accelerator_type: {compute['accelerator_type']}")
    if "accelerator_count" in compute:
        print(f"compute.accelerator_count: {compute['accelerator_count']}")
    provenance = metadata.get("provenance", {})
    git = provenance.get("git", {})
    if "commit" in git:
        print(f"git.commit: {git['commit']}")
    dataset = provenance.get("dataset", {})
    if "name" in dataset:
        print(f"dataset.name: {dataset['name']}")
    if missing:
        print(f"missing high-value fields: {', '.join(missing)}")


def _emit_inspect_failure(
    args: argparse.Namespace, outcome: VerificationOutcome, sidecar: str
) -> int:
    if args.json:
        envelope = _envelope(
            "inspect", outcome.exit_code, outcome.status, args.checkpoint, sidecar, outcome.detail
        )
        print(json.dumps(envelope, indent=2))
    else:
        print(
            f"inspect failed: {outcome.status}: {outcome.detail.get('message', '')}",
            file=sys.stderr,
        )
    return outcome.exit_code


def _cmd_verify(args: argparse.Namespace) -> int:
    if not os.path.exists(args.checkpoint):
        return _usage_error(f"checkpoint does not exist: {args.checkpoint}")
    outcome = verify_checkpoint(args.checkpoint)
    sidecar = sidecar_path_for(args.checkpoint)
    if args.json:
        envelope = _envelope(
            "verify", outcome.exit_code, outcome.status, args.checkpoint, sidecar, outcome.detail
        )
        print(json.dumps(envelope, indent=2))
        return outcome.exit_code
    if outcome.status == "match":
        print(SUCCESS_MESSAGE)
    else:
        print(
            f"verify failed: {outcome.status}: {outcome.detail.get('message', '')}", file=sys.stderr
        )
    return outcome.exit_code


def _cmd_diff(args: argparse.Namespace) -> int:
    for label, path in (("first", args.checkpoint_a), ("second", args.checkpoint_b)):
        if not os.path.exists(path):
            return _usage_error(f"{label} checkpoint does not exist: {path}")

    sides: dict[str, dict[str, Any]] = {}
    for label, path in (("a", args.checkpoint_a), ("b", args.checkpoint_b)):
        sidecar = sidecar_path_for(path)
        if not os.path.lexists(sidecar):
            outcome = VerificationOutcome(
                STATUS_MISSING_SIDECAR, EXIT_MISSING_SIDECAR, {"sidecar_path": sidecar}
            )
            return _emit_diff_failure(args, outcome, path)
        try:
            sides[label] = validate_metadata(load_sidecar(sidecar))
        except UnsupportedSchemaError as error:
            return _emit_diff_failure(
                args, VerificationOutcome("unsupported_schema", 13, {"message": str(error)}), path
            )
        except SchemaError as error:
            return _emit_diff_failure(
                args, VerificationOutcome("invalid_schema", 11, {"message": str(error)}), path
            )
        except (SidecarIOError, OSError) as error:
            return _emit_diff_failure(
                args, VerificationOutcome("io_error", 14, {"message": str(error)}), path
            )

    groups = _grouped_diff(_flatten(sides["a"]), _flatten(sides["b"]))
    identical = all(not changes for changes in groups.values())
    status = "identical" if identical else "differences_found"
    if args.json:
        envelope = _envelope(
            "diff", 0, status, args.checkpoint_b, sidecar_path_for(args.checkpoint_b), groups
        )
        print(json.dumps(envelope, indent=2))
        return 0
    _print_diff(groups, status)
    return 0


_DIFF_GROUPS = {
    "training": ("training",),
    "provenance": ("provenance", "lineage"),
    "compute": ("compute", "optimizer_state"),
    "artifact": ("checkpoint",),
}


def _group_for(path: str) -> str:
    root = path.split(".", 1)[0]
    for group, sections in _DIFF_GROUPS.items():
        if root in sections:
            return group
    return "other"


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(item, dict):
                flat.update(_flatten(item, child))
            else:
                flat[child] = item
    elif prefix:
        flat[prefix] = value
    return flat


def _grouped_diff(left: dict[str, Any], right: dict[str, Any]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    union_keys = sorted(set(left) | set(right), key=lambda key: key.encode("utf-8"))
    for key in union_keys:
        in_left, in_right = key in left, key in right
        if in_left and in_right and left[key] == right[key]:
            continue
        entry: dict[str, Any] = {}
        if in_left:
            entry["from"] = left[key]
        if in_right:
            entry["to"] = right[key]
        change = "removed" if not in_right else ("added" if not in_left else "changed")
        groups.setdefault(_group_for(key), {}).setdefault(change, {})[key] = entry
    return groups


def _print_diff(groups: dict[str, dict[str, Any]], status: str) -> None:
    print(f"status: {status}")
    for group in ("artifact", "training", "provenance", "compute", "other"):
        if group not in groups:
            continue
        print(f"{group}:")
        for change, entries in sorted(groups[group].items()):
            for key, entry in sorted(entries.items()):
                if change == "changed":
                    print(f"  {key}: {entry['from']!r} -> {entry['to']!r}")
                elif change == "added":
                    print(f"  {key}: (absent) -> {entry['to']!r}")
                else:
                    print(f"  {key}: {entry['from']!r} -> (absent)")


def _emit_diff_failure(
    args: argparse.Namespace, outcome: VerificationOutcome, checkpoint: str
) -> int:
    if args.json:
        envelope = _envelope(
            "diff",
            outcome.exit_code,
            outcome.status,
            checkpoint,
            sidecar_path_for(checkpoint),
            outcome.detail,
        )
        print(json.dumps(envelope, indent=2))
    else:
        print(
            f"diff failed: {outcome.status}: {outcome.detail.get('message', '')}", file=sys.stderr
        )
    return outcome.exit_code


def _cmd_version(args: argparse.Namespace) -> int:
    if args.json:
        envelope = _envelope("version", 0, "ok", None, None, {"version": __version__})
        print(json.dumps(envelope, indent=2))
    else:
        print(__version__)
    return 0


def _envelope(
    command: str,
    exit_code: int,
    status: str,
    checkpoint_path: str | None,
    sidecar_path: str | None,
    detail: dict[str, Any],
) -> dict[str, Any]:
    return {
        "cli_output_version": CLI_OUTPUT_VERSION,
        "command": command,
        "exit_code": exit_code,
        "status": status,
        "checkpoint_path": checkpoint_path,
        "sidecar_path": sidecar_path,
        "detail": detail,
    }


def _usage_error(message: str) -> int:
    print(f"modelmeta: error: {message}", file=sys.stderr)
    return 2


def _dig(mapping: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = mapping
    for segment in path:
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current
