#!/usr/bin/env python3
"""Extract Peru Andean-GC QC series (days_w_data_qc >= 5000) into stations/."""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "02-datos" / "crudos"
OUT = RAW / "stations"
MIN_QC = 5000


def main() -> None:
    meta = pd.read_csv(RAW / "andean-gc" / "AndeanGC_metadata.csv")
    peru = meta[(meta.country == "Peru") & (meta.days_w_data_qc >= MIN_QC)].sort_values(
        "days_w_data_qc", ascending=False
    )
    cols = ["date"] + peru.gauge_id.tolist()
    df = pd.read_csv(
        RAW / "andean-gc" / "AndeanGC_data_1950_2024_qc.csv",
        usecols=cols, parse_dates=["date"],
    )
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for _, row in peru.iterrows():
        gid = row.gauge_id
        name = str(row.gauge_name).strip()
        slug = "".join(
            c if c.isalnum() or c == "_" else "_"
            for c in name.lower().replace(" ", "_").replace("ñ", "n")
        )
        series = df[["date", gid]].dropna(subset=[gid]).rename(columns={gid: "discharge_m3s"})
        series = series.sort_values("date").reset_index(drop=True)
        path = OUT / f"{gid}_{slug}_daily_qc.csv"
        series.to_csv(path, index=False)
        rows.append({
            "gauge_id": gid,
            "gauge_name": name,
            "slug": slug,
            "gauge_lat": float(row.gauge_lat),
            "gauge_lon": float(row.gauge_lon),
            "days_w_data_qc": int(row.days_w_data_qc),
            "n_extracted": len(series),
            "date_start": str(series.date.iloc[0].date()),
            "date_end": str(series.date.iloc[-1].date()),
            "elev_mean": float(row.elev_mean) if pd.notna(row.elev_mean) else None,
            "basin_area": float(row.basin_area) if pd.notna(row.basin_area) else None,
            "is_altiplano_focus": gid == "P00000055",
            "is_southern_peru": float(row.gauge_lat) < -13.5,
        })
        print(f"{gid} {name}: n={len(series)}")
    pd.DataFrame(rows).to_csv(OUT / "peru_benchmark_stations.csv", index=False)


if __name__ == "__main__":
    main()
