"""End-to-end pipeline: generate -> model -> forecast -> charts -> metrics.

Produces everything under ``outputs/`` (committed: metrics.json, charts,
kpi csvs, samples). The full-size CSVs and the SQLite mart are build
artifacts written to ``--artifact-dir`` (default: a temp dir) and are NOT
committed -- regenerate them with ``python -m src.pipeline``.

After the run, README.md's metrics table (between METRICS markers) is
patched with the measured values, so every number in the README is an
actual output of this repo's code.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import tempfile

from . import generate as G
from . import glm_models as M
from . import nlp_classify as N
from . import forecast as F
from . import charts as CH
from . import config as C
from .build_db import build_db
from .run_kpis import run_kpis

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _jsonable(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if k in ("params",):
            out[k] = {kk: float(vv) for kk, vv in v.items()}
        elif k == "confusion_matrix":
            out[k] = [[int(x) for x in row] for row in v]
        elif k == "classification_report":
            out[k] = v  # already JSON-safe floats/ints
        elif isinstance(v, dict):
            out[k] = _jsonable(v)
        elif isinstance(v, (list, tuple)):
            out[k] = list(v)
        else:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                out[k] = v
    # drop non-serializable model objects if ever present
    out.pop("model_obj", None)
    return out


def run(seed: int = C.SEED, artifact_dir: str | None = None) -> dict:
    artifact_dir = artifact_dir or tempfile.mkdtemp(prefix="pet_ins_claims_")
    os.makedirs(artifact_dir, exist_ok=True)
    out_dir = os.path.join(REPO_ROOT, "outputs")
    os.makedirs(out_dir, exist_ok=True)

    print("== 1/6 generating synthetic data ==", flush=True)
    data = G.generate_all(seed=seed)
    policies, claims, notes = data["policies"], data["claims"], data["notes"]

    print("== 2/6 fitting GLMs ==", flush=True)
    sev = M.fit_severity_glm(claims)
    freq = M.fit_frequency_glm(policies, claims)

    print("== 3/6 NLP classification ==", flush=True)
    nlp = N.train_and_evaluate(notes)

    print("== 4/6 loss-ratio forecast ==", flush=True)
    monthly = F.monthly_loss_ratio(policies, claims)
    fc = F.forecast_loss_ratio(monthly)

    print("== 5/6 SQLite mart + KPI scripts ==", flush=True)
    db_path = os.path.join(artifact_dir, "pet_insurance.sqlite")
    build_db(db_path, data=data, seed=seed)
    run_kpis(db_path, os.path.join(out_dir, "kpis"))

    print("== 6/6 charts + metrics ==", flush=True)
    models = {"monthly": monthly, "forecast": fc, "severity": sev,
              "frequency": freq, "nlp": nlp}
    CH.render_all(data, models, os.path.join(out_dir, "charts"))

    # samples (committed; full data stays in artifact_dir)
    samp_dir = os.path.join(out_dir, "samples")
    os.makedirs(samp_dir, exist_ok=True)
    policies.sample(2000, random_state=seed).to_csv(
        os.path.join(samp_dir, "policies_sample.csv"), index=False)
    claims.sample(2000, random_state=seed).to_csv(
        os.path.join(samp_dir, "claims_sample.csv"), index=False)
    notes.sample(2000, random_state=seed).to_csv(
        os.path.join(samp_dir, "claim_notes_sample.csv"), index=False)

    metrics = {
        "seed": seed,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "synthetic_data": True,
        "counts": {
            "policies": int(len(policies)),
            "claims": int(len(claims)),
            "claim_notes": int(len(notes)),
            "categories": int(len(C.CONDITION_NAMES)),
            "category_list": sorted(C.CONDITION_NAMES),
        },
        "book": {
            "total_incurred": float(claims["claim_cost"].sum()),
            "total_earned_premium": float(policies["earned_premium"].sum()),
            "loss_ratio": float(claims["claim_cost"].sum()
                                / policies["earned_premium"].sum()),
            "mean_severity": float(claims["claim_cost"].mean()),
            "policies_with_claims": int(claims["policy_id"].nunique()),
        },
        "severity_glm": _jsonable({k: v for k, v in sev.items()
                                   if k != "params"}),
        "severity_glm_params": {k: float(v) for k, v in sev["params"].items()},
        "frequency_glm": _jsonable({k: v for k, v in freq.items()
                                    if k != "params"}),
        "nlp": _jsonable({k: v for k, v in nlp.items()
                          if k not in ("confusion_matrix",
                                       "classification_report")}),
        "nlp_confusion_matrix": [[int(x) for x in row]
                                 for row in nlp["confusion_matrix"]],
        "forecast": _jsonable(fc),
    }
    metrics["severity_glm"]["deviance_explained_pct"] = round(
        sev["deviance_explained"] * 100, 2)
    metrics["frequency_glm"]["deviance_explained_pct"] = round(
        freq["deviance_explained"] * 100, 2)
    metrics["nlp"]["accuracy_pct"] = round(nlp["accuracy"] * 100, 2)
    metrics["forecast"]["mape_pct"] = round(fc["mape"] * 100, 2)

    mpath = os.path.join(out_dir, "metrics.json")
    with open(mpath, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"wrote {mpath}", flush=True)

    update_readme(metrics)
    print("\nAll measured metrics written. Full-size artifacts in "
          f"{artifact_dir} (not committed).", flush=True)
    return metrics


METRICS_TABLE_TMPL = """| Metric | Measured value |
|---|---|
| Synthetic claims | {claims:,} |
| Synthetic policies | {policies:,} |
| Synthetic claim notes | {notes:,} |
| Condition categories | {categories} |
| Book loss ratio | {loss_ratio:.1%} |
| Mean claim severity | ${mean_severity:,.0f} |
| Gamma severity GLM — deviance explained | {sev_r2:.2%} |
| Poisson frequency GLM — deviance explained | {freq_r2:.2%} |
| NLP note classifier — test accuracy (12 classes) | {nlp_acc:.2%} |
| 12-month loss-ratio forecast — holdout MAPE | {mape:.2%} |
| Seasonal-naive baseline — holdout MAPE | {naive_mape:.2%} |
"""


def update_readme(metrics: dict):
    readme = os.path.join(REPO_ROOT, "README.md")
    if not os.path.exists(readme):
        print("README.md not found; skipping metrics patch.", flush=True)
        return
    table = METRICS_TABLE_TMPL.format(
        claims=metrics["counts"]["claims"],
        policies=metrics["counts"]["policies"],
        notes=metrics["counts"]["claim_notes"],
        categories=metrics["counts"]["categories"],
        loss_ratio=metrics["book"]["loss_ratio"],
        mean_severity=metrics["book"]["mean_severity"],
        sev_r2=metrics["severity_glm"]["deviance_explained"],
        freq_r2=metrics["frequency_glm"]["deviance_explained"],
        nlp_acc=metrics["nlp"]["accuracy"],
        mape=metrics["forecast"]["mape"],
        naive_mape=metrics["forecast"]["baseline_seasonal_naive_mape"],
    )
    with open(readme) as f:
        content = f.read()
    pattern = re.compile(r"<!-- METRICS:START -->.*?<!-- METRICS:END -->",
                         re.DOTALL)
    replacement = "<!-- METRICS:START -->\n" + table + "<!-- METRICS:END -->"
    if not pattern.search(content):
        print("METRICS markers not found in README; skipping patch.",
              flush=True)
        return
    with open(readme, "w") as f:
        f.write(pattern.sub(replacement, content))
    print("README metrics table patched with measured values.", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=C.SEED)
    ap.add_argument("--artifact-dir", default=None)
    args = ap.parse_args()
    run(seed=args.seed, artifact_dir=args.artifact_dir)


if __name__ == "__main__":
    main()
