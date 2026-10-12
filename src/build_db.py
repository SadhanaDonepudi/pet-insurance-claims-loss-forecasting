"""Build the SQLite analytics mart from generated DataFrames.

Creates: policies, claims, claim_notes (from ``sql/schema.sql``) plus a
``policy_months`` mart table (one row per active policy-month with that
month's earned-premium slice) used by the monthly loss-ratio KPI.

Usage:
    python -m src.build_db --db /tmp/pet_insurance.sqlite [--seed 20261012]
"""

from __future__ import annotations

import argparse
import os
import sqlite3

import numpy as np
import pandas as pd

from . import generate as G
from . import config as C


def _policy_months(policies: pd.DataFrame) -> pd.DataFrame:
    window_start = pd.Timestamp(C.WINDOW_START)
    window_end = pd.Timestamp(C.WINDOW_END)
    eff = policies["effective_date"].clip(lower=window_start, upper=window_end)
    exp_days = (policies["exposure_years"] * 365.25).round().astype(int)
    end = (policies["effective_date"] + pd.to_timedelta(exp_days, unit="D")
           ).clip(lower=window_start, upper=window_end)

    eff_ym = (eff.dt.year * 12 + eff.dt.month - 1).to_numpy()
    end_ym = (end.dt.year * 12 + end.dt.month - 1).to_numpy()
    n_months = np.maximum(end_ym - eff_ym + 1, 1)

    total = int(n_months.sum())
    pol_idx = np.repeat(np.arange(len(policies)), n_months)
    starts = np.repeat(np.cumsum(n_months) - n_months, n_months)
    ym = eff_ym[pol_idx] + (np.arange(total) - starts)
    per_month = (policies["earned_premium"].to_numpy() / n_months)[pol_idx]

    return pd.DataFrame({
        "policy_id": policies["policy_id"].to_numpy()[pol_idx],
        "brand": policies["brand"].to_numpy()[pol_idx],
        "month": [f"{v // 12:04d}-{v % 12 + 1:02d}" for v in ym],
        "earned_premium": per_month,
    })


def build_db(db_path: str, data: dict | None = None,
             seed: int = C.SEED) -> str:
    if data is None:
        data = G.generate_all(seed=seed)
    policies, claims, notes = data["policies"], data["claims"], data["notes"]

    sql_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sql")
    with open(os.path.join(sql_dir, "schema.sql")) as f:
        schema = f.read()

    if os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    con.executescript(schema)

    pol = policies.copy()
    pol["effective_date"] = pol["effective_date"].dt.strftime("%Y-%m-%d")
    pol = pol.drop(columns=["premium_scale"], errors="ignore")
    pol.to_sql("policies", con, if_exists="append", index=False)

    cl = claims.copy()
    cl["claim_date"] = cl["claim_date"].dt.strftime("%Y-%m-%d")
    cl["has_note"] = cl["has_note"].astype(int)
    cl.to_sql("claims", con, if_exists="append", index=False)

    notes.to_sql("claim_notes", con, if_exists="append", index=False)

    pm = _policy_months(policies)
    pm.to_sql("policy_months", con, if_exists="replace", index=False)
    con.execute("CREATE INDEX idx_pm_month_brand ON policy_months(month, brand)")

    con.commit()
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("policies", "claims", "claim_notes", "policy_months")}
    con.close()
    print(f"wrote {db_path}: " + ", ".join(f"{t}={n:,}" for t, n in counts.items()))
    return db_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="/tmp/pet_insurance.sqlite")
    ap.add_argument("--seed", type=int, default=C.SEED)
    args = ap.parse_args()
    build_db(args.db, seed=args.seed)


if __name__ == "__main__":
    main()
