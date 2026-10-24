#!/usr/bin/env python3
"""
Leakage-free multi-station streamflow and hydrological-drought forecasting benchmark
for the Peruvian Andes and the Altiplano (Andean-GC + ERA5 + MERRA-2 + GloFAS).

Protocol (per gauge and lead time h in {1, 3, 7} days):
  1. Daily calendar index (gaps stay NaN, so lags/targets are true calendar offsets).
  2. Predictors use information available at issue time t (Q_t included, as for
     persistence); target Q_{t+h}.
  3. Chronological 70/15/15 split with an h-day embargo between blocks.
  4. Hyper-parameters and target form (level Q_{t+h} or change Q_{t+h}-Q_t) chosen on
     mean RMSE over three chronological validation blocks (the validation block and
     two earlier blocks of train); the chosen model is refit on train+val and scored
     once on test.
  5. Skill vs persistence with 95% moving-block-bootstrap intervals and a
     Diebold-Mariano test (Harvey et al. small-sample correction).
  6. Drought detection: variable-threshold level method (monthly 20th percentile of
     the fit period); POD/FAR/CSI of forecast vs observed below-threshold days, both
     raw and with a forecast-side threshold factor chosen on validation CSI.
  7. Data-fusion ablation (base = ERA5; fused = + MERRA-2 precip + GloFAS
     discharge) on identical rows where the extra sources overlap (>= 1984).
  8. Expanding-window walk-forward (3 folds, Ridge with inner validation) on every gauge.
  9. Resolution test: ERA5 vs ERA5 + CHIRPS (0.05 deg, catchment-mean) precipitation
     on identical rows (CHIRPS from 1981).

Usage (from project root, with venv activated):
    export MPLBACKEND=Agg
    python 03-codigo/fetch_data.py      # once
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
from joblib import Parallel, delayed
from scipy import stats
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg
from metrics_utils import (block_bootstrap_skill, diebold_mariano, drought_scores,
                           summarize)

warnings.filterwarnings("ignore")

BASELINES = ["persistence", "climatology"]
LEARNERS = ["Ridge", "RandomForest", "HistGB", "XGBoost", "MLP", "XGBoost-log"]


# --------------------------------------------------------------------------- data
def load_station(row) -> pd.DataFrame:
    """Daily calendar frame: q + ERA5 (+ MERRA-2, GloFAS candidate cells)."""
    q = pd.read_csv(cfg.STATIONS_DIR / f"{row.gauge_id}_{row.slug}_daily_qc.csv",
                    parse_dates=["date"]).rename(columns={"discharge_m3s": "q"})
    idx = pd.date_range(q.date.min(), q.date.max(), freq="D")
    df = q.set_index("date").reindex(idx)
    df.index.name = "date"
    era = pd.read_csv(cfg.CLIMATE_DIR / "era5" / f"{row.gauge_id}.csv", parse_dates=["date"])
    df = df.join(era.set_index("date"), how="left")
    pw = cfg.CLIMATE_DIR / "merra2_power" / f"{row.gauge_id}.csv"
    if pw.exists():
        df = df.join(pd.read_csv(pw, parse_dates=["date"]).set_index("date"), how="left")
    ch = cfg.CLIMATE_DIR / "chirps" / f"{row.gauge_id}.csv"
    if ch.exists():
        df = df.join(pd.read_csv(ch, parse_dates=["date"]).set_index("date"), how="left")
    gl = cfg.CLIMATE_DIR / "glofas" / f"{row.gauge_id}.csv"
    if gl.exists():
        g = pd.read_csv(gl, parse_dates=["date"]).set_index("date").add_prefix("glofas_")
        df = df.join(g, how="left")
    return df.reset_index()


def snap_glofas(df: pd.DataFrame, fit_end: pd.Timestamp) -> pd.Series | None:
    """Pick the GloFAS cell with best KGE against observed Q over the fit period only."""
    from metrics_utils import kge
    cells = [c for c in df.columns if c.startswith("glofas_cell")]
    if not cells:
        return None
    fit = df[df.date <= fit_end]
    best, best_k = None, -np.inf
    for c in cells:
        m = fit[["q", c]].dropna()
        if len(m) < 365:
            continue
        k = kge(m.q.values, m[c].values)
        if np.isfinite(k) and k > best_k:
            best, best_k = c, k
    return None if best is None else df[best]


# ----------------------------------------------------------------------- features
def add_features(df: pd.DataFrame, h: int, fused: bool = False,
                 chirps: bool = False) -> tuple[pd.DataFrame, list]:
    out = df.copy()
    doy = out.date.dt.dayofyear
    out["sin_doy"] = np.sin(2 * np.pi * doy / 365.25)
    out["cos_doy"] = np.cos(2 * np.pi * doy / 365.25)
    cols = ["sin_doy", "cos_doy"]
    for lag in cfg.LAGS_Q:
        out[f"q_lag{lag}"] = out.q.shift(lag); cols.append(f"q_lag{lag}")
    for w in cfg.ROLL_WINDOWS:  # windows end at t (inclusive): no future information
        r = out.q.rolling(w, min_periods=int(0.8 * w))
        out[f"q_mean{w}"] = r.mean(); out[f"q_std{w}"] = r.std()
        cols += [f"q_mean{w}", f"q_std{w}"]
    out["q_diff1"] = out.q - out.q.shift(1); cols.append("q_diff1")

    def precip_block(src: str, tag: str):
        for lag in cfg.LAGS_P:
            out[f"{tag}_lag{lag}"] = out[src].shift(lag); cols.append(f"{tag}_lag{lag}")
        for w in cfg.P_SUMS:
            out[f"{tag}_sum{w}"] = out[src].rolling(w, min_periods=int(0.8 * w)).sum()
            cols.append(f"{tag}_sum{w}")

    precip_block("precip_era5", "p")
    out["t2m_mean7"] = out.t2m_era5.rolling(7, min_periods=5).mean()
    out["t2m_mean30"] = out.t2m_era5.rolling(30, min_periods=24).mean()
    cols += ["t2m_era5", "t2m_mean7", "t2m_mean30"]

    if chirps:
        precip_block("precip_chirps", "pch")
    if fused:
        precip_block("precip_merra2", "pm2")
        out["gq_lag0"] = out["glofas_q"]
        out["gq_lag1"] = out["glofas_q"].shift(1)
        out["gq_mean7"] = out["glofas_q"].rolling(7, min_periods=6).mean()
        out["gq_diff1"] = out["glofas_q"] - out["gq_lag1"]
        cols += ["gq_lag0", "gq_lag1", "gq_mean7", "gq_diff1"]

    out["y"] = out.q.shift(-h)
    out["target_date"] = out.date + pd.Timedelta(days=h)
    out["y_persist"] = out.q
    return out, cols


def split_with_embargo(data: pd.DataFrame, h: int):
    """Chronological 70/15/15 split; drop the last h rows of train/val (target overlap)."""
    n = len(data)
    a, b = int(n * cfg.TRAIN_FRAC), int(n * (cfg.TRAIN_FRAC + cfg.VAL_FRAC))
    train = data.iloc[: max(a - h, 0)]
    val = data.iloc[a: max(b - h, a)]
    test = data.iloc[b:]
    return train, val, test


def climatology_predict(fit: pd.DataFrame, target_dates: pd.Series) -> np.ndarray:
    """Day-of-year mean of Q on the fit period, circularly smoothed (15 d), by target date."""
    tmp = pd.DataFrame({"doy": fit.target_date.dt.dayofyear.values, "y": fit.y.values})
    daily = tmp.groupby("doy").y.mean().reindex(range(1, 367)).interpolate().ffill().bfill()
    v = daily.values
    ext = np.r_[v[-7:], v, v[:7]]
    smooth = pd.Series(ext).rolling(15, center=True).mean().values[7:-7]
    return smooth[target_dates.dt.dayofyear.values - 1]


# ------------------------------------------------------------------------- models
def model_grid(name: str) -> list[dict]:
    targets = ["level", "delta"]
    if name == "Ridge":
        return [{"alpha": a, "target": t} for a in [0.1, 1.0, 10.0, 100.0] for t in targets]
    if name == "RandomForest":
        return [{"max_depth": d, "target": t} for d in [8, 16] for t in targets]
    if name == "HistGB":
        return [{"max_depth": d, "target": t} for d in [3, 6] for t in targets]
    if name == "XGBoost":
        return [{"max_depth": d, "target": t} for d in [3, 6] for t in targets]
    if name == "MLP":
        return [{"alpha": a, "target": t} for a in [1e-4, 1e-2] for t in targets]
    if name == "XGBoost-log":  # low-flow oriented: change in log discharge
        return [{"max_depth": d, "target": "logdelta"} for d in [3, 6]]
    raise ValueError(name)


def make_model(name: str, p: dict):
    if name == "Ridge":
        return Pipeline([("s", StandardScaler()), ("m", Ridge(alpha=p["alpha"]))])
    if name == "RandomForest":
        return RandomForestRegressor(n_estimators=150, max_depth=p["max_depth"], min_samples_leaf=5,
                                     max_features=0.5, max_samples=0.7, n_jobs=1,
                                     random_state=cfg.RANDOM_STATE)
    if name == "HistGB":
        return HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_depth=p["max_depth"],
                                             random_state=cfg.RANDOM_STATE)
    if name in ("XGBoost", "XGBoost-log"):
        return XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=p["max_depth"],
                            subsample=0.8, colsample_bytree=0.8, n_jobs=1,
                            random_state=cfg.RANDOM_STATE, verbosity=0)
    if name == "MLP":
        return Pipeline([("s", StandardScaler()), ("m", MLPRegressor(
            hidden_layer_sizes=(64, 32), alpha=p["alpha"], max_iter=400, early_stopping=True,
            random_state=cfg.RANDOM_STATE))])
    raise ValueError(name)


def fit_predict(name, p, Xtr, ytr, qtr, Xte, qte):
    """Fit on level, change or log-change target; always return level forecasts (>= 0)."""
    target = {"level": ytr, "delta": ytr - qtr,
              "logdelta": np.log1p(ytr) - np.log1p(qtr)}[p["target"]]
    m = make_model(name, p).fit(Xtr, target)
    yhat = m.predict(Xte)
    if p["target"] == "delta":
        yhat = yhat + qte
    elif p["target"] == "logdelta":
        yhat = np.expm1(np.log1p(qte) + yhat)
    return np.clip(yhat, 0.0, None)


def selection_blocks(train, val, h):
    """(fit, score) pairs for model selection: the validation block and up to
    SELECTION_BLOCKS - 1 earlier blocks of the same length cut from train, each
    scored after an h-row embargo. Only train and val are used."""
    pairs, n = [(train, val)], len(val)
    for j in range(1, cfg.SELECTION_BLOCKS):
        end = len(train) - (j - 1) * n
        start = end - n
        if start - h < n:  # keep at least one block of training data
            break
        pairs.append((train.iloc[: start - h], train.iloc[start:end]))
    return pairs


def tune_and_test(name, train, val, test, cols, h=0):
    """Select config on mean RMSE over chronological validation blocks, refit on
    train+val, predict test. Also returns the selected config's validation forecast."""
    best, best_rmse, best_val = None, np.inf, None
    pairs = selection_blocks(train, val, h)
    for p in model_grid(name):
        scores = []
        for fit_blk, sc_blk in pairs:
            yv = fit_predict(name, p, fit_blk[cols].values, fit_blk.y.values, fit_blk.q.values,
                             sc_blk[cols].values, sc_blk.q.values)
            scores.append(float(np.sqrt(np.mean((sc_blk.y.values - yv) ** 2))))
            if sc_blk is val:
                yv_val = yv
        r = float(np.mean(scores))
        if r < best_rmse:
            best, best_rmse, best_val = p, r, yv_val
    fit = pd.concat([train, val])
    yhat = fit_predict(name, best, fit[cols].values, fit.y.values, fit.q.values,
                       test[cols].values, test.q.values)
    return yhat, best, best_rmse, best_val


