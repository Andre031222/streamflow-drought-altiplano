"""Map of 13 Peru Andean-GC benchmark gauges (real coords from stations_peru_benchmark_meta.csv)."""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
meta = pd.read_csv(ROOT / "02-datos/crudos/stations_peru_benchmark_meta.csv")
focus = meta[meta["is_altiplano_focus"] == True]
others = meta[meta["is_altiplano_focus"] != True]

fig, ax = plt.subplots(figsize=(6.2, 7.2))
ax.scatter(others["gauge_lon"], others["gauge_lat"], s=55, c="#4C78A8",
           edgecolors="white", linewidths=0.6, zorder=3, label="Peru benchmark gauges")
ax.scatter(focus["gauge_lon"], focus["gauge_lat"], s=140, c="#E45756",
           marker="*", edgecolors="black", linewidths=0.5, zorder=4,
           label="Focus: Puente Isla Cabanillas")
short = {
    "Puente Isla Cabanillas": "Cabanillas", "Egemsa Km 105": "Egemsa Km105",
    "La Capilla": "La Capilla", "Condorcerro": "Condorcerro", "Salamanca": "Salamanca",
    "Cahua": "Cahua", "Recreta": "Recreta", "Quitaracsa": "Quitaracsa", "Colcas": "Colcas",
    "Chancos": "Chancos", "Pachacoto": "Pachacoto", "Llanganuco": "Llanganuco", "Ocoña": "Ocoña",
}
for _, r in meta.iterrows():
    label = short.get(r["gauge_name"], r["gauge_name"])
    dx, dy = 0.12, 0.12
    if label == "Cabanillas":
        dx, dy = 0.18, -0.22
    elif label == "Ocoña":
        dx, dy = 0.12, -0.22
    elif label == "Salamanca":
        dx, dy = -1.35, 0.05
    ax.annotate(label, (r["gauge_lon"] + dx, r["gauge_lat"] + dy), fontsize=7, color="#222222")
ax.set_xlabel("Longitude (°E)")
ax.set_ylabel("Latitude (°N)")
ax.set_title("Peru Andean-GC gauges in the open multi-station benchmark\n(≥5000 QC days; Altiplano focus highlighted)")
ax.grid(True, linestyle=":", alpha=0.45)
ax.set_aspect("equal", adjustable="datalim")
ax.set_xlim(meta["gauge_lon"].min() - 1.2, meta["gauge_lon"].max() + 1.5)
ax.set_ylim(meta["gauge_lat"].min() - 1.0, meta["gauge_lat"].max() + 1.0)
ax.legend(loc="lower left", fontsize=8, framealpha=0.92)
out = ROOT / "04-resultados/figuras"
for ext in ("png", "pdf"):
    fig.savefig(out / f"fig00_station_map.{ext}", dpi=600, bbox_inches="tight")
print("wrote fig00_station_map.{png,pdf}")
