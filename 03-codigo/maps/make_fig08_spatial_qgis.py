#!/usr/bin/env python3
"""Figure fig08 -- spatial forecast skill and drought synchrony, rendered headless with PyQGIS.

Two side-by-side map panels (Springer text width, 122 mm) over the same extent,
projection, relief and Natural Earth layers as ``make_fig00_qgis.py``:

(a) *Forecast skill at 7-day lead* -- catchments filled with a diverging Crameri
    ``vik`` ramp (reversed: blue = better than persistence), centred at 0 and
    clipped to [-0.3, 0.3], by ``skill_h7``; one fixed-size circle per gauge in
    the same colour, with a bold black outline when the 95 % CI excludes 0
    (``sig``) and a thin grey outline otherwise. Cabanillas (P00000055) labelled.
(b) *Hydrological-drought synchrony* -- lines between gauge pairs with
    ``n_months >= 60`` and ``rho_ssi >= 0.2`` (Spearman rho of monthly SSI-30),
    coloured with Crameri ``batlow`` classes and widened with rho (weak drawn
    first, strongest on top); gauges as region markers (Okabe-Ito, as in fig00).

Gauges that would overlap at this scale (Cordillera Blanca and Chilean Altiplano
clusters) are displaced radially by a small repulsion step computed on paper
(mm); a thin leader joins each displaced symbol to its true location. Both
panels use the same displaced positions, so the pair lines in (b) end on the
markers.

Inputs (defaults)::

    04-resultados/tablas/spatial_gauge_skill.csv
        gauge_id, gauge_name, region, lat, lon, skill_h7, skill_lo, skill_hi, sig,
        csi_h7, csi_pers_h7
    04-resultados/tablas/spatial_ssi_pairs.csv
        gauge_a, gauge_b, lat_a, lon_a, lat_b, lon_b, dist_km, n_months, rho_ssi

plus the fig00 layers (relief RGB in 02-datos/crudos/dem/, Natural Earth clips
in 02-datos/crudos/naturalearth/clip/, catchments_benchmark19.gpkg). Run
``make_fig00_qgis.py`` once first if the relief RGB / NE clips are missing.

How to run (repository root; same QGIS 4.2.2 bundle as fig00, the script
re-executes itself with the bundled python3.12 if needed)::

    QGIS=/Applications/QGIS-final-4_2_2.app/Contents
    PYTHONHOME=$QGIS/Frameworks $QGIS/MacOS/python3.12 03-codigo/maps/make_fig08_spatial_qgis.py

Options: ``--mock`` builds random but realistic mock tables (coordinates from
02-datos/crudos/stations/benchmark_stations.csv) in ``/tmp/fig08_mock`` and
renders from them (output then gets a ``_MOCK`` suffix unless ``--out`` is
given); ``--skill CSV`` / ``--pairs CSV`` override the inputs; ``--out STEM``
overrides the output stem; ``--no-pdf``; ``FIG_DPI=200`` env var for a quick
PNG preview.

Outputs: ``04-resultados/figuras/fig08_spatial_skill_synchrony.png`` (600 dpi)
and ``.pdf`` (vectors/text kept, relief rasterised at 300 dpi).
"""
from __future__ import annotations

import csv
import math
import os
import subprocess
import sys
from pathlib import Path

QGIS_APP = Path(os.environ.get("QGIS_APP", "/Applications/QGIS-final-4_2_2.app"))
QC = QGIS_APP / "Contents"
ROOT = Path(__file__).resolve().parents[2]


def _reexec_with_qgis_python() -> None:
    try:
        import qgis.core  # noqa: F401
        return
    except ImportError:
        pass
    py = QC / "MacOS/python3.12"
    if not py.is_file():
        sys.exit(f"QGIS python not found at {py}; set QGIS_APP")
    env = dict(os.environ, PYTHONHOME=str(QC / "Frameworks"))
    env.pop("PYTHONPATH", None)
    sys.exit(subprocess.call([str(py), __file__, *sys.argv[1:]], env=env))


_reexec_with_qgis_python()

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"] = str(QC / "Resources/qgis/proj")
os.environ["GDAL_DATA"] = str(QC / "Resources/qgis/gdal")
os.environ["QGIS_PREFIX_PATH"] = str(QGIS_APP)
os.environ["QGIS_PLUGINPATH"] = str(QC / "PlugIns/qgis")

import numpy as np  # noqa: E402
from qgis.core import (  # noqa: E402
    Qgis,
    QgsApplication,
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureRequest,
    QgsField,
    QgsFillSymbol,
    QgsGeometry,
    QgsGradientColorRamp,
    QgsGradientFillSymbolLayer,
    QgsGradientStop,
    QgsGraduatedSymbolRenderer,
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemMap,
    QgsLayoutItemMapGrid,
    QgsLayoutItemScaleBar,
    QgsLayoutItemShape,
    QgsLayoutMeasurement,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsLegendStyle,
    QgsLineSymbol,
    QgsMarkerLineSymbolLayer,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsPointXY,
    QgsPrintLayout,
    QgsProject,
    QgsProperty,
    QgsRasterLayer,
    QgsRectangle,
    QgsRendererCategory,
    QgsRendererRange,
    QgsSimpleLineCallout,
    QgsSingleSymbolRenderer,
    QgsSymbolLayer,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)
