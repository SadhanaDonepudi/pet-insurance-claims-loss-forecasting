# Tableau Dashboard Spec — Pet Insurance Claims Analytics

> Build blueprint for a Tableau workbook over the synthetic mart
> (`policies`, `claims`, `claim_notes`, `policy_months`). Tableau Desktop
> cannot run in this environment, so the spec below is the implementation
> plan; `outputs/charts/*.png` are the static stand-ins rendered by
> `src/charts.py` from the same data.

## 1. Data source & model

- **Connection:** SQLite `pet_insurance.sqlite` (built by
  `python -m src.build_db`), or the CSV extracts.
- **Relationships (logical layer):**
  - `claims` → `policies` on `policy_id` (many-to-one)
  - `claim_notes` → `claims` on `claim_id` (many-to-one)
  - `policy_months` → `policies` on `policy_id` (many-to-one)
- **Date handling:** `claims.claim_date` (Date). `policy_months.month`
  (`YYYY-MM`) parsed to month-date for the earned-premium trend.
- **Data source filter:** none (full synthetic book). Extract recommended
  for the 200k-claim fact.

## 2. Calculated fields

| Field | Formula |
|---|---|
| `Loss Ratio` | `SUM([claim_cost]) / SUM([earned_premium])` — note: earned premium lives at policy grain; use the `policy_months` blend or a FIXED LOD: `{FIXED [month], [brand] : SUM([earned_premium])}` |
| `Frequency per 1k EY` | `COUNT([claim_id]) / SUM([in_window_exposure_years]) * 1000` |
| `Avg Severity` | `AVG([claim_cost])` |
| `Loss Ratio YoY Δ` | `ZN([Loss Ratio]) - LOOKUP(ZN([Loss Ratio]), -12)` |
| `Condition Share of Losses` | `SUM([claim_cost]) / TOTAL(SUM([claim_cost]))` |
| `LR vs Plan (68%)` | `[Loss Ratio] - 0.68` |
| `Forecast MAPE` | (static text from `outputs/metrics.json`: 2.76%) |

## 3. Dashboard layouts

### D1 — Executive Loss Ratio Overview
- **KPI tiles (top):** Book loss ratio, YoY Δ, earned premium, incurred
  losses, forecast MAPE. Conditional red/amber/green on `LR vs Plan`.
- **Main:** monthly loss-ratio line (actual) with the 12-month Holt-Winters
  forecast overlaid as a dashed line + holdout actuals
  (see `outputs/charts/loss_ratio_forecast.png`).
- **Filters:** brand, state, year. **Drill-down:** click a brand → filters
  D2/D3 to that brand (dashboard action).

### D2 — Claims Operations (drill-down: brand → state → territory → breed)
- **Hierarchy drill:** `brand` → `state` → `territory` → `breed` on rows;
  expanding a brand reveals its states, then territories, then breeds.
- **Measures:** loss ratio (bar, color by `LR vs Plan`), frequency per 1k
  EY, avg severity, claim count.
- **Heat view:** state × brand loss-ratio matrix
  (see `outputs/charts/loss_ratio_brand_state.png`).
- **Top conditions:** bar of claim counts + avg severity dual axis
  (see `outputs/charts/top_conditions.png`).

### D3 — Actuarial Deep Dive
- **GLM actual-vs-expected:** decile-of-predicted-severity calibration
  scatter (see `outputs/charts/severity_calibration.png`); frequency
  actual-vs-expected by breed (see `outputs/charts/frequency_by_breed.png`).
- **NLP panel:** confusion-matrix heatmap of the 12 note categories with
  accuracy annotation (see `outputs/charts/nlp_confusion_matrix.png`).
- **Volume:** monthly claim counts + earned premium dual axis
  (see `outputs/charts/claim_volume_trend.png`).

## 4. Interactions

- Dashboard actions: D1 brand select → filter D2, D3. D2 hierarchy
  expand/collapse. Hover tooltips show policies, exposure-years, and both
  frequency and severity.
- Parameters: `Plan LR` (default 0.68), `Forecast horizon` (default 12).

## 5. Static stand-ins (this repo)

| Chart file | Tableau equivalent |
|---|---|
| `loss_ratio_forecast.png` | D1 forecast overlay |
| `severity_calibration.png` | D3 GLM calibration |
| `nlp_confusion_matrix.png` | D3 NLP panel |
| `top_conditions.png` | D2 condition mix |
| `frequency_by_breed.png` | D3 frequency actual-vs-expected |
| `loss_ratio_brand_state.png` | D2 state × brand heat |
| `claim_volume_trend.png` | D3 volume trend |
