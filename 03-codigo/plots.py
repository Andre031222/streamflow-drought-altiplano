#!/usr/bin/env python3
"""Publication figures (600 dpi PNG + vector PDF) from the tables written by
run_experiment.py. Colour-blind-safe palettes (Okabe-Ito, Crameri scientific maps).

Usage: python 03-codigo/plots.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from cmcrameri import cm as cmc

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg

OKABE = {"black": "#000000", "orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73",
         "yellow": "#F0E442", "blue": "#0072B2", "vermillion": "#D55E00", "purple": "#CC79A7",
         "grey": "#8C8C8C"}
MODEL_COLORS = {"persistence": OKABE["grey"], "climatology": OKABE["sky"], "Ridge": OKABE["green"],
                "RandomForest": OKABE["purple"], "HistGB": OKABE["orange"], "XGBoost": OKABE["blue"],
                "MLP": OKABE["vermillion"], "XGBoost-log": OKABE["yellow"]}
REGION_COLORS = {"Altiplano": OKABE["purple"], "Cordillera Blanca": OKABE["blue"],
                 "Western/Southern Andes": OKABE["orange"]}
REGION_ORDER = ["Altiplano", "Cordillera Blanca", "Western/Southern Andes"]
LEARNERS = ["Ridge", "RandomForest", "HistGB", "XGBoost", "MLP", "XGBoost-log"]


def style() -> None:
    sns.set_theme(context="paper", style="ticks")
    mpl.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
        "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7, "legend.frameon": False,
        "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
        "savefig.dpi": 600, "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
        "pdf.fonttype": 42, "lines.linewidth": 0.9,
    })


def save(fig, name: str) -> None:
    for ext in ("png", "pdf"):
        fig.savefig(cfg.FIG / f"{name}.{ext}")
    plt.close(fig)
    print("  wrote", name)


def short(name: str) -> str:
    s = (name.replace("(O En El Limite)", "").replace("Rio ", "").replace(" En ", " @ ")
         .replace("Desembocadura", "mouth").replace("Nacimiento", "source").replace("Vertedero", "weir")
         .replace("Antes Junta Valle Ancho", "").replace("Estancia ", ""))
    return " ".join(s.split())[:24]


def val_selected(met: pd.DataFrame) -> pd.DataFrame:
    """Per gauge/horizon, the learner with the lowest *validation* RMSE (no test peeking)."""
    ml = met[met.model.isin(LEARNERS)]
    return ml.loc[ml.groupby(["gauge_id", "horizon"]).val_RMSE.idxmin()]


def station_order(met: pd.DataFrame) -> pd.DataFrame:
    st = met[["gauge_id", "gauge_name", "region"]].drop_duplicates()
    st["r"] = st.region.map({r: i for i, r in enumerate(REGION_ORDER)})
    return st.sort_values(["r", "gauge_name"]).drop(columns="r")


# --------------------------------------------------------------------- figures
def fig_focus_hydrograph_ssi(ssi: pd.DataFrame, splits: dict) -> None:
    d = ssi[ssi.gauge_id == cfg.FOCUS_STATION_ID].copy()
    d["date"] = pd.to_datetime(d.date)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.0, 3.6), sharex=True,
                                 gridspec_kw={"height_ratios": [1.5, 1], "hspace": 0.08})
    a1.plot(d.date, d.q, color=OKABE["black"], lw=0.5)
    for (k, col) in [("train", OKABE["blue"]), ("val", OKABE["orange"]), ("test", OKABE["vermillion"])]:
        s, e = (pd.Timestamp(x) for x in splits["7"][k])
        a1.axvspan(s, e, color=col, alpha=0.10, lw=0)
        a1.text(s + (e - s) / 2, 0.97, k, transform=a1.get_xaxis_transform(), ha="center",
                va="top", color=col, fontsize=7, fontweight="bold")
    a1.set_ylabel("Q (m$^3$ s$^{-1}$)")
    a1.set_yscale("log")
    a1.set_title(f"{cfg.FOCUS_STATION_NAME} ({cfg.FOCUS_STATION_ID}) — daily discharge and "
                 "nonparametric SSI-30", loc="left")
    s = d.ssi30.values
    a2.fill_between(d.date, 0, s, where=s >= 0, color=OKABE["blue"], lw=0, alpha=0.8)
    a2.fill_between(d.date, 0, s, where=s < 0, color=OKABE["vermillion"], lw=0, alpha=0.8)
    a2.axhline(-1, color=OKABE["black"], lw=0.5, ls="--")
    a2.text(0.995, 0.04, "dashed: moderate drought (SSI < −1)", transform=a2.transAxes, ha="right",
            va="bottom", fontsize=6.5, bbox={"fc": "white", "ec": "none", "alpha": 0.85, "pad": 1})
    a2.set_ylabel("SSI-30")
    a2.set_ylim(-3.2, 3.2)
    a2.xaxis.set_major_locator(mdates.YearLocator(4))
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    save(fig, "fig01_focus_hydrograph_ssi")


def fig_focus_forecast(preds: pd.DataFrame, best: str, h: int) -> None:
    p = preds.copy()
    p["target_date"] = pd.to_datetime(p.target_date)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.5), gridspec_kw={"width_ratios": [2.3, 1]})
    for ax, sub in [(a1, p), (a2, None)]:
        if sub is None:
            wet = p.set_index("target_date").y_true.rolling(90).mean().idxmax()
            sub = p[(p.target_date > wet - pd.Timedelta(days=100)) & (p.target_date < wet + pd.Timedelta(days=30))]
        ax.plot(sub.target_date, sub.y_true, color=OKABE["black"], lw=0.9, label="observed")
        ax.plot(sub.target_date, sub.persistence, color=MODEL_COLORS["persistence"], lw=0.8,
                ls="--", label="persistence")
        ax.plot(sub.target_date, sub[best], color=MODEL_COLORS[best], lw=0.9, label=f"{best} (val-selected)")
        ax.plot(sub.target_date, sub.threshold, color=OKABE["vermillion"], lw=0.6, ls=":",
                label="drought threshold (monthly Q20)")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y" if ax is a2 else "%Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1) if ax is a2 else mdates.YearLocator())
        if ax is a2:
            for lab in ax.get_xticklabels()[1::2]:
                lab.set_visible(False)
    a1.set_ylabel("Q (m$^3$ s$^{-1}$)")
    a1.set_title(f"(a) Test period, lead {h} d", loc="left")
    a2.set_title("(b) Zoom: wettest season", loc="left")
    a1.legend(ncol=2, loc="upper left")
    save(fig, f"fig02_focus_forecast_h{h}")


def fig_skill_heatmap(met: pd.DataFrame, h: int) -> None:
    m = met[(met.horizon == h) & met.model.isin(["climatology"] + LEARNERS)]
    order = station_order(met)
    piv = m.pivot(index="gauge_id", columns="model", values="skill_vs_persistence").loc[order.gauge_id]
    lo = m.pivot(index="gauge_id", columns="model", values="skill_lo").loc[order.gauge_id]
    piv = piv[["climatology"] + LEARNERS]
    lo = lo[piv.columns]
    fig, ax = plt.subplots(figsize=(5.2, 5.0))
    vmax = 0.4
    sns.heatmap(piv.clip(-vmax, vmax), cmap=cmc.vik_r, center=0, vmin=-vmax, vmax=vmax, ax=ax,
                annot=piv.round(2), fmt="", annot_kws={"fontsize": 6},
                cbar_kws={"label": "RMSE skill vs persistence (clipped ±0.4)", "shrink": 0.7},
                linewidths=0.4, linecolor="white")
    for i, gid in enumerate(piv.index):
        for j, c in enumerate(piv.columns):
            if lo.loc[gid, c] > 0:
                ax.add_patch(plt.Rectangle((j, i), 1, 1, fill=False, ec="black", lw=0.9))
    ax.set_yticklabels([short(n) for n in order.gauge_name], rotation=0)
    for lab, r in zip(ax.get_yticklabels(), order.region):
        lab.set_color(REGION_COLORS[r]); lab.set_fontweight("bold")
    ax.set_xticklabels(["Clim." if c == "climatology" else c for c in piv.columns], rotation=30, ha="right")
    ax.set_xlabel(""); ax.set_ylabel("")
    ax.set_title(f"Skill vs persistence at lead {h} d (boxed: 95% block-bootstrap CI > 0)", loc="left")
    handles = [mpl.patches.Patch(color=REGION_COLORS[r], label=r) for r in REGION_ORDER]
    fig.legend(handles=handles, loc="lower center", ncol=3, bbox_to_anchor=(0.45, -0.03),
               title="gauge label colour = region", title_fontsize=7)
    save(fig, f"fig03_skill_heatmap_h{h}")


def fig_lead_skill(met: pd.DataFrame) -> None:
    b = val_selected(met)
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.4), sharey=True)
    for ax, r in zip(axes, REGION_ORDER):
        sub = b[b.region == r]
        for gid, g in sub.groupby("gauge_id"):
            g = g.sort_values("horizon")
            ax.plot(g.horizon, g.skill_vs_persistence, color=REGION_COLORS[r], alpha=0.35, lw=0.7,
                    marker="o", ms=2)
        med = sub.groupby("horizon").skill_vs_persistence.median()
        ax.plot(med.index, med.values, color=REGION_COLORS[r], lw=2.0, marker="o", ms=4, label="median")
        ax.axhline(0, color="black", lw=0.5)
        ax.set_xticks(cfg.HORIZONS)
        ax.set_xlabel("lead time (days)")
        ax.set_title(f"{r} (n={sub.gauge_id.nunique()})", loc="left")
    axes[0].set_ylabel("skill of val-selected learner")
    axes[0].legend(loc="upper left")
    save(fig, "fig04_lead_skill_by_region")


def fig_drought(met: pd.DataFrame, h: int) -> None:
    b = val_selected(met)
    b = b[b.horizon == h].set_index("gauge_id")
    p = met[(met.horizon == h) & (met.model == "persistence")].set_index("gauge_id")
    xl = met[(met.horizon == h) & (met.model == "XGBoost-log")].set_index("gauge_id")
    order = station_order(met)
    order = order[order.gauge_id.isin(b.index)]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.6), sharey=True)
    y = np.arange(len(order))[::-1]
    for ax, metric, lab in [(axes[0], "drought_CSI", "CSI (higher is better)"),
                            (axes[1], "drought_FAR", "FAR (lower is better)")]:
        pv, bv = p.loc[order.gauge_id, metric].values, b.loc[order.gauge_id, metric].values
        xv = xl.loc[order.gauge_id, metric].values
        for yi, a, c, r in zip(y, pv, bv, order.region):
            ax.plot([a, c], [yi, yi], color="#BBBBBB", lw=1.2, zorder=1)
        ax.scatter(pv, y, color=MODEL_COLORS["persistence"], s=16, zorder=2, label="persistence")
        ax.scatter(bv, y, c=[REGION_COLORS[r] for r in order.region], s=22, marker="D", zorder=3,
                   label="val-selected learner")
        ax.scatter(xv, y, facecolor="none", edgecolor=OKABE["black"], s=24, marker="^", lw=0.7,
                   zorder=4, label="XGBoost-log")
        ax.set_xlabel(lab)
        ax.set_xlim(0, 1)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([short(n) for n in order.gauge_name])
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, bbox_to_anchor=(0.55, 0.0))
    fig.suptitle(f"Drought-day detection at lead {h} d (variable threshold, monthly Q20 of fit period)",
                 x=0.02, ha="left", fontsize=8.5)
    save(fig, f"fig05_drought_detection_h{h}")


def fig_fusion(fus: pd.DataFrame, h: int) -> None:
    f = fus[(fus.horizon == h) & fus.model.isin(["Ridge", "XGBoost"])]
    if f.empty:
        return
    piv = f.pivot_table(index=["gauge_id", "gauge_name", "region", "model"], columns="feature_set",
                        values="skill_vs_persistence").reset_index()
    piv["delta"] = piv.fused - piv.base
    g = fus[(fus.horizon == h) & (fus.model == "GloFAS")].set_index("gauge_id")
    order = station_order(piv)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 3.0), sharey=True,
                                 gridspec_kw={"width_ratios": [1.4, 1]})
    y = {gid: i for i, gid in enumerate(order.gauge_id[::-1])}
    for mdl, off, mk in [("Ridge", -0.15, "o"), ("XGBoost", 0.15, "s")]:
        s = piv[piv.model == mdl]
        a1.barh([y[x] + off for x in s.gauge_id], s.delta, height=0.28, color=MODEL_COLORS[mdl], label=mdl)
    a1.axvline(0, color="black", lw=0.5)
    a1.set_xlabel("Δ skill (fused − ERA5-only)")
    a1.set_yticks(list(y.values()))
    a1.set_yticklabels([short(n) for n in order.gauge_name[::-1]])
    a1.legend(loc="lower right")
    a1.set_title(f"(a) Adding MERRA-2 precipitation + GloFAS, lead {h} d", loc="left")
    gv = g.reindex(order.gauge_id[::-1]).NSE.values
    a2.barh(list(y.values()), np.clip(gv, -1, 1), color=[REGION_COLORS[r] for r in order.region[::-1]])
    a2.axvline(0, color="black", lw=0.5)
    a2.set_xlim(-1, 1)
    a2.set_xlabel("NSE of raw GloFAS simulation (clipped at −1)")
    a2.set_title("(b) GloFAS v4 reanalysis vs gauge", loc="left")
    save(fig, f"fig06_fusion_ablation_h{h}")


def fig_walkforward(wf: pd.DataFrame, h: int) -> None:
    w = wf[wf.horizon == h].copy()
    order = station_order(w)
    w["label"] = w.gauge_name.map(short)
    fig, ax = plt.subplots(figsize=(7.0, 2.6))
    x = {gid: i for i, gid in enumerate(order.gauge_id)}
    for fold, mk in zip([1, 2, 3], ["o", "s", "^"]):
        s = w[w.fold == fold]
        ax.scatter([x[g] + (fold - 2) * 0.18 for g in s.gauge_id], s.skill_vs_persistence,
                   c=[REGION_COLORS[r] for r in s.region], marker=mk, s=18, label=f"fold {fold}",
                   edgecolor="black", linewidth=0.3)
    ax.axhline(0, color="black", lw=0.5)
    ax.set_xticks(list(x.values()))
    ax.set_xticklabels([short(n) for n in order.gauge_name], rotation=60, ha="right")
    ax.set_ylabel("Ridge skill vs persistence")
    ax.set_title(f"Expanding-window walk-forward, lead {h} d", loc="left")
    leg = ax.legend(loc="upper right", ncol=3)
    for hd in leg.legend_handles:
        hd.set_facecolor("white")
    save(fig, f"fig07_walkforward_h{h}")


def main() -> None:
    style()
    met = pd.read_csv(cfg.TAB / "metrics_by_station.csv")
    fus = pd.read_csv(cfg.TAB / "metrics_fusion_ablation.csv")
    wf = pd.read_csv(cfg.TAB / "metrics_walkforward.csv")
    ssi = pd.read_csv(cfg.PROC / "ssi30_all_gauges.csv")
    meta = json.load(open(cfg.TAB / "experiment_meta.json"))
    fig_focus_hydrograph_ssi(ssi, meta["splits"][cfg.FOCUS_STATION_ID])
    best = val_selected(met)
    for h in cfg.HORIZONS:
        pf = cfg.PROC / f"predictions_{cfg.FOCUS_STATION_ID}_h{h}.csv"
        b = best[(best.gauge_id == cfg.FOCUS_STATION_ID) & (best.horizon == h)].model.iloc[0]
        if h == 7 and pf.exists():
            fig_focus_forecast(pd.read_csv(pf), b, h)
    fig_skill_heatmap(met, 7)
    fig_lead_skill(met)
    fig_drought(met, 7)
    fig_fusion(fus, 7)
    fig_walkforward(wf, 7)


if __name__ == "__main__":
    main()
