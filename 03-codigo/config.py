"""Paths and experiment settings for the Andean streamflow / drought benchmark."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "02-datos" / "crudos"
PROC = ROOT / "02-datos" / "procesados"
FIG = ROOT / "04-resultados" / "figuras"
TAB = ROOT / "04-resultados" / "tablas"
CODE = ROOT / "03-codigo"
STATIONS_DIR = RAW / "stations"
CLIMATE_DIR = RAW / "clima"
STATION_META = STATIONS_DIR / "benchmark_stations.csv"
MANUSCRIPT = ROOT / "01-articulo" / "manuscrito"

MIN_QC_DAYS = 5000

# Primary Altiplano focus station (figures, walk-forward, drought case study)
FOCUS_STATION_ID = "P00000055"
FOCUS_STATION_NAME = "Puente Isla Cabanillas"

# Chronological split fractions of the calendar-continuous record (no shuffle)
TRAIN_FRAC = 0.70
VAL_FRAC = 0.15  # used for hyper-parameter selection; remainder = test

HORIZONS = [1, 3, 7]  # days ahead
RANDOM_STATE = 42
N_JOBS = -1

# Features (all computed on a daily calendar index; gaps stay NaN)
LAGS_Q = [0, 1, 2, 3, 7, 14, 30]          # lag 0 = Q_t (information available at issue time)
ROLL_WINDOWS = [7, 14, 30]
LAGS_P = [0, 1, 2, 3, 7]
P_SUMS = [7, 30, 90]

# Hydrological drought: variable threshold level method on daily Q
DROUGHT_QUANTILE = 0.20   # monthly Q80 exceedance (20th percentile) from TRAINING data
SSI_WINDOW = 30           # accumulation for the nonparametric SSI

# Uncertainty
N_BOOT = 1000
BOOT_BLOCK = 30           # days (moving-block bootstrap)

MIN_ROWS_AFTER_FEATURES = 800

# Model selection: mean validation RMSE over this many chronological blocks
# (the official validation block plus earlier blocks of the same length in train)
SELECTION_BLOCKS = 3

# Drought decision: forecast-side threshold factor chosen on validation CSI
DROUGHT_FACTORS = [round(0.80 + 0.05 * i, 2) for i in range(21)]  # 0.80 ... 1.80

# Walk-forward (expanding window) on focus station
WF_N_SPLITS = 3
WF_MIN_TRAIN_FRAC = 0.50