def calibrate_drought_factor(y_val, yhat_val, thr_val) -> float:
    """Factor k for the forecast-side threshold (drought if yhat < k * thr) that
    maximizes CSI on the validation block; 1.0 if validation has no drought days."""
    obs = y_val < thr_val
    if not obs.any():
        return 1.0
    best_k, best_csi = 1.0, -1.0
    for k in cfg.DROUGHT_FACTORS:
        csi = drought_scores(obs, yhat_val < k * thr_val)["CSI"]
        if np.isfinite(csi) and csi > best_csi + 1e-12:
            best_k, best_csi = k, csi
    return best_k


# ---------------------------------------------------------------------- per gauge
def drought_threshold(fit: pd.DataFrame) -> pd.Series:
    """Monthly Q20 (variable threshold) from the fit period's observed discharge."""
    q = fit[["date", "q"]].dropna()
    return q.groupby(q.date.dt.month).q.quantile(cfg.DROUGHT_QUANTILE)


def run_gauge_horizon(row, df_raw: pd.DataFrame, h: int) -> dict:
    feat, cols = add_features(df_raw, h)
    data = feat.dropna(subset=["y"] + cols).reset_index(drop=True)
    if len(data) < cfg.MIN_ROWS_AFTER_FEATURES:
        return {}
    train, val, test = split_with_embargo(data, h)
    fit = pd.concat([train, val])
    y, pers = test.y.values, test.y_persist.values
    preds = {"persistence": pers, "climatology": climatology_predict(fit, test.target_date)}
    val_preds = {"persistence": val.y_persist.values,
                  "climatology": climatology_predict(train, val.target_date)}
    chosen, val_rmse = {}, {}
    for name in LEARNERS:
        preds[name], chosen[name], val_rmse[name], val_preds[name] = tune_and_test(
            name, train, val, test, cols, h)

    thr = drought_threshold(fit)
    thr_t = thr.reindex(test.target_date.dt.month.values).values
    thr_v = drought_threshold(train).reindex(val.target_date.dt.month.values).values
    base = {"gauge_id": row.gauge_id, "gauge_name": row.gauge_name, "region": row.region,
            "horizon": h, "n_train": len(train), "n_val": len(val), "n_test": len(test),
            "test_start": str(test.date.iloc[0].date()), "test_end": str(test.date.iloc[-1].date())}
    rows = []
    for name, yhat in preds.items():
        lo, hi = block_bootstrap_skill(y, yhat, pers, cfg.N_BOOT, cfg.BOOT_BLOCK, cfg.RANDOM_STATE)
        dm_stat, dm_p = diebold_mariano(y, yhat, pers, h) if name != "persistence" else (np.nan, np.nan)
        ds = drought_scores(y < thr_t, yhat < thr_t)
        k_cal = calibrate_drought_factor(val.y.values, val_preds[name], thr_v)
        dc = drought_scores(y < thr_t, yhat < k_cal * thr_t)
        rows.append({**base, "model": name, **summarize(y, yhat, pers),
                     "skill_lo": lo, "skill_hi": hi, "dm_stat": dm_stat, "dm_p": dm_p,
                     **{f"drought_{k}": v for k, v in ds.items()},
                     "drought_factor": k_cal,
                     **{f"droughtcal_{k}": v for k, v in dc.items() if k != "n_events"},
                     "val_RMSE": val_rmse.get(name, np.nan),
                     "config": json.dumps(chosen.get(name, {}))})
    pred_df = pd.DataFrame({"date": test.date.values, "target_date": test.target_date.values,
                            "y_true": y, "threshold": thr_t, **preds})
    split_dates = {k: [str(d.date.iloc[0].date()), str(d.date.iloc[-1].date())]
                   for k, d in [("train", train), ("val", val), ("test", test)]}
    return {"metrics": rows, "preds": pred_df, "splits": split_dates, "n_features": len(cols)}


