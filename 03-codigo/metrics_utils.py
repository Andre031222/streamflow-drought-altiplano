"""Hydrological forecast metrics (RMSE, MAE, NSE, KGE, skill)."""
from __future__ import annotations
import numpy as np


def rmse(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mae(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_true - y_pred)))


def nse(y_true, y_pred) -> float:
    """Nash-Sutcliffe efficiency."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.sum((y_true - np.mean(y_true)) ** 2)
    if denom == 0:
        return float("nan")
    return float(1.0 - np.sum((y_true - y_pred) ** 2) / denom)


def kge(y_true, y_pred) -> float:
    """Kling-Gupta efficiency (2009 three-component form).

    KGE = 1 - sqrt( (r-1)^2 + (alpha-1)^2 + (beta-1)^2 )
    where r is Pearson correlation, alpha = sigma_sim/sigma_obs,
    beta = mu_sim/mu_obs.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if len(y_true) < 2:
        return float("nan")
    sd_o = np.std(y_true, ddof=0)
    sd_s = np.std(y_pred, ddof=0)
    mu_o = np.mean(y_true)
    mu_s = np.mean(y_pred)
    if sd_o == 0 or sd_s == 0:
        return float("nan")
    r = np.corrcoef(y_true, y_pred)[0, 1]
    alpha = sd_s / sd_o
    if mu_o == 0:
        return float("nan")
    beta = mu_s / mu_o
    return float(1.0 - np.sqrt((r - 1.0) ** 2 + (alpha - 1.0) ** 2 + (beta - 1.0) ** 2))


def skill_vs_persistence(y_true, y_pred, y_persist) -> float:
    """1 - RMSE_model / RMSE_persistence (positive = better than persistence)."""
    r_m = rmse(y_true, y_pred)
    r_p = rmse(y_true, y_persist)
    if r_p == 0:
        return float("nan")
    return float(1.0 - r_m / r_p)


def summarize(y_true, y_pred, y_persist) -> dict:
    return {
        "RMSE": rmse(y_true, y_pred),
        "MAE": mae(y_true, y_pred),
        "NSE": nse(y_true, y_pred),
        "KGE": kge(y_true, y_pred),
        "skill_vs_persistence": skill_vs_persistence(y_true, y_pred, y_persist),
    }
