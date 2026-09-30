# Abstract (ICICCDS 2027) — borrador v1

**Title:** Open-data machine learning for streamflow and hydrological drought forecasting in the Peruvian Altiplano

**Authors:** Richar Andre Vilca-Solorzano, Dina Maribel Yana-Yucra  
**Affiliation:** Universidad Nacional del Altiplano, Puno, Peru  
**Track (sugerido):** Intelligent Computing & AI / Data Science & Big Data Analytics

## Abstract (English)

Hydrological drought and highly variable streamflow threaten water security for communities and agriculture across the Peruvian Altiplano. Operational forecasting is often limited by sparse gauges and uneven access to proprietary models. We present a fully open, reproducible machine-learning pipeline for short-horizon streamflow forecasting and hydrological drought indication using publicly available discharge and climate series for Altiplano basins. After quality control and lag-based feature construction, we compare classical baselines (persistence and seasonal climatology) against lightweight learners suitable for commodity laptops (regularized linear models, random forests, and gradient boosting), under a strict temporal train–validation–test split that prevents leakage. Forecast skill is reported with RMSE, MAE, Nash–Sutcliffe efficiency (NSE), and skill relative to persistence at multiple lead times. We further derive a simple standardized streamflow / drought index from the same open series to illustrate early-warning use cases. All raw sources, licenses, code, and metrics are released with the paper. Results show whether ML improves upon naive baselines under high-altitude hydroclimatic seasonality and highlight failure modes when gauges are short or gappy. The study does not claim operational replacement of national hydrological services; it offers a transparent benchmark and decision-support prototype for data-sparse Andean catchments.

**Keywords:** streamflow forecasting, hydrological drought, Altiplano, open data, machine learning, Nash–Sutcliffe efficiency

## Resumen (español)

La sequía hidrológica y la alta variabilidad del caudal afectan la seguridad hídrica en el Altiplano peruano. Presentamos un pipeline abierto y reproducible de aprendizaje automático para pronóstico de caudal a corto plazo e indicios de sequía hidrológica, usando series públicas de descarga y clima. Comparamos baselines (persistencia y climatología estacional) con modelos livianos (lineales regularizados, bosques aleatorios y gradient boosting) bajo partición temporal estricta, reportando RMSE, MAE, NSE y skill frente a persistencia. Publicamos fuentes, licencias, código y métricas. El trabajo es un benchmark transparente para cuencas andinas con datos escasos, no un reemplazo operativo de los servicios hidrológicos nacionales.

## Nota
Los números de resultados se insertarán tras correr `03-codigo/run_experiment.py` (métricas reales, sin inventar).
