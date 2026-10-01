# Abstract (ICICCDS 2027): versión final, generada desde el manuscrito

**Title:** Honest Baselines for Streamflow and Hydrological-Drought Forecasting in the Tropical Andes: An Open, Leakage-Free Multi-Station Benchmark with an Altiplano Focus

**Authors:** Richar Andre Vilca-Solorzano, Dina Maribel Yana-Yucra, Renato Quispe-Vargas. Faculty of Statistical and Computer Engineering, Universidad Nacional del Altiplano, Puno, Peru

Short-range streamflow forecasts and early drought signals matter in the tropical Andes, yet reported machine-learning gains are hard to compare because evaluation is rarely leakage-free. We release an open benchmark of 19 Andean-GC gauges (7 Altiplano, including Puente Isla Cabanillas in the Titicaca basin; 6 Cordillera Blanca; 6 western/southern Andes) fused with ERA5, MERRA-2 and GloFAS v4. Persistence and climatology are compared with five learner families at 1-, 3- and 7-day leads under a calendar-continuous, embargoed, validation-tuned protocol with block-bootstrap intervals, Diebold–Mariano tests and walk-forward refits. Learners beat persistence at 15/19 gauges at one day and 18/19 at seven days (median skill 0.101). At Cabanillas the one-day skill is 0.110 (95% CI 0.064–0.144), reversing an earlier leaky result. Lower RMSE did not improve drought-day detection (median CSI 0.43 for persistence vs. 0.30). Hydrological drought decorrelates over ≈582 km, and skill follows hydroclimatic regime rather than location.

**Keywords:** streamflow forecasting; hydrological drought; Altiplano; machine learning; persistence baseline; data leakage; spatial statistics; open benchmark
