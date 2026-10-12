"""12-month loss-ratio forecasting.

Builds the monthly loss-ratio series (incurred losses / earned premium),
fits Holt-Winters (additive trend + additive seasonality) on all months
except the final 12, forecasts the 12 holdout months, and reports the
MEASURED forecast error (MAPE) against actual holdout loss ratios.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from . import config as C


def monthly_loss_ratio(policies: pd.DataFrame,
                       claims: pd.DataFrame) -> pd.DataFrame:
    """Monthly earned premium, incurred losses and loss ratio, 2019-01..2026-12."""
    months = pd.period_range(C.WINDOW_START, C.WINDOW_END, freq="M")
    monthly = pd.DataFrame({"month": months})

    # Earned premium: spread each policy's earned premium uniformly over its
    # active in-window months (approximation consistent with the generator).
    window_start = pd.Timestamp(C.WINDOW_START)
    window_end = pd.Timestamp(C.WINDOW_END)
    eff = policies["effective_date"].clip(lower=window_start, upper=window_end)
    exp_days = (policies["exposure_years"] * 365.25).round().astype(int)
    end = (policies["effective_date"] + pd.to_timedelta(exp_days, unit="D")
           ).clip(lower=window_start, upper=window_end)
    eff_p = eff.dt.to_period("M").astype(str)
    end_p = end.dt.to_period("M").astype(str)

    earned = np.zeros(len(months))
    month_str = months.astype(str).to_numpy()
    # vectorized via searchsorted on sorted month index
    m_idx = {m: i for i, m in enumerate(month_str)}
    s_idx = np.array([m_idx[m] for m in eff_p])
    e_idx = np.array([m_idx[m] for m in end_p])
    per_month = (policies["earned_premium"] / (e_idx - s_idx + 1)).to_numpy()
    # accumulate with bincount trick: add per_month at s_idx, subtract after e_idx
    delta = np.zeros(len(months) + 1)
    np.add.at(delta, s_idx, per_month)
    np.add.at(delta, e_idx + 1, -per_month)
    earned = np.cumsum(delta)[:-1]

    incurred = (claims.assign(m=claims["claim_date"].dt.to_period("M").astype(str))
                      .groupby("m")["claim_cost"].sum()
                      .reindex(month_str, fill_value=0.0).to_numpy())
    n_claims = (claims.assign(m=claims["claim_date"].dt.to_period("M").astype(str))
                      .groupby("m").size()
                      .reindex(month_str, fill_value=0).to_numpy())

    monthly["earned_premium"] = earned
    monthly["incurred_losses"] = incurred
    monthly["n_claims"] = n_claims
    monthly["loss_ratio"] = incurred / np.maximum(earned, 1e-9)
    monthly["date"] = months.to_timestamp()
    return monthly


def forecast_loss_ratio(monthly: pd.DataFrame,
                        n_holdout: int = C.N_HOLDOUT_MONTHS) -> dict:
    """Holt-Winters forecast of the last ``n_holdout`` months; MEASURED MAPE."""
    y = monthly["loss_ratio"].to_numpy(dtype=float)
    train, actual = y[:-n_holdout], y[-n_holdout:]

    fit = ExponentialSmoothing(train, trend="add", seasonal="add",
                               seasonal_periods=12,
                               initialization_method="estimated").fit()
    fc = np.asarray(fit.forecast(n_holdout))
    ape = np.abs(fc - actual) / np.maximum(actual, 1e-9)

    # Seasonal-naive baseline for context
    naive = train[-12:]
    naive_ape = np.abs(naive - actual) / np.maximum(actual, 1e-9)

    return {
        "model": C.FORECAST_MODEL,
        "n_train_months": int(len(train)),
        "n_holdout_months": int(n_holdout),
        "forecast": [float(v) for v in fc],
        "actual": [float(v) for v in actual],
        "holdout_months": monthly["month"].astype(str).to_list()[-n_holdout:],
        "mape": float(np.mean(ape)),
        "mae": float(np.mean(np.abs(fc - actual))),
        "mean_holdout_lr": float(np.mean(actual)),
        "baseline_seasonal_naive_mape": float(np.mean(naive_ape)),
        "max_ape": float(np.max(ape)),
    }
