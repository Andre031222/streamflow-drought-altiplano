"""Paths and experiment settings for multi-station Peru streamflow ML study."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "02-datos" / "crudos"
PROC = ROOT / "02-datos" / "procesados"
FIG = ROOT / "04-resultados" / "figuras"
TAB = ROOT / "04-resultados" / "tablas"
CODE = ROOT / "03-codigo"
STATIONS_DIR = RAW / "stations"
OPENMETEO_DIR = RAW / "openmeteo"
STATION_META = STATIONS_DIR / "peru_benchmark_stations.csv"

# Primary Altiplano focus station (figures, SSI, walk-forward)
FOCUS_STATION_ID = "P00000055"
FOCUS_STATION_NAME = "Puente Isla Cabanillas"

# Temporal split fractions (chronological, no shuffle)
TRAIN_FRAC = 0.70
VAL_FRAC = 0.15
# remainder = test

HORIZONS = [1, 7]  # days ahead
RANDOM_STATE = 42
N_JOBS = -1

# Feature windows
LAGS_Q = [1, 2, 3, 7, 14, 30]
ROLL_WINDOWS = [7, 14, 30]
LAGS_P = [0, 1, 2, 3, 7]

# Minimum usable rows after feature build (skip short remnants)
MIN_ROWS_AFTER_FEATURES = 800

# Walk-forward (expanding window) on focus station only
WF_N_SPLITS = 3
WF_MIN_TRAIN_FRAC = 0.50

# Model complexity tuned for laptop runtime (<45 min for ~13 stations)
RF_N_EST = 120
GB_N_EST = 120
XGB_N_EST = 200
MLP_MAX_ITER = 350
