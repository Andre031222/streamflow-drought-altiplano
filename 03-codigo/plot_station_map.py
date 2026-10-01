"""Thin public runner for fig00 (Figure 1, benchmark station map).

The map is rendered headless with PyQGIS by ``03-codigo/maps/make_fig00_qgis.py``
(tracked). That script must run under the Python bundled with QGIS; if it is
started from any other interpreter (e.g. the project .venv) it re-executes
itself with ``$QGIS_APP/Contents/MacOS/python3.12`` and
``PYTHONHOME=$QGIS_APP/Contents/Frameworks`` (default QGIS_APP:
``/Applications/QGIS-final-4_2_2.app``).

Usage (from repo root)::

    python 03-codigo/plot_station_map.py            # full 600 dpi PNG + PDF
    python 03-codigo/plot_station_map.py --no-pdf   # PNG only

Direct call, equivalent::

    QGIS=/Applications/QGIS-final-4_2_2.app/Contents
    PYTHONHOME=$QGIS/Frameworks $QGIS/MacOS/python3.12 03-codigo/maps/make_fig00_qgis.py

Outputs: ``04-resultados/figuras/fig00_station_map.{png,pdf}``
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "maps" / "make_fig00_qgis.py"


def main() -> int:
    if not SCRIPT.is_file():
        print(f"ERROR: missing {SCRIPT}", file=sys.stderr)
        return 1
    return subprocess.call([sys.executable, str(SCRIPT), *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
