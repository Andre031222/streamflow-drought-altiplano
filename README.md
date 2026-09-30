# An Open Multi-Station Benchmark for Streamflow Forecasts and Hydrological Drought Indication in the Peruvian Altiplano

**Venue target:** ICICCDS 2027  
**Authors:** Richar Andre Vilca-Solorzano, Dina Maribel Yana-Yucra  
**Affiliation:** Universidad Nacional del Altiplano (UNAP), Facultad de Ingenieria Estadistica e Informatica (FINESI), Puno, Peru  
**ORCID:** [0009-0003-2385-5263](https://orcid.org/0009-0003-2385-5263) (Vilca-Solorzano), [0009-0003-6218-2735](https://orcid.org/0009-0003-6218-2735) (Yana-Yucra)  
**Corresponding email:** andrevilcasolorzano@gmail.com  
**Code:** https://github.com/Andre031222/streamflow-drought-altiplano

Reproducible laptop-scale **multi-station Peru benchmark** (13 SENAMHI gauges with Andean-GC `days_w_data_qc >= 5000`) comparing persistence, seasonal climatology, Ridge, Random Forest, Gradient Boosting, XGBoost, and a small MLP for 1- and 7-day streamflow forecasts. Altiplano focus: **Puente Isla Cabanillas** (`P00000055`), plus SSI-30 drought index (month-wise z-score of 30-day mean; parametric approx.).

## Related open repositories

This paper continues an open Altiplano research / software line:

| Repository | Role | Citation / DOI |
| --- | --- | --- |
| [frost-prediction-altiplano-puno](https://github.com/Andre031222/frost-prediction-altiplano-puno) | Prior multi-station comparative climate ML (frost / $T_{min}$) | IJACSA 2025, [10.14569/IJACSA.2025.0160992](https://doi.org/10.14569/IJACSA.2025.0160992) |
| [agroyachay](https://github.com/Andre031222/agroyachay) | Cloud IoT + LLM platform for Andean smallholders | SoftwareX 2026, [10.1016/j.softx.2026.103037](https://doi.org/10.1016/j.softx.2026.103037); Zenodo [10.5281/zenodo.20829992](https://doi.org/10.5281/zenodo.20829992) |
| [agrocommish](https://github.com/Andre031222/agrocommish) | Desktop ESP32 edge commissioning companion to AgroYachay | Zenodo software [10.5281/zenodo.20655609](https://doi.org/10.5281/zenodo.20655609) (SoftwareX in preparation; **not** a published journal article) |
| [streamflow-drought-altiplano](https://github.com/Andre031222/streamflow-drought-altiplano) | **This paper** — open hydrology analysis / streamflow & drought forecasting (not farm IoT) | ICICCDS 2027 target |

## Canonical manuscript

- LaTeX (Springer SVMult): `01-articulo/manuscrito/caudal-sequia-altiplano.tex`
- Shared macros / numbers: `01-articulo/manuscrito/cifras.tex`
- Compiled PDF copy: `01-articulo/caudal-sequia-altiplano.pdf`
- Abstract draft: `01-articulo/00-abstract.md`

Compile:

```bash
cd 01-articulo/manuscrito
pdflatex caudal-sequia-altiplano.tex
pdflatex caudal-sequia-altiplano.tex
```

Figures are included from `figuras/` (symlink to `04-resultados/figuras/`).

## Repository layout

| Path | Content |
| --- | --- |
| `01-articulo/manuscrito/` | Springer manuscript sources |
| `02-datos/fuentes/INVENTARIO.md` | Data URLs and licenses |
| `02-datos/crudos/stations/` | Extracted daily QC CSVs (13 stations) |
| `02-datos/crudos/openmeteo/` | Open-Meteo precip caches |
| `02-datos/procesados/` | Merged series, SSI, prediction tables |
| `03-codigo/` | Python multi-station pipeline |
| `04-resultados/figuras/` | Figures (PNG at 600 dpi + PDF) |
| `04-resultados/tablas/` | `metrics_by_station.csv`, walk-forward, summary |

## How to reproduce

Requirements: Python 3.10+ (tested on macOS arm64 with Python 3.14), about 500 MB disk for the Andean-GC QC CSV.

```bash
cd /path/to/streamflow-drought-altiplano
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export MPLBACKEND=Agg
python 03-codigo/run_experiment.py
```

### Data not shipped in git (size)

The full Andean-GC QC CSV (`AndeanGC_data_1950_2024_qc.csv`, ~22 MB) is **excluded** from this repository. Download Andean-GC from Zenodo ([10.5281/zenodo.18035801](https://doi.org/10.5281/zenodo.18035801)), place the QC CSV and metadata under `02-datos/crudos/andean-gc/`, then re-run `03-codigo/extract_stations.py` if you need to rebuild station extracts. The 13 station CSVs under `02-datos/crudos/stations/`, Open-Meteo caches, processed tables, metrics and figures **are** included for reproducibility without re-downloading the full dump.

Outputs:

- `04-resultados/tablas/metrics_by_station.csv`
- `04-resultados/tablas/metrics_walkforward_cabanillas.csv`
- `04-resultados/tablas/metrics_summary.md`
- `04-resultados/figuras/fig01_*` ... `fig08_*` (PNG 600 dpi and PDF)

## Key results (actual multi-station run only)

Stations used: **13**. Focus: Puente Isla Cabanillas (`P00000055`), chronological test $n=982$ (h=1).

| Model | Horizon | NSE | KGE | Skill vs persistence |
| --- | ---: | ---: | ---: | ---: |
| persistence | 1 d | 0.902 | 0.951 | 0.000 |
| MLP (best ML at 1 d) | 1 d | 0.871 | 0.912 | -0.146 |
| Ridge (best at 7 d) | 7 d | 0.550 | 0.674 | +0.086 |
| persistence | 7 d | 0.462 | 0.731 | 0.000 |

Multi-station (h=7): best ML skill > 0 at **13/13** stations (median skill 0.102); Ridge skill > 0 at 13/13 (mean skill 0.078). Walk-forward Ridge at Cabanillas h=7: mean skill 0.100 across 3 expanding folds.

Full metrics: `04-resultados/tablas/metrics_by_station.csv`. Do not substitute invented numbers.

## Data provenance

See `02-datos/fuentes/INVENTARIO.md` (Andean-GC CC BY 4.0; Open-Meteo / ERA5-Land terms).

## License

MIT (see `LICENSE`). Upstream datasets keep their own licenses.
