"""Hydrological forecast metrics, uncertainty and drought-detection scores."""
from __future__ import annotations

import numpy as np
from scipy import stats


def rmse(y_true, y_pred) -> float:
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mae(y_true, y_pred) -> float:
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    return float(np.mean(np.abs(y_true - y_pred)))


def nse(y_true, y_pred) -> float:
    """Nash-Sutcliffe efficiency."""
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    denom = np.sum((y_true - y_true.mean()) ** 2)
    return float("nan") if denom == 0 else float(1.0 - np.sum((y_true - y_pred) ** 2) / denom)


def kge(y_true, y_pred) -> float:
    """Kling-Gupta efficiency (Gupta et al. 2009): 1 - sqrt((r-1)^2 + (a-1)^2 + (b-1)^2)."""
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    if len(y_true) < 2:
        return float("nan")
    sd_o, sd_s, mu_o = y_true.std(), y_pred.std(), y_true.mean()
    if sd_o == 0 or sd_s == 0 or mu_o == 0:
        return float("nan")
    r = np.corrcoef(y_true, y_pred)[0, 1]
    return float(1.0 - np.sqrt((r - 1) ** 2 + (sd_s / sd_o - 1) ** 2 + (y_pred.mean() / mu_o - 1) ** 2))


def skill_vs_persistence(y_true, y_pred, y_persist) -> float:
    """1 - RMSE_model / RMSE_persistence (positive = better than persistence)."""
    r_p = rmse(y_true, y_persist)
    return float("nan") if r_p == 0 else float(1.0 - rmse(y_true, y_pred) / r_p)


def summarize(y_true, y_pred, y_persist) -> dict:
    return {"RMSE": rmse(y_true, y_pred), "MAE": mae(y_true, y_pred), "NSE": nse(y_true, y_pred),
            "KGE": kge(y_true, y_pred),
            "skill_vs_persistence": skill_vs_persistence(y_true, y_pred, y_persist)}


def block_bootstrap_skill(y, yhat, pers, n_boot=1000, block=30, seed=42) -> tuple[float, float]:
    """95% moving-block bootstrap interval of skill vs persistence (Kuensch 1989)."""
    y, yhat, pers = (np.asarray(a, float) for a in (y, yhat, pers))
    n = len(y)
    if n < 2 * block:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    e_m, e_p = (y - yhat) ** 2, (y - pers) ** 2
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(n_boot, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n_boot, -1)[:, :n]
    sk = 1.0 - np.sqrt(e_m[idx].mean(1)) / np.sqrt(e_p[idx].mean(1))
    return float(np.percentile(sk, 2.5)), float(np.percentile(sk, 97.5))


def diebold_mariano(y, yhat, pers, h: int) -> tuple[float, float]:
    """DM test of equal squared-error accuracy (model vs persistence), with the
    Harvey-Leybourne-Newbold small-sample correction and h-1 autocovariance lags.
    Negative statistic = model more accurate. Two-sided p-value from Student t."""
    y, yhat, pers = (np.asarray(a, float) for a in (y, yhat, pers))
    d = (y - yhat) ** 2 - (y - pers) ** 2
    n = len(d)
    dbar = d.mean()
    dc = d - dbar
    lags = max(h - 1, 0)
    gamma = [np.dot(dc[k:], dc[: n - k]) / n for k in range(lags + 1)]
    var = (gamma[0] + 2 * sum(gamma[1:])) / n
    if var <= 0:
        return float("nan"), float("nan")
    dm = dbar / np.sqrt(var)
    hln = np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    stat = dm * hln
    return float(stat), float(2 * stats.t.sf(abs(stat), df=n - 1))


def drought_scores(obs_event, fc_event) -> dict:
    """POD, FAR and CSI (Schaefer 1990) of below-threshold (drought) days."""
    o, f = np.asarray(obs_event, bool), np.asarray(fc_event, bool)
    hits = int(np.sum(o & f)); misses = int(np.sum(o & ~f)); fa = int(np.sum(~o & f))
    pod = hits / (hits + misses) if hits + misses else float("nan")
    far = fa / (hits + fa) if hits + fa else float("nan")
    csi = hits / (hits + misses + fa) if hits + misses + fa else float("nan")
    return {"POD": pod, "FAR": far, "CSI": csi, "n_events": hits + misses}
