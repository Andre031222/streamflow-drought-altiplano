# Multi-station Peru benchmark — test metrics (real run)

Stations used: **13**

Focus (Altiplano): Puente Isla Cabanillas (P00000055)

SSI-30: month-wise z-score of 30-day rolling mean (parametric approx.; see Vicente-Serrano et al. 2012 for full SSI).

## Focus station (chronological test)

| model | horizon | RMSE | MAE | NSE | KGE | skill_vs_persistence | n_test |
| --- | --- | --- | --- | --- | --- | --- | --- |
| persistence | 1 | 11.0730 | 4.6901 | 0.9021 | 0.9511 | 0.0000 | 982 |
| climatology | 1 | 28.4738 | 15.9772 | 0.3527 | 0.5063 | -1.5715 | 982 |
| Ridge | 1 | 13.8417 | 8.0810 | 0.8470 | 0.8953 | -0.2500 | 982 |
| RandomForest | 1 | 13.3158 | 6.5124 | 0.8584 | 0.9046 | -0.2025 | 982 |
| GradientBoosting | 1 | 12.8232 | 6.6273 | 0.8687 | 0.8960 | -0.1581 | 982 |
| MLP | 1 | 12.6927 | 6.5466 | 0.8714 | 0.9123 | -0.1463 | 982 |
| XGBoost | 1 | 12.9455 | 6.4976 | 0.8662 | 0.9012 | -0.1691 | 982 |
| persistence | 7 | 25.9630 | 12.5663 | 0.4622 | 0.7312 | 0.0000 | 981 |
| climatology | 7 | 28.4954 | 15.9263 | 0.3522 | 0.5088 | -0.0975 | 981 |
| Ridge | 7 | 23.7371 | 14.2826 | 0.5505 | 0.6743 | 0.0857 | 981 |
| RandomForest | 7 | 27.6312 | 14.6023 | 0.3909 | 0.6260 | -0.0643 | 981 |
| GradientBoosting | 7 | 25.6444 | 13.9529 | 0.4754 | 0.6386 | 0.0123 | 981 |
| MLP | 7 | 24.4466 | 13.3983 | 0.5232 | 0.6795 | 0.0584 | 981 |
| XGBoost | 7 | 27.1563 | 14.7400 | 0.4117 | 0.6263 | -0.0460 | 981 |

## Multi-station highlights (lead 7 d)

| gauge_name | best_model | NSE | KGE | skill |
| --- | --- | ---: | ---: | ---: |
| La Capilla | XGBoost | 0.704 | 0.813 | 0.161 |
| Quitaracsa | GradientBoosting | 0.425 | 0.495 | 0.158 |
| Cahua | MLP | 0.747 | 0.822 | 0.136 |
| Egemsa Km 105 | MLP | 0.766 | 0.831 | 0.122 |
| Recreta | MLP | 0.657 | 0.658 | 0.118 |
| Chancos | Ridge | 0.590 | 0.651 | 0.106 |
| Ocoña | MLP | 0.673 | 0.684 | 0.102 |
| Condorcerro | Ridge | 0.630 | 0.662 | 0.098 |
| Puente Isla Cabanillas | Ridge | 0.550 | 0.674 | 0.086 |
| Llanganuco | XGBoost | 0.863 | 0.911 | 0.061 |
| Salamanca | Ridge | 0.566 | 0.684 | 0.055 |
| Pachacoto | Ridge | 0.651 | 0.696 | 0.019 |
| Colcas | RandomForest | 0.631 | 0.778 | 0.003 |

Stations with positive skill at h=7 (best ML): 13/13

Median best-ML skill at h=7: 0.102

### Ridge vs persistence at h=7 (all stations)

- Mean NSE Ridge: 0.639
- Mean NSE persistence: 0.569
- Mean skill Ridge: 0.078
- Median skill Ridge: 0.086
- Stations Ridge skill>0: 13/13

## Walk-forward (expanding) — Cabanillas Ridge

| horizon | fold | NSE | KGE | skill_vs_persistence | n_train | n_test | test_start | test_end |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 0.7903 | 0.8699 | -0.1913 | 3270 | 1090 | 2012-09-05 | 2015-08-30 |
| 1 | 2 | 0.7963 | 0.8590 | -0.2789 | 4360 | 1090 | 2015-08-31 | 2021-06-06 |
| 1 | 3 | 0.8510 | 0.8997 | -0.2482 | 5450 | 1091 | 2021-06-07 | 2024-12-30 |
| 7 | 1 | 0.6042 | 0.7402 | 0.1364 | 3267 | 1089 | 2012-09-02 | 2015-08-26 |
| 7 | 2 | 0.4481 | 0.5940 | 0.0796 | 4356 | 1089 | 2015-08-27 | 2021-06-01 |
| 7 | 3 | 0.5597 | 0.6848 | 0.0847 | 5445 | 1090 | 2021-06-02 | 2024-12-24 |

Runtime: 125.5 s
