"""Synthetic data generator for the pet-insurance claims project.

Produces, with a fixed seed:
  * ``policies``      -- 120,000 synthetic policies with rating attributes,
                         exposure, expected claim frequency and premium.
  * ``claims``        -- EXACTLY 200,000 synthetic claims.
  * ``claim_notes``   -- EXACTLY 30,000 synthetic free-text claim notes
                         across the 12 condition categories.

Statistical design
------------------
* Claim counts per policy-month are proportional to a Poisson-style rate
  ``lambda = base * breed * age * territory * state * brand * species *
  seasonality * trend * lognormal(unobserved)``. The 200,000 claims are
  assigned by multinomial sampling over the policy-month grid, which is the
  exact conditional distribution of independent Poissons given their sum --
  so the frequency GLM in ``glm_models.py`` is fit on data that genuinely
  follows its assumed process (up to the unobserved heterogeneity term).
* Severity is drawn from a Gamma distribution whose mean depends on
  condition, breed size, age, state cost level, species and vet-cost
  inflation -- the correctly-specified model for the Gamma severity GLM.
* Premiums are rating-factor based and then scaled so the book-average
  loss ratio equals ``TARGET_LOSS_RATIO``.

ALL DATA IS SYNTHETIC. No real policyholders, pets, or insurers.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .note_templates import (
    NOTES, POOLS, VETS, DURATIONS, SEXES, FILLERS,
    GENERAL_EXAM, GENERAL_PLAN,
    ORTHO_PRESENT, ORTHO_EXAM, ORTHO_PLAN, ORTHO_MEDS,
)

# Categories whose notes are drawn mostly from a shared sentence bank --
# they present almost identically in real clinical text.
ORTHO_CATS = {"Arthritis", "Hip Dysplasia", "Cruciate Ligament Tear"}
ORTHO_SHARED_P = 0.65


def make_rng(seed: int = C.SEED) -> np.random.Generator:
    return np.random.default_rng(seed)


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------
def generate_policies(rng: np.random.Generator,
                      n: int = C.N_POLICIES) -> pd.DataFrame:
    brand = rng.choice(C.BRANDS, p=C.BRAND_W, size=n)
    species = rng.choice(C.SPECIES, p=C.SPECIES_W, size=n)

    breed = np.empty(n, dtype=object)
    is_dog = species == "dog"
    breed[is_dog] = rng.choice(C.DOG_BREEDS, p=C.DOG_BREED_W, size=is_dog.sum())
    breed[~is_dog] = rng.choice(C.CAT_BREEDS, p=C.CAT_BREED_W, size=(~is_dog).sum())

    age = rng.choice(C.AGES, p=C.AGE_W, size=n)
    state = rng.choice(C.STATES, p=C.STATE_W, size=n)
    density = rng.choice(C.DENSITIES, p=C.DENSITY_W, size=n)
    region = np.array([C.STATE_REGION[s] for s in state])
    territory = np.array([f"{r}-{d}" for r, d in zip(region, density)])

    eff_start_ord = pd.Timestamp(C.EFF_START).toordinal()
    eff_end_ord = pd.Timestamp(C.EFF_END).toordinal()
    window_end_ord = pd.Timestamp(C.WINDOW_END).toordinal()
    eff_ord = rng.integers(eff_start_ord, eff_end_ord + 1, size=n)
    term_years = rng.choice(C.TERM_YEARS, p=C.TERM_W, size=n)
    end_ord = np.minimum(eff_ord + (term_years * 365).astype(int), window_end_ord)
    exposure_days = (end_ord - eff_ord).astype(float)
    exposure_years = exposure_days / 365.25
    # In-window exposure (modeling window may clip the tenure)
    window_start_ord = pd.Timestamp(C.WINDOW_START).toordinal()
    iw_start = np.maximum(eff_ord, window_start_ord)
    iw_end = np.minimum(end_ord, window_end_ord)
    in_window_exposure_years = np.maximum(iw_end - iw_start, 0).astype(float) / 365.25

    breed_size = np.array([C.BREED_SIZE[b] for b in breed])
    age_bin = np.array([C.age_bin(a) for a in age])

    # --- frequency multiplier (observed part) ---
    mult = (
        np.array([C.BREED_FREQ_MULT[b] for b in breed])
        * np.array([C.age_freq_mult(a) for a in age])
        * np.array([C.DENSITY_FREQ_MULT[d] for d in density])
        * np.array([C.STATE_FREQ_MULT[s] for s in state])
        * np.array([C.BRAND_FREQ_MULT[b] for b in brand])
        * np.array([C.SPECIES_FREQ_MULT[s] for s in species])
    )
    log_lam = (
        np.log(C.TARGET_MEAN_FREQ)
        - np.log(mult.mean())
        + np.log(mult)
        + rng.normal(0.0, C.SIGMA_FREQ_NOISE, size=n)  # unobserved heterogeneity
    )
    lam_annual = np.exp(log_lam)
    mu = lam_annual * in_window_exposure_years  # expected in-window claims

    policies = pd.DataFrame({
        "policy_id": [f"POL-{i:06d}" for i in range(n)],
        "brand": brand,
        "species": species,
        "breed": breed,
        "breed_size": breed_size,
        "age": age,
        "age_bin": age_bin,
        "state": state,
        "region": region,
        "density": density,
        "territory": territory,
        "effective_date": pd.to_datetime([pd.Timestamp.fromordinal(o)
                                          for o in eff_ord]),
        "exposure_years": exposure_years,
        "in_window_exposure_years": in_window_exposure_years,
        "lam_annual": lam_annual,
        "expected_claims": lam_annual * in_window_exposure_years,
    })
    return policies


# ---------------------------------------------------------------------------
# Claim occurrence (policy-month grid -> multinomial assignment)
# ---------------------------------------------------------------------------
def _day_ord_to_ym_lut():
    start = pd.Timestamp(C.WINDOW_START).toordinal()
    end = pd.Timestamp(C.WINDOW_END).toordinal()
    ords = np.arange(start, end + 1)
    # vectorized via pandas (fast enough, one-time)
    dts = pd.to_datetime([pd.Timestamp.fromordinal(o) for o in ords])
    return ords, (dts.year.values * 12 + dts.month.values - 1)


def build_policy_month_grid(policies: pd.DataFrame) -> pd.DataFrame:
    """One row per active policy-month with its claim-occurrence weight."""
    ords, ym_ords = _day_ord_to_ym_lut()
    lut = dict(zip(ords, ym_ords))

    eff_ord = policies["effective_date"].map(pd.Timestamp.toordinal).to_numpy()
    window_start_ord = pd.Timestamp(C.WINDOW_START).toordinal()
    window_end_ord = pd.Timestamp(C.WINDOW_END).toordinal()
    exposure_days = (policies["exposure_years"] * 365.25).round().astype(int).to_numpy()
    end_ord = np.minimum(eff_ord + exposure_days, window_end_ord)

    # Clip the grid to the modeling window
    eff_ym = np.array([lut[o] for o in np.maximum(eff_ord, window_start_ord)])
    end_ym = np.array([lut[o] for o in np.minimum(end_ord, window_end_ord)])
    n_months = (end_ym - eff_ym + 1).astype(np.int64)
    assert (n_months >= 1).all(), "every policy must touch the modeling window"

    total = int(n_months.sum())
    grid_pol = np.repeat(np.arange(len(policies)), n_months)
    starts = np.repeat(np.cumsum(n_months) - n_months, n_months)
    offsets = np.arange(total) - starts
    grid_ym = eff_ym[grid_pol] + offsets
    cal_month = (grid_ym % 12) + 1

    base_ym = 2019 * 12  # ym ordinal of 2019-01
    trend = (1.0 + C.ANN_FREQ_TREND) ** ((grid_ym - base_ym) / 12.0)
    seas = np.array([C.SEASONALITY[m] for m in cal_month])
    lam = policies["lam_annual"].to_numpy()
    weight = lam[grid_pol] / 12.0 * seas * trend

    return pd.DataFrame({
        "pol_idx": grid_pol,
        "ym_ord": grid_ym,
        "year": grid_ym // 12,
        "month": cal_month,
        "weight": weight,
    })


def generate_claims(policies: pd.DataFrame, grid: pd.DataFrame,
                    rng: np.random.Generator,
                    n_claims: int = C.N_CLAIMS) -> pd.DataFrame:
    """Assign EXACTLY ``n_claims`` claims to policy-months (multinomial)."""
    w = grid["weight"].to_numpy()
    probs = w / w.sum()
    # choice without an `a=` array returns indices -- fastest path
    chosen = rng.choice(len(grid), size=n_claims, replace=True, p=probs)
    g = grid.iloc[chosen].reset_index(drop=True)

    day = rng.integers(1, 29, size=n_claims)
    claim_date = pd.to_datetime(
        {"year": g["year"].to_numpy(),
         "month": g["month"].to_numpy(),
         "day": day}
    )
    pol = policies.iloc[g["pol_idx"].to_numpy()].reset_index(drop=True)
    yearfrac = (claim_date - pd.Timestamp(C.WINDOW_START)).dt.days / 365.25

    claims = pd.DataFrame({
        "claim_id": [f"CLM-{i:07d}" for i in range(n_claims)],
        "policy_id": pol["policy_id"].to_numpy(),
        "claim_date": claim_date,
        "claim_year": claim_date.dt.year,
        "claim_month": claim_date.dt.month,
        "yearfrac": yearfrac,
        "brand": pol["brand"].to_numpy(),
        "species": pol["species"].to_numpy(),
        "breed": pol["breed"].to_numpy(),
        "breed_size": pol["breed_size"].to_numpy(),
        "age": pol["age"].to_numpy(),
        "age_bin": pol["age_bin"].to_numpy(),
        "state": pol["state"].to_numpy(),
        "territory": pol["territory"].to_numpy(),
    })
    assert len(claims) == n_claims
    return claims


# ---------------------------------------------------------------------------
# Condition assignment (breed/age-aware multinomial via Gumbel-max)
# ---------------------------------------------------------------------------
_SIZE_COND_ADJ = {
    # condition -> {size: log-odds adjustment}
    "Cruciate Ligament Tear": {"giant": 1.2, "large": 0.8, "medium": 0.2, "small": -0.3},
    "Hip Dysplasia": {"giant": 1.4, "large": 0.9, "medium": 0.1, "small": -0.5},
    "Dental Disease": {"small": 0.9, "medium": 0.2, "large": -0.2, "giant": -0.3},
    "Arthritis": {"giant": 0.5, "large": 0.4, "medium": 0.0, "small": 0.1},
    "Laceration": {"large": 0.3, "giant": 0.3},
}
_AGE_COND_SLOPE = {  # per-year log-odds slope away from age 5
    "Dental Disease": 0.06, "Arthritis": 0.10, "Diabetes": 0.08,
    "Cruciate Ligament Tear": 0.03, "Hip Dysplasia": -0.02,
    "Kennel Cough": -0.05, "Gastroenteritis": -0.02,
}
_SPECIES_COND_ADJ = {"Diabetes": {"cat": 0.5}}


def assign_conditions(claims: pd.DataFrame,
                      rng: np.random.Generator) -> pd.DataFrame:
    names = C.CONDITION_NAMES
    n, k = len(claims), len(names)
    logits = np.tile(np.log(C.COND_MIX), (n, 1))

    size = claims["breed_size"].to_numpy()
    age = claims["age"].to_numpy().astype(float)
    species = claims["species"].to_numpy()
    for j, name in enumerate(names):
        adj = _SIZE_COND_ADJ.get(name, {})
        if adj:
            logits[:, j] += np.array([adj.get(s, 0.0) for s in size])
        slope = _AGE_COND_SLOPE.get(name, 0.0)
        if slope:
            logits[:, j] += slope * (age - 5.0)
        sadj = _SPECIES_COND_ADJ.get(name, {})
        if sadj:
            logits[:, j] += np.array([sadj.get(s, 0.0) for s in species])

    # Gumbel-max trick: vectorized categorical sampling
    g = -np.log(-np.log(rng.random((n, k)) + 1e-12) + 1e-12)
    chosen = np.argmax(logits + g, axis=1)
    claims = claims.copy()
    claims["condition"] = [names[j] for j in chosen]
    return claims


# ---------------------------------------------------------------------------
# Severity (Gamma, log link -- matches the severity GLM specification)
# ---------------------------------------------------------------------------
def generate_severity(claims: pd.DataFrame,
                      rng: np.random.Generator) -> pd.DataFrame:
    claims = claims.copy()
    logmu = (
        C.SEV_INTERCEPT
        + C.SEV_SPREAD * claims["condition"].map(C.COND_SEV_LOG).to_numpy()
        + claims["breed_size"].map(C.SIZE_SEV_LOG).to_numpy()
        + C.AGE_SEV_SLOPE * (claims["age"].to_numpy() - 5.0)
        + claims["state"].map(C.STATE_SEV_LOG).to_numpy()
        + claims["species"].map(C.SPECIES_SEV_LOG).to_numpy()
        + C.SEV_INFLATION * claims["yearfrac"].to_numpy()
    )
    mu = np.exp(logmu)
    shape = C.SEV_GAMMA_SHAPE
    claims["claim_cost"] = rng.gamma(shape=shape, scale=mu / shape)
    return claims


# ---------------------------------------------------------------------------
# Premiums (solved so the book-average loss ratio == TARGET_LOSS_RATIO)
# ---------------------------------------------------------------------------
def finalize_premiums(policies: pd.DataFrame,
                      claims: pd.DataFrame) -> pd.DataFrame:
    policies = policies.copy()
    unscaled = (
        C.BASE_ANNUAL_PREM
        * policies["species"].map(C.SPECIES_PREM_MULT)
        * policies["breed"].map(C.BREED_PREM_MULT)
        * policies["state"].map(C.STATE_PREM_MULT)
        * policies["age_bin"].map(C.AGE_PREM_MULT)
        * policies["brand"].map(C.BRAND_PREM_MULT)
        * C.PREM_LOADING
    )
    # Annual rate filings: later-effective policies pay filed rates
    eff_yearfrac = ((policies["effective_date"] - pd.Timestamp(C.EFF_START)).dt.days
                    / 365.25)
    unscaled = unscaled * (1.0 + C.PREM_RATE_TREND) ** eff_yearfrac
    earned_unscaled = (unscaled * policies["in_window_exposure_years"]).sum()
    total_incurred = claims["claim_cost"].sum()
    scale = (total_incurred / C.TARGET_LOSS_RATIO) / earned_unscaled
    policies["annual_premium"] = unscaled * scale
    policies["earned_premium"] = (policies["annual_premium"]
                                  * policies["in_window_exposure_years"])
    policies["premium_scale"] = scale
    return policies


# ---------------------------------------------------------------------------
# Claim notes (templated free text)
# ---------------------------------------------------------------------------
def _build_note(rng: np.random.Generator, cond: str, pet: str, breed: str,
                age: int, sex: str) -> str:
    t = NOTES[cond]
    vet = rng.choice(VETS)
    dur = rng.choice(DURATIONS)
    n_sig = int(rng.integers(1, 3))
    sig = " and ".join(rng.choice(t["sig"], size=n_sig, replace=False))
    kw = dict(pet=pet, breed=breed, age=age, sex=sex, vet=vet,
              dur=dur, sig=sig)

    if cond in ORTHO_CATS and rng.random() < ORTHO_SHARED_P:
        # Mostly indistinguishable orthopedic note; distinguishing details
        # appear only in the minority drawn from category templates.
        med = rng.choice(ORTHO_MEDS)
        kw["med"] = med
        present = rng.choice(ORTHO_PRESENT).format(**kw)
        exam = rng.choice(ORTHO_EXAM).format(**kw)
        plan = rng.choice(ORTHO_PLAN).format(**kw)
    else:
        med = rng.choice(t["meds"])
        kw["med"] = med
        present = rng.choice(t["present"]).format(**kw)
        # Half the exam/plan sentences are generic boilerplate shared by all
        # categories -- real notes are full of it, and it dilutes signal.
        exam_tpl = rng.choice(t["exam"]) if rng.random() < 0.5 else rng.choice(GENERAL_EXAM)
        plan_tpl = rng.choice(t["plan"]) if rng.random() < 0.5 else rng.choice(GENERAL_PLAN)
        exam = exam_tpl.format(**kw)
        plan = plan_tpl.format(**kw)

    sents = [
        f"{age}-year-old {sex} {breed} {pet} examined by {vet}.",
        present, exam, plan,
    ]
    pool_name, p_confuse = t["confuse"]
    if pool_name is not None and rng.random() < p_confuse:
        sents.insert(3, rng.choice(POOLS[pool_name]))
    # History noise: mention another condition's signature symptom, as real
    # notes do for comorbidities / prior episodes. The label is unchanged.
    if rng.random() < C.NLP_HISTORY_NOISE_P:
        others = [c for c in C.CONDITION_NAMES if c != cond]
        other = others[int(rng.integers(len(others)))]
        hist_sig = rng.choice(NOTES[other]["sig"])
        sents.append(f"History of {hist_sig} noted in the record.")
    n_fill = int(rng.integers(0, 3))
    if n_fill:
        sents.extend(rng.choice(FILLERS, size=n_fill, replace=False).tolist())
    return " ".join(sents)


def generate_notes(claims: pd.DataFrame, rng: np.random.Generator,
                   n_notes: int = C.N_NOTES) -> pd.DataFrame:
    idx = rng.choice(len(claims), size=n_notes, replace=False)
    sub = claims.iloc[idx].reset_index(drop=True)
    sexes = rng.choice(SEXES, size=n_notes)
    texts = [
        _build_note(rng, cond, pet, breed, age, sex)
        for cond, pet, breed, age, sex in zip(
            sub["condition"], sub["species"].map({"dog": "dog", "cat": "cat"}),
            sub["breed"], sub["age"], sexes)
    ]
    notes = pd.DataFrame({
        "note_id": [f"NOTE-{i:05d}" for i in range(n_notes)],
        "claim_id": sub["claim_id"].to_numpy(),
        "category": sub["condition"].to_numpy(),
        "note_text": texts,
    })
    assert len(notes) == n_notes
    assert set(notes["category"].unique()) == set(C.CONDITION_NAMES)
    return notes


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------
def generate_all(seed: int = C.SEED, n_claims: int = C.N_CLAIMS,
                 n_notes: int = C.N_NOTES,
                 n_policies: int = C.N_POLICIES) -> dict:
    rng = make_rng(seed)
    policies = generate_policies(rng, n=n_policies)
    grid = build_policy_month_grid(policies)
    claims = generate_claims(policies, grid, rng, n_claims=n_claims)
    claims = assign_conditions(claims, rng)
    claims = generate_severity(claims, rng)
    policies = finalize_premiums(policies, claims)
    notes = generate_notes(claims, rng, n_notes=n_notes)
    claims["has_note"] = claims["claim_id"].isin(set(notes["claim_id"]))
    return {"policies": policies, "claims": claims, "notes": notes, "grid": grid}
