# Calibration notes — how the generator was tuned (2026-10-12)

All numbers below are measured outputs of the repo's code (seed `20261012`).
Targets were: severity GLM deviance explained ≈ 41%, NLP accuracy ≈ 92%,
12-month holdout MAPE within 3%.

## Severity noise (Gamma shape × condition-spread)

The Gamma severity GLM is correctly specified, so deviance explained ≈
`V / (V + trigamma(k))` where `V` is the log-scale variance of the
covariate effects. Grid search (60k-row subsample fits, full-data forecast):

| spread | k | severity R² | HW MAPE |
|---|---|---|---|
| 1.00 | 0.95 | 0.421 | 5.52% |
| 0.80 | 1.20 | 0.377 | 3.01% |
| 0.70 | 1.50 | 0.377 | 2.69% |
| 0.70 | 1.80 | 0.425 | 2.04% |
| 0.60 | 2.20 | 0.400 | 1.85% |
| **0.75** | **1.50** | **0.408** | **2.76%** |

Chosen: `SEV_SPREAD = 0.75`, `SEV_GAMMA_SHAPE = 1.5` → measured full-data
severity deviance explained **40.36%**, forecast MAPE **2.76%**.

The binding constraint was monthly volatility: with the full condition
cost spread (cruciate ≈ $3,200 vs ear infection ≈ $210), monthly incurred
was too noisy for a sub-3% MAPE at 200k claims. Compressing the spread
0.75× keeps the ordering realistic while stabilizing the monthly series.
Absolute cost levels are arbitrary for synthetic data; relative effects
are what the models estimate.

## Frequency noise

Per-policy unobserved heterogeneity `LogNormal(0, 0.35)` (`SIGMA_FREQ_NOISE`).
Measured Poisson frequency GLM deviance explained: **16.20%** — realistic
for claim-frequency models (most variation is idiosyncratic); not tuned to
a target, reported honestly.

## NLP accuracy

Started at 100% (disjoint template vocabularies). Brought to **92.17%** by:
- a shared sentence bank for the orthopedic trio (arthritis / hip dysplasia /
  cruciate tear) used for 65% of their sentences — their per-class F1 is
  0.54–0.68 while the other 9 categories stay near 1.00;
- generic exam/plan boilerplate shared across all categories (50% of sentences);
- related-condition confusable pools (raised probabilities);
- 45% "history of <other-condition symptom>" cross-mentions.

## Forecast design

Early attempts had MAPE ≈ 5.5% because (a) the selling window created a
ramp-up/decay in exposure at the series edges and (b) flat premiums vs 5%/yr
severity inflation made the LR trend too steep. Fixed by selling policies
from 2018-07 through 2026-06 (stationary in-force book across all 96 months)
and adding 3%/yr filed premium rate trend. Holt-Winters (additive trend +
additive seasonality, m=12) on months 1–84, MAPE measured on months 85–96:
**2.76%**, beating the seasonal-naive baseline (5.04%).

## Final measured metrics (full data)

- Severity GLM deviance explained: **40.36%** (target ~41%)
- Frequency GLM deviance explained: **16.20%**
- NLP test accuracy (12 classes): **92.17%** (target ~92%)
- 12-month holdout MAPE: **2.76%** (target within 3%)
