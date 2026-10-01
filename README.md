# Honest Baselines for Streamflow and Hydrological-Drought Forecasting in the Tropical Andes

**An open, leakage-free multi-station benchmark with an Altiplano focus.**

**Venue:** ICICCDS 2027, International Conference on Intelligent Computing, Communication and Data Science
**Authors:** Richar Andre Vilca-Solorzano\* ([0009-0003-2385-5263](https://orcid.org/0009-0003-2385-5263)), Dina Maribel Yana-Yucra ([0009-0003-6218-2735](https://orcid.org/0009-0003-6218-2735)), Renato Quispe-Vargas ([0009-0005-2367-7852](https://orcid.org/0009-0005-2367-7852))
**Affiliation:** Faculty of Statistical and Computer Engineering (FINESI), Universidad Nacional del Altiplano (UNAP), Puno, Peru
\* Corresponding author: 75521963@est.unap.edu.pe

## What this repository contains

The benchmark covers 19 long-record Andean-GC gauges in three regions:

- **Altiplano (7):** Puente Isla Cabanillas in Peru, in the Lake Titicaca basin, plus the Lauca/Caquena headwaters in Chile.
- **Cordillera Blanca (6):** glacier-fed catchments.
- **Western/southern Andes (6).**

The gauges are fused with ERA5, NASA POWER/MERRA-2 and GloFAS v4. Persistence and climatology are compared with Ridge, random forest, histogram gradient boosting, XGBoost (level and log-change targets) and an MLP at 1-, 3- and 7-day leads.

The protocol is designed to avoid leakage:

- a calendar-continuous daily index, so lags are true day offsets;
- identical information at issue time for every method, including Q_t;
- chronological 70/15/15 splits with an h-day embargo between blocks;
- validation-only selection of hyper-parameters and target form;
- 95% moving-block bootstrap intervals and Diebold–Mariano tests of skill against persistence;
- drought-day detection scored with POD, FAR and CSI (variable threshold), plus a nonparametric SSI-30;
- expanding-window walk-forward refits at every gauge;
- spatial statistics: a drought-synchrony correlogram, Moran's I of skill and catchment-attribute drivers;
- maps rendered with **QGIS 4.2** (PyQGIS, headless).

## Key results (generated automatically; see `04-resultados/tablas/metrics_summary.md`)

- At 7 days, learners beat persistence at **18/19** gauges, with median skill **0.101**. The 95% CI excludes zero at 12 gauges.
- At 1 day, learners beat persistence at 15/19 gauges. At Cabanillas the skill is **0.110 [0.064, 0.144]**. An earlier, leaky version of this pipeline had reported a loss here.
- Walk-forward: 53 of 57 gauge–fold combinations have positive 7-day skill (median 0.103).
- RMSE gains do not carry over to drought-day detection. Median CSI is **0.43 for persistence and 0.30 for the learners**.
- Hydrological drought decorrelates over **≈582 km**. Skill shows no spatial clustering (Moran's I p = 0.37) and instead follows hydroclimatic regime.

## Layout

| Path | Content |
| --- | --- |
| `00-gestion/` | Decisions, plan and project log (`00-INDICE.md`) |
| `01-articulo/manuscrito/` | Springer SVMult source: `caudal-sequia-altiplano.tex`, `results.tex` and `backmatter.tex`; auto-generated `cifras.tex` and `tab_*.tex`; `references.bib` (DOIs verified, see `references_verification.md`) |
| `01-articulo/caudal-sequia-altiplano.pdf` | Submission PDF |
| `02-datos/fuentes/INVENTARIO.md` | Data provenance and licences |
| `02-datos/crudos/stations/` | 19 gauge extracts and `benchmark_stations.csv` |
| `02-datos/crudos/clima/` | ERA5, MERRA-2 (NASA POWER) and GloFAS caches and fetch manifests |
| `03-codigo/` | Pipeline: `extract_stations.py`, `fetch_data.py`, `run_experiment.py`, `plots.py`, `spatial_analysis.py`, `make_cifras.py`, `tests/` |
| `03-codigo/maps/` | QGIS map scripts (`make_fig00_qgis.py`, `make_fig08_spatial_qgis.py`) and `.qgz` project |
| `04-resultados/` | Figures (600 dpi PNG + PDF) and result tables |

## Reproduce

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MPLBACKEND=Agg
python -m pytest 03-codigo/tests -q        # leakage / calendar / metric tests
python 03-codigo/extract_stations.py       # needs the Andean-GC QC CSV from Zenodo
python 03-codigo/fetch_data.py             # ERA5, NASA POWER, GloFAS (rate-limited, resumable)
python 03-codigo/run_experiment.py         # about 4 min on a 10-core laptop
python 03-codigo/plots.py
python 03-codigo/spatial_analysis.py
python 03-codigo/make_cifras.py            # writes every number in the paper
# maps (QGIS 4.2 bundled Python; see the script docstrings)
python 03-codigo/maps/make_fig00_qgis.py
python 03-codigo/maps/make_fig08_spatial_qgis.py
cd 01-articulo/manuscrito && pdflatex caudal-sequia-altiplano && bibtex caudal-sequia-altiplano && pdflatex caudal-sequia-altiplano && pdflatex caudal-sequia-altiplano
```

## Data and licences

- Andean-GC: [10.5281/zenodo.18035801](https://doi.org/10.5281/zenodo.18035801), CC BY 4.0.
- ERA5 and GloFAS: Copernicus, accessed via Open-Meteo (CC BY 4.0).
- NASA POWER: public NASA data.

Code is released under the MIT licence (`LICENSE`).
