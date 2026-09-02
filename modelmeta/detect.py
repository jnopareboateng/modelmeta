"""Best-effort accelerator detection across vendors (NVIDIA/AMD/Intel/Ascend/Biren/CPU).

This module never imports torch at import time and never raises. It is purely
informational — the sidecar remains declarative: if detection fails we return
count=1, type="unknown"/"cpu" with source="fallback". Callers decide whether to
trust a detected count or supply their own `accelerator_count` / `accelerator_type`.

Wall-clock time is always true; gpu_hours = wall_hours * accelerator_count is
only meaningful when the count/type are accurately declared.
"""

from __future__ import annotations

import os
import re
import subprocess
from typing import Any


def _normalize_name(raw: str) -> str:
    """Lowercase, slugify a device name for sidecar storage."""
    name = raw.strip().lower()
    # Keep alphanum + underscore, collapse spaces/dashes
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    # Truncate to avoid huge strings from weird drivers
    return name[:64] if name else "unknown"


def _env_count(env_name: str) -> int | None:
    val = os.environ.get(env_name)
    if val is None:
        return None
    val = val.strip()
    if not val or val == "-1":
        return None
    # CUDA_VISIBLE_DEVICES="0,1,2"  or  ""  or  "-1"
    parts = [p.strip() for p in val.split(",") if p.strip() not in ("", "-1")]
    if not parts:
        return None
    return len(parts)


def _try_torch() -> dict[str, Any] | None:
    """Probe torch if installed, without importing at module load."""
    try:
        import torch  # type: ignore[import-not-found]
    except Exception:
        return None

    # 1) NVIDIA / AMD via cuda (ROCm also exposes cuda API)
    try:
        cuda = getattr(torch, "cuda", None)
        is_avail = getattr(cuda, "is_available", None) if cuda else None
        if cuda is not None and is_avail is not None and is_avail():
            count = int(cuda.device_count())
            if count > 0:
                try:
                    raw_name = cuda.get_device_name(0)
                except Exception:
                    raw_name = ""
                normalized = _normalize_name(raw_name) if raw_name else "cuda_device"
                accel_type = normalized
                return {
                    "accelerator_count": count,
                    "accelerator_type": accel_type,
                    "source": "torch.cuda",
                    "detail": raw_name,
                }
    except Exception:
        pass

    # 2) Intel XPU
    try:
        xpu = getattr(torch, "xpu", None)
        if xpu is not None and hasattr(xpu, "is_available") and xpu.is_available():
            count = int(xpu.device_count())
            return {
                "accelerator_count": max(count, 1),
                "accelerator_type": "intel_xpu",
                "source": "torch.xpu",
            }
    except Exception:
        pass

    # 3) Apple MPS
    try:
        backends = getattr(torch, "backends", None)
        mps = getattr(backends, "mps", None) if backends else None
        if mps is not None and hasattr(mps, "is_available") and mps.is_available():
            return {
                "accelerator_count": 1,
                "accelerator_type": "apple_mps",
                "source": "torch.mps",
            }
    except Exception:
        pass

    # 4) Huawei Ascend via torch_npu (separate package)
    try:
        import torch_npu  # type: ignore[import-not-found]  # noqa: F401

        npu = getattr(torch, "npu", None)
        if npu is not None and hasattr(npu, "is_available") and npu.is_available():
            try:
                count = int(npu.device_count())
            except Exception:
                count = 1
            return {
                "accelerator_count": max(count, 1),
                "accelerator_type": "huawei_ascend",
                "source": "torch_npu",
            }
    except Exception:
        pass

    return None


def _try_smi() -> dict[str, Any] | None:
    """Best-effort subprocess probes for vendor SMI tools (2s timeout each)."""
    # NVIDIA
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if names:
                return {
                    "accelerator_count": len(names),
                    "accelerator_type": _normalize_name(names[0]),
                    "source": "nvidia-smi",
                    "detail": names[0],
                }
    except (OSError, subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # AMD rocm-smi
    try:
        result = subprocess.run(
            ["rocm-smi", "--showproductname"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            # Count cards by lines containing product name
            lines = [ln for ln in result.stdout.splitlines() if "Card" in ln or "GPU" in ln]
            count = len(lines) if lines else 1
            return {
                "accelerator_count": count,
                "accelerator_type": "amd_rocm",
                "source": "rocm-smi",
            }
    except (OSError, subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def detect_accelerators() -> dict[str, Any]:
    """Return best-effort accelerator info, never raises, never imports torch at load.

    Returns dict with ``accelerator_count`` (int), ``accelerator_type`` (slug
    like ``nvidia_a100``/``amd_mi300``/``intel_xpu``/``huawei_ascend``/``cpu``),
    ``source`` (torch.cuda, nvidia-smi, env, fallback), and optional ``detail``.

    The caller decides whether to use the detected count or declare their own.
    Detection answers "what is visible/available", not "what this process actually
    used" — only the training framework knows utilization. Wall-clock time is
    always authoritative; gpu_hours = wall_hours * count is only as good as count.
    """
    # 1) torch probe (covers most NVIDIA/AMD/Intel/Apple/Huawei when torch is installed)
    info = _try_torch()
    if info is not None:
        return info

    # 2) SMI tools (no torch needed)
    info = _try_smi()
    if info is not None:
        return info

    # 3) Env vars (allocation, not utilization)
    for env_name in (
        "CUDA_VISIBLE_DEVICES",
        "HIP_VISIBLE_DEVICES",
        "ROCR_VISIBLE_DEVICES",
        "ASCEND_RT_VISIBLE_DEVICES",
        "ZE_AFFINITY_MASK",
    ):
        count = _env_count(env_name)
        if count is not None:
            return {
                "accelerator_count": count,
                "accelerator_type": "unknown",
                "source": env_name,
            }

    # 4) Fallback — likely CPU-only or unknown silicon (Biren/MooreThreads expose cuda but
    # would have been caught by torch; if torch not installed we can't tell)
    return {
        "accelerator_count": 1,
        "accelerator_type": "cpu",
        "source": "fallback",
    }
