#!/usr/bin/env python3
"""Download the auxiliary open data sources for every benchmark gauge.

Sources (all public, no key):
  * ERA5 (0.25 deg) daily precipitation and 2 m mean temperature
    at the catchment centroid (Open-Meteo Historical Weather API, model era5; the era5_land
    endpoint returns no precipitation).
  * NASA POWER daily precipitation (PRECTOTCORR, MERRA-2 bias-corrected with GPCP)
    and 2 m temperature at the catchment centroid (from 1981).
  * CHIRPS v2.0 (0.05 deg) daily precipitation averaged over the catchment polygon
    (ClimateSERV API, NASA/SERVIR; from 1981).
  * GloFAS v4 reanalysis daily river discharge (Open-Meteo Flood API, from 1984) on
    a 3 x 3 neighbourhood (0.05 deg) around the gauge; the cell used as a predictor
    is chosen later using the training period only (see run_experiment.py).

Outputs go to 02-datos/crudos/clima/<source>/<gauge_id>.csv plus a manifest.
Existing files are skipped, so the script can be re-run after rate-limit errors.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg

ERA5_URL = "https://archive-api.open-meteo.com/v1/archive"
GLOFAS_URL = "https://flood-api.open-meteo.com/v1/flood"
POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
CHIRPS_URL = "https://climateserv.servirglobal.net/api/"
CATCHMENTS = cfg.RAW / "andean-gc" / "catchments_benchmark19.gpkg"
ERA5_VARS = ["precipitation_sum", "temperature_2m_mean"]
GLOFAS_START = pd.Timestamp("1984-01-01")
POWER_START = pd.Timestamp("1981-01-01")
CHIRPS_START = pd.Timestamp("1981-01-01")
LAST_DAY = pd.Timestamp("2024-12-31")


def get(url: str, params: dict, tries: int = 12) -> bytes:
    full = url + "?" + urllib.parse.urlencode(params, safe=",")
    for k in range(tries):
        try:
            with urllib.request.urlopen(full, timeout=180) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="ignore")
            if "Hourly" in body or "Daily" in body:  # wait for the quota window to reset
                now = pd.Timestamp.now()
                wait = int((now.ceil("h") - now).total_seconds()) + 90
            else:
                wait = 65 if e.code == 429 else 10 * (k + 1)
            print(f"    HTTP {e.code}; retry in {wait}s")
            time.sleep(wait)
        except Exception as e:  # network hiccup
            print(f"    {e}; retry")
            time.sleep(10 * (k + 1))
    raise RuntimeError(f"failed: {full[:160]}")


def period(row, floor: pd.Timestamp | None = None) -> tuple[str, str]:
    start = pd.Timestamp(row.date_start) - pd.Timedelta(days=120)
    start = max(start, pd.Timestamp("1950-01-02"))
    if floor is not None:
        start = max(start, floor)
    end = min(pd.Timestamp(row.date_end), LAST_DAY)
    return str(start.date()), str(end.date())


def fetch_era5(row, out: Path) -> None:
    """Request in 8-year chunks: one long multi-variable request exceeds the API's
    per-minute weight budget."""
    s, e = period(row)
    parts = []
    for a in pd.date_range(s, e, freq=pd.DateOffset(years=8)):
        b = min(a + pd.DateOffset(years=8) - pd.Timedelta(days=1), pd.Timestamp(e))
        raw = json.loads(get(ERA5_URL, {
            "latitude": f"{row.basin_cenlat:.4f}", "longitude": f"{row.basin_cenlon:.4f}",
            "start_date": str(a.date()), "end_date": str(b.date()), "daily": ",".join(ERA5_VARS),
            "models": "era5", "timezone": "GMT",
        }))
        d = raw["daily"]
        parts.append(pd.DataFrame({
            "date": d["time"], "precip_era5": d["precipitation_sum"],
            "t2m_era5": d["temperature_2m_mean"],
        }))
        time.sleep(8)  # stay well below the per-minute and hourly weight limits
    pd.concat(parts).drop_duplicates("date").sort_values("date").to_csv(out, index=False)


def fetch_power(row, out: Path) -> None:
    if pd.Timestamp(row.date_end) < POWER_START:
        return
    s, e = period(row, POWER_START)
    txt = get(POWER_URL, {
        "parameters": "PRECTOTCORR,T2M", "community": "AG",
        "latitude": f"{row.basin_cenlat:.4f}", "longitude": f"{row.basin_cenlon:.4f}",
        "start": s.replace("-", ""), "end": e.replace("-", ""), "format": "CSV",
    }).decode()
    body = txt.split("-END HEADER-")[1]
    df = pd.read_csv(StringIO(body))
    df["date"] = pd.to_datetime(df.YEAR.astype(str), format="%Y") + pd.to_timedelta(df.DOY - 1, "D")
    df = df.replace(-999.0, np.nan)
    df[["date", "PRECTOTCORR", "T2M"]].rename(
        columns={"PRECTOTCORR": "precip_merra2", "T2M": "t2m_merra2"}
    ).to_csv(out, index=False)


def chirps_polygon(gauge_id: str) -> dict:
    """Catchment outline as a GeoJSON polygon (largest part, simplified); catchments
    smaller than a few CHIRPS cells are buffered so that at least one cell centre falls inside."""
    import geopandas as gpd
    g = gpd.read_file(CATCHMENTS).set_index("gauge_id").geometry[gauge_id]
    if g.geom_type == "MultiPolygon":
        g = max(g.geoms, key=lambda p: p.area)
    if g.area < 0.01:  # ~ 4 CHIRPS cells
        g = g.buffer(0.03)
    tol = 0.005
    g0 = g
    while True:  # keep the request URL short: at most ~40 vertices
        g = g0.simplify(tol)
        if len(g.exterior.coords) <= 40:
            break
        tol *= 1.5
    return {"type": "Polygon", "coordinates": [[[round(x, 4), round(y, 4)] for x, y in g.exterior.coords]]}


def fetch_chirps(row, out: Path) -> None:
    if pd.Timestamp(row.date_end) < CHIRPS_START:
        return
    s, e = (pd.Timestamp(d) for d in period(row, CHIRPS_START))
    geom = json.dumps(chirps_polygon(row.gauge_id))
    parts = []
    for a in pd.date_range(s, e, freq="10YS").union([s]):  # one request per decade
        b = min(a + pd.DateOffset(years=10) - pd.Timedelta(days=1), e)
        jid = json.loads(get(CHIRPS_URL + "submitDataRequest/", {
            "datatype": 0, "intervaltype": 0, "operationtype": 5,  # CHIRPS daily, mean
            "begintime": a.strftime("%m/%d/%Y"), "endtime": b.strftime("%m/%d/%Y"),
            "geometry": geom, "isZip_CurrentDataType": "false"}))[0]
        for _ in range(300):
            prog = json.loads(get(CHIRPS_URL + "getDataRequestProgress/", {"id": jid}))[0]
            if prog >= 100 or prog < 0:
                break
            time.sleep(3)
        data = json.loads(get(CHIRPS_URL + "getDataFromRequest/", {"id": jid}))["data"]
        parts.append(pd.DataFrame({"date": pd.to_datetime([d["date"] for d in data], format="%m/%d/%Y"),
                                   "precip_chirps": [d["raw_value"] for d in data]}))
    df = pd.concat(parts).drop_duplicates("date").sort_values("date")
    df.loc[df.precip_chirps < 0, "precip_chirps"] = np.nan  # ClimateSERV no-data flag
    df.to_csv(out, index=False)


def fetch_glofas(row, out: Path) -> None:
    if pd.Timestamp(row.date_end) < GLOFAS_START:
        return
    s, e = period(row, GLOFAS_START)
    offs = np.arange(-1, 2) * 0.05
    lats = [row.gauge_lat + a for a in offs for _ in offs]
    lons = [row.gauge_lon + b for _ in offs for b in offs]
    raw = json.loads(get(GLOFAS_URL, {
        "latitude": ",".join(f"{v:.4f}" for v in lats),
        "longitude": ",".join(f"{v:.4f}" for v in lons),
        "start_date": s, "end_date": e, "daily": "river_discharge", "cell_selection": "nearest",
    }))
    cols = {}
    for k, loc in enumerate(raw):
        cols["date"] = loc["daily"]["time"]
        cols[f"cell{k:02d}"] = loc["daily"]["river_discharge"]
    df = pd.DataFrame(cols)
    df = df.loc[:, ~df.T.duplicated()]  # neighbouring requests can snap to the same cell
    df.to_csv(out, index=False)


def main() -> None:
    meta = pd.read_csv(cfg.STATION_META)
    only = set(sys.argv[1:])  # optional: restrict to some sources, e.g. `glofas`
    manifest = []
    for src, fn in [("era5", fetch_era5), ("merra2_power", fetch_power), ("glofas", fetch_glofas),
                    ("chirps", fetch_chirps)]:
        if only and src not in only:
            continue
        d = cfg.CLIMATE_DIR / src
        d.mkdir(parents=True, exist_ok=True)
        for _, row in meta.iterrows():
            out = d / f"{row.gauge_id}.csv"
            status = "cached"
            if not out.exists():
                try:
                    fn(row, out)
                    status = "ok" if out.exists() else "no_overlap"
                except Exception as e:
                    status = f"error:{e}"
                time.sleep(8.0)
            print(f"{src:13s} {row.gauge_id} {status}")
            manifest.append({"source": src, "gauge_id": row.gauge_id, "status": status,
                             "file": str(out.relative_to(cfg.ROOT)) if out.exists() else ""})
    tag = "_".join(sorted(only)) if only else "all"
    pd.DataFrame(manifest).to_csv(cfg.CLIMATE_DIR / f"fetch_manifest_{tag}.csv", index=False)


if __name__ == "__main__":
    main()