from qgis.PyQt.QtCore import QMetaType, QPointF, Qt  # noqa: E402
from qgis.PyQt.QtGui import QColor, QFont  # noqa: E402

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
STATIONS = ROOT / "02-datos/crudos/stations/benchmark_stations.csv"
CATCH = ROOT / "02-datos/crudos/andean-gc/catchments_benchmark19.gpkg"
RELIEF = ROOT / "02-datos/crudos/dem/relief_rgb_0p0075deg.tif"
NE_CLIP = ROOT / "02-datos/crudos/naturalearth/clip"
TAB = ROOT / "04-resultados/tablas"
SKILL_CSV = TAB / "spatial_gauge_skill.csv"
PAIRS_CSV = TAB / "spatial_ssi_pairs.csv"
OUT = ROOT / "04-resultados/figuras/fig08_spatial_skill_synchrony"
MOCK_DIR = Path(os.environ.get("FIG08_MOCK_DIR", "/tmp/fig08_mock"))

# --------------------------------------------------------------------------
# Design constants (shared with fig00)
# --------------------------------------------------------------------------
FONT = "Arial"
C_CB, C_WS, C_ALT, C_FOCUS = "#0072B2", "#E69F00", "#CC79A7", "#D55E00"
# Water kept neutral (not blue) so it never reads as positive skill in panel (a)
C_WATER, C_WATER_LINE, C_TEXT = "#E3E8EB", "#8FA3B1", "#222222"
FOCUS_ID = "P00000055"

# Crameri vik, reversed (index 0 = skill -0.3 -> dark red; 1 = +0.3 -> navy)
VIK_R = ['#590008', '#731406', '#912d06', '#b2511d', '#c27041', '#cf8c66', '#dbaa8d',
         '#e9cab8', '#ece5e0', '#c6dbe6', '#94bed2', '#619ebd', '#307da6', '#0c5e92',
         '#034481', '#022b71', '#001261']
SKILL_LIM = 0.3
# Crameri batlow classes for rho_ssi (lower bound, upper bound, colour, width mm)
RHO_CLASSES = [(0.2, 0.4, "#95872c", 0.16), (0.4, 0.6, "#477150", 0.32),
               (0.6, 0.8, "#165062", 0.52), (0.8, 1.0001, "#011959", 0.80)]
RHO_MIN, NMONTHS_MIN = 0.2, 60

MAP_CRS = QgsCoordinateReferenceSystem.fromProj(
    "+proj=lcc +lat_0=-13 +lon_0=-74.5 +lat_1=-9 +lat_2=-17 +datum=WGS84 +units=m +no_defs")
WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")

