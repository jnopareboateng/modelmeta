"""Optional adapters integrating modelmeta with common training setups."""

from __future__ import annotations

from modelmeta.adapters import torch_loop
from modelmeta.adapters.torch_loop import capture_git_state, stamp_checkpoint

__all__ = ["capture_git_state", "stamp_checkpoint", "torch_loop"]
