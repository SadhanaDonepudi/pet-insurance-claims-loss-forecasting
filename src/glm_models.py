"""Frequency (Poisson) and severity (Gamma) GLMs via statsmodels.

* Frequency: claim counts aggregated to the policy level, Poisson GLM with
  log link and ``log(in_window_exposure_years)`` offset.
* Severity: individual claim costs, Gamma GLM with log link.

Both models are fit on the synthetic data produced by ``generate.py``.
Reported fit statistic: deviance explained
``1 - residual_deviance / null_deviance`` (pseudo-R^2).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm


def _design_matrix(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    X = pd.get_dummies(df[columns], drop_first=True, dtype=float)
    X = sm.add_constant(X, has_constant="add")
    return X.astype(float)


# NOTE on collinearity (both deliberate):
# * `species` is excluded: it is an exact function of `breed`.
# * `territory` (= region x density) is represented via `state` + `density`:
#   region is an exact function of state, so state + territory dummies are
#   rank-deficient (sum_d territory_{r,d} = sum_{s in r} state_s per region).
#   state + density spans the same information without the deficiency.
FREQ_COLS = ["breed", "age_bin", "state", "density", "brand"]
SEV_COLS = ["condition", "breed", "age_bin", "state", "claim_year"]


def fit_frequency_glm(policies: pd.DataFrame,
                      claims: pd.DataFrame) -> dict:
    """Poisson GLM of claim counts per policy with exposure offset."""
    counts = claims.groupby("policy_id").size().rename("n_claims")
    df = policies.set_index("policy_id")[["in_window_exposure_years"] + FREQ_COLS].copy()
    df["n_claims"] = counts.reindex(df.index).fillna(0).astype(int).to_numpy()
    df = df[df["in_window_exposure_years"] > 0].copy()

    X = _design_matrix(df, FREQ_COLS)
    offset = np.log(df["in_window_exposure_years"].to_numpy())
    model = sm.GLM(df["n_claims"].to_numpy(), X,
                   family=sm.families.Poisson(),
                   offset=offset).fit(cov_type="HC0")

    dev_explained = 1.0 - model.deviance / model.null_deviance
    return {
        "model": "Poisson frequency GLM (log link, log-exposure offset)",
        "n_policies": int(len(df)),
        "n_claims": int(df["n_claims"].sum()),
        "converged": bool(model.converged),
        "deviance_explained": float(dev_explained),
        "null_deviance": float(model.null_deviance),
        "resid_deviance": float(model.deviance),
        "aic": float(model.aic),
        "params": model.params.round(6).to_dict(),
    }


def fit_severity_glm(claims: pd.DataFrame) -> dict:
    """Gamma GLM of claim cost with log link."""
    df = claims[SEV_COLS + ["claim_cost"]].copy()
    X = _design_matrix(df, SEV_COLS)
    model = sm.GLM(df["claim_cost"].to_numpy(), X,
                   family=sm.families.Gamma(link=sm.families.links.Log())
                   ).fit(cov_type="HC0")

    dev_explained = 1.0 - model.deviance / model.null_deviance
    return {
        "model": "Gamma severity GLM (log link)",
        "n_claims": int(len(df)),
        "converged": bool(model.converged),
        "deviance_explained": float(dev_explained),
        "null_deviance": float(model.null_deviance),
        "resid_deviance": float(model.deviance),
        "aic": float(model.aic),
        "mean_cost": float(df["claim_cost"].mean()),
        "params": model.params.round(6).to_dict(),
    }