def run_fusion_ablation(row, df_raw: pd.DataFrame, h: int) -> list[dict]:
    """Base vs fused predictors on identical rows (period covered by MERRA-2 and GloFAS)."""
    if "precip_merra2" not in df_raw or not any(c.startswith("glofas_cell") for c in df_raw):
        return []
    df = df_raw.copy()
    probe, _ = add_features(df.assign(glofas_q=0.0), h, fused=True)
    probe_cols = [c for c in probe.columns if c.startswith(("pm2_",))]
    # provisional valid rows to find the fit end for GloFAS snapping
    tmp = probe.dropna(subset=["y", "q_lag30"] + probe_cols)
    tmp = tmp[tmp.date >= pd.Timestamp("1984-03-01")]
    if len(tmp) < cfg.MIN_ROWS_AFTER_FEATURES:
        return []
    fit_end = tmp.date.iloc[int(len(tmp) * (cfg.TRAIN_FRAC + cfg.VAL_FRAC)) - 1]
    g = snap_glofas(df, fit_end)
    if g is None:
        return []
    df["glofas_q"] = g
    feat_f, cols_f = add_features(df, h, fused=True)
    _, cols_b = add_features(df, h, fused=False)
    data = feat_f.dropna(subset=["y"] + cols_f).reset_index(drop=True)
    if len(data) < cfg.MIN_ROWS_AFTER_FEATURES:
        return []
    train, val, test = split_with_embargo(data, h)
    y, pers = test.y.values, test.y_persist.values
    out = []
    for fs, cols in [("base", cols_b), ("fused", cols_f)]:
        for name in ["Ridge", "XGBoost"]:
            yhat, p, _, _ = tune_and_test(name, train, val, test, cols, h)
            out.append({"gauge_id": row.gauge_id, "gauge_name": row.gauge_name, "region": row.region,
                        "horizon": h, "feature_set": fs, "model": name, "n_test": len(test),
                        **summarize(y, yhat, pers)})
    # Raw GloFAS reanalysis at the target date: a process-model *simulation* driven by
    # observed forcing (not a forecast), reported only as a physical reference.
    g_target = df.set_index("date").glofas_q.reindex(test.target_date).values
    ok = np.isfinite(g_target)
    out.append({"gauge_id": row.gauge_id, "gauge_name": row.gauge_name, "region": row.region,
                "horizon": h, "feature_set": "glofas_raw", "model": "GloFAS",
                "n_test": int(ok.sum()), **summarize(y[ok], g_target[ok], pers[ok])})
    return out