# --------------------------------------------------------------------------
# Layout geometry (mm), Springer text width 122 mm
# --------------------------------------------------------------------------
PAGE_W = 122.0
EXT_LON, EXT_LAT = (-80.5, -68.0), (-19.0, -7.5)
PAN_Y, PAN_W, GAP = 4.6, 57.0, 2.0
PAN_X = (PAGE_W - 2 * PAN_W - GAP, PAGE_W - PAN_W)  # left margin holds the lat labels
CIRCLE_MM = 1.9      # gauge circle diameter, panel (a)
MIN_SEP_MM = 2.45   # minimum centre spacing after displacement


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def truthy(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes", "t")


def make_mock(out_dir: Path = MOCK_DIR, seed: int = 8) -> tuple[Path, Path]:
    """Random but plausible mock tables (development only; never in 04-resultados)."""
    rng = np.random.default_rng(seed)
    st = read_csv(STATIONS)
    out_dir.mkdir(parents=True, exist_ok=True)
    fs, fp = out_dir / "spatial_gauge_skill.csv", out_dir / "spatial_ssi_pairs.csv"
    with open(fs, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["gauge_id", "gauge_name", "region", "lat", "lon", "skill_h7", "skill_lo",
                    "skill_hi", "sig", "csi_h7", "csi_pers_h7"])
        for r in st:
            s = float(np.clip(rng.normal(0.08, 0.14), -0.35, 0.45))
            hw = rng.uniform(0.04, 0.16)
            cp = rng.uniform(0.3, 0.6)
            w.writerow([r["gauge_id"], r["gauge_name"], r["region"], r["gauge_lat"], r["gauge_lon"],
                        f"{s:.4f}", f"{s - hw:.4f}", f"{s + hw:.4f}", s - hw > 0,
                        f"{cp + rng.uniform(-0.05, 0.12):.3f}", f"{cp:.3f}"])
    span = {}
    for r in st:
        y0, m0 = map(int, r["date_start"][:7].split("-"))
        y1, m1 = map(int, r["date_end"][:7].split("-"))
        a, b = y0 * 12 + m0, y1 * 12 + m1
        span[r["gauge_id"]] = (a, b, min(1.0, float(r["days_w_data_qc"]) / ((b - a + 1) * 30.4)))
    with open(fp, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["gauge_a", "gauge_b", "lat_a", "lon_a", "lat_b", "lon_b", "dist_km",
                    "n_months", "rho_ssi"])
        for i, ra in enumerate(st):
            for rb in st[i + 1:]:
                la, oa, lb, ob = (float(ra["gauge_lat"]), float(ra["gauge_lon"]),
                                  float(rb["gauge_lat"]), float(rb["gauge_lon"]))
                d = haversine(la, oa, lb, ob)
                sa, sb = span[ra["gauge_id"]], span[rb["gauge_id"]]
                nm = int(max(0, min(sa[1], sb[1]) - max(sa[0], sb[0]) + 1) * sa[2] * sb[2])
                rho = float(np.clip(0.92 * math.exp(-d / 450.0) + rng.normal(0.05, 0.12), -0.3, 0.98))
                w.writerow([ra["gauge_id"], rb["gauge_id"], la, oa, lb, ob, f"{d:.1f}", nm, f"{rho:.3f}"])
    return fs, fp


def haversine(la1, lo1, la2, lo2) -> float:
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def fnum(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def skill_color(v) -> str:
    """Hex colour of the clipped, reversed vik ramp (grey when missing)."""
    v = fnum(v)
    if math.isnan(v):
        return "#bdbdbd"
    t = (min(max(v, -SKILL_LIM), SKILL_LIM) + SKILL_LIM) / (2 * SKILL_LIM) * (len(VIK_R) - 1)
    i = min(int(t), len(VIK_R) - 2)
    f = t - i
    c0, c1 = QColor(VIK_R[i]), QColor(VIK_R[i + 1])
    rgb = [round(a + (b - a) * f) for a, b in ((c0.red(), c1.red()), (c0.green(), c1.green()),
                                                (c0.blue(), c1.blue()))]
    return "#%02x%02x%02x" % tuple(rgb)


def vik_ramp() -> QgsGradientColorRamp:
    n = len(VIK_R) - 1
    return QgsGradientColorRamp(QColor(VIK_R[0]), QColor(VIK_R[-1]), False,
                                [QgsGradientStop(i / n, QColor(c)) for i, c in enumerate(VIK_R[1:-1], 1)])


# --------------------------------------------------------------------------
# Styling helpers (as fig00)
# --------------------------------------------------------------------------
def tfmt(size, color=C_TEXT, bold=False, italic=False, buffer=0.0, buffer_color="#ffffff"):
    f = QFont(FONT)
    f.setBold(bold)
    f.setItalic(italic)
    t = QgsTextFormat()
    t.setFont(f)
    t.setSize(size)
    t.setSizeUnit(Qgis.RenderUnit.Points)
    t.setColor(QColor(color))
    if buffer > 0:
        b = QgsTextBufferSettings()
        b.setEnabled(True)
        b.setSize(buffer)
        b.setSizeUnit(Qgis.RenderUnit.Millimeters)
        b.setColor(QColor(buffer_color))
        b.setOpacity(0.85)
        t.setBuffer(b)
    return t


def vlayer(path, name, layer=None) -> QgsVectorLayer:
    path = Path(path)
    if path.is_dir():
        path, layer = path / f"{layer}.fgb", None
    uri = f"{path}|layername={layer}" if layer else str(path)
    lyr = QgsVectorLayer(uri, name, "ogr")
    if not lyr.isValid():
        raise RuntimeError(f"invalid layer {uri}")
    return lyr


def fill(color, outline="transparent", width=0.0, opacity=1.0) -> QgsFillSymbol:
    s = QgsFillSymbol.createSimple({"color": color, "outline_color": outline, "outline_width": str(width),
                                    "outline_width_unit": "MM", "style": "solid", "joinstyle": "round"})
    s.setOpacity(opacity)
    return s


def line(color, width, opacity=1.0) -> QgsLineSymbol:
    s = QgsLineSymbol.createSimple({"line_color": color, "line_width": str(width), "line_width_unit": "MM",
                                    "capstyle": "round", "joinstyle": "round"})
    s.setOpacity(opacity)
    return s


def marker(shape, color, size, outline="#1a1a1a", ow=0.25) -> QgsMarkerSymbol:
    return QgsMarkerSymbol.createSimple({
        "name": shape, "color": color, "size": str(size), "size_unit": "MM",
        "outline_color": outline, "outline_width": str(ow), "outline_width_unit": "MM"})


def mem_layer(geom: str, name: str, fields: list[tuple[str, QMetaType.Type]]) -> QgsVectorLayer:
    lyr = QgsVectorLayer(f"{geom}?crs=EPSG:4326", name, "memory")
    lyr.dataProvider().addAttributes([QgsField(n, t) for n, t in fields])
    lyr.updateFields()
    return lyr


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------
def extent_lcc(lon0, lon1, lat0, lat1, n=40) -> QgsRectangle:
    tr = QgsCoordinateTransform(WGS84, MAP_CRS, QgsProject.instance())
    xs, ys = [], []
    for t in np.linspace(0, 1, n):
        for lo, la in [(lon0 + t * (lon1 - lon0), lat0), (lon0 + t * (lon1 - lon0), lat1),
                       (lon0, lat0 + t * (lat1 - lat0)), (lon1, lat0 + t * (lat1 - lat0))]:
            p = tr.transform(QgsPointXY(lo, la))
            xs.append(p.x())
            ys.append(p.y())
    return QgsRectangle(min(xs), min(ys), max(xs), max(ys))


def displace(pts: dict[str, tuple[float, float]], m_per_mm: float,
             frame: QgsRectangle | None = None, margin_mm: float = 1.6) -> dict[str, tuple[float, float]]:
    """Repel symbols closer than MIN_SEP_MM on paper; weak spring back to the true position."""
    tr = QgsCoordinateTransform(WGS84, MAP_CRS, QgsProject.instance())
    ids = list(pts)
    xy0 = np.array([[tr.transform(QgsPointXY(lo, la)).x(), tr.transform(QgsPointXY(lo, la)).y()]
                    for la, lo in (pts[i] for i in ids)]) / m_per_mm
    xy = xy0.copy()
    for _ in range(600):
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                d = xy[j] - xy[i]
                r = math.hypot(*d)
                if r < MIN_SEP_MM:
                    u = d / r if r > 1e-6 else np.array([math.cos(i + j), math.sin(i + j)])
                    push = 0.5 * (MIN_SEP_MM - r) * u
                    xy[i] -= push
                    xy[j] += push
        xy += 0.03 * (xy0 - xy)
        if frame is not None:  # keep symbols inside the map frame
            xy[:, 0] = np.clip(xy[:, 0], frame.xMinimum() / m_per_mm + margin_mm,
                               frame.xMaximum() / m_per_mm - margin_mm)
            xy[:, 1] = np.clip(xy[:, 1], frame.yMinimum() / m_per_mm + margin_mm,
                               frame.yMaximum() / m_per_mm - margin_mm)
    tb = QgsCoordinateTransform(MAP_CRS, WGS84, QgsProject.instance())
    out = {}
    for k, (x, y) in zip(ids, xy * m_per_mm):
        p = tb.transform(QgsPointXY(x, y))
        out[k] = (p.y(), p.x())
    return out


# --------------------------------------------------------------------------
# Layers
# --------------------------------------------------------------------------
def make_layers(project: QgsProject, skill: list[dict], pairs: list[dict], disp: dict,
                km_per_mm: float) -> dict:
    L = {}
    ne = NE_CLIP
    L["ocean"] = vlayer(ne, "Ocean", "ocean")
    L["ocean"].setRenderer(QgsSingleSymbolRenderer(fill(C_WATER)))
    L["land"] = vlayer(ne, "Land", "countries")
    L["land"].setRenderer(QgsSingleSymbolRenderer(fill("#ffffff")))
    L["relief"] = QgsRasterLayer(str(RELIEF), "Relief", "gdal")
    if not L["relief"].isValid():
        raise RuntimeError("relief invalid")
    L["relief"].renderer().setOpacity(0.55)  # lighter than fig00: the data carry the colour
    L["veil"] = vlayer(ne, "Neighbours veil", "countries")
    L["veil"].setSubsetString("\"ADM0_A3\" <> 'PER'")
    L["veil"].setRenderer(QgsSingleSymbolRenderer(fill("#ffffff", opacity=0.45)))
    L["borders"] = vlayer(ne, "International boundary", "countries")
    L["borders"].setSubsetString("\"ADM0_A3\" <> 'PER'")
    L["borders"].setRenderer(QgsSingleSymbolRenderer(fill("transparent", "#8a8a8a", 0.2)))
    L["peru"] = vlayer(ne, "Peru boundary", "countries")
    L["peru"].setSubsetString("\"ADM0_A3\" = 'PER'")
    L["peru"].setRenderer(QgsSingleSymbolRenderer(fill("transparent", "#3a3a3a", 0.4)))
    L["lakes"] = vlayer(ne, "Lakes", "lakes")
    L["lakes"].setRenderer(QgsSingleSymbolRenderer(fill(C_WATER, C_WATER_LINE, 0.15)))

    S = {r["gauge_id"]: r for r in skill}

    # ---- (a) catchments by skill (largest drawn first)
    src = vlayer(CATCH, "src", "catchments")
    cat = mem_layer("MultiPolygon", "Catchments (skill)", [
        ("gauge_id", QMetaType.Type.QString), ("area", QMetaType.Type.Double), ("col", QMetaType.Type.QString)])
    feats = []
    for f in src.getFeatures():
        gid = f["gauge_id"]
        if gid not in S:
            continue
        nf = QgsFeature(cat.fields())
        nf.setGeometry(f.geometry().simplify(0.003))  # ~0.06 mm on paper; keeps the PDF small
        nf.setAttributes([gid, float(f["basin_area"]), skill_color(S[gid]["skill_h7"])])
        feats.append(nf)
    cat.dataProvider().addFeatures(feats)
    sym = fill("#cccccc", "#4a4a4a", 0.12, opacity=0.9)
    sym.symbolLayer(0).setDataDefinedProperty(QgsSymbolLayer.Property.FillColor, QgsProperty.fromField("col"))
    r = QgsSingleSymbolRenderer(sym)
    r.setOrderBy(QgsFeatureRequest.OrderBy([QgsFeatureRequest.OrderByClause("area", False)]))
    r.setOrderByEnabled(True)
    cat.setRenderer(r)
    L["catch"] = cat

    # ---- leaders from true to displayed gauge position
    lead = mem_layer("LineString", "Leaders", [("gauge_id", QMetaType.Type.QString)])
    dots = mem_layer("Point", "True location", [("gauge_id", QMetaType.Type.QString)])
    lf, df = [], []
    for gid, r_ in S.items():
        la, lo = float(r_["lat"]), float(r_["lon"])
        dla, dlo = disp[gid]
        if haversine(la, lo, dla, dlo) / km_per_mm > 0.5 * CIRCLE_MM + 0.8:  # leader clearly visible
            f = QgsFeature(lead.fields())
            f.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(lo, la), QgsPointXY(dlo, dla)]))
            f.setAttributes([gid])
            lf.append(f)
            f = QgsFeature(dots.fields())
            f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lo, la)))
            f.setAttributes([gid])
            df.append(f)
    lead.dataProvider().addFeatures(lf)
    L["_n_leaders"] = len(lf)
    dots.dataProvider().addFeatures(df)
    lead.setRenderer(QgsSingleSymbolRenderer(line("#3a3a3a", 0.13)))
    dots.setRenderer(QgsSingleSymbolRenderer(marker("circle", "#3a3a3a", 0.45, "transparent", 0)))
    L["lead"], L["dots"] = lead, dots

    # ---- (a) gauge circles coloured by skill, outline by significance
    gs = mem_layer("Point", "Gauges (skill)", [
        ("gauge_id", QMetaType.Type.QString), ("col", QMetaType.Type.QString),
        ("sig", QMetaType.Type.QString), ("lbl", QMetaType.Type.QString)])
    feats = []
    for gid, r_ in S.items():
        la, lo = disp[gid]
        f = QgsFeature(gs.fields())
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lo, la)))
        f.setAttributes([gid, skill_color(r_["skill_h7"]), "sig" if truthy(r_["sig"]) else "ns",
                         "Puente Isla\nCabanillas" if gid == FOCUS_ID else None])
        feats.append(f)
    gs.dataProvider().addFeatures(feats)
    cats = []
    for key, oc, ow, lab in [("ns", "#8c8c8c", 0.18, "95% CI includes 0"),
                             ("sig", "#000000", 0.5, "95% CI excludes 0")]:
        s = marker("circle", "#ffffff", CIRCLE_MM, oc, ow)
        s.symbolLayer(0).setDataDefinedProperty(QgsSymbolLayer.Property.FillColor, QgsProperty.fromField("col"))
        cats.append(QgsRendererCategory(key, s, lab))
    gr = QgsCategorizedSymbolRenderer("sig", cats)
    gs.setRenderer(gr)
    st = QgsPalLayerSettings()
    st.fieldName = "lbl"
    st.setFormat(tfmt(5.6, C_TEXT, bold=True, buffer=0.5))
    st.placement = Qgis.LabelPlacement.OverPoint
    st.multilineAlignment = Qgis.LabelMultiLineAlignment.Center
    dd = st.dataDefinedProperties()
    dd.setProperty(QgsPalLayerSettings.Property.OffsetQuad, QgsProperty.fromValue(1))  # above
    st.setDataDefinedProperties(dd)
    st.xOffset, st.yOffset = 0.0, -1.6
    st.offsetUnits = Qgis.RenderUnit.Millimeters
    pls = st.placementSettings()
    pls.setOverlapHandling(Qgis.LabelOverlapHandling.AllowOverlapIfRequired)
    st.setPlacementSettings(pls)
    c = QgsSimpleLineCallout()
    c.setEnabled(True)
    c.setLineSymbol(line("#444444", 0.15))
    c.setMinimumLength(0.6)
    c.setMinimumLengthUnit(Qgis.RenderUnit.Millimeters)
    c.setOffsetFromAnchor(1.3)
    c.setOffsetFromAnchorUnit(Qgis.RenderUnit.Millimeters)
    st.setCallout(c)
    gs.setLabeling(QgsVectorLayerSimpleLabeling(st))
    gs.setLabelsEnabled(True)
    L["gskill"] = gs

    # ---- (b) synchrony lines (weak first, strongest on top)
    pl = mem_layer("LineString", "SSI-30 synchrony", [
        ("gauge_a", QMetaType.Type.QString), ("gauge_b", QMetaType.Type.QString),
        ("rho", QMetaType.Type.Double), ("n_months", QMetaType.Type.Int)])
    feats = []
    for p in pairs:
        a, b = p["gauge_a"], p["gauge_b"]
        try:
            rho, nm = float(p["rho_ssi"]), int(float(p["n_months"]))
        except ValueError:
            continue
        if not (rho >= RHO_MIN and nm >= NMONTHS_MIN and a in disp and b in disp):
            continue
        f = QgsFeature(pl.fields())
        f.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(disp[a][1], disp[a][0]),
                                                  QgsPointXY(disp[b][1], disp[b][0])]))
        f.setAttributes([a, b, rho, nm])
        feats.append(f)
    pl.dataProvider().addFeatures(feats)
    ranges = []
    for lo, hi, col, w in RHO_CLASSES:
        lab = f"{lo:.1f}–{min(hi, 1.0):.1f}"
        ranges.append(QgsRendererRange(lo, hi, line(col, w, opacity=0.6 if lo < 0.4 else 0.9), lab))
    rr = QgsGraduatedSymbolRenderer("rho", ranges)
    rr.setOrderBy(QgsFeatureRequest.OrderBy([QgsFeatureRequest.OrderByClause("rho", True)]))
    rr.setOrderByEnabled(True)
    pl.setRenderer(rr)
    L["pairs"] = pl
    L["_n_pairs"] = len(feats)

    # ---- (b) gauges by region (fig00 symbology, smaller)
    gr_ = mem_layer("Point", "Gauges (region)", [("gauge_id", QMetaType.Type.QString),
                                                 ("cls", QMetaType.Type.QString), ("z", QMetaType.Type.Int)])
    feats = []
    for gid, r_ in S.items():
        la, lo = disp[gid]
        cls = ("focus" if gid == FOCUS_ID else {"Cordillera Blanca": "cb", "Altiplano": "alt"}
               .get(r_["region"], "ws"))
        f = QgsFeature(gr_.fields())
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lo, la)))
        f.setAttributes([gid, cls, 2 if cls == "focus" else 1])
        feats.append(f)
    gr_.dataProvider().addFeatures(feats)
    rc = QgsCategorizedSymbolRenderer("cls", [
        QgsRendererCategory("cb", marker("circle", C_CB, 1.75, ow=0.2), "Cordillera Blanca"),
        QgsRendererCategory("ws", marker("square", C_WS, 1.6, ow=0.2), "Western / southern Andes"),
        QgsRendererCategory("alt", marker("triangle", C_ALT, 2.05, ow=0.2), "Altiplano (Chile)"),
        QgsRendererCategory("focus", marker("star", C_FOCUS, 3.2, ow=0.25), "Puente Isla Cabanillas"),
    ])
    rc.setOrderBy(QgsFeatureRequest.OrderBy([QgsFeatureRequest.OrderByClause("z", True)]))
    rc.setOrderByEnabled(True)
    gr_.setRenderer(rc)
    L["greg"] = gr_

    # Legend-only layer for leaders
    L["lg_lead"] = mem_layer("LineString", "True location", [])
    lg = line("#3a3a3a", 0.13)
    ml = QgsMarkerLineSymbolLayer()
    ml.setPlacements(Qgis.MarkerLinePlacement.FirstVertex)
    ml.setSubSymbol(marker("circle", "#3a3a3a", 0.5, "transparent", 0))
    lg.appendSymbolLayer(ml)
    L["lg_lead"].setRenderer(QgsSingleSymbolRenderer(lg))

    for k, v in L.items():
        if k.startswith("_"):
            continue
        project.addMapLayer(v, False)
        project.layerTreeRoot().addLayer(v)
    return L


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------
def add_map(layout, mid, x, y, w, h, extent, layers):
    m = QgsLayoutItemMap(layout)
    m.setId(mid)
    m.attemptMove(QgsLayoutPoint(x, y, Qgis.LayoutUnit.Millimeters))
    m.attemptResize(QgsLayoutSize(w, h, Qgis.LayoutUnit.Millimeters))
    m.setCrs(MAP_CRS)
    m.setLayers(layers)
    m.setKeepLayerSet(True)
    m.setExtent(extent)
    m.setFrameEnabled(True)
    m.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, Qgis.LayoutUnit.Millimeters))
    m.setFrameStrokeColor(QColor("#333333"))
    m.setBackgroundColor(QColor(C_WATER))
    layout.addLayoutItem(m)
    return m


