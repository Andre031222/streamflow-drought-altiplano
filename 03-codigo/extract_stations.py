#!/usr/bin/env python3
"""Extract Andean-GC QC discharge series for the benchmark gauges into stations/.

Selection (all with days_w_data_qc >= 5000):
  * every Peru gauge (SENAMHI), and
  * the Altiplano gauges of the Lauca/Caquena headwaters (Chile, DGA), which share
    the endorheic Altiplano plateau with the Peruvian focus gauge Cabanillas.

Requires the full Andean-GC QC CSV (Zenodo 10.5281/zenodo.18035801) under
02-datos/crudos/andean-gc/.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg

AGC = cfg.RAW / "andean-gc"


def region_of(row) -> str:
    if row.gauge_id == cfg.FOCUS_STATION_ID or (
        row.country == "Chile" and -19.0 < row.gauge_lat < -17.0 and row.gauge_lon > -70.0
    ):
        return "Altiplano"
    if row.country == "Peru" and row.gauge_lat > -10.2 and row.gauge_lon < -77.2 and row.days_w_data_qc < 9000:
        return "Cordillera Blanca"
    return "Western/Southern Andes"


def slugify(name: str) -> str:
    s = name.lower().replace("ñ", "n").replace(" ", "_")
    s = "".join(c if c.isalnum() or c == "_" else "_" for c in s)
    return "_".join(p for p in s.split("_") if p)


def main() -> None:
    meta = pd.read_csv(AGC / "AndeanGC_metadata.csv")
    peru = meta[(meta.country == "Peru")]
    alti = meta[(meta.country == "Chile") & meta.gauge_lat.between(-19.0, -17.0) & (meta.gauge_lon > -70.0)]
    sel = pd.concat([peru, alti])
    sel = sel[sel.days_w_data_qc >= cfg.MIN_QC_DAYS].sort_values("days_w_data_qc", ascending=False)

    data = pd.read_csv(AGC / "AndeanGC_data_1950_2024_qc.csv",
                       usecols=["date"] + sel.gauge_id.tolist(), parse_dates=["date"])
    cfg.STATIONS_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for _, r in sel.iterrows():
        slug = slugify(str(r.gauge_name).strip())
        s = (data[["date", r.gauge_id]].dropna()
             .rename(columns={r.gauge_id: "discharge_m3s"}).sort_values("date"))
        s.to_csv(cfg.STATIONS_DIR / f"{r.gauge_id}_{slug}_daily_qc.csv", index=False)
        rows.append({
            "gauge_id": r.gauge_id, "gauge_name": str(r.gauge_name).strip(), "slug": slug,
            "country": r.country, "region": region_of(r),
            "gauge_lat": r.gauge_lat, "gauge_lon": r.gauge_lon,
            "basin_cenlat": r.basin_cenlat, "basin_cenlon": r.basin_cenlon,
            "basin_area": r.basin_area, "elev_mean": r.elev_mean,
            "glacier_area_RGI60": r.glacier_area_RGI60,
            "days_w_data_qc": int(r.days_w_data_qc), "n_extracted": len(s),
            "date_start": str(s.date.iloc[0].date()), "date_end": str(s.date.iloc[-1].date()),
            "is_focus": r.gauge_id == cfg.FOCUS_STATION_ID,
        })
        print(f"{r.gauge_id} {r.gauge_name:35s} {region_of(r):22s} n={len(s)}")
    pd.DataFrame(rows).to_csv(cfg.STATION_META, index=False)
    print(f"Wrote {cfg.STATION_META} ({len(rows)} gauges)")


if __name__ == "__main__":
    main()
