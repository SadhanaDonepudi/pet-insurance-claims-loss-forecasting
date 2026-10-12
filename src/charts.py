"""Static chart rendering (matplotlib) for the README and Tableau spec.

All charts are built from the synthetic data / fitted models produced by
``pipeline.py``; every number shown is a measured output of this repo's code.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from . import config as C  # noqa: E402
from . import glm_models as M  # noqa: E402

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150,
    "font.size": 9, "axes.titlesize": 11, "axes.titleweight": "bold",
})
COLORS = {"primary": "#1f4e79", "accent": "#c0392b", "teal": "#148f77",
          "grey": "#7f8c8d", "amber": "#d68910"}


def chart_loss_ratio_forecast(monthly: pd.DataFrame, fc: dict, path: str):
    fig, ax = plt.subplots(figsize=(10, 4.2))
    dates = monthly["date"]
    n = fc["n_holdout_months"]
    ax.plot(dates[:-n], monthly["loss_ratio"][:-n], color=COLORS["primary"],
            lw=1.6, label="Actual loss ratio (train)")
    ax.plot(dates[-n:], monthly["loss_ratio"][-n:], color=COLORS["primary"],
            lw=1.6, ls="--", label="Actual loss ratio (holdout)")
    fc_dates = dates[-n:]
    ax.plot(fc_dates, fc["forecast"], color=COLORS["accent"], lw=1.8,
            marker="o", ms=3, label="Holt-Winters forecast")
    ax.axvline(dates.iloc[-n], color=COLORS["grey"], ls=":", lw=1)
    ax.text(dates.iloc[-n], ax.get_ylim()[1] * 0.98, "  forecast origin",
            color=COLORS["grey"], va="top", fontsize=8)
    ax.set_title(f"Monthly loss ratio — 12-month holdout forecast "
                 f"(MAPE {fc['mape']:.2%})")
    ax.set_ylabel("Loss ratio")
    ax.legend(frameon=False, loc="upper left")
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def chart_severity_calibration(claims: pd.DataFrame, sev: dict, path: str):
    df = claims[M.SEV_COLS + ["claim_cost"]].copy()
    X = M._design_matrix(df, M.SEV_COLS)
    params = pd.Series(sev["params"]).reindex(X.columns).fillna(0.0)
    pred = np.exp(np.asarray(X @ params))
    df["pred"] = pred
    df["decile"] = pd.qcut(df["pred"], 10, labels=False, duplicates="drop")
    cal = df.groupby("decile").agg(pred_mean=("pred", "mean"),
                                   actual_mean=("claim_cost", "mean"))
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    lim = [0, max(cal.max().max() * 1.05, 1)]
    ax.plot(lim, lim, color=COLORS["grey"], ls="--", lw=1, label="Perfect calibration")
    ax.scatter(cal["pred_mean"], cal["actual_mean"], color=COLORS["primary"],
               s=45, zorder=3, label="Decile of predicted severity")
    for i, row in cal.iterrows():
        ax.annotate(f"d{i+1}", (row["pred_mean"], row["actual_mean"]),
                    fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_title(f"Gamma severity GLM calibration\n"
                 f"(deviance explained {sev['deviance_explained']:.1%})")
    ax.set_xlabel("Mean predicted cost ($)")
    ax.set_ylabel("Mean actual cost ($)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def chart_nlp_confusion(nlp: dict, path: str):
    cm = np.array(nlp["confusion_matrix"])
    labels = nlp["categories"]
    # share of each true class predicted as each class
    share = cm / np.maximum(cm.sum(axis=1, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=(8.2, 7.0))
    im = ax.imshow(share, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)), [l.replace(" ", "\n") for l in labels],
                  fontsize=7)
    ax.set_yticks(range(len(labels)), labels, fontsize=7)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(f"Claim-note classifier confusion matrix "
                 f"(accuracy {nlp['accuracy']:.1%})")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    for i in range(len(labels)):
        for j in range(len(labels)):
            if share[i, j] >= 0.08:
                ax.text(j, i, f"{share[i, j]:.0%}", ha="center", va="center",
                        fontsize=6, color="white" if share[i, j] > 0.5 else "black")
    fig.colorbar(im, ax=ax, label="Share of true class")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def chart_top_conditions(claims: pd.DataFrame, path: str):
    g = (claims.groupby("condition")
               .agg(n=("claim_cost", "size"),
                    mean_cost=("claim_cost", "mean"),
                    total=("claim_cost", "sum"))
               .sort_values("total", ascending=True))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    axes[0].barh(g.index, g["n"], color=COLORS["primary"])
    axes[0].set_title("Claim count by condition")
    axes[0].set_xlabel("Claims")
    axes[1].barh(g.index, g["mean_cost"], color=COLORS["teal"])
    axes[1].set_title("Average severity by condition")
    axes[1].set_xlabel("Mean paid ($)")
    for ax in axes:
        ax.tick_params(labelsize=8)
    fig.suptitle("Condition mix — volume vs. severity", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def chart_frequency_by_breed(policies: pd.DataFrame, claims: pd.DataFrame,
                             path: str):
    counts = claims.groupby("policy_id").size().rename("n_claims")
    df = policies.set_index("policy_id")[["breed", "in_window_exposure_years"]].copy()
    df["n_claims"] = counts.reindex(df.index).fillna(0).to_numpy()
    g = (df.groupby("breed")
           .agg(claims=("n_claims", "sum"),
                ey=("in_window_exposure_years", "sum"))
           .assign(freq_per_1k=lambda d: d["claims"] / d["ey"] * 1000)
           .sort_values("freq_per_1k", ascending=True))
    fig, ax = plt.subplots(figsize=(7.2, 6.4))
    ax.barh(g.index, g["freq_per_1k"], color=COLORS["amber"])
    ax.set_title("Claim frequency per 1,000 exposure-years by breed")
    ax.set_xlabel("Claims per 1,000 exposure-years")
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def chart_loss_ratio_brand_state(policies: pd.DataFrame, claims: pd.DataFrame,
                                 path: str):
    earned = policies.groupby(["brand", "state"])["earned_premium"].sum()
    incurred = claims.groupby(["brand", "state"])["claim_cost"].sum()
    lr = (incurred / earned).unstack("brand")
    fig, ax = plt.subplots(figsize=(10, 4.6))
    x = np.arange(len(lr.index))
    w = 0.25
    for i, brand in enumerate(lr.columns):
        ax.bar(x + (i - 1) * w, lr[brand], width=w, label=brand)
    ax.set_xticks(x, lr.index)
    ax.axhline(1.0, color=COLORS["accent"], ls="--", lw=1, label="100% LR")
    ax.set_title("Loss ratio by state and brand (drill-down view)")
    ax.set_ylabel("Loss ratio")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def chart_claim_volume(monthly: pd.DataFrame, path: str):
    fig, ax1 = plt.subplots(figsize=(10, 4.0))
    ax1.bar(monthly["date"], monthly["n_claims"], width=22,
            color=COLORS["primary"], alpha=0.75, label="Claim count")
    ax1.set_ylabel("Claims per month", color=COLORS["primary"])
    ax2 = ax1.twinx()
    ax2.plot(monthly["date"], monthly["earned_premium"] / 1e6,
             color=COLORS["accent"], lw=1.6, label="Earned premium ($M)")
    ax2.set_ylabel("Earned premium ($M)", color=COLORS["accent"])
    ax1.set_title("Monthly claim volume and earned premium (2019–2026)")
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def render_all(data: dict, models: dict, outdir: str) -> list[str]:
    import os
    os.makedirs(outdir, exist_ok=True)
    paths = []
    specs = [
        ("loss_ratio_forecast.png", chart_loss_ratio_forecast,
         (models["monthly"], models["forecast"])),
        ("severity_calibration.png", chart_severity_calibration,
         (data["claims"], models["severity"])),
        ("nlp_confusion_matrix.png", chart_nlp_confusion,
         (models["nlp"],)),
        ("top_conditions.png", chart_top_conditions,
         (data["claims"],)),
        ("frequency_by_breed.png", chart_frequency_by_breed,
         (data["policies"], data["claims"])),
        ("loss_ratio_brand_state.png", chart_loss_ratio_brand_state,
         (data["policies"], data["claims"])),
        ("claim_volume_trend.png", chart_claim_volume,
         (models["monthly"],)),
    ]
    for fname, fn, args in specs:
        p = os.path.join(outdir, fname)
        fn(*args, p)
        paths.append(p)
    return paths