def add_label(layout, text, x, y, w, h, fmt, halign=Qt.AlignmentFlag.AlignLeft,
              valign=Qt.AlignmentFlag.AlignTop, bg=None):
    lab = QgsLayoutItemLabel(layout)
    lab.setText(text)
    lab.setTextFormat(fmt)
    lab.setHAlign(halign)
    lab.setVAlign(valign)
    lab.attemptMove(QgsLayoutPoint(x, y, Qgis.LayoutUnit.Millimeters))
    lab.attemptResize(QgsLayoutSize(w, h, Qgis.LayoutUnit.Millimeters))
    if bg is not None:
        lab.setBackgroundEnabled(True)
        lab.setBackgroundColor(QColor(bg))
    layout.addLayoutItem(lab)
    return lab


def style_grid(m, interval, sides, size=5.2, skip=(-68,)):
    grid = QgsLayoutItemMapGrid("graticule", m)
    grid.setCrs(WGS84)
    grid.setIntervalX(interval)
    grid.setIntervalY(interval)
    grid.setStyle(QgsLayoutItemMapGrid.GridStyle.Solid)
    grid.setLineSymbol(line("#ffffff", 0.12, opacity=0.7))
    grid.setAnnotationEnabled(True)
    grid.setAnnotationFormat(QgsLayoutItemMapGrid.AnnotationFormat.CustomFormat)
    grid.setAnnotationExpression(
        f"CASE WHEN @grid_number IN ({','.join(str(v) for v in skip) or 'NULL'}) THEN '' "
        "WHEN @grid_axis = 'x' THEN to_string(abs(@grid_number)) || '°W' "
        "ELSE to_string(abs(@grid_number)) || '°S' END")
    grid.setAnnotationTextFormat(tfmt(size, "#333333"))
    grid.setAnnotationFrameDistance(0.7)
    for side, pos in [(QgsLayoutItemMapGrid.BorderSide.Left, "left"),
                      (QgsLayoutItemMapGrid.BorderSide.Right, "right"),
                      (QgsLayoutItemMapGrid.BorderSide.Top, "top"),
                      (QgsLayoutItemMapGrid.BorderSide.Bottom, "bottom")]:
        if pos in sides:
            grid.setAnnotationDisplay(QgsLayoutItemMapGrid.DisplayMode.ShowAll, side)
            grid.setAnnotationPosition(QgsLayoutItemMapGrid.AnnotationPosition.OutsideMapFrame, side)
            grid.setAnnotationDirection(
                QgsLayoutItemMapGrid.AnnotationDirection.Vertical
                if pos in ("left", "right") else QgsLayoutItemMapGrid.AnnotationDirection.Horizontal, side)
        else:
            grid.setAnnotationDisplay(QgsLayoutItemMapGrid.DisplayMode.HideAll, side)
    grid.setFrameStyle(QgsLayoutItemMapGrid.FrameStyle.InteriorTicks)
    grid.setFrameWidth(1.0)
    grid.setFramePenSize(0.25)
    grid.setFramePenColor(QColor("#333333"))
    m.grids().addGrid(grid)
    return grid


