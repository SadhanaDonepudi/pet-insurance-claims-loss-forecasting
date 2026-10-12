"""Pytest suite for the pet-insurance claims project.

Covers: exact counts (200,000 claims / 30,000 notes / 12 categories),
GLM convergence, reproducibility, and forecast-error computation.
Heavier tests share module-scoped fixtures so the full data is generated
once (~10 s).
"""

import json
import os

import numpy as np
import pandas as pd
import pytest

from src import generate as G
from src import glm_models as M
from src import nlp_classify as N
from src import forecast as F
from src import config as C

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED_CATEGORIES = set(C.CONDITION_NAMES)


@pytest.fixture(scope="module")
def data():
    return G.generate_all(seed=C.SEED)


# ---------------------------------------------------------------- counts ---
def test_claim_count_exact(data):
    assert len(data["claims"]) == 200_000


def test_policy_count_exact(data):
    assert len(data["policies"]) == 120_000


def test_note_count_exact(data):
    assert len(data["notes"]) == 30_000


def test_twelve_categories_claims(data):
    assert set(data["claims"]["condition"].unique()) == EXPECTED_CATEGORIES


def test_twelve_categories_notes(data):
    assert set(data["notes"]["category"].unique()) == EXPECTED_CATEGORIES
    assert len(EXPECTED_CATEGORIES) == 12


def test_note_claim_link(data):
    assert set(data["notes"]["claim_id"]).issubset(set(data["claims"]["claim_id"]))
    assert data["claims"]["has_note"].sum() == len(data["notes"])


def test_claim_dates_in_window(data):
    lo, hi = pd.Timestamp(C.WINDOW_START), pd.Timestamp(C.WINDOW_END)
    assert data["claims"]["claim_date"].min() >= lo
    assert data["claims"]["claim_date"].max() <= hi


def test_claim_costs_positive(data):
    assert (data["claims"]["claim_cost"] > 0).all()


# ------------------------------------------------------------------- GLMs ---
@pytest.fixture(scope="module")
def sev_fit(data):
    return M.fit_severity_glm(data["claims"])


@pytest.fixture(scope="module")
def freq_fit(data):
    return M.fit_frequency_glm(data["policies"], data["claims"])


def test_severity_glm_converged(sev_fit):
    assert sev_fit["converged"] is True
    assert 0.0 < sev_fit["deviance_explained"] < 1.0
    assert sev_fit["n_claims"] == 200_000


def test_frequency_glm_converged(freq_fit):
    assert freq_fit["converged"] is True
    assert 0.0 < freq_fit["deviance_explained"] < 1.0


# ------------------------------------------------------- reproducibility ---
def test_reproducibility_of_counts():
    """Same seed -> identical frames (counts and checksums)."""
    a = G.generate_all(seed=C.SEED)
    b = G.generate_all(seed=C.SEED)
    for key in ("policies", "claims", "notes"):
        assert len(a[key]) == len(b[key])
        assert a[key].equals(b[key]), f"{key} not reproducible"
    assert (a["claims"]["claim_cost"].sum()
            == b["claims"]["claim_cost"].sum())


def test_different_seed_differs():
    a = G.generate_policies(G.make_rng(C.SEED), n=1000)
    b = G.generate_policies(G.make_rng(C.SEED + 1), n=1000)
    assert not a.equals(b)


# ------------------------------------------------------------------- NLP ---
@pytest.fixture(scope="module")
def nlp_result(data):
    return N.train_and_evaluate(data["notes"])


def test_nlp_accuracy_sane(nlp_result):
    assert nlp_result["n_categories"] == 12
    assert nlp_result["n_notes"] == 30_000
    assert 0.85 <= nlp_result["accuracy"] <= 1.0
    assert nlp_result["categories"] == sorted(EXPECTED_CATEGORIES)


# --------------------------------------------------------------- forecast ---
def test_forecast_error_computation():
    """MAPE is computed correctly on a controlled series."""
    rng = np.random.default_rng(0)
    dates = pd.date_range("2020-01-01", periods=36, freq="MS")
    lr = 0.65 + 0.02 * np.sin(2 * np.pi * np.arange(36) / 12) \
        + rng.normal(0, 0.005, 36)
    monthly = pd.DataFrame({"month": dates.strftime("%Y-%m"),
                            "loss_ratio": lr, "date": dates})
    out = F.forecast_loss_ratio(monthly, n_holdout=12)
    assert len(out["forecast"]) == 12
    assert len(out["actual"]) == 12
    manual = np.mean(np.abs(np.array(out["forecast"]) - np.array(out["actual"]))
                     / np.array(out["actual"]))
    assert out["mape"] == pytest.approx(manual, rel=1e-9)
    assert 0.0 <= out["mape"] < 0.25


def test_monthly_series_length(data):
    monthly = F.monthly_loss_ratio(data["policies"], data["claims"])
    assert len(monthly) == 96  # 2019-01 .. 2026-12 (84 train + 12 holdout)
    assert (monthly["earned_premium"] > 0).all()


# ----------------------------------------------------------------- metrics ---
def test_metrics_json_schema():
    """outputs/metrics.json (written by the pipeline) has the required keys."""
    mpath = os.path.join(REPO_ROOT, "outputs", "metrics.json")
    if not os.path.exists(mpath):
        pytest.skip("run `python -m src.pipeline` first")
    with open(mpath) as f:
        m = json.load(f)
    assert m["counts"]["claims"] == 200_000
    assert m["counts"]["claim_notes"] == 30_000
    assert m["counts"]["categories"] == 12
    for key in ("severity_glm", "frequency_glm", "nlp", "forecast", "book"):
        assert key in m
    assert 0.0 < m["severity_glm"]["deviance_explained"] < 1.0
    assert 0.0 <= m["forecast"]["mape"] < 1.0
