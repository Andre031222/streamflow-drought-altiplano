#!/usr/bin/env python3
"""Spatial statistics of the benchmark results.

1. Hydrological-drought synchrony: Spearman correlation of monthly SSI-30 between all
   gauge pairs with >= 60 overlapping months, versus great-circle distance; exponential
   correlogram rho(d) = c * exp(-d / d0) with a gauge-level bootstrap CI for d0.
2. Spatial autocorrelation of forecast skill: global Moran's I (inverse-distance weights,
   row-standardised) with a permutation test.
3. Skill drivers: Spearman rank correlation between 7-day skill (val-selected learner)
   and Andean-GC catchment attributes, permutation p-values with Holm correction.

Outputs: 04-resultados/tablas/spatial_*.csv|json and fig09_spatial_statistics.{png,pdf}.
Usage: python 03-codigo/spatial_analysis.py
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import optimize, stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg
from plots import OKABE, REGION_COLORS, REGION_ORDER, save, style, val_selected

RNG = np.random.default_rng(cfg.RANDOM_STATE)
MIN_MONTHS = 60
ATTRS = {"basin_area": "Catchment area", "elev_mean": "Mean elevation",
         "glacier_frac": "Glacier fraction", "aridity_ERA5": "Aridity index",
         "prcp_pci_ERA5": "Precip. concentration", "frac_snow_ERA5": "Snow fraction",
         "low_prec_freq_ERA5": "Dry-day frequency"}


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi, dl = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def monthly_ssi(ssi: pd.DataFrame) -> pd.DataFrame:
    s = ssi.copy()
    s["date"] = pd.to_datetime(s.date)
    s["month"] = s.date.dt.to_period("M")
    g = s.groupby(["gauge_id", "month"]).ssi30.agg(["mean", "count"]).reset_index()
    g = g[g["count"] >= 20]
    return g.pivot(index="month", columns="gauge_id", values="mean")


def expo(d, c, d0):
    return c * np.exp(-d / d0)


def fit_correlogram(pairs: pd.DataFrame) -> tuple[float, float]:
    (c, d0), _ = optimize.curve_fit(expo, pairs.dist_km, pairs.rho_ssi, p0=[0.8, 300],
                                    bounds=([0, 1], [1, 5000]))
    return float(c), float(d0)


def moran_i(x: np.ndarray, w: np.ndarray, n_perm: int = 9999) -> tuple[float, float]:
    w = w / w.sum(axis=1, keepdims=True)
    z = x - x.mean()

    def stat(v):
        return len(v) / w.sum() * (v @ w @ v) / (v @ v)

    obs = stat(z)
    perms = np.array([stat(RNG.permutation(z)) for _ in range(n_perm)])
    p = (np.sum(np.abs(perms - perms.mean()) >= abs(obs - perms.mean())) + 1) / (n_perm + 1)
    return float(obs), float(p)


def perm_spearman(x, y, n_perm=9999) -> tuple[float, float]:
    rho = stats.spearmanr(x, y).statistic
    perms = np.array([stats.spearmanr(x, RNG.permutation(y)).statistic for _ in range(n_perm)])
    return float(rho), float((np.sum(np.abs(perms) >= abs(rho)) + 1) / (n_perm + 1))


def main() -> None:
    style()
    st = pd.read_csv(cfg.STATION_META)
    agc = pd.read_csv(cfg.RAW / "andean-gc" / "AndeanGC_metadata.csv").set_index("gauge_id")
    met = pd.read_csv(cfg.TAB / "metrics_by_station.csv")
    ssi = pd.read_csv(cfg.PROC / "ssi30_all_gauges.csv")

    # ---------------- per-gauge skill table (for the QGIS map)
    best = val_selected(met)
    b7 = best[best.horizon == 7].set_index("gauge_id")
    p7 = met[(met.model == "persistence") & (met.horizon == 7)].set_index("gauge_id")
    g = st.set_index("gauge_id").loc[b7.index]
    skill = pd.DataFrame({
        "gauge_id": b7.index, "gauge_name": g.gauge_name.values, "region": g.region.values,
        "lat": g.gauge_lat.values, "lon": g.gauge_lon.values,
        "best_model": b7.model.values, "skill_h7": b7.skill_vs_persistence.values,
        "skill_lo": b7.skill_lo.values, "skill_hi": b7.skill_hi.values,
        "sig": (b7.skill_lo > 0).values, "csi_h7": b7.drought_CSI.values,
        "csi_pers_h7": p7.drought_CSI.reindex(b7.index).values})
    skill.to_csv(cfg.TAB / "spatial_gauge_skill.csv", index=False)

    # ---------------- drought synchrony
    ms = monthly_ssi(ssi)
    coords = st.set_index("gauge_id")[["gauge_lat", "gauge_lon", "region"]]
    rows = []
    for a, b in itertools.combinations(ms.columns, 2):
        both = ms[[a, b]].dropna()
        if len(both) < MIN_MONTHS:
            continue
        la, oa, ra = coords.loc[a]
        lb, ob, rb = coords.loc[b]
        rows.append({"gauge_a": a, "gauge_b": b, "lat_a": la, "lon_a": oa, "lat_b": lb, "lon_b": ob,
                     "region_a": ra, "region_b": rb, "same_region": ra == rb,
                     "dist_km": float(haversine_km(la, oa, lb, ob)), "n_months": len(both),
                     "rho_ssi": float(stats.spearmanr(both[a], both[b]).statistic),
                     "cooc_drought": float(((both[a] < -1) & (both[b] < -1)).mean()
                                           / max(((both[a] < -1).mean() * (both[b] < -1).mean()), 1e-9))})
    pairs = pd.DataFrame(rows)
    pairs.to_csv(cfg.TAB / "spatial_ssi_pairs.csv", index=False)
    c, d0 = fit_correlogram(pairs)
    gauges = sorted(set(pairs.gauge_a) | set(pairs.gauge_b))
    d0_boot = []
    for _ in range(500):  # gauge-level bootstrap (pairs are not independent)
        pick = set(RNG.choice(gauges, size=len(gauges), replace=True))
        sub = pairs[pairs.gauge_a.isin(pick) & pairs.gauge_b.isin(pick)]
        if len(sub) >= 8:
            try:
                d0_boot.append(fit_correlogram(sub)[1])
            except RuntimeError:
                pass
    d0_lo, d0_hi = np.percentile(d0_boot, [2.5, 97.5])
    rho_dist = stats.spearmanr(pairs.dist_km, pairs.rho_ssi)

    # ---------------- Moran's I of 7-day skill
    lat, lon = skill.lat.values, skill.lon.values
    D = haversine_km(lat[:, None], lon[:, None], lat[None, :], lon[None, :])
    W = np.where(D > 0, 1.0 / np.maximum(D, 1.0), 0.0)
    mi, mp = moran_i(skill.skill_h7.values, W)

    # ---------------- skill vs catchment attributes
    at = agc.loc[skill.gauge_id].copy()
    at["glacier_frac"] = at.glacier_area_RGI60 / at.basin_area
    drv = []
    for k, lab in ATTRS.items():
        v = at[k].values.astype(float)
        ok = np.isfinite(v)
        r, p = perm_spearman(v[ok], skill.skill_h7.values[ok])
        drv.append({"attribute": k, "label": lab, "rho": r, "p_perm": p, "n": int(ok.sum())})
    drv = pd.DataFrame(drv).sort_values("p_perm")
    m = len(drv)
    drv["p_holm"] = np.minimum(1, np.maximum.accumulate((m - np.arange(m)) * drv.p_perm.values))
    drv.to_csv(cfg.TAB / "spatial_skill_drivers.csv", index=False)

    summary = {"n_pairs": int(len(pairs)), "n_gauges_pairs": len(gauges), "min_months": MIN_MONTHS,
               "corr_c": c, "corr_d0_km": d0, "corr_d0_ci": [float(d0_lo), float(d0_hi)],
               "spearman_rho_dist": float(rho_dist.statistic), "spearman_p_dist": float(rho_dist.pvalue),
               "median_rho_same_region": float(pairs[pairs.same_region].rho_ssi.median()),
               "median_rho_cross_region": float(pairs[~pairs.same_region].rho_ssi.median()),
               "n_same_region": int(pairs.same_region.sum()),
               "moran_I": mi, "moran_p": mp, "moran_expected": -1 / (len(skill) - 1),
               "top_driver": drv.iloc[0].to_dict()}
    json.dump(summary, open(cfg.TAB / "spatial_summary.json", "w"), indent=2, default=float)

    # ---------------- figure: correlogram + drivers
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.8), gridspec_kw={"width_ratios": [1.5, 1], "wspace": 0.75})
    for same, mk, lab in [(True, "o", "same region"), (False, "x", "different regions")]:
        s = pairs[pairs.same_region == same]
        col = [REGION_COLORS[r] for r in s.region_a] if same else OKABE["grey"]
        a1.scatter(s.dist_km, s.rho_ssi, c=col, marker=mk, s=14 if same else 12, lw=0.8 if not same else 0.3,
                   edgecolor="black" if same else None, alpha=0.85, label=lab)
    dd = np.linspace(0, pairs.dist_km.max() * 1.02, 200)
    a1.plot(dd, expo(dd, c, d0), color="black", lw=1.2,
            label=f"$\\rho={c:.2f}\\,e^{{-d/{d0:.0f}\\,\\mathrm{{km}}}}$")
    for q in d0_lo, d0_hi:
        a1.plot(dd, expo(dd, c, q), color="black", lw=0.5, ls=":")
    a1.axhline(0, color="black", lw=0.4)
    a1.set_xlabel("distance between gauges (km)")
    a1.set_ylabel("Spearman $\\rho$ of monthly SSI-30")
    a1.set_title(f"(a) Drought synchrony ({len(pairs)} pairs, ≥{MIN_MONTHS} months overlap)", loc="left")
    a1.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="none", framealpha=0.9)
    d = drv.sort_values("rho")
    cols = [OKABE["vermillion"] if p < 0.05 else "#BBBBBB" for p in d.p_perm]
    a2.barh(d.label, d.rho, color=cols)
    a2.axvline(0, color="black", lw=0.5)
    a2.set_xlim(-1, 1)
    a2.set_xlabel("Spearman $\\rho$ with 7-day skill")
    a2.set_title(f"(b) Skill drivers (n={len(skill)}; red: p<0.05)", loc="left")
    save(fig, "fig09_spatial_statistics")
    print(json.dumps(summary, indent=1, default=float))
    print(drv.round(3).to_string())


if __name__ == "__main__":
    main()
