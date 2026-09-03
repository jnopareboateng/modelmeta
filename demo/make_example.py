"""Regenerate the committed demo example (deterministic).

Run from the repo root:  python demo/make_example.py
Requires: scikit-learn  (uv pip install scikit-learn)

Trains study-hours -> exam-score regression, saves examples/score_model.pkl
and stamps its hash-linked sidecar. Verifies clean before finishing.
"""

from __future__ import annotations

# The direct script entry point adds the repository root before importing the
# local package, so this import block intentionally follows executable setup.
# ruff: noqa: E402
import hashlib
import pathlib
import pickle
import sys
import time

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import yaml
from modelmeta import MetaWriter
from modelmeta.verify import verify_checkpoint
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


def main() -> None:
    rng = np.random.default_rng(7)
    hours = rng.uniform(0, 10, size=300)
    score = 5 * hours + 50 + rng.normal(0, 4, size=300)
    X, y = hours.reshape(-1, 1), score
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)

    t0 = time.monotonic()
    reg = HistGradientBoostingRegressor(max_iter=200, random_state=42)
    reg.fit(Xtr, ytr)
    pred = reg.predict(Xte)
    r2 = float(r2_score(yte, pred))
    rmse = float(mean_squared_error(yte, pred) ** 0.5)
    train_secs = time.monotonic() - t0

    out = REPO_ROOT / "demo" / "examples"
    out.mkdir(parents=True, exist_ok=True)
    ckpt = out / "score_model.pkl"
    with open(ckpt, "wb") as handle:
        pickle.dump(reg, handle)

    ds_digest = "sha256:" + hashlib.sha256(np.ascontiguousarray(X).tobytes()).hexdigest()
    writer = MetaWriter(
        run_context={
            "run_id": "demo_study_001",
            "dataset": {
                "name": "study-hours-vs-score",
                "version": "synthetic-v1",
                "digest": ds_digest,
                "rows": int(X.shape[0]),
            },
        }
    )
    writer._run_start_monotonic = time.monotonic() - train_secs
    sidecar = writer.on_checkpoint_saved(
        ckpt,
        training_state={"global_step": 200, "loss": rmse, "epoch": 1},
        compute_state={"framework": "sklearn", "accelerator_count": 1, "accelerator_type": "cpu"},
    )
    result = verify_checkpoint(str(ckpt))
    with open(sidecar) as handle:
        meta = yaml.safe_load(handle)
    print(f"sidecar: {sidecar}")
    print(f"verify: {result.status} ({result.exit_code})")
    print(f"r2: {r2:.4f} rmse: {rmse:.4f} train_secs: {train_secs:.2f}")
    print(f"sha: {meta['checkpoint']['sha256'][:12]} size: {meta['checkpoint']['size_bytes']}")
    if result.status != "match":
        raise SystemExit("example failed verification")


if __name__ == "__main__":
    main()
