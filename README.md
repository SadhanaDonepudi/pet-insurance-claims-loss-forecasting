# Pet Insurance Claims Analytics & Loss Ratio Forecasting

> **All data in this project is 100% synthetic**, generated in code with a
> fixed seed. No real policyholders, pets, insurers, or medical records are
> represented. Every number in this README is a measured output of the
> repo's own pipeline (`python -m src.pipeline` → `outputs/metrics.json`).

An end-to-end actuarial analytics project on synthetic pet-insurance data:
a **Poisson frequency GLM** and **Gamma severity GLM** (statsmodels), an
**NLP claim-note classifier** (TF-IDF + logistic regression, 12 condition
categories), a **12-month loss-ratio forecast** (Holt-Winters), SQL KPI
mart (SQLite), and a Tableau dashboard spec with rendered static charts.

## Measured results

<!-- METRICS:START -->
| Metric | Measured value |
|---|---|
| Synthetic claims | 200,000 |
| Synthetic policies | 120,000 |
| Synthetic claim notes | 30,000 |
| Condition categories | 12 |
| Book loss ratio | 68.0% |
| Mean claim severity | $705 |
| Gamma severity GLM — deviance explained | 40.36% |
| Poisson frequency GLM — deviance explained | 16.20% |
| NLP note classifier — test accuracy (12 classes) | 92.17% |
| 12-month loss-ratio forecast — holdout MAPE | 2.76% |
| Seasonal-naive baseline — holdout MAPE | 5.04% |
<!-- METRICS:END -->

*Table auto-patched by `src/pipeline.py` from `outputs/metrics.json`.*

**Headline findings (measured):**
- The Gamma severity GLM explains **~41% of deviance** — condition,
  breed size, age, state cost level, species, and vet-cost inflation are
  strong severity drivers; the rest is idiosyncratic claim noise.
- The Poisson frequency GLM explains **~16% of deviance** — typical for
  claim frequency, where most variation is random.
- The note classifier hits **~92% accuracy**; errors concentrate in the
  orthopedic trio (arthritis / hip dysplasia / cruciate tear), whose notes
  read almost identically — just like real clinical text.
- The 12-month holdout loss-ratio forecast achieves **MAPE within 3%**,
  roughly halving the seasonal-naive baseline error.

## Repository structure

```
├── src/
│   ├── config.py          # seeds, exact counts, rating factors, 12 categories
│   ├── generate.py        # vectorized synthetic data generator
│   ├── note_templates.py  # templated clinical-note vocabulary
│   ├── glm_models.py      # Poisson frequency + Gamma severity GLMs
│   ├── nlp_classify.py    # TF-IDF + logistic regression classifier
│   ├── forecast.py        # monthly loss ratio + Holt-Winters forecast
│   ├── charts.py          # matplotlib chart rendering (PNG)
│   ├── build_db.py        # SQLite mart builder
│   ├── run_kpis.py        # executes sql/kpi_*.sql → CSV
│   └── pipeline.py        # end-to-end orchestrator
├── sql/
│   ├── schema.sql         # mart DDL (policies, claims, claim_notes, policy_months)
│   └── kpi_0{1..5}_*.sql # monthly LR, frequency/severity, brand×state,
│                         #   condition mix, territory scorecard
├── outputs/
│   ├── metrics.json       # every measured number (pipeline output)
│   ├── charts/*.png       # rendered charts (Tableau stand-ins)
│   ├── kpis/*.csv         # SQL KPI results
│   └── samples/*.csv      # 2,000-row extracts (full data is regenerated)
├── tests/test_pipeline.py # pytest suite
├── data_dictionary.md
├── architecture.md
├── tableau_dashboard_spec.md
└── docs/calibration.md    # how the generator was tuned to its targets
```

## Quickstart

```bash
pip install -r requirements.txt

# Full pipeline: generate 200k claims + 30k notes, fit GLMs, classify,
# forecast, build SQLite mart, run KPIs, render charts (~1-2 min)
python -m src.pipeline

# Outputs land in outputs/; full-size CSVs/SQLite go to a temp dir (not committed)

# Tests
pytest tests/ -q
```

## Data

| Table | Rows (exact) | Grain |
|---|---|---|
| `policies` | 120,000 | one row per synthetic policy |
| `claims` | **200,000** | one row per synthetic claim |
| `claim_notes` | **30,000** | one row per synthetic note, **12** categories |

See `data_dictionary.md` for every column. The 12 condition categories are
fixed in `src/config.py` and asserted by the test suite.

## Models

- **Frequency:** Poisson GLM, log link, `log(in_window_exposure_years)`
  offset; covariates breed, age band, state, density, brand.
- **Severity:** Gamma GLM, log link; covariates condition, breed, age band,
  state, claim year.
- **NLP:** TF-IDF (word 1–2 grams, 8k features) → multinomial logistic
  regression; stratified 80/20 split.
- **Forecast:** monthly loss ratio (incurred / earned), Holt-Winters
  additive trend + seasonality (m=12); trained on months 1–84, MAPE
  measured on the final 12 holdout months.

Design notes (collinearity handling, calibration grid) live in
`architecture.md` and `docs/calibration.md`.

## Tableau

`tableau_dashboard_spec.md` is the build blueprint: data model,
calculated fields (loss ratio, frequency per 1k EY, YoY Δ), three
dashboards (Executive LR overview; Operations drill-down
brand → state → territory → breed; Actuarial deep dive), and the mapping
from each `outputs/charts/*.png` to its dashboard equivalent.

## Limitations

- Synthetic by design: relationships are simplified versions of real
  insurance dynamics; absolute dollar levels are arbitrary.
- The generator's "truth" is known, so GLM fit quality partly reflects a
  correctly-specified model — the honest signal is in the *measured*
  metrics and the documented calibration, not in beating a benchmark.

## License

MIT — see `LICENSE`.
