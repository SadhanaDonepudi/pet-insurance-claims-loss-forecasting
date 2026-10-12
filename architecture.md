# Architecture — Pet Insurance Claims Analytics & Loss Ratio Forecasting

> All data is synthetic (fixed seed `20261012`). This document describes the
> pipeline, not a production system.

## Pipeline overview

```
┌─────────────────────────┐
│  src/config.py          │  seeds, exact counts, rating factors,
│                         │  condition list, tuning knobs
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│  src/generate.py        │  120k policies → policy-month grid
│  (vectorized numpy)     │  → multinomial assignment of EXACTLY 200k claims
│                         │  → breed/age-aware condition mix (Gumbel-max)
│                         │  → Gamma severity → premiums solved to 68% LR
│                         │  → 30k templated claim notes (12 categories)
└───────────┬─────────────┘
            ▼
┌──────────────────────────────────────────────────────────┐
│  Modeling (all measured, reported honestly)              │
│  src/glm_models.py   Poisson frequency GLM (log-exposure │
│                      offset) + Gamma severity GLM        │
│  src/nlp_classify.py TF-IDF (1–2g) + logistic regression │
│                      on 30k notes → 12 categories        │
│  src/forecast.py     monthly loss ratio → Holt-Winters   │
│                      → 12-month holdout forecast + MAPE   │
└───────────┬──────────────────────────────────────────────┘
            ▼
┌─────────────────────────┐
│  SQLite mart            │  src/build_db.py → policies/claims/
│  sql/*.sql KPIs         │  claim_notes/policy_months; src/run_kpis.py
│                         │  runs 5 KPI scripts → outputs/kpis/*.csv
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│  outputs/               │  metrics.json (every README number),
│                         │  charts/*.png (matplotlib), samples (2k rows)
└─────────────────────────┘
```

Run it: `python -m src.pipeline` (≈1–2 min). Full-size CSVs/SQLite go to a
temp artifact dir and are **not** committed; committed samples are 2,000-row
extracts. Tests: `pytest tests/`.

## Statistical design notes

- **Claim counts.** Each policy-month has a Poisson-style rate
  `λ = base × breed × age × territory × state × brand × species ×
  seasonality × trend × LogNormal(0, σ)` with `σ = 0.35` of *unobserved*
  heterogeneity. The 200,000 claims are assigned by multinomial sampling
  over the policy-month grid — the exact conditional distribution of
  independent Poissons given their sum — so the frequency GLM is fit on
  data that follows its assumed process up to the unobserved term.
- **Severity.** `Gamma(shape=1.5, mean=μ)` with
  `log μ = condition + breed size + age + state + species + 5%/yr inflation`
  (condition spread compressed 0.75×; see `docs/calibration.md`). The Gamma
  GLM with log link is therefore correctly specified; the noise level was
  tuned so deviance explained lands near 41%.
- **Premiums.** Rating-factor premiums × 3%/yr filed rate trend, then scaled
  so the book-average loss ratio equals 68%. Brand rating differs
  (PawGuard underprices → structurally higher LR), which the Tableau
  drill-down surfaces.
- **Notes.** Templated clinical text. The orthopedic trio (arthritis / hip
  dysplasia / cruciate tear) shares most of its sentence bank — as in real
  notes — which is where the classifier's errors concentrate. Notes also
  carry generic boilerplate, related-condition vocabulary, and "history of
  …" cross-mentions.
- **Forecast.** Monthly loss ratio = incurred / earned. Holt-Winters
  (additive trend + additive seasonality, m=12) trained on months 1–84,
  evaluated on the final 12 months. Seasonal-naive baseline included for
  context.

## Why the GLM excludes some columns

- `species` is an exact function of `breed` → excluded (rank deficiency).
- `territory` = region × density, and region is an exact function of
  `state` → `state` + `territory` dummies are rank-deficient (3 redundant
  dimensions). The frequency GLM uses `state` + `density` instead, which
  spans the same information.

## Reproducibility

Single seed (`SEED = 20261012`) drives one `numpy.random.Generator` stream
consumed in a fixed order. Re-running the generator yields byte-identical
frames (asserted by `tests/test_pipeline.py::test_reproducibility`).