def colour_bar(layout, x, y, w=36.0, h=2.0):
    gl = QgsGradientFillSymbolLayer()
    gl.setGradientColorType(Qgis.GradientColorSource.ColorRamp)
    ramp = vik_ramp()  # keep Python refs alive until the symbol owns clones
    gl.setColorRamp(ramp)
    gl.setGradientType(Qgis.GradientType.Linear)
    gl.setCoordinateMode(Qgis.SymbolCoordinateReference.Feature)
    gl.setReferencePoint1(QPointF(0, 0.5))
    gl.setReferencePoint2(QPointF(1, 0.5))
    sym = QgsFillSymbol([gl])
    border = fill("transparent", "#555555", 0.15)
    sym.appendSymbolLayer(border.symbolLayer(0).clone())
    sh = QgsLayoutItemShape(layout)
    sh.setShapeType(QgsLayoutItemShape.Shape.Rectangle)
    sh.setSymbol(sym)
    sh.attemptMove(QgsLayoutPoint(x, y + 3.4, Qgis.LayoutUnit.Millimeters))
    sh.attemptResize(QgsLayoutSize(w, h, Qgis.LayoutUnit.Millimeters))
    layout.addLayoutItem(sh)
    add_label(layout, "RMSE skill vs persistence", x - 0.2, y, w + 4, 3.2,
              tfmt(6.0, C_TEXT, bold=True))
    for v in (-0.3, -0.15, 0.0, 0.15, 0.3):
        xx = x + w * (v + SKILL_LIM) / (2 * SKILL_LIM)
        t = f"{v:+.2f}".replace("+0.00", "0").replace("-", "−")
        if v == -0.3:
            t = "≤ −0.30"
        elif v == 0.3:
            t = "≥ +0.30"
        add_label(layout, t, xx - 6, y + 3.4 + h + 0.3, 12, 2.6, tfmt(5.0, "#333333"),
                  halign=Qt.AlignmentFlag.AlignHCenter)
        tick = QgsLayoutItemShape(layout)
        tick.setShapeType(QgsLayoutItemShape.Shape.Rectangle)
        tick.setSymbol(fill("#555555"))
        tick.attemptMove(QgsLayoutPoint(xx - 0.05, y + 3.4 + h, Qgis.LayoutUnit.Millimeters))
        tick.attemptResize(QgsLayoutSize(0.1, 0.5, Qgis.LayoutUnit.Millimeters))
        layout.addLayoutItem(tick)
    add_label(layout, "← worse than persistence", x, y + 3.4 + h + 2.8, w * 0.75, 2.6,
              tfmt(4.8, "#666666", italic=True))
    add_label(layout, "better →", x + w * 0.6, y + 3.4 + h + 2.8, w * 0.4, 2.6,
              tfmt(4.8, "#666666", italic=True), halign=Qt.AlignmentFlag.AlignRight)


