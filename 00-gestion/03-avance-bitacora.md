# Bitácora de avance — caudal / sequía hidrológica Altiplano

**Proyecto:** `10-paper-caudal-sequia-hidrologica-altiplano`  
**Autores:** Richar Andre Vilca-Solorzano, Dina Maribel Yana-Yucra (UNAP / FINESI, Puno)  
**Fecha de esta entrada:** 2026-09-30 (hora Lima, UTC−5)  
**Documento bilingüe (ES principal / EN breve):** progreso técnico, citas y pendientes de envío.

---

## 1. Objetivos / Objectives

### Español
Entregar un **benchmark abierto multiestación** (laptop-scale) de pronóstico de caudal a corto plazo e **indicación de sequía hidrológica (SSI-30)** para el Altiplano peruano, con foco en la estación SENAMHI **Puente Isla Cabanillas** (`P00000055`, Andean-GC), y comparación honesta frente a baselines de **persistencia** y **climatología estacional**.

Concretamente:
1. Extraer caudal diario QC de Andean-GC (CC BY 4.0) para todas las estaciones Perú con `days_w_data_qc ≥ 5000` (**n = 13**).
2. Emparejar precipitación diaria Open-Meteo / ERA5-Land en lat/lon de cada aforo.
3. Comparar persistencia, climatología, Ridge, Random Forest, Gradient Boosting, XGBoost y un MLP pequeño bajo **particiones cronológicas sin fuga** y **walk-forward** en Cabanillas.
4. Reportar RMSE, MAE, NSE, KGE y *skill* vs. persistencia a horizontes **h = 1** y **h = 7** días.
5. Publicar figuras, tablas, código reproducible y manuscito Springer (SVMult), sin pretender reemplazar SENAMHI.

### English (brief)
Open multi-station Peru streamflow / SSI-30 drought benchmark with Altiplano focus (Cabanillas), leakage-free chronological validation, and honest persistence baselines — research prototype, not an operational forecast service.

---

## 2. Metodología / Methodology

### Datos
| Fuente | Uso | Licencia / nota |
| --- | --- | --- |
| Andean-GC v1.1 (Zenodo `10.5281/zenodo.18035801`) | Caudal diario QC; 13 aforos Perú ≥5000 días QC | CC BY 4.0 |
| Open-Meteo Historical API (ERA5-Land) | Precipitación diaria en cada gauge | Reanálisis Copernicus vía API |
| Meta estaciones | `02-datos/crudos/stations_peru_benchmark_meta.csv` | Incluye flag Altiplano / sur |

**Foco Altiplano:** Puente Isla Cabanillas (`P00000055`; ≈15.47°S, 70.22°W; sistema Coata–Cabanillas / Titicaca). Ventana de modelado alineada: **1994-08-15 → 2024-12-30** (`cifras.tex`).

### Modelos y validación
- Features: rezagos de caudal, estadísticas rodantes, precipitación y estacionalidad (**21** features).
- Split cronológico Cabanillas: train / val / test ≈ **4578 / 981 / 982** (h=1).
- Walk-forward expansivo (3 folds) en Cabanillas para confirmar estabilidad.
- Métricas: RMSE, MAE, NSE, KGE, skill vs. persistencia.

### Principio de validación (adaptado de Fred Torres Cruz / Springer 2026)
El manuscrito ya cita el trabajo de **Torres Cruz** sobre CV bloqueada/espacial y modelos CAR (ver §5). En agricultura, la CV aleatoria **sobreestimó** el error y el ajuste respecto a CV bloqueada (**RMSE +9.1%** y **R² +25.1%** en el estudio blocked-CV). Aquí adaptamos el mismo principio al caudal: **no mezclar aleatoriamente días/cuencas**; preferir **particiones temporales** y *walk-forward* (y, a futuro, bloqueo por cuenca si se amplía el set).