def run_chirps_ablation(row, df_raw: pd.DataFrame, h: int) -> list[dict]:
    """ERA5 vs ERA5 + CHIRPS (0.05 deg, catchment mean) precipitation on identical rows."""
    if "precip_chirps" not in df_raw or df_raw.precip_chirps.notna().sum() < 365:
        return []
    feat_c, cols_c = add_features(df_raw, h, chirps=True)
    _, cols_b = add_features(df_raw, h)
    data = feat_c.dropna(subset=["y"] + cols_c).reset_index(drop=True)
    if len(data) < cfg.MIN_ROWS_AFTER_FEATURES:
        return []
    train, val, test = split_with_embargo(data, h)
    y, pers = test.y.values, test.y_persist.values
    out = []
    for fs, cols in [("era5", cols_b), ("era5_chirps", cols_c)]:
        for name in ["Ridge", "XGBoost"]:
            yhat, p, _, _ = tune_and_test(name, train, val, test, cols, h)
            out.append({"gauge_id": row.gauge_id, "gauge_name": row.gauge_name, "region": row.region,
                        "horizon": h, "feature_set": fs, "model": name, "n_test": len(test),
                        **summarize(y, yhat, pers)})
    return out


def walk_forward(row, df_raw: pd.DataFrame, h: int) -> list[dict]:
    """Expanding window: Ridge (alpha/target chosen on the last 15% of each fold's train)."""
    feat, cols = add_features(df_raw, h)
    data = feat.dropna(subset=["y"] + cols).reset_index(drop=True)
    n = len(data)
    start = int(n * cfg.WF_MIN_TRAIN_FRAC)
    block = (n - start) // cfg.WF_N_SPLITS
    rows = []
    for i in range(cfg.WF_N_SPLITS):
        te_a = start + i * block
        te_b = n if i == cfg.WF_N_SPLITS - 1 else te_a + block
        fit = data.iloc[: te_a - h]
        cut = int(len(fit) * 0.85)
        tr, va = fit.iloc[: cut - h], fit.iloc[cut:]
        te = data.iloc[te_a:te_b]
        yhat, p, _, _ = tune_and_test("Ridge", tr, va, te, cols, h)
        pers = te.y_persist.values
        rows.append({"gauge_id": row.gauge_id, "gauge_name": row.gauge_name, "region": row.region,
                     "horizon": h, "fold": i + 1, "n_train": len(fit), "n_test": len(te),
                     "test_start": str(te.date.iloc[0].date()), "test_end": str(te.date.iloc[-1].date()),
                     **summarize(te.y.values, yhat, pers)})
    return rows


