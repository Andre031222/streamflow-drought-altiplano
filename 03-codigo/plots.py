"""Publication-quality figures (600 dpi PNG + PDF), colorblind-friendly."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

COLORS = {
    "obs": "#000000",
    "persist": "#E69F00",
    "clim": "#56B4E9",
    "ridge": "#009E73",
    "rf": "#CC79A7",
    "gb": "#D55E00",
    "xgb": "#0072B2",
    "mlp": "#F0E442",
    "train": "#0072B2",
    "val": "#E69F00",
    "test": "#D55E00",
    "ssi_pos": "#009E73",
    "ssi_neg": "#D55E00",
}

MODEL_CMAP = {
    "persistence": COLORS["persist"],
    "climatology": COLORS["clim"],
    "Ridge": COLORS["ridge"],
    "RandomForest": COLORS["rf"],
    "GradientBoosting": COLORS["gb"],
    "XGBoost": COLORS["xgb"],
    "MLP": COLORS["mlp"],
}


def _style():
    mpl.rcParams.update({
        "figure.dpi": 150,
        "savefig.dpi": 600,
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "legend.fontsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linestyle": "--",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def save_fig(fig, path_stem: Path):
    path_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{path_stem}.png", dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(f"{path_stem}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_hydrograph(df: pd.DataFrame, splits: dict, out: Path, station: str):
    _style()
    fig, ax = plt.subplots(figsize=(10, 3.8))
    qcol = "discharge_m3s" if "discharge_m3s" in df.columns else "q"
    ax.plot(df["date"], df[qcol], color=COLORS["obs"], lw=0.6, label="Observed Q")
    for name, color, alpha in [
        ("train", COLORS["train"], 0.08),
        ("val", COLORS["val"], 0.12),
        ("test", COLORS["test"], 0.10),
    ]:
        d0, d1 = splits[name]
        ax.axvspan(d0, d1, color=color, alpha=alpha, label=f"{name.capitalize()} split")
    ax.set_ylabel("Discharge (m3/s)")
    ax.set_xlabel("Date")
    ax.set_title(f"Daily streamflow — {station}")
    ax.legend(ncol=4, loc="upper right", frameon=False)
    save_fig(fig, out)


def plot_forecast_compare(dates, y_true, preds: dict, out: Path, horizon: int, station: str):
    _style()
    fig, ax = plt.subplots(figsize=(10, 3.8))
    ax.plot(dates, y_true, color=COLORS["obs"], lw=1.0, label="Observed")
    style_map = {
        "persistence": (COLORS["persist"], "--", 1.0),
        "climatology": (COLORS["clim"], ":", 1.0),
        "Ridge": (COLORS["ridge"], "-", 1.1),
        "RandomForest": (COLORS["rf"], "-", 1.1),
        "GradientBoosting": (COLORS["gb"], "-", 1.1),
        "XGBoost": (COLORS["xgb"], "-", 1.2),
        "MLP": (COLORS["mlp"], "-.", 1.0),
    }
    for name, yhat in preds.items():
        c, ls, lw = style_map.get(name, ("#333333", "-", 1.0))
        ax.plot(dates, yhat, color=c, ls=ls, lw=lw, label=name, alpha=0.9)
    ax.set_ylabel("Discharge (m3/s)")
    ax.set_xlabel("Date")
    ax.set_title(f"Test-period forecasts — {station} (lead {horizon} d)")
    ax.legend(ncol=3, loc="upper right", frameon=False)
    save_fig(fig, out)


def plot_skill_bars(metrics_df: pd.DataFrame, out: Path, station: str):
    _style()
    horizons = sorted(metrics_df["horizon"].unique())
    models = list(dict.fromkeys(metrics_df["model"]))
    x = np.arange(len(models))
    width = 0.35 if len(horizons) == 2 else 0.8 / max(len(horizons), 1)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, metric, ylabel in zip(
        axes, ["NSE", "skill_vs_persistence"], ["NSE", "Skill vs persistence"]
    ):
        for i, h in enumerate(horizons):
            sub = metrics_df[metrics_df.horizon == h].set_index("model").reindex(models)
            vals = sub[metric].values
            offset = (i - (len(horizons) - 1) / 2) * width
            ax.bar(
                x + offset, vals, width, label=f"lead {h} d",
                color=[MODEL_CMAP.get(m, "#888") for m in models],
                edgecolor="white", linewidth=0.5, alpha=0.85 if i == 0 else 0.55,
            )
        ax.axhline(0, color="k", lw=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels(models, rotation=25, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_title(ylabel)
        ax.legend(frameon=False)
    fig.suptitle(f"Test skill by model — {station}", y=1.02, fontsize=12)
    fig.tight_layout()
    save_fig(fig, out)


def plot_scatter(y_true, y_pred, out: Path, model: str, horizon: int, nse_val: float):
    _style()
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    ax.scatter(y_true, y_pred, s=8, alpha=0.35, c=COLORS["xgb"], edgecolors="none")
    lims = [0, max(np.nanmax(y_true), np.nanmax(y_pred)) * 1.05]
    ax.plot(lims, lims, "k--", lw=1, label="1:1")
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.set_xlabel("Observed Q (m3/s)")
    ax.set_ylabel("Predicted Q (m3/s)")
    ax.set_title(f"{model} · lead {horizon} d · NSE={nse_val:.3f}")
    ax.set_aspect("equal")
    ax.legend(frameon=False)
    save_fig(fig, out)


def plot_ssi(dates, ssi, out: Path, station: str):
    _style()
    fig, ax = plt.subplots(figsize=(10, 3.2))
    s = np.asarray(ssi, dtype=float)
    ax.fill_between(
        dates, s, 0, where=s >= 0, color=COLORS["ssi_pos"], alpha=0.5,
        interpolate=True, label="Wet / high flow",
    )
    ax.fill_between(
        dates, s, 0, where=s < 0, color=COLORS["ssi_neg"], alpha=0.5,
        interpolate=True, label="Dry / low flow",
    )
    ax.axhline(-1.0, color="#D55E00", ls="--", lw=0.9, label="Moderate drought (-1)")
    ax.axhline(-1.5, color="#D55E00", ls=":", lw=0.9, label="Severe (-1.5)")
    ax.set_ylabel("SSI-30 (z-score of 30d mean)")
    ax.set_xlabel("Date")
    ax.set_title(f"Standardized Streamflow Index (30-day) — {station}")
    ax.legend(ncol=4, loc="lower left", frameon=False)
    save_fig(fig, out)


def plot_multi_station_skill_heatmap(metrics_df: pd.DataFrame, out: Path, horizon: int = 7):
    """Heatmap of skill_vs_persistence by station x model at a given horizon."""
    _style()
    sub = metrics_df[
        (metrics_df.horizon == horizon)
        & (~metrics_df.model.isin(["persistence"]))
    ].copy()
    if sub.empty:
        return
    pivot = sub.pivot_table(
        index="gauge_name", columns="model", values="skill_vs_persistence", aggfunc="mean"
    )
    # Order stations by median skill
    pivot = pivot.loc[pivot.median(axis=1).sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(10, max(4.5, 0.35 * len(pivot))))
    im = ax.imshow(pivot.values, aspect="auto", cmap="RdYlGn", vmin=-0.5, vmax=0.5)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=30, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            if np.isfinite(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7,
                        color="black" if abs(v) < 0.35 else "white")
    ax.set_title(f"Skill vs persistence by station (lead {horizon} d)")
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02, label="Skill")
    fig.tight_layout()
    save_fig(fig, out)


def plot_multi_station_nse_bars(metrics_df: pd.DataFrame, out: Path, horizon: int = 7,
                                model: str = "Ridge"):
    """Horizontal bars of NSE for one model across stations."""
    _style()
    sub = metrics_df[(metrics_df.horizon == horizon) & (metrics_df.model == model)].copy()
    pers = metrics_df[(metrics_df.horizon == horizon) & (metrics_df.model == "persistence")][
        ["gauge_id", "NSE"]
    ].rename(columns={"NSE": "NSE_persist"})
    sub = sub.merge(pers, on="gauge_id", how="left")
    sub = sub.sort_values("NSE", ascending=True)
    fig, ax = plt.subplots(figsize=(8, max(4.0, 0.32 * len(sub))))
    y = np.arange(len(sub))
    ax.barh(y, sub["NSE"].values, color=MODEL_CMAP.get(model, "#555"), alpha=0.85, label=model)
    ax.scatter(sub["NSE_persist"].values, y, color=COLORS["persist"], marker="|", s=120,
               linewidths=2, label="persistence", zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(sub["gauge_name"].values)
    ax.axvline(0, color="k", lw=0.6)
    ax.set_xlabel("NSE")
    ax.set_title(f"Multi-station NSE at lead {horizon} d ({model} vs persistence)")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    save_fig(fig, out)


def plot_lead_skill_curve(metrics_df: pd.DataFrame, out: Path, station: str):
    """NSE by lead for focus station (models as lines)."""
    _style()
    sub = metrics_df[metrics_df.gauge_name == station].copy()
    if sub.empty:
        # try partial name match
        sub = metrics_df[metrics_df.gauge_name.str.contains(station.split()[0], case=False, na=False)]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for model, g in sub.groupby("model"):
        g = g.sort_values("horizon")
        ax.plot(
            g["horizon"], g["NSE"], marker="o", lw=1.5,
            color=MODEL_CMAP.get(model, "#333"), label=model,
        )
    ax.set_xlabel("Lead time (days)")
    ax.set_ylabel("NSE")
    ax.set_xticks(sorted(sub["horizon"].unique()))
    ax.set_title(f"Lead-time skill curve — {station}")
    ax.legend(ncol=2, frameon=False, fontsize=8)
    fig.tight_layout()
    save_fig(fig, out)