def make_legend(layout, mapitem, items, x, y, title="", cols=1, sym_w=3.6, sym_h=2.2):
    leg = QgsLayoutItemLegend(layout)
    leg.setTitle(title)
    leg.setLinkedMap(mapitem)
    leg.setAutoUpdateModel(False)
    root = leg.model().rootGroup()
    root.removeAllChildren()
    from qgis.core import QgsLegendRenderer
    for lyr, name in items:
        node = root.addLayer(lyr)
        if name is not None:
            node.setUseLayerName(False)
            node.setName(name)
        elif lyr.renderer().type() != "singleSymbol":
            QgsLegendRenderer.setNodeLegendStyle(node, QgsLegendStyle.Style.Hidden)
    leg.setColumnCount(cols)
    leg.setSplitLayer(True)
    leg.setEqualColumnWidth(False)
    leg.setSymbolWidth(sym_w)
    leg.setSymbolHeight(sym_h)
    leg.setColumnSpace(2.5)
    leg.rstyle(QgsLegendStyle.Style.Title).setTextFormat(tfmt(6.0, C_TEXT, bold=True))
    leg.rstyle(QgsLegendStyle.Style.Title).setMargin(QgsLegendStyle.Side.Bottom, 0.6)
    leg.rstyle(QgsLegendStyle.Style.SymbolLabel).setTextFormat(tfmt(5.6, C_TEXT))
    leg.rstyle(QgsLegendStyle.Style.Subgroup).setTextFormat(tfmt(6.0, C_TEXT, bold=True))
    leg.rstyle(QgsLegendStyle.Style.Group).setTextFormat(tfmt(6.0, C_TEXT, bold=True))
    leg.rstyle(QgsLegendStyle.Style.Symbol).setMargin(QgsLegendStyle.Side.Top, 0.55)
    leg.rstyle(QgsLegendStyle.Style.Subgroup).setMargin(QgsLegendStyle.Side.Bottom, 0.2)
    leg.setBoxSpace(0.0)
    leg.setBackgroundEnabled(False)
    leg.setFrameEnabled(False)
    leg.attemptMove(QgsLayoutPoint(x, y, Qgis.LayoutUnit.Millimeters))
    layout.addLayoutItem(leg)
    leg.adjustBoxSize()
    leg.refresh()
    return leg