def process_gauge(row) -> dict:
    t0 = time.time()
    df = load_station(row)
    res = {"gauge_id": row.gauge_id, "metrics": [], "preds": {}, "splits": {}, "fusion": [], "wf": [],
           "chirps": []}
    for h in cfg.HORIZONS:
        r = run_gauge_horizon(row, df, h)
        if not r:
            continue
        res["metrics"] += r["metrics"]
        res["splits"][h] = r["splits"]
        res["n_features"] = r["n_features"]
        if row.gauge_id == cfg.FOCUS_STATION_ID:
            res["preds"][h] = r["preds"]
        res["fusion"] += run_fusion_ablation(row, df, h)
        res["chirps"] += run_chirps_ablation(row, df, h)
        res["wf"] += walk_forward(row, df, h)
    res["seconds"] = round(time.time() - t0, 1)
    print(f"  done {row.gauge_id} {row.gauge_name} ({res['seconds']} s)", flush=True)
    return res


# --------------------------------------------------------------------------- main
def nonparametric_ssi(dates: pd.Series, q: pd.Series, window: int) -> pd.Series:
    """Nonparametric SSI: rolling mean -> Gringorten plotting position per calendar
    month -> standard-normal quantile (Farahmand & AghaKouchak 2015)."""
    qa = q.rolling(window, min_periods=int(0.8 * window)).mean()
    out = pd.Series(np.nan, index=q.index)
    for m in range(1, 13):
        mask = (dates.dt.month == m) & qa.notna()
        v = qa[mask]
        if len(v) < 10:
            continue
        rank = v.rank(method="average")
        out[mask] = stats.norm.ppf((rank - 0.44) / (len(v) + 0.12))
    return out


