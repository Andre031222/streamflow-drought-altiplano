"""Validation tests for the benchmark pipeline (run: python -m pytest 03-codigo/tests -q)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_experiment as R
from metrics_utils import (block_bootstrap_skill, diebold_mariano, drought_scores, kge, nse,
                           skill_vs_persistence)


def synthetic(n=900, gap=(300, 340), seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2000-01-01", periods=n, freq="D")
    q = 10 + 5 * np.sin(2 * np.pi * np.arange(n) / 365) + rng.gamma(2, 1, n)
    q[gap[0]:gap[1]] = np.nan
    return pd.DataFrame({"date": dates, "q": q, "precip_era5": rng.gamma(1, 2, n),
                         "t2m_era5": rng.normal(5, 2, n)})


def test_lags_and_target_are_calendar_offsets():
    df = synthetic()
    for h in (1, 3, 7):
        f, cols = R.add_features(df, h)
        d = f.dropna(subset=["y"] + cols)
        qs = df.set_index("date").q
        assert np.allclose(d.y.values, qs.reindex(d.target_date).values)
        assert np.allclose(d.q_lag7.values, qs.reindex(d.date - pd.Timedelta(days=7)).values)
        assert np.allclose(d.q_lag0.values, d.y_persist.values)  # model sees Q_t like persistence


def test_no_future_information_in_features():
    df = synthetic(gap=(0, 0))
    h = 7
    f1, cols = R.add_features(df, h)
    df2 = df.copy()
    df2.loc[500:, ["q", "precip_era5", "t2m_era5"]] *= 100.0  # perturb the future
    f2, _ = R.add_features(df2, h)
    # all features at t=499 must be identical (only information up to t)
    assert np.allclose(f1.loc[499, cols].astype(float), f2.loc[499, cols].astype(float), equal_nan=True)


def test_rows_next_to_gap_are_dropped():
    df = synthetic(gap=(300, 340))
    f, cols = R.add_features(df, 7)
    d = f.dropna(subset=["y"] + cols)
    assert not ((d.date >= "2000-10-20") & (d.date <= "2001-01-04")).any()  # t+7 or t-30 inside gap


def test_split_is_chronological_with_embargo():
    df = synthetic(gap=(0, 0))
    f, cols = R.add_features(df, 7)
    d = f.dropna(subset=["y"] + cols).reset_index(drop=True)
    tr, va, te = R.split_with_embargo(d, 7)
    assert tr.target_date.max() < va.date.min()
    assert va.target_date.max() < te.date.min()


def test_metrics_reference_values():
    y = np.array([1.0, 2, 3, 4, 5])
    assert nse(y, y) == 1.0 and abs(kge(y, y) - 1.0) < 1e-12
    assert abs(nse(y, np.full(5, y.mean()))) < 1e-12
    assert skill_vs_persistence(y, y, y + 1) == 1.0
    d = drought_scores([1, 1, 0, 0], [1, 0, 1, 0])
    assert d["POD"] == 0.5 and d["FAR"] == 0.5 and abs(d["CSI"] - 1 / 3) < 1e-12


def test_bootstrap_and_dm_detect_clear_improvement():
    rng = np.random.default_rng(1)
    y = rng.normal(0, 1, 1500)
    good, bad = y + rng.normal(0, 0.3, 1500), y + rng.normal(0, 1.0, 1500)
    lo, hi = block_bootstrap_skill(y, good, bad)
    assert 0 < lo < hi
    stat, p = diebold_mariano(y, good, bad, 1)
    assert stat < 0 and p < 1e-6
    stat, p = diebold_mariano(y, bad, bad + rng.normal(0, 1e-9, 1500), 1)
    assert p > 0.01


def test_ssi_is_standard_normal_per_month():
    df = synthetic(n=365 * 20, gap=(0, 0))
    s = R.nonparametric_ssi(df.date, df.q, 30).dropna()
    assert abs(s.mean()) < 0.05 and abs(s.std() - 1) < 0.1
