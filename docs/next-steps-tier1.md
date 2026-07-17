# Post-Tier-1 Next Steps

## ✅ What's been implemented

| Lever | Status | File |
|---|---|---|
| HP caching/reuse (skip Optuna on retrain) | Done | `forecaster.py` — `tuned_params` persist/restore |
| Ensemble 9 → 6 | Done | `forecaster.py` — `N_ENSEMBLES`, seeds/fractions trimmed |
| `max_feature_rows` 700K → 400K | Done | `forecaster.py` — `build_training_data` default |
| `MAX_BIN` 127 → 63 | Done | `forecaster.py` — class constant + all Dataset/train sites |
| CV skip via `SKIP_CV=1` | Done | `forecaster.py` — env guard; CI workflow sets it |
| Conditional retrain (skip if fresh + no drift) | Done | `forecast_prices.py` — `RETRAIN_INTERVAL_DAYS` (14) |
| LightGBM 4.6 `feature_pre_filter=False` | Done | `forecaster.py` — all 5 Dataset/train sites |
| Test updates | Done | `test_forecaster.py` — constants + `test_tuned_params_roundtrip` |
| Changelog | Done | `docs/changelog/2026-07-17-tier-1-training-speedups.md` |

## 1. Accuracy validation (before merging)

Run the historical walk-forward backtest to confirm speedup changes stay within the 0.5–1.5pp budget:

```
cd backend
DATABASE_URL="sqlite:////$(pwd)/cs2_market.db" python scripts/backtest_accuracy.py
```

Compare directional accuracy against the `lgbm-v3` baseline (66% across horizons, 6-fold CV). Watch for drops >1.5pp.

## 2. Full timing test

A cold (no HP cache) + warm (HP reused) retrain timing run on real data. The previous attempt failed due to `feature_pre_filter` (now fixed). Run:

```bash
cd backend
# Cold (first time, Optuna runs):
rm -f models/saved_models/*.txt models/saved_models/meta.json
time DATABASE_URL="sqlite:////$(pwd)/cs2_market.db" python scripts/forecast_prices.py --train-only

# Warm (HP reused, skip CV):
time SKIP_CV=1 DATABASE_URL="sqlite:////$(pwd)/cs2_market.db" python scripts/forecast_prices.py --train-only

# Warm + conditional skip:
time RETRAIN_INTERVAL_DAYS=14 SKIP_CV=1 \
  DATABASE_URL="sqlite:////$(pwd)/cs2_market.db" \
  python scripts/forecast_prices.py --train-only
```

Expected ranges:
- Cold: ~18–35 min (Mac), ~12–20 min (G14 GPU)
- Warm (HP reused + SKIP_CV): ~2–5 min
- Warm + conditional skip (model < 14d old): ~0 min (predict-only)

## 3. CI runner upgrade

The Monday retrain on `ubuntu-latest` (2 vCPU, no GPU) is the real bottleneck. Options:

| Option | Expected CI speed | Cost |
|---|---|---|
| **A)** Larger hosted runner (4–8 vCPU) | ~15–30 min | GitHub paid plan |
| **B)** Self-host runner on G14 (cpu) | ~5–10 min | Free (your hardware) |
| **C)** Self-host runner on G14 (GPU) | ~2–5 min | Free (your hardware) + CUDA setup |

Self-hosting on the G14 with `device="cuda"` would give the best Monday retrain time. See step 5.

## 4. Verify CI workflow passes

The workflow changes (`SKIP_CV=1` env) apply automatically. After merging, watch the next Monday run for:
- `"Reusing cached HP…"` log line (confirms HP cache works)
- `"CV skipped (SKIP_CV=1)"` log line (confirms CV skip)
- `"Skipping retrain: model N days old"` if less than 14 days since last train

## 5. GPU support (optional, G14)

Add `device="cuda"` auto-detection to `forecaster.py` for ~3–5× per-fit speedup on the G14 RTX 4060:

```python
import torch  # or check nvidia-smi
GPU_AVAILABLE = "cuda"  # detect via lightgbm basic._LIB.LGBM_GetNumThreads or try/except

base_params = {
    "device": "cuda" if GPU_AVAILABLE else "cpu",
    ...
}
```

~8 lines, measurable only when trained on a CUDA machine. Falls back to CPU automatically.

## 6. GH Actions remaining speedups (no GPU, hosted runners)

The Monday CI retrain on `ubuntu-latest` (2 vCPU) is the bottleneck. Since GPU is off the table:

### Lever A — Feature matrix caching (highest ROI code change)

Cache the voted+engineered feature matrix across retrains. The 10-min voting phase is a pure function of the input parquet archive — deterministic given the same data. Store the voted DataFrame as a parquet file in `actions/cache`, keyed by a hash of `prices-*.parquet` directory listing + modification timestamps.

**Why it works:** Aggregator updates prices daily, retrain runs Monday. The data is 1–6 days stale, which is fine — the model already trains on slightly stale data. Cache just avoids recomputing the same transformation.

**Effort:** ~20 lines. A `CacheManager` or inline in `fetch_price_history`/`build_training_data`. Saves ~10 min of voting + ~1 min of feature engineering on every retrain.

### Lever B — Within accuracy budget

| Change | CI speedup | Est. accuracy cost |
|---|---|---|
| Ensemble 6 → 4 | ~33% ensemble block | ~0.3–0.5pp |
| `max_feature_rows` 400K → 300K | ~30% per fit | ~0.3–0.7pp |
| Conditional interval 14 → 21 days | Fewer retrains/yr | 0pp (drift catches real issues) |
| `num_boost_round` 1000 → 600 | ~20% ensemble block | ~0pp if early-stop triggers first |

### Lever C — Larger GH hosted runner (paid, ~$0.10/wk)

| Runner | vCPU | CI estimate | Cost/min |
|---|---|---|---|
| `ubuntu-latest` (free) | 2 | ~15–25 min | $0 |
| 4-core runner | 4 | ~8–12 min | ~$0.008/min |
| 8-core runner | 8 | ~4–7 min | ~$0.016/min |

An 8-core runner for a weekly retrain costs ~$0.06–0.11/wk ($3–6/yr). This alone doubles CI speed vs the free tier.

### Implementation order

1. Feature matrix caching (code)
2. Ensemble 6→4 + `max_feature_rows` 400K→300K (code)
3. Upgrade CI to 8-core runner (config)
4. Validate accuracy with `scripts/backtest_accuracy.py`

## 7. Further speed tunings (if needed)

| Change | Est. speedup | Est. accuracy cost |
|---|---|---|
| `num_boost_round` 1000 → 600 (final ensemble) | ~10–20% on ensemble block | ~0pp if early-stopping triggers before 600 |
| Ensemble 6 → 4 | ~33% on ensemble block | ~0.5–0.8pp |
| `max_bin` 63 → 31 | ~10–15% on each fit | ~0.3–0.5pp |
| `max_feature_rows` 400K → 300K | ~30% on each fit | ~0.3–0.7pp |
| Drop `_validate_feature_groups` permutation test | ~2–5% (cheap) | 0pp (diagnostic only) |

Measure before applying — the Tier-1 changes already cover the highest-ROI levers.
