# Social feature audit — VADER is noise, not signal

**Date:** 2026-07-22

**Files changed:**
- `docs/research/feature-engineering.md` — added audit notice (§10 header), updated NLP recommendations (§10.4), added gap analysis to §10.6, added §10.10 post-mortem, updated Phase 5 status, revised implementation order

---

## What

Audited social feature importance after 3 days of production data collection. Social features (`social_mentions_1d`, `social_mentions_7d`, `social_mention_velocity`, `social_sentiment_7d`, `social_score_7d`) do not rank in the top 20 by gain importance for any horizon out of 122 total features. They contribute approximately zero marginal predictive value.

## Root cause

VADER is a general-purpose 2014 lexicon. CS2 market jargon ("BFK CW MW low float", "blue gem T1 pattern", "sleeping") scores as neutral. The 5 features exist in the model but the model correctly ignores them.

## Implications

- Adding more source volume (Twitter, Discord, YouTube) is wasted effort — the bottleneck is NLP accuracy, not data volume.
- The design rationale in the original changelog (2026-07-19) argued VADER was sufficient because "the real signal is mention velocity, not nuanced sentiment." Feature importance disproves this — mention velocity ranks outside top 20 too.
- The social_aggregates table (planned in research doc §10.3) is not needed. On-the-fly aggregation works fine.

## Recommendation

1. **Replace VADER with ModernFinBERT** (ONNX INT8, ~10ms/post, ~88% acc) — the single fix that unblocks all social value.
2. **Add r/GlobalOffensive** (50 posts/run, score filter >10) — 5.4M sub reach, zero-effort line change.
3. **Add 1d/3d/14d/30d rolling windows** — captures different time scales.
4. **Add sentiment-price divergence** — the actual leading indicator signal.
5. **Skip Twitter, Discord, YouTube** — triple maintenance, zero marginal value until NLP is fixed.

## Expected impact after fixes

Social features reach rank ~30-50 (up from outside top 20). +1-3pp directional accuracy for the ~20% of items with active social discussion. Social features will never dominate (80% of items have zero mentions on any given day), but they stop being dead weight.

See `docs/research/feature-engineering.md` §10.10 for the full post-mortem.