### Pipeline de código (público vs. local)
| Ruta | Rol | ¿Git? |
| --- | --- | --- |
| `03-codigo/run_experiment.py`, `plots.py`, `config.py`, `metrics_utils.py`, `extract_stations.py` | Experimento reproducible del paper | Sí (crítico) |
| `03-codigo/plot_station_map.py` | Runner delgado que invoca el mapa local | Sí (fino) |
| `03-codigo/local/*` | Scripts pesados QGIS/Cartopy, `.qgz`, CSV auxiliar fig00 | **No** — gitignored |

---

## 3. Resultados / Results (corrida real 2026-09-30)

Números tomados de `04-resultados/tablas/metrics_summary.md` y `01-articulo/manuscrito/cifras.tex` (no inventados).

### Cabanillas — test cronológico
| Modelo | h | NSE | KGE | skill vs. pers. | n_test |
| --- | ---: | ---: | ---: | ---: | ---: |
| Persistencia | 1 | **0.902** | 0.951 | 0.000 | 982 |
| MLP (mejor ML h=1) | 1 | 0.871 | 0.912 | −0.146 | 982 |
| Persistencia | 7 | 0.462 | 0.731 | 0.000 | 981 |
| **Ridge** | 7 | **0.550** | 0.674 | **+0.086** | 981 |

Interpretación: a **1 día**, la persistencia sigue siendo la más fuerte; a **7 días**, Ridge mejora sobre persistencia (skill positivo).

### Multiestación (h = 7)
- Mejor ML con skill > 0: **13/13** estaciones.
- Mediana del mejor skill ML: **0.102**.
- Ridge: skill > 0 en 13/13; skill medio **0.078**; NSE medio Ridge **0.639** vs. persistencia **0.569**.

### Walk-forward Ridge (Cabanillas, h = 7)
Skill por fold: 0.136, 0.080, 0.085 → media **≈ 0.100** (`wfMeanSkillHSeven`). Runtime total ≈ **126 s** en laptop.

### Figuras generadas
`fig01`…`fig08` en `04-resultados/figuras/` (hidrograma, forecast, scatter, barras, SSI-30, heatmap multiestación, lead-skill). **fig00** actualizado a basemap satélite/terreno (ver §6).

---

## 4. Conclusiones / Conclusions (provisionales del paper)

1. El benchmark abierto de **13** aforos Perú es viable en laptop y documenta honestamente que **a h=1 la persistencia domina**, mientras que a **h=7 Ridge (y otros ML) aportan skill positivo** en todas las estaciones del set.
2. El SSI-30 paramétrico (z-score mensual de la media móvil 30 días) es un **indicador simplificado** de sequía hidrológica para el benchmark — **no** un SSI distribucional operativo tipo Vicente-Serrano.
3. La validación cronológica / walk-forward alinea el paper con la advertencia metodológica de Torres Cruz (blocked-CV): la CV aleatoria puede **inflar** el desempeño aparente.
4. Limitaciones: una sola fuente de precipitación; SSI-30 simplificado; no es reemplazo SENAMHI.
5. Trabajo futuro: más aforos Altiplano cuando la longitud QC lo permita; SSI/SPEI distribucional; LSTM/transfer bajo el mismo protocolo honesto frente a persistencia.

---

## 5. Citas Fred Torres Cruz (verificadas / ya en el manuscrito)

> En Springer el apellido aparece como **Torres Cruz** (sin guion). En frost / AgroYachay el bib del repo usa a veces `Torres-Cruz`. Abajo: forma verificada para Springer + claves ya usadas en el `.tex`.

### 5.1 Blocked / hierarchical CV (Springer 2026) — clave manuscrito: `torres2026blockedcv`
**Apaza, W. Vilca; Torres Cruz, F.; Carpio Vargas, E. E.** (2026). *Blocked and Hierarchical Cross-Validation for Agricultural Data with Spatial Autocorrelation: Application to Peru's National Agricultural Survey.* En: *Green Technologies and Sustainable Intelligence — Volume II*. Springer Proceedings in Physics **352**: **3–13**. DOI: [10.1007/978-3-032-20151-5_1](https://doi.org/10.1007/978-3-032-20151-5_1).