def build_layout(project, L, extent, pan_h, page_h):
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName("fig08")
    layout.pageCollection().page(0).setPageSize(QgsLayoutSize(PAGE_W, page_h, Qgis.LayoutUnit.Millimeters))

    under = [L["lakes"], L["peru"], L["borders"], L["veil"], L["ocean"], L["relief"], L["land"]]
    lay_a = [L["gskill"], L["dots"], L["lead"], L["catch"]] + under
    lay_b = [L["greg"], L["pairs"], L["dots"], L["lead"]] + under
    ma = add_map(layout, "a", PAN_X[0], PAN_Y, PAN_W, pan_h, extent, lay_a)
    mb = add_map(layout, "b", PAN_X[1], PAN_Y, PAN_W, pan_h, extent, lay_b)
    style_grid(ma, 4.0, ("left", "bottom"))
    style_grid(mb, 4.0, ("bottom",))

    for m, x, txt in [(ma, PAN_X[0], "(a) Forecast skill at 7-day lead"),
                      (mb, PAN_X[1], "(b) Hydrological-drought synchrony")]:
        add_label(layout, txt, x - 0.2, 0.4, PAN_W, 3.8, tfmt(6.6, C_TEXT, bold=True))

    # Scale bar in the Pacific of panel (a)
    sb = QgsLayoutItemScaleBar(layout)
    sb.setStyle("Single Box")
    sb.setLinkedMap(ma)
    sb.setUnits(Qgis.DistanceUnit.Kilometers)
    sb.setUnitLabel("km")
    sb.setUnitsPerSegment(100)
    sb.setNumberOfSegments(2)
    sb.setNumberOfSegmentsLeft(0)
    sb.setHeight(0.9)
    sb.setLineWidth(0.2)
    sb.setTextFormat(tfmt(5.0, "#333333"))
    sb.setLabelBarSpace(0.6)
    sb.setBoxContentSpace(0.0)
    sb.setSegmentSizeMode(Qgis.ScaleBarSegmentSizeMode.Fixed)
    sb.attemptMove(QgsLayoutPoint(PAN_X[0] + 2.5, PAN_Y + pan_h - 6.0, Qgis.LayoutUnit.Millimeters))
    layout.addLayoutItem(sb)
    sb.update()

    # rho legend inside panel (b), in the empty Pacific (south-west corner)
    rx, ry = PAN_X[1] + 2.0, PAN_Y + pan_h - 17.5
    add_label(layout, "Spearman ρ,\nmonthly SSI-30", rx, ry, 22, 6.0, tfmt(5.6, C_TEXT, bold=True))
    make_legend(layout, mb, [(L["pairs"], None)], rx, ry + 6.0, cols=1, sym_w=5.0, sym_h=1.6)

    # Legends below the panels
    ly = PAN_Y + pan_h + 4.4
    cb_w = 32.0
    colour_bar(layout, PAN_X[0] + 0.5, ly, w=cb_w)
    # (leaders are short and mostly hidden under the circles: explained in the credit line, not legended)
    make_legend(layout, ma, [(L["gskill"], None)],
                PAN_X[0] + cb_w + 4.0, ly + 0.4, cols=1, sym_w=2.6)
    add_label(layout, "Gauges",
              PAN_X[1] + 0.3, ly, PAN_W + 2, 3.2, tfmt(6.0, C_TEXT, bold=True))
    make_legend(layout, mb, [(L["greg"], None)], PAN_X[1] + 0.3, ly + 3.0, cols=2, sym_w=2.6)

    add_label(layout,
              "Data: catchments and gauges from Andean-GC (CC BY 4.0); relief from Copernicus GLO-90 DEM; "
              "boundaries and lakes from Natural Earth. Lambert conformal conic projection. Clustered gauge "
              "symbols slightly displaced to avoid overlap. (b) shows pairs with ≥ 60 overlapping "
              "months and ρ ≥ 0.2.",
              PAN_X[0], page_h - 5.6, PAGE_W - PAN_X[0], 5.4, tfmt(4.6, "#555555"))
    return layout


