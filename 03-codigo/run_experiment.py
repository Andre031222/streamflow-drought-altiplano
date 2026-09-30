#!/usr/bin/env python3
"""
Multi-station Peru streamflow forecasting benchmark (Andean-GC + Open-Meteo).

Primary focus: SENAMHI gauge Puente Isla Cabanillas (Altiplano / Titicaca system).
Benchmark: Peru gauges with days_w_data_qc >= 5000.

Usage (from project root, with venv activated):
    export MPLBACKEND=Agg
    python 03-codigo/run_experiment.py
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as cfg
from metrics_utils import summarize
import plots

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    from xgboost import XGBRegressor
    HAS_XGB = True
except Exception:
    HAS_XGB = False


def load_station_meta() -> pd.DataFrame:
    return pd.read_csv(cfg.STATION_META)


def load_merged(gauge_id: str, slug: str) -> pd.DataFrame:
    """Load discharge + precip for one station, align on calendar day."""
    q_path = cfg.STATIONS_DIR / f"{gauge_id}_{slug}_daily_qc.csv"
    p_path = cfg.OPENMETEO_DIR / f"precip_{gauge_id}_{slug}_daily.csv"
    q = pd.read_csv(q_path, parse_dates=["date"])
    q = q.rename(columns={"discharge_m3s": "q"})
    p = pd.read_csv(p_path, parse_dates=["date"])
    p = p.rename(columns={"precip_mm": "precip"})
    df = q.merge(p, on="date", how="inner")
    df = df.sort_values("date").reset_index(drop=True)
    return df


def add_features(df: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Build lag/rolling/calendar features; target is q at t+horizon."""
    out = df.copy()
    out["doy"] = out["date"].dt.dayofyear
    out["month"] = out["date"].dt.month
    out["sin_doy"] = np.sin(2 * np.pi * out["doy"] / 365.25)
    out["cos_doy"] = np.cos(2 * np.pi * out["doy"] / 365.25)

    for lag in cfg.LAGS_Q:
        out[f"q_lag{lag}"] = out["q"].shift(lag)
    for w in cfg.ROLL_WINDOWS:
        out[f"q_roll{w}"] = out["q"].shift(1).rolling(w, min_periods=max(3, w // 3)).mean()
        out[f"q_std{w}"] = out["q"].shift(1).rolling(w, min_periods=max(3, w // 3)).std()

    if "precip" in out.columns:
        for lag in cfg.LAGS_P:
            out[f"p_lag{lag}"] = out["precip"].shift(lag)
        out["p_roll7"] = out["precip"].shift(0).rolling(7, min_periods=3).sum()
        out["p_roll30"] = out["precip"].shift(0).rolling(30, min_periods=10).sum()

    out["y"] = out["q"].shift(-horizon)
    out["y_persist"] = out["q"]
    return out


def temporal_split(df: pd.DataFrame):
    """Chronological train/val/test (no shuffle)."""
    n = len(df)
    n_train = int(n * cfg.TRAIN_FRAC)
    n_val = int(n * cfg.VAL_FRAC)
    train = df.iloc[:n_train]
    val = df.iloc[n_train : n_train + n_val]
    test = df.iloc[n_train + n_val :]
    return train, val, test


def feature_columns(df: pd.DataFrame) -> list[str]:
    exclude = {"date", "q", "precip", "y", "y_persist", "doy", "month", "ssi30"}
    return [c for c in df.columns if c not in exclude]


def climatology_predict(train: pd.DataFrame, target_dates: pd.Series) -> np.ndarray:
    """Seasonal mean by day-of-year (smoothed with 7-day circular rolling)."""
    tmp = train[["date", "y"]].dropna().copy()
    tmp["doy"] = tmp["date"].dt.dayofyear
    daily = tmp.groupby("doy")["y"].mean()
    full = pd.Series(index=np.arange(1, 367), dtype=float)
    full.loc[daily.index] = daily.values
    full = full.ffill().bfill()
    vals = full.values
    ext = np.r_[vals[-3:], vals, vals[:3]]
    smooth = pd.Series(ext).rolling(7, center=True).mean().iloc[3:-3].values
    clim = pd.Series(smooth, index=full.index)
    doys = target_dates.dt.dayofyear.values
    return clim.loc[doys].values.astype(float)


def build_models() -> dict:
    models = {
        "Ridge": Pipeline([
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=1.0, random_state=cfg.RANDOM_STATE)),
        ]),
        "RandomForest": RandomForestRegressor(
            n_estimators=cfg.RF_N_EST,
            max_depth=10,
            min_samples_leaf=5,
            random_state=cfg.RANDOM_STATE,
            n_jobs=cfg.N_JOBS,
        ),
        "GradientBoosting": GradientBoostingRegressor(
            n_estimators=cfg.GB_N_EST,
            max_depth=3,
            learning_rate=0.05,
            random_state=cfg.RANDOM_STATE,
        ),
        "MLP": Pipeline([
            ("scaler", StandardScaler()),
            ("model", MLPRegressor(
                hidden_layer_sizes=(64, 32),
                activation="relu",
                max_iter=cfg.MLP_MAX_ITER,
                early_stopping=True,
                random_state=cfg.RANDOM_STATE,
            )),
        ]),
    }
    if HAS_XGB:
        models["XGBoost"] = XGBRegressor(
            n_estimators=cfg.XGB_N_EST,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="reg:squarederror",
            random_state=cfg.RANDOM_STATE,
            n_jobs=cfg.N_JOBS,
        )
    return models


def ssi30_zscore_by_month(dates: pd.Series, q: pd.Series, window: int = 30) -> pd.Series:
    """SSI-30 as month-wise z-score of the 30-day rolling mean discharge.

    This is a parametric/normal approximation (z-score), NOT the full
    Vicente-Serrano et al. (2012) distributional SSI that fits a probability
    distribution per calendar month and transforms to a standard normal via
    the cumulative distribution. Limitations: assumes approximate normality
    within each month after rolling; sensitive to zeros/skew; intended as an
    illustrative drought indicator for this open benchmark, not an operational
    SSI product.
    """
    q30 = q.rolling(window, min_periods=max(15, window // 2)).mean()
    month = dates.dt.month
    out = pd.Series(np.nan, index=q.index, dtype=float)
    for m in range(1, 13):
        mask = month == m
        vals = q30[mask]
        mu = vals.mean()
        sd = vals.std()
        if sd and sd > 0:
            out.loc[mask] = (vals - mu) / sd
        else:
            out.loc[mask] = 0.0
    return out


def run_horizon(df_raw: pd.DataFrame, horizon: int, station_info: dict) -> tuple:
    feat = add_features(df_raw, horizon)
    cols = feature_columns(feat)
    needed = ["y", "y_persist"] + cols
    data = feat.dropna(subset=needed).reset_index(drop=True)
    if len(data) < cfg.MIN_ROWS_AFTER_FEATURES:
        return None, None, None

    train, val, test = temporal_split(data)
    if len(test) < 50 or len(train) < 200:
        return None, None, None

    X_cols = cols
    y_test = test["y"].values
    persist = test["y_persist"].values
    clim = climatology_predict(train, test["date"])

    rows = []
    pred_store = {
        "date": test["date"].values,
        "y_true": y_test,
        "persistence": persist,
        "climatology": clim,
    }
    base_meta = {
        "gauge_id": station_info["gauge_id"],
        "gauge_name": station_info["gauge_name"],
        "horizon": horizon,
        "n_test": len(test),
        "n_train": len(train),
        "n_val": len(val),
        "validation": "chronological",
    }

    for model_name, yhat in [("persistence", persist), ("climatology", clim)]:
        rows.append({**base_meta, "model": model_name, **summarize(y_test, yhat, persist)})

    models = build_models()
    X_train = train[X_cols].values
    y_train = train["y"].values
    X_test = test[X_cols].values

    for name, model in models.items():
        t0 = time.time()
        model.fit(X_train, y_train)
        yhat = model.predict(X_test)
        elapsed = time.time() - t0
        pred_store[name] = yhat
        rows.append({
            **base_meta,
            "model": name,
            **summarize(y_test, yhat, persist),
            "fit_seconds": round(elapsed, 3),
        })
        print(
            f"  [{station_info['gauge_id']} h={horizon}d] {name:18s} "
            f"NSE={rows[-1]['NSE']:.3f} KGE={rows[-1]['KGE']:.3f} ({elapsed:.1f}s)"
        )

    metrics = pd.DataFrame(rows)
    preds = pd.DataFrame(pred_store)
    meta = {
        "splits": {
            "train": (train["date"].iloc[0], train["date"].iloc[-1]),
            "val": (val["date"].iloc[0], val["date"].iloc[-1]),
            "test": (test["date"].iloc[0], test["date"].iloc[-1]),
        },
        "features": X_cols,
        "n_rows": len(data),
    }
    return metrics, meta, preds


def walk_forward_focus(df_raw: pd.DataFrame, horizon: int, station_info: dict) -> pd.DataFrame:
    """Expanding-window walk-forward check on the focus station (Ridge + persistence)."""
    feat = add_features(df_raw, horizon)
    cols = feature_columns(feat)
    needed = ["y", "y_persist"] + cols
    data = feat.dropna(subset=needed).reset_index(drop=True)
    n = len(data)
    min_train = int(n * cfg.WF_MIN_TRAIN_FRAC)
    # remaining length after min_train split into WF_N_SPLITS test blocks
    rem = n - min_train
    block = rem // cfg.WF_N_SPLITS
    if block < 40:
        return pd.DataFrame()

    rows = []
    for i in range(cfg.WF_N_SPLITS):
        train_end = min_train + i * block
        test_start = train_end
        test_end = n if i == cfg.WF_N_SPLITS - 1 else train_end + block
        train = data.iloc[:train_end]
        test = data.iloc[test_start:test_end]
        if len(test) < 30:
            continue
        y_test = test["y"].values
        persist = test["y_persist"].values
        X_train = train[cols].values
        y_train = train["y"].values
        X_test = test[cols].values

        # Persistence
        rows.append({
            "gauge_id": station_info["gauge_id"],
            "gauge_name": station_info["gauge_name"],
            "horizon": horizon,
            "fold": i + 1,
            "model": "persistence",
            "validation": "walk_forward_expanding",
            "n_train": len(train),
            "n_test": len(test),
            "test_start": str(test["date"].iloc[0].date()),
            "test_end": str(test["date"].iloc[-1].date()),
            **summarize(y_test, persist, persist),
        })
        # Ridge only (fast, competitive at h=7)
        model = Pipeline([
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=1.0, random_state=cfg.RANDOM_STATE)),
        ])
        model.fit(X_train, y_train)
        yhat = model.predict(X_test)
        rows.append({
            "gauge_id": station_info["gauge_id"],
            "gauge_name": station_info["gauge_name"],
            "horizon": horizon,
            "fold": i + 1,
            "model": "Ridge",
            "validation": "walk_forward_expanding",
            "n_train": len(train),
            "n_test": len(test),
            "test_start": str(test["date"].iloc[0].date()),
            "test_end": str(test["date"].iloc[-1].date()),
            **summarize(y_test, yhat, persist),
        })
        print(
            f"  [WF fold {i+1} h={horizon}] Ridge NSE={rows[-1]['NSE']:.3f} "
            f"skill={rows[-1]['skill_vs_persistence']:.3f} "
            f"n_train={len(train)} n_test={len(test)}"
        )
    return pd.DataFrame(rows)


def main() -> None:
    t_global = time.time()
    cfg.PROC.mkdir(parents=True, exist_ok=True)
    cfg.FIG.mkdir(parents=True, exist_ok=True)
    cfg.TAB.mkdir(parents=True, exist_ok=True)

    meta = load_station_meta()
    print(f"Stations in meta: {len(meta)}")
    print(f"XGBoost available: {HAS_XGB}")

    all_metrics = []
    wf_metrics = []
    focus_bundle = {}
    used_stations = []
    skipped = []
    meta_all = {}

    for _, srow in meta.iterrows():
        info = {
            "gauge_id": srow.gauge_id,
            "gauge_name": srow.gauge_name,
            "slug": srow.slug,
        }
        print(f"\n=== {info['gauge_id']} {info['gauge_name']} ===")
        try:
            df = load_merged(info["gauge_id"], info["slug"])
        except Exception as e:
            print(f"  skip load error: {e}")
            skipped.append({**info, "reason": f"load:{e}"})
            continue
        print(f"  merged rows: {len(df)} | {df.date.min().date()} .. {df.date.max().date()}")

        station_ok = False
        for h in cfg.HORIZONS:
            metrics, hmeta, preds = run_horizon(df, h, info)
            if metrics is None:
                print(f"  skip h={h}: insufficient rows after features")
                continue
            station_ok = True
            all_metrics.append(metrics)
            meta_all[f"{info['gauge_id']}_h{h}"] = {
                "splits": {
                    k: [str(v[0].date()), str(v[1].date())]
                    for k, v in hmeta["splits"].items()
                },
                "n_features": len(hmeta["features"]),
                "n_rows": hmeta["n_rows"],
            }
            if info["gauge_id"] == cfg.FOCUS_STATION_ID:
                preds.to_csv(cfg.PROC / f"predictions_{info['gauge_id']}_h{h}.csv", index=False)
                focus_bundle[h] = (df, metrics, hmeta, preds)

        if not station_ok:
            skipped.append({**info, "reason": "insufficient_features"})
            continue

        used_stations.append(info)

        # SSI + walk-forward only for focus
        if info["gauge_id"] == cfg.FOCUS_STATION_ID:
            ssi = ssi30_zscore_by_month(df["date"], df["q"], window=30)
            ssi_df = pd.DataFrame({"date": df["date"], "q": df["q"], "ssi30": ssi})
            ssi_df.to_csv(cfg.PROC / "cabanillas_ssi30.csv", index=False)
            df.to_csv(cfg.PROC / "cabanillas_q_precip_daily.csv", index=False)
            print("\n--- Walk-forward (expanding) on focus station ---")
            for h in cfg.HORIZONS:
                wf = walk_forward_focus(df, h, info)
                if not wf.empty:
                    wf_metrics.append(wf)

    if not all_metrics:
        print("No stations produced metrics. Abort.")
        sys.exit(1)

    metrics_df = pd.concat(all_metrics, ignore_index=True)
    metrics_path = cfg.TAB / "metrics_by_station.csv"
    metrics_df.to_csv(metrics_path, index=False)
    print(f"\nWrote {metrics_path} ({len(metrics_df)} rows, {len(used_stations)} stations)")

    if wf_metrics:
        wf_df = pd.concat(wf_metrics, ignore_index=True)
        wf_path = cfg.TAB / "metrics_walkforward_cabanillas.csv"
        wf_df.to_csv(wf_path, index=False)
        print(f"Wrote {wf_path}")
    else:
        wf_df = pd.DataFrame()

    # Also keep single-station legacy name for focus chronological metrics
    focus_m = metrics_df[metrics_df.gauge_id == cfg.FOCUS_STATION_ID]
    focus_m.to_csv(cfg.TAB / "metrics_test.csv", index=False)

    with open(cfg.TAB / "experiment_meta.json", "w") as f:
        json.dump({
            "n_stations_used": len(used_stations),
            "stations_used": used_stations,
            "stations_skipped": skipped,
            "focus_station_id": cfg.FOCUS_STATION_ID,
            "focus_station_name": cfg.FOCUS_STATION_NAME,
            "has_xgboost": HAS_XGB,
            "horizons": cfg.HORIZONS,
            "ssi30_method": (
                "Month-wise z-score of 30-day rolling mean discharge "
                "(parametric approx.; not full Vicente-Serrano distributional SSI)"
            ),
            "by_station_horizon": meta_all,
            "runtime_seconds": round(time.time() - t_global, 1),
        }, f, indent=2)

    # --- Figures ---
    print("\nGenerating figures (600 dpi PNG + PDF)...")
    if focus_bundle:
        df_focus, met1, hmeta1, preds1 = focus_bundle[1]
        splits_plot = {
            k: (pd.Timestamp(v[0]), pd.Timestamp(v[1]))
            for k, v in hmeta1["splits"].items()
        }
        plots.plot_hydrograph(
            df_focus.dropna(subset=["q"]),
            splits_plot,
            cfg.FIG / "fig01_hydrograph_cabanillas",
            cfg.FOCUS_STATION_NAME,
        )
        for h, bundle in focus_bundle.items():
            _, met, _, preds = bundle
            ml_models = [
                m for m in ["XGBoost", "GradientBoosting", "RandomForest", "Ridge", "MLP"]
                if m in preds.columns
            ]
            show = {
                "persistence": preds["persistence"].values,
                "climatology": preds["climatology"].values,
            }
            # Prefer best skill ML models for overlay
            sub = met[~met.model.isin(["persistence", "climatology"])]
            if not sub.empty:
                best_names = sub.sort_values("NSE", ascending=False)["model"].head(2).tolist()
                for m in best_names:
                    if m in preds.columns:
                        show[m] = preds[m].values
            plots.plot_forecast_compare(
                preds["date"], preds["y_true"].values, show,
                cfg.FIG / f"fig02_forecast_test_h{h}",
                h, cfg.FOCUS_STATION_NAME,
            )
            best_row = sub.loc[sub["NSE"].idxmax()]
            best_name = best_row["model"]
            plots.plot_scatter(
                preds["y_true"].values, preds[best_name].values,
                cfg.FIG / f"fig03_scatter_best_h{h}",
                best_name, h, float(best_row["NSE"]),
            )
        plots.plot_skill_bars(
            focus_m, cfg.FIG / "fig04_skill_bars", cfg.FOCUS_STATION_NAME,
        )
        ssi_df = pd.read_csv(cfg.PROC / "cabanillas_ssi30.csv", parse_dates=["date"])
        plots.plot_ssi(
            ssi_df["date"], ssi_df["ssi30"].values,
            cfg.FIG / "fig05_ssi30", cfg.FOCUS_STATION_NAME,
        )
        plots.plot_lead_skill_curve(
            focus_m, cfg.FIG / "fig08_lead_skill_cabanillas", cfg.FOCUS_STATION_NAME,
        )

    plots.plot_multi_station_skill_heatmap(
        metrics_df, cfg.FIG / "fig06_multistation_skill_heatmap_h7", horizon=7,
    )
    plots.plot_multi_station_nse_bars(
        metrics_df, cfg.FIG / "fig07_multistation_nse_bars_h7", horizon=7, model="Ridge",
    )

    # --- Markdown summary ---
    summary_path = cfg.TAB / "metrics_summary.md"
    with open(summary_path, "w") as f:
        f.write("# Multi-station Peru benchmark — test metrics (real run)\n\n")
        f.write(f"Stations used: **{len(used_stations)}**\n\n")
        f.write("Focus (Altiplano): "
                f"{cfg.FOCUS_STATION_NAME} ({cfg.FOCUS_STATION_ID})\n\n")
        f.write("SSI-30: month-wise z-score of 30-day rolling mean "
                "(parametric approx.; see Vicente-Serrano et al. 2012 for full SSI).\n\n")

        f.write("## Focus station (chronological test)\n\n")
        if not focus_m.empty:
            cols = ["model", "horizon", "RMSE", "MAE", "NSE", "KGE",
                    "skill_vs_persistence", "n_test"]
            fm = focus_m[cols]
            f.write("| " + " | ".join(fm.columns) + " |\n")
            f.write("| " + " | ".join(["---"] * len(fm.columns)) + " |\n")
            for _, row in fm.iterrows():
                cells = []
                for c in fm.columns:
                    v = row[c]
                    cells.append(f"{v:.4f}" if isinstance(v, float) else str(v))
                f.write("| " + " | ".join(cells) + " |\n")

        f.write("\n## Multi-station highlights (lead 7 d)\n\n")
        h7 = metrics_df[metrics_df.horizon == 7]
        # Best skill model per station among ML
        ml = h7[~h7.model.isin(["persistence", "climatology"])]
        if not ml.empty:
            idx = ml.groupby("gauge_id")["skill_vs_persistence"].idxmax()
            best = ml.loc[idx][
                ["gauge_name", "model", "NSE", "KGE", "skill_vs_persistence"]
            ].sort_values("skill_vs_persistence", ascending=False)
            f.write("| gauge_name | best_model | NSE | KGE | skill |\n")
            f.write("| --- | --- | ---: | ---: | ---: |\n")
            for _, row in best.iterrows():
                f.write(
                    f"| {row.gauge_name} | {row.model} | {row.NSE:.3f} | "
                    f"{row.KGE:.3f} | {row.skill_vs_persistence:.3f} |\n"
                )
            f.write("\n")
            n_pos = int((best.skill_vs_persistence > 0).sum())
            f.write(f"Stations with positive skill at h=7 (best ML): "
                    f"{n_pos}/{len(best)}\n\n")
            med_skill = float(best.skill_vs_persistence.median())
            f.write(f"Median best-ML skill at h=7: {med_skill:.3f}\n\n")

        # Aggregate Ridge vs persistence
        ridge = h7[h7.model == "Ridge"]
        pers = h7[h7.model == "persistence"]
        if not ridge.empty and not pers.empty:
            f.write("### Ridge vs persistence at h=7 (all stations)\n\n")
            f.write(f"- Mean NSE Ridge: {ridge.NSE.mean():.3f}\n")
            f.write(f"- Mean NSE persistence: {pers.NSE.mean():.3f}\n")
            f.write(f"- Mean skill Ridge: {ridge.skill_vs_persistence.mean():.3f}\n")
            f.write(f"- Median skill Ridge: {ridge.skill_vs_persistence.median():.3f}\n")
            f.write(f"- Stations Ridge skill>0: "
                    f"{int((ridge.skill_vs_persistence > 0).sum())}/{len(ridge)}\n\n")

        if not wf_df.empty:
            f.write("## Walk-forward (expanding) — Cabanillas Ridge\n\n")
            wfr = wf_df[wf_df.model == "Ridge"][
                ["horizon", "fold", "NSE", "KGE", "skill_vs_persistence",
                 "n_train", "n_test", "test_start", "test_end"]
            ]
            f.write("| " + " | ".join(wfr.columns) + " |\n")
            f.write("| " + " | ".join(["---"] * len(wfr.columns)) + " |\n")
            for _, row in wfr.iterrows():
                cells = []
                for c in wfr.columns:
                    v = row[c]
                    cells.append(f"{v:.4f}" if isinstance(v, float) else str(v))
                f.write("| " + " | ".join(cells) + " |\n")

        f.write(f"\nRuntime: {time.time() - t_global:.1f} s\n")
        if skipped:
            f.write("\nSkipped: " + ", ".join(
                f"{s['gauge_id']}({s.get('reason','')})" for s in skipped
            ) + "\n")

    print(f"Wrote {summary_path}")
    print(f"Done in {time.time() - t_global:.1f}s | stations={len(used_stations)}")


if __name__ == "__main__":
    main()