Hallazgo citado para este paper de caudal: la CV aleatoria **sobreestimó** RMSE en **9.1%** y R² en **25.1%** frente a CV bloqueada → principio adaptado a splits **temporales / por cuenca**.

### 5.2 Bayesian hierarchical CAR (Springer 2026) — clave: `torres2026bayescar`
**Maquera Andrade, A. J.; Torres Cruz, F.** (2026). *Bayesian Spatial Analysis of Agricultural Yields and Climate Vulnerability in Southern Peru Using Hierarchical CAR Models* (2024). En el mismo volumen Springer Proceedings in Physics **352**: **43–55**. DOI: [10.1007/978-3-032-20151-5_4](https://doi.org/10.1007/978-3-032-20151-5_4).

### 5.3 Otras citas de la línea abierta ya en `references.bib` / `.tex`
| Clave | Referencia breve |
| --- | --- |
| `torres2025frost` | Torres-Cruz, Yana-Yucra, Vilca-Solorzano. Frost / Tmin multiestación Altiplano. **IJACSA** 16(9), 2025. DOI `10.14569/IJACSA.2025.0160992`. |
| `torres2026agroyachay` | Torres-Cruz et al. **AgroYachay** IoT+LLM. **SoftwareX** 36:103037 (2026). DOI `10.1016/j.softx.2026.103037`; Zenodo `10.5281/zenodo.20829992`. |
| `vilca2026agrocommish` | Vilca-Solorzano et al. (Torres-Cruz coautor). **AgroCommish** ESP32. **Zenodo** software `10.5281/zenodo.20655609` (SoftwareX *en preparación*; **no** citar como artículo SoftwareX publicado). |

Estas tres últimas + CAR/blocked-CV ya aparecen en la sección *Related Work* de `caudal-sequia-altiplano.tex`. Nota: `torres2026bayescar` y `torres2026blockedcv` están como `\bibitem` en el `.tex` canónico; conviene añadirlas también a `references.bib` en una pasada posterior.

---

## 6. Estado de figuras, códigos y mapa fig00 (QGIS / Python)

### Visualización fig00 (prioridad cartográfica)
| Ítem | Estado |
| --- | --- |
| Salida | `04-resultados/figuras/fig00_station_map.png` + `.pdf` (600 dpi) |
| Estaciones | 13; **Cabanillas** resaltada (estrella roja) |
| Cambio visual | De fondo beige / *World Shaded Relief* + vector Natural Earth → **Esri World Imagery** (satélite / terreno real: Andes, costa, vegetación) + *World Hillshade* ligero; marco oscuro; etiquetas legibles sobre imagen |
| Qué funcionó | **Python / Cartopy** (`03-codigo/local/plot_station_map_earthy.py`) con tiles Esri; `imagery_ok=True` (2026-09-30 ~18:14 Lima) |
| QGIS intentado primero | Sí. App `/Applications/QGIS-final-4_2_2.app`; `qgis_process --version` OK (QGIS 4.2.2). `PROJ_LIB` → `.../Resources/qgis/proj` (`proj.db` OK); `GDAL_DATA` → `.../Resources/qgis/gdal`. |
| Límite QGIS headless | En modo *offscreen*, el registro de proveedores **no incluye `wms`**; falló `QgsRasterLayer(..., "wms")` para XYZ Imagery (“Cannot instantiate the 'wms' data provider”). Sí hay `xyzvectortiles`, `gdal`, `ogr`, `memory`. |
| Entregable QGIS | Proyecto estaciones `03-codigo/local/fig00_station_map.qgz` + CSV `stations_fig00.csv` + script `make_fig00_qgis.py` (para GUI). |

#### Pasos QGIS GUI (si se desea regenerar el raster en escritorio)
1. Abrir `03-codigo/local/fig00_station_map.qgz` en QGIS 4.2.2.
2. *Browser → XYZ Tiles → New Connection*:  
   - Imagery: `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`  
   - Hillshade (opcional, opacidad ~35%): `.../Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}`
3. Extensión sugerida: lon −80.2…−68.0, lat −17.9…−7.4; etiquetar Cabanillas; exportar *Layout* PNG/PDF a `04-resultados/figuras/`.

### Política git (sin push en esta sesión)
- `03-codigo/local/` → **gitignore** (scripts experimentales / QGIS-pesados / `.qgz`).
- Códigos críticos del paper permanecen en `03-codigo/` versionable.
- **No** se hace `git push` desde esta bitácora.

---

## 7. Venue y envío (corregido 2026-09-30 noche)

- **Venue correcto:** ICICCDS 2027, *International Conference on Intelligent Computing, Communication and Data Science* (el nombre lo confirma la página de login del CMT).
- **Portal:** https://cmt3.research.microsoft.com/ICICCDS2027
- **Fecha límite:** 30 Sep 2026, ampliada unas horas según los autores.
- **ERRATA de esta sección:** la "verificación" anterior apuntaba a **ICCCDS 2027** (Communication, Computing and Data Security, TCET Mumbai, Smart CMS, fecha límite 30 Oct 2026). Es **otro congreso** y no aplica a este paper.

## 8. Resumen de esta sesión (2026-09-30 tarde)

1. Se intentó **QGIS primero** (PROJ/GDAL corregidos); headless sin provider `wms` → no export raster XYZ; sí se guardó **`.qgz`** de estaciones.
2. **Fallback Python** con Esri World Imagery + Hillshade → **fig00 tierra/satélite** escrito en disco (PNG ~15 MB, PDF ~19 MB).
3. Scripts pesados bajo `03-codigo/local/` + política gitignore; runner público delgado.
4. Esta bitácora documenta objetivos, métodos, resultados reales, conclusiones, citas Torres Cruz y pendiente CMT **sin urgencia**.

*Fin de la entrada.*

## Destino de envío (venue)

- **Conferencia:** ICICCDS 2027
- **Portal CMT:** https://cmt3.research.microsoft.com/ICICCDS2027
- **PDF a enviar:** `01-articulo/caudal-sequia-altiplano.pdf`
- **Autores:** Richar Andre Vilca-Solorzano y Dina Maribel Yana-Yucra (UNAP–FINESI)
- **Estado:** pendiente de submit (horario ampliado; prioridad en calidad)
- **Nota:** verificar en el sitio oficial si el nombre aparece también como ICCCDS; el CMT acordado para este trabajo es el enlace de arriba.


---

## 9. Revisión crítica y rehecho completo (2026-09-30, 18:00–)

**Errores encontrados en la versión anterior (invalidaban conclusiones):**
1. Los modelos ML no recibían Q_t (solo desde t−1), mientras que la persistencia sí → la conclusión "a h=1 gana la persistencia" era un artefacto (con Q_t, Ridge h=1 skill +0.07 en Cabanillas).
2. Los rezagos y el objetivo se calculaban por fila y no por día: las series tienen huecos de hasta 8 años, así que "t+7" podía caer meses después.
3. El split de validación se calculaba pero no se usaba (no había tuning).
4. La precipitación se atribuía a "ERA5-Land", pero el endpoint era5_land de Open-Meteo no sirve precipitación.
5. Bibliografía: autores incorrectos en Crisnejas (son Vásquez-Ramírez y Vásquez-Paredes) y Ramis (son Lujano et al.); título de frost incorrecto.
6. fig00 pesaba 19 MB en PDF.

**Rediseño:** 19 aforos (13 Perú + 6 Altiplano chileno), 3 regiones, h = 1/3/7, ERA5 en el centroide de cuenca + NASA POWER/MERRA-2 + GloFAS v4 (ablación de fusión), tuning en validación con embargo, IC por block-bootstrap, test de Diebold–Mariano, detección de sequía (umbral variable Q20 mensual; POD/FAR/CSI), SSI-30 no paramétrico, walk-forward en las 19 estaciones, tests automáticos (`03-codigo/tests`), cifras generadas automáticamente (`make_cifras.py`), bibliografía de 60 entradas con DOI verificado en Crossref (`references_verification.md`), mapa en QGIS (`03-codigo/maps/`).