def parse_args(argv):
    a = {"mock": "--mock" in argv, "no_pdf": "--no-pdf" in argv, "skill": SKILL_CSV, "pairs": PAIRS_CSV,
         "out": None}
    for k in ("skill", "pairs", "out"):
        if f"--{k}" in argv:
            a[k] = Path(argv[argv.index(f"--{k}") + 1])
    return a


def main() -> int:
    args = parse_args(sys.argv[1:])
    if args["mock"]:
        args["skill"], args["pairs"] = make_mock()
        print("mock tables:", args["skill"], args["pairs"])
    out = args["out"] or (OUT.with_name(OUT.name + "_MOCK") if args["mock"] else OUT)
    for p in (args["skill"], args["pairs"], CATCH, RELIEF, NE_CLIP / "countries.fgb"):
        if not Path(p).is_file():
            print(f"missing {p} (run make_fig00_qgis.py for relief/NE clips; or use --mock)", file=sys.stderr)
            return 1
    skill, pairs = read_csv(args["skill"]), read_csv(args["pairs"])

    QgsApplication.setPrefixPath(str(QGIS_APP), True)
    app = QgsApplication([], False)
    app.initQgis()
    project = QgsProject.instance()
    project.setCrs(MAP_CRS)

    ext = extent_lcc(EXT_LON[0], EXT_LON[1], EXT_LAT[0], EXT_LAT[1])
    pan_h = round(PAN_W * ext.height() / ext.width(), 2)
    m_per_mm = ext.width() / PAN_W
    page_h = PAN_Y + pan_h + 4.4 + 11.6 + 6.0
    disp = displace({r["gauge_id"]: (float(r["lat"]), float(r["lon"])) for r in skill}, m_per_mm, ext)

    L = make_layers(project, skill, pairs, disp, m_per_mm / 1000.0)
    print(f"gauges: {len(skill)}  leaders: {L['_n_leaders']}  pairs drawn: {L['_n_pairs']} / {len(pairs)}  page: {PAGE_W} x {page_h:.1f} mm")
    layout = build_layout(project, L, ext, pan_h, page_h)
    project.layoutManager().addLayout(layout)
    layout.refresh()

    out.parent.mkdir(parents=True, exist_ok=True)
    ex = QgsLayoutExporter(layout)
    s = QgsLayoutExporter.ImageExportSettings()
    s.dpi = int(os.environ.get("FIG_DPI", "600"))
    print("png:", ex.exportToImage(str(out) + ".png", s))
    if not args["no_pdf"]:
        p = QgsLayoutExporter.PdfExportSettings()
        p.dpi = 300
        p.rasterizeWholeImage = False
        p.forceVectorOutput = False
        p.textRenderFormat = Qgis.TextRenderFormat.AlwaysText
        p.exportMetadata = False
        p.simplifyGeometries = True
        print("pdf:", ex.exportToPdf(str(out) + ".pdf", p))
    app.exitQgis()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