def main() -> None:
    t0 = time.time()
    for d in (cfg.PROC, cfg.FIG, cfg.TAB):
        d.mkdir(parents=True, exist_ok=True)
    meta = pd.read_csv(cfg.STATION_META)
    print(f"Gauges: {len(meta)} | horizons {cfg.HORIZONS}")
    results = Parallel(n_jobs=min(8, len(meta)), verbose=0)(
        delayed(process_gauge)(r) for r in meta.itertuples())

    metrics = pd.DataFrame([m for r in results for m in r["metrics"]])
    metrics.to_csv(cfg.TAB / "metrics_by_station.csv", index=False)
    pd.DataFrame([m for r in results for m in r["fusion"]]).to_csv(
        cfg.TAB / "metrics_fusion_ablation.csv", index=False)
    pd.DataFrame([m for r in results for m in r["chirps"]]).to_csv(
        cfg.TAB / "metrics_chirps_ablation.csv", index=False)
    pd.DataFrame([m for r in results for m in r["wf"]]).to_csv(
        cfg.TAB / "metrics_walkforward.csv", index=False)
    for r in results:
        for h, p in r["preds"].items():
            p.to_csv(cfg.PROC / f"predictions_{r['gauge_id']}_h{h}.csv", index=False)

    # Descriptive nonparametric SSI-30 for every gauge (full record)
    ssi_all = []
    for row in meta.itertuples():
        df = load_station(row)
        ssi_all.append(pd.DataFrame({"gauge_id": row.gauge_id, "date": df.date, "q": df.q,
                                     "ssi30": nonparametric_ssi(df.date, df.q, cfg.SSI_WINDOW)}))
    pd.concat(ssi_all).to_csv(cfg.PROC / "ssi30_all_gauges.csv", index=False)

    with open(cfg.TAB / "experiment_meta.json", "w") as f:
        json.dump({"n_gauges": int(meta.shape[0]), "horizons": cfg.HORIZONS,
                   "n_features_base": int(max(r.get("n_features", 0) for r in results)),
                   "splits": {r["gauge_id"]: r["splits"] for r in results},
                   "seconds_per_gauge": {r["gauge_id"]: r["seconds"] for r in results},
                   "runtime_seconds": round(time.time() - t0, 1)}, f, indent=2)
    print(f"Done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
