# Manuscript draft (companion to LaTeX)

**Canonical manuscript:** `01-articulo/manuscrito/caudal-sequia-altiplano.tex` (Springer SVMult; macros in `cifras.tex`).  
**Abstract source of truth for title/keywords:** `01-articulo/00-abstract.md`.

## Title

Open-data machine learning for streamflow and hydrological drought forecasting in the Peruvian Altiplano

## Authors

Richar Andre Vilca-Solorzano & Dina Maribel Yana-Yucra (Universidad Nacional del Altiplano, Puno, Peru)

## Resumen (espanol)

La sequia hidrologica y la variabilidad del caudal afectan la seguridad hidrica en el Altiplano peruano. Presentamos un pipeline abierto y reproducible de aprendizaje automatico para pronostico de caudal a 1 y 7 dias e un indice tipo SSI-30, usando caudal SENAMHI redistribuido en Andean-GC (estacion Puente Isla Cabanillas) y precipitacion Open-Meteo/ERA5-Land. Bajo particion temporal estricta, la persistencia obtiene el mejor NSE a 1 dia (0.907). A 7 dias, Ridge mejora la persistencia (NSE 0.562 frente a 0.486; skill +0.077). Publicamos fuentes, licencias, codigo, tablas y figuras a 600 dpi. El trabajo es un benchmark transparente, no un reemplazo operativo de los servicios hidrologicos nacionales.

## Results (from actual `run_experiment.py`)

Primary data: Andean-GC QC, station P00000055, analysis window 2000-01-01 onward with precip; test n=874.

See `04-resultados/tablas/metrics_test.csv` and LaTeX Table 1 for full RMSE/MAE/NSE/skill.

## Limitations

Single long Altiplano gauge in the main protocol; reanalysis precip; approximate SSI; no claim of operational deployment.
