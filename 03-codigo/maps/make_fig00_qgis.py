#!/usr/bin/env python3
"""Figure 1 (fig00) -- benchmark station map rendered headless with PyQGIS.

Renders ``04-resultados/figuras/fig00_station_map.{png,pdf}`` with QGIS 4.2.2
(no GUI, no web tiles). Everything is drawn from local data:

* gauges ............ 02-datos/crudos/stations/benchmark_stations.csv (19 gauges)
* catchments ........ 02-datos/crudos/andean-gc/catchments_benchmark19.gpkg
                      (filtered from Andean-GC ``AndeanGC_shape.gpkg``, Zenodo 18035801)
* relief ............ 02-datos/crudos/dem/copdem90_andes_0p0075deg.tif
                      (Copernicus GLO-90 COGs, mosaicked + averaged to 0.0075 deg ~ 830 m);
                      insets use copdem90_inset_{cb,cl}.tif (0.0025/0.0015 deg), fetched
                      on first run from the public AWS COGs (network needed once)
* vectors ........... 02-datos/crudos/naturalearth/ne_*  (Natural Earth 10m/50m)

How to run (macOS, QGIS 4.2.2 app bundle; from the repository root)::

    QGIS=/Applications/QGIS-final-4_2_2.app/Contents
    PYTHONHOME=$QGIS/Frameworks $QGIS/MacOS/python3.12 03-codigo/maps/make_fig00_qgis.py

``PYTHONHOME`` must point at ``Contents/Frameworks`` (the bundled stdlib lives
in ``Contents/Frameworks/lib/python3.12``). The script itself sets
``QT_QPA_PLATFORM=offscreen``, ``PROJ_LIB``/``PROJ_DATA``, ``GDAL_DATA`` and --
the key fix for the missing ``wms``/``delimitedtext`` providers -- the QGIS
prefix to the *.app root*: QGIS on macOS resolves plugins as
``<prefix>/Contents/PlugIns/qgis``. Override the bundle location with the
``QGIS_APP`` environment variable. If launched with a non-QGIS interpreter the
script re-executes itself with the bundled one.

Derived inputs that are missing (relief RGB, Natural Earth clip) are rebuilt
automatically (``--rebuild`` forces it); the DEM mosaic and Natural Earth
downloads are documented in ``fetch_inputs_help``. Options: ``--no-pdf``;
``FIG_DPI=200`` env var for a quick low-resolution PNG preview.

Outputs: PNG at 600 dpi; PDF with vectors/text kept as vectors and the relief
rasterised at 300 dpi (JPEG inside the PDF, ~2-3 MB); a ``.qgz`` project next
to this script for opening the same layout in the QGIS GUI.
"""
from __future__ import annotations

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
from osgeo import gdal, ogr  # noqa: E402
from qgis.core import (  # noqa: E402
    Qgis,
    QgsApplication,
    QgsCategorizedSymbolRenderer,
    QgsColorRampShader,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsFillSymbol,
    QgsGeometry,
    QgsLayerTreeGroup,
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemMap,
    QgsLayoutItemMapGrid,
    QgsLayoutItemMapOverview,
    QgsLayoutItemPicture,
    QgsLayoutItemPolyline,
    QgsLayoutItemScaleBar,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsLegendStyle,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsPointXY,
    QgsPrintLayout,
    QgsProject,
    QgsProperty,
    QgsRasterLayer,
    QgsRasterShader,
    QgsRectangle,
    QgsRendererCategory,
    QgsSimpleLineCallout,
    QgsSingleBandPseudoColorRenderer,
    QgsSingleSymbolRenderer,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
    QgsFeatureRequest,
)
from qgis.PyQt.QtCore import QMetaType, QPointF, Qt  # noqa: E402
from qgis.PyQt.QtGui import QColor, QFont, QPolygonF  # noqa: E402

gdal.UseExceptions()

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
STATIONS = ROOT / "02-datos/crudos/stations/benchmark_stations.csv"
CATCH = ROOT / "02-datos/crudos/andean-gc/catchments_benchmark19.gpkg"
DEM = ROOT / "02-datos/crudos/dem/copdem90_andes_0p0075deg.tif"
RELIEF = ROOT / "02-datos/crudos/dem/relief_rgb_0p0075deg.tif"
NE_DIR = ROOT / "02-datos/crudos/naturalearth"
NE_CLIP = NE_DIR / "clip"  # one small FlatGeobuf per layer (tracked)
OUT = ROOT / "04-resultados/figuras/fig00_station_map"
QGZ = ROOT / "03-codigo/maps/fig00_station_map.qgz"
# Finer relief for the zoom insets (GLO-90 read directly from the public COGs, cached locally)
FINE = {
    "cb": ((-78.8, -76.6, -8.0, -11.1), 0.0025, range(9, 12), range(77, 80)),
    "cl": ((-69.9, -68.5, -17.5, -19.0), 0.0015, range(18, 20), range(69, 71)),
}
SVG_NORTH = QC / "Resources/qgis/svg/arrows/NorthArrow_02.svg"


def fetch_inputs_help() -> str:
    return """Missing inputs. Rebuild them (repo root) with:
  # Andean-GC catchments (then filter to the 19 gauge_ids -> catchments_benchmark19.gpkg)
  curl -L -o 02-datos/crudos/andean-gc/AndeanGC_shape.gpkg \\
       "https://zenodo.org/records/18035801/files/AndeanGC_shape.gpkg?download=1"
  # Copernicus GLO-90 tiles S04..S20 x W067..W081, each gdalwarp'ed from
  #  /vsicurl/https://copernicus-dem-90m.s3.amazonaws.com/<tile>/<tile>.tif
  # to -tr 0.0075 0.0075 -r average, then gdalbuildvrt + gdalwarp
  #  -te -82.5 -20.5 -66.5 -6.0 -> 02-datos/crudos/dem/copdem90_andes_0p0075deg.tif
  # Natural Earth: https://naciscdn.org/naturalearth/{10m,50m}/{cultural,physical}/<name>.zip
  #  unzipped into 02-datos/crudos/naturalearth/<name>/"""


# --------------------------------------------------------------------------
# Design constants (Okabe-Ito, colour-blind safe)
# --------------------------------------------------------------------------
FONT = "Arial"
C_CB = "#0072B2"      # Cordillera Blanca (historical)       blue
C_WS = "#E69F00"      # Western/Southern Andes                orange
C_ALT = "#CC79A7"     # Altiplano, DGA Chile                  reddish purple
C_FOCUS = "#D55E00"   # Puente Isla Cabanillas (focus)        vermilion
C_WATER = "#C9DDEB"
C_WATER_LINE = "#5B8DB8"
C_TEXT = "#222222"
REGION_COLOR = {"Cordillera Blanca": C_CB, "Western/Southern Andes": C_WS, "Altiplano": C_ALT}

MAP_CRS = QgsCoordinateReferenceSystem.fromProj(
    "+proj=lcc +lat_0=-13 +lon_0=-74.5 +lat_1=-9 +lat_2=-17 +datum=WGS84 +units=m +no_defs"
)
WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")

# Short labels. Cluster: 'cb' = Cordillera Blanca inset, 'cl' = Chilean Altiplano inset.
SHORT = {
    "P00000031": "La Capilla", "P00000008": "Condorcerro", "P00000041": "Salamanca",
    "P00000047": "Km 105", "P00000027": "Cahua", "P00000022": "Recreta",
    "P00000021": "Quitaracsa", "P00000005": "Colcas", "P00000003": "Chancos",
    "P00000016": "Pachacoto", "P00000055": "Puente Isla\nCabanillas", "P00000011": "Llanganuco",
    "P00000040": "Ocoña",
    "X01020002": "Desaguadero\n(Cotacotani)", "X01001002": "Caquena\n(Vertedero)",
    "X01020003": "Lauca\n(El Lago)", "X01021001": "Lauca\n(Japu)",
    "X01001003": "Colpacagua", "X01001001": "Caquena\n(Nacimiento)",
}
# Label placement per map: "quadrant;dx;dy" (mm on paper). Quadrants:
# 0 above-left 1 above 2 above-right 3 left 4 over 5 right 6 below-left 7 below 8 below-right.
# Empty string = no label in that map.
LBL = {
    #            main              cb (inset b)        cl (inset c)
    "P00000031": ("5;0.4;0",         "",                 ""),
    "P00000008": ("",                "5;0.4;0",          ""),
    "P00000041": ("1;0;-0.4",        "",                 ""),
    "P00000047": ("5;0.4;0",         "",                 ""),
    "P00000027": ("",                "3;-0.4;0",         ""),
    "P00000022": ("",                "5;0.4;0",          ""),
    "P00000021": ("",                "5;0.4;0",          ""),
    "P00000005": ("",                "3;-0.4;0",         ""),
    "P00000003": ("",                "5;0.4;0",          ""),
    "P00000016": ("",                "3;-0.4;0",         ""),
    "P00000055": ("0;-0.6;-0.3",     "",                 ""),
    "P00000011": ("",                "5;0.4;0",          ""),
    "P00000040": ("5;0.4;0",         "",                 ""),
    "X01001002": ("",                "",                 "3;-1.3;-0.6"),
    "X01001003": ("",                "",                 "5;1.3;-0.5"),
    "X01001001": ("",                "",                 "5;1.2;0.4"),
    "X01020002": ("",                "",                 "5;1.0;0.6"),
    "X01020003": ("",                "",                 "3;-0.6;0"),
    "X01021001": ("",                "",                 "3;-0.6;0"),
}
CLUSTER_CB = {"P00000022", "P00000021", "P00000005", "P00000003", "P00000016", "P00000011"}

# --------------------------------------------------------------------------
# Layout geometry (mm). Springer LNCS text width = 122 mm.
# --------------------------------------------------------------------------
PAGE_W, PAGE_H = 122.0, 138.0
MAIN_X, MAIN_Y, MAIN_W, MAIN_H = 8.0, 2.0, 112.0, 104.0
MAIN_LON, MAIN_LAT = (-81.6, -67.6), (-19.55, -7.0)
PAGE_H = 141.0
CB_EXT = (-78.42, -76.95, -8.36, -10.72)       # lon_min, lon_max, lat_top, lat_bottom
CL_EXT = (-69.50, -68.92, -17.83, -18.66)


# --------------------------------------------------------------------------
# Data preparation
# --------------------------------------------------------------------------
def fetch_fine_dem(key: str) -> Path:
    (lon0, lon1, lat0, lat1), res, lats, lons = FINE[key]
    out = DEM.parent / f"copdem90_inset_{key}.tif"
    if out.is_file():
        return out
    srcs = []
    for la in lats:
        for lo in lons:
            n = f"Copernicus_DSM_COG_30_S{la:02d}_00_W{lo:03d}_00_DEM"
            srcs.append(f"/vsicurl/https://copernicus-dem-90m.s3.amazonaws.com/{n}/{n}.tif")
    gdal.SetConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    vrt = gdal.BuildVRT("/vsimem/fine.vrt", srcs)
    gdal.Warp(str(out), vrt, outputBounds=(lon0, lat1, lon1, lat0), xRes=res, yRes=res,
              resampleAlg="average", dstNodata=-32768, outputType=gdal.GDT_Int16,
              creationOptions=["COMPRESS=DEFLATE", "PREDICTOR=2"])
    vrt = None
    return out


def build_relief(dem: Path = DEM, relief: Path = RELIEF) -> None:
    """Hypsometric tint x hillshade -> RGBA GeoTIFF (EPSG:4326)."""
    ds = gdal.Open(str(dem))
    z = ds.GetRasterBand(1).ReadAsArray().astype("float32")
    nod = ds.GetRasterBand(1).GetNoDataValue()
    gt = ds.GetGeoTransform()
    valid = z != nod
    z[~valid] = 0.0
    z[z < 0] = 0.0
    ny, nx = z.shape
    lat = gt[3] + gt[5] * (np.arange(ny) + 0.5)
    dy = abs(gt[5]) * 111320.0
    dx = gt[1] * 111320.0 * np.cos(np.radians(lat))[:, None]
    gy, gx = np.gradient(z)
    sx, sy = gx / dx, -gy / dy  # east / north slopes
    exag = 1.6

    def shade(az, alt):
        az, alt = np.radians(az), np.radians(alt)
        slope = np.arctan(exag * np.hypot(sx, sy))
        aspect = np.arctan2(-sx, -sy)  # direction of steepest descent, from north
        return np.clip(np.sin(alt) * np.cos(slope)
                       + np.cos(alt) * np.sin(slope) * np.cos(az - aspect), 0, 1)

    hs = 0.6 * shade(315, 40) + 0.25 * shade(270, 50) + 0.15 * shade(0, 60)
    hs = hs / max(np.percentile(hs[valid], 99.5), 1e-6)
    hs = np.clip(hs, 0, 1)
    # Subtle hypsometric tint (m -> RGB)
    stops = np.array([0, 300, 1000, 2000, 3000, 3800, 4500, 5200, 6000], "float32")
    cols = np.array([
        [214, 226, 204], [222, 230, 205], [233, 232, 207], [236, 226, 199],
        [229, 212, 186], [219, 203, 180], [208, 197, 184], [224, 220, 216],
        [248, 248, 248]], "float32")
    tint = np.stack([np.interp(z, stops, cols[:, i]) for i in range(3)], axis=-1)
    k = (0.50 + 0.50 * hs)[..., None]  # multiply blend, soft
    rgb = np.clip(tint * k, 0, 255).astype("uint8")
    drv = gdal.GetDriverByName("GTiff")
    out = drv.Create(str(relief), nx, ny, 4, gdal.GDT_Byte,
                     options=["COMPRESS=DEFLATE", "PREDICTOR=2", "TILED=YES", "PHOTOMETRIC=RGB",
                              "ALPHA=YES"])
    out.SetGeoTransform(gt)
    out.SetProjection(ds.GetProjection())
    for i in range(3):
        out.GetRasterBand(i + 1).WriteArray(rgb[..., i])
    out.GetRasterBand(4).WriteArray((valid * 255).astype("uint8"))
    out.BuildOverviews("AVERAGE", [2, 4, 8])
    out = None


def build_ne_clip() -> None:
    """Clip the Natural Earth shapefiles to the study region into one small GeoPackage."""
    jobs = [
        ("ne_10m_admin_0_countries", "countries", (-86, -24, -62, -2)),
        ("ne_10m_lakes", "lakes", (-86, -24, -62, -2)),
        ("ne_10m_rivers_lake_centerlines", "rivers", (-86, -24, -62, -2)),
        ("ne_10m_ocean", "ocean", (-86, -24, -62, -2)),
        ("ne_50m_admin_0_countries", "sa_countries", (-95, -60, -28, 16)),
    ]
    NE_CLIP.mkdir(parents=True, exist_ok=True)
    for name, layer, bbox in jobs:
        src = NE_DIR / name / f"{name}.shp"
        if not src.is_file():
            sys.exit(f"missing {src}\n{fetch_inputs_help()}")
        dst = NE_CLIP / f"{layer}.fgb"
        if dst.exists():
            dst.unlink()
        ds = gdal.VectorTranslate(str(dst), str(src), format="FlatGeobuf", layerName=layer,
                                  clipSrc=list(bbox), geometryType="PROMOTE_TO_MULTI", makeValid=True)
        ds = None


def read_stations() -> list[dict]:
    import csv
    with open(STATIONS, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------
# Styling helpers
# --------------------------------------------------------------------------
def tfmt(size: float, color: str = C_TEXT, bold=False, italic=False, buffer=0.0,
         buffer_color="#ffffff", spacing=0.0) -> QgsTextFormat:
    f = QFont(FONT)
    f.setBold(bold)
    f.setItalic(italic)
    if spacing:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
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


def vlayer(path: Path | str, name: str, layer: str | None = None) -> QgsVectorLayer:
    path = Path(path)
    if path.is_dir():  # Natural Earth clip folder
        path, layer = path / f"{layer}.fgb", None
    uri = f"{path}|layername={layer}" if layer else str(path)
    lyr = QgsVectorLayer(uri, name, "ogr")
    if not lyr.isValid():
        raise RuntimeError(f"invalid layer {uri}")
    return lyr


def fill(color: str, outline: str = "transparent", width: float = 0.0, opacity: float = 1.0,
         style: str = "solid") -> QgsFillSymbol:
    s = QgsFillSymbol.createSimple({
        "color": color, "outline_color": outline, "outline_width": str(width),
        "outline_width_unit": "MM", "style": style, "joinstyle": "round"})
    s.setOpacity(opacity)
    return s


def line(color: str, width: float, dash: str | None = None, opacity=1.0) -> QgsLineSymbol:
    props = {"line_color": color, "line_width": str(width), "line_width_unit": "MM",
             "capstyle": "round", "joinstyle": "round"}
    if dash:
        props.update({"use_custom_dash": "1", "customdash": dash, "customdash_unit": "MM"})
    s = QgsLineSymbol.createSimple(props)
    s.setOpacity(opacity)
    return s


def marker(shape: str, color: str, size: float, outline="#1a1a1a", ow=0.25,
           inset_scale: float | None = None) -> QgsMarkerSymbol:
    m = QgsMarkerSymbol.createSimple({
        "name": shape, "color": color, "size": str(size), "size_unit": "MM",
        "outline_color": outline, "outline_width": str(ow), "outline_width_unit": "MM"})
    if inset_scale is not None:  # smaller markers inside the crowded Chile inset
        m.setDataDefinedSize(QgsProperty.fromExpression(
            f"if(@map_id = 'cl', {size * inset_scale}, {size})"))
    return m


def label_layer(lyr, expr, fmt, placement=Qgis.LabelPlacement.OverPoint, obstacle=False,
                priority=5, callout=False, props=None, is_expression=True):
    s = QgsPalLayerSettings()
    s.fieldName = expr
    s.isExpression = is_expression
    s.setFormat(fmt)
    s.placement = placement
    pls = s.placementSettings()
    pls.setOverlapHandling(Qgis.LabelOverlapHandling.AllowOverlapIfRequired)
    pls.setAllowDegradedPlacement(True)
    s.setPlacementSettings(pls)
    s.priority = priority
    s.obstacleSettings().setIsObstacle(obstacle)
    if callout:
        c = QgsSimpleLineCallout()
        c.setEnabled(True)
        c.setLineSymbol(line("#444444", 0.15))
        c.setMinimumLength(1.2)
        c.setMinimumLengthUnit(Qgis.RenderUnit.Millimeters)
        c.setOffsetFromAnchor(0.9)
        c.setOffsetFromAnchorUnit(Qgis.RenderUnit.Millimeters)
        s.setCallout(c)
    if props:
        dd = s.dataDefinedProperties()
        for key, val in props.items():
            dd.setProperty(key, QgsProperty.fromExpression(val))
        s.setDataDefinedProperties(dd)
    lyr.setLabeling(QgsVectorLayerSimpleLabeling(s))
    lyr.setLabelsEnabled(True)


# --------------------------------------------------------------------------
# Layers
# --------------------------------------------------------------------------
def make_layers(project: QgsProject) -> dict:
    L = {}
    ne = str(NE_CLIP)

    L["ocean"] = vlayer(ne, "Ocean", "ocean")
    L["ocean"].setRenderer(QgsSingleSymbolRenderer(fill(C_WATER)))

    L["relief"] = QgsRasterLayer(str(RELIEF), "Relief", "gdal")
    if not L["relief"].isValid():
        raise RuntimeError("relief invalid")

    for key in FINE:
        L[f"relief_{key}"] = QgsRasterLayer(str(DEM.parent / f"relief_rgb_inset_{key}.tif"),
                                            f"Relief inset {key}", "gdal")

    # Neighbouring countries: veil (muted); Peru left clear
    L["veil"] = vlayer(ne, "Neighbours veil", "countries")
    L["veil"].setSubsetString("\"ADM0_A3\" <> 'PER'")
    L["veil"].setRenderer(QgsSingleSymbolRenderer(fill("#ffffff", opacity=0.42)))

    L["borders"] = vlayer(ne, "International boundary", "countries")
    L["borders"].setSubsetString("\"ADM0_A3\" <> 'PER'")
    L["borders"].setRenderer(QgsSingleSymbolRenderer(fill("transparent", "#7a7a7a", 0.22)))

    L["peru"] = vlayer(ne, "Peru boundary", "countries")
    L["peru"].setSubsetString("\"ADM0_A3\" = 'PER'")
    L["peru"].setRenderer(QgsSingleSymbolRenderer(fill("transparent", "#2b2b2b", 0.45)))

    L["rivers"] = vlayer(ne, "Rivers", "rivers")
    L["rivers"].setSubsetString("\"scalerank\" <= 8 AND \"featurecla\" <> 'Lake Centerline'")
    L["rivers"].setRenderer(QgsSingleSymbolRenderer(line(C_WATER_LINE, 0.2, opacity=0.8)))

    L["lakes"] = vlayer(ne, "Lakes", "lakes")
    L["lakes"].setRenderer(QgsSingleSymbolRenderer(fill(C_WATER, C_WATER_LINE, 0.18)))

    # Catchments: filled by region, drawn largest first
    L["catch"] = vlayer(CATCH, "Catchments", "catchments")
    cats = []
    for reg, col in REGION_COLOR.items():
        sym = fill(col, col, 0.22, opacity=1.0)
        sym.symbolLayer(0).setFillColor(QColor(col).lighter(100))
        c = QColor(col)
        c.setAlphaF(0.22)
        sym.symbolLayer(0).setFillColor(c)
        cats.append(QgsRendererCategory(reg, sym, reg))
    fsym = fill(C_FOCUS, C_FOCUS, 0.3)
    c = QColor(C_FOCUS)
    c.setAlphaF(0.22)
    fsym.symbolLayer(0).setFillColor(c)
    cats.append(QgsRendererCategory("focus", fsym, "focus"))
    r = QgsCategorizedSymbolRenderer(
        "CASE WHEN \"gauge_id\" = 'P00000055' THEN 'focus' ELSE \"region\" END", cats)
    r.setOrderBy(QgsFeatureRequest.OrderBy([QgsFeatureRequest.OrderByClause("basin_area", False)]))
    r.setOrderByEnabled(True)
    L["catch"].setRenderer(r)
    # Cabanillas catchment in focus colour
    L["catch"].setSubsetString("")

    # Gauges
    st = read_stations()
    g = QgsVectorLayer("Point?crs=EPSG:4326", "Gauges", "memory")
    pr = g.dataProvider()
    pr.addAttributes([
        QgsField("gauge_id", QMetaType.Type.QString), QgsField("name", QMetaType.Type.QString),
        QgsField("short", QMetaType.Type.QString), QgsField("cls", QMetaType.Type.QString),
        QgsField("lbl_main", QMetaType.Type.QString), QgsField("lbl_cb", QMetaType.Type.QString),
        QgsField("lbl_cl", QMetaType.Type.QString), QgsField("zorder", QMetaType.Type.Int)])
    g.updateFields()
    feats = []
    for row in st:
        gid = row["gauge_id"]
        if gid == "P00000055":
            cls = "focus"
        elif row["region"] == "Cordillera Blanca":
            cls = "cb"
        elif row["region"] == "Altiplano":
            cls = "alt"
        else:
            cls = "ws"
        f = QgsFeature(g.fields())
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(row["gauge_lon"]), float(row["gauge_lat"]))))
        lm, lb, lc = LBL[gid]
        f.setAttributes([gid, row["gauge_name"], SHORT[gid], cls, lm, lb, lc, 2 if cls == "focus" else 1])
        feats.append(f)
    pr.addFeatures(feats)
    g.updateExtents()
    cats = [
        QgsRendererCategory("cb", marker("circle", C_CB, 2.0), "Cordillera Blanca, Peru (historical, 1950s–1970s)"),
        QgsRendererCategory("ws", marker("square", C_WS, 1.9), "Western / southern Andes, Peru"),
        QgsRendererCategory("alt", marker("triangle", C_ALT, 2.4, inset_scale=0.72),
                            "Altiplano, northern Chile (DGA)"),
        QgsRendererCategory("focus", marker("star", C_FOCUS, 3.8, ow=0.3),
                            "Altiplano focus: Puente Isla Cabanillas (Peru)"),
    ]
    gr = QgsCategorizedSymbolRenderer("cls", cats)
    gr.setOrderBy(QgsFeatureRequest.OrderBy([QgsFeatureRequest.OrderByClause("zorder", True)]))
    gr.setOrderByEnabled(True)
    g.setRenderer(gr)

    pick = ("CASE WHEN @map_id = 'main' THEN \"lbl_main\" WHEN @map_id = 'cb' THEN \"lbl_cb\" "
            "WHEN @map_id = 'cl' THEN \"lbl_cl\" ELSE '' END")
    label_layer(
        g,
        f"if(({pick}) = '', NULL, \"short\")",
        tfmt(6.0, C_TEXT, buffer=0.55),
        priority=10, callout=True,
        props={
            QgsPalLayerSettings.Property.OffsetQuad:
                f"to_int(array_get(string_to_array({pick}, ';'), 0))",
            QgsPalLayerSettings.Property.OffsetXY:
                f"array_get(string_to_array({pick}, ';'), 1) || ',' || array_get(string_to_array({pick}, ';'), 2)",
            QgsPalLayerSettings.Property.Bold: "\"cls\" = 'focus'",
            QgsPalLayerSettings.Property.Size: "if(\"cls\" = 'focus', 6.5, 6.0)",
        })
    L["gauges"] = g

    # Place-name labels (countries, ocean, lake) as a separate memory layer
    names = QgsVectorLayer("Point?crs=EPSG:4326", "Names", "memory")
    npr = names.dataProvider()
    npr.addAttributes([QgsField("txt", QMetaType.Type.QString), QgsField("kind", QMetaType.Type.QString),
                       QgsField("maps", QMetaType.Type.QString)])
    names.updateFields()
    for lon, lat, txt, kind, maps in [
        (-74.3, -10.7, "P E R U", "country", "main"),
        (-68.3, -17.6, "BOLIVIA", "neigh", "main"),
        (-70.1, -19.3, "CHILE", "neigh", "main"),
        (-69.0, -8.05, "BRAZIL", "neigh", "none"),
        (-80.35, -9.2, "Pacific\nOcean", "sea", "main"),
        (-68.45, -16.55, "Lake\nTiticaca", "lake", "main"),
        (-75.9, -13.5, "Andes", "range", "none"),
        (-69.04, -18.30, "BOLIVIA", "neigh", "cl"),
        (-69.40, -18.36, "CHILE", "neigh", "cl"),
    ]:
        f = QgsFeature(names.fields())
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
        f.setAttributes([txt, kind, maps])
        npr.addFeatures([f])
    names.setRenderer(QgsSingleSymbolRenderer(marker("circle", "#ffffff", 0.01, outline="transparent", ow=0)))
    names.renderer().symbol().setOpacity(0)
    label_layer(
        names,
        "if(\"maps\" = @map_id, \"txt\", NULL)",
        tfmt(6.0, "#555555", buffer=0.0),
        priority=9,
        props={
            QgsPalLayerSettings.Property.Size:
                "CASE WHEN \"kind\"='country' THEN 9 WHEN \"kind\"='sea' THEN 7 "
                "WHEN @map_id='cl' THEN 5 WHEN \"kind\"='lake' THEN 6 ELSE 6.5 END",
            QgsPalLayerSettings.Property.Italic: "\"kind\" IN ('sea','lake','range')",
            QgsPalLayerSettings.Property.Bold: "\"kind\" = 'country'",
            QgsPalLayerSettings.Property.Color:
                "CASE WHEN \"kind\" IN ('sea','lake') THEN '#3F6E96' WHEN \"kind\"='country' "
                "THEN '#3a3a3a' ELSE '#6b6b6b' END",
            QgsPalLayerSettings.Property.FontLetterSpacing:
                "CASE WHEN \"kind\"='country' THEN 1.2 WHEN \"kind\"='neigh' THEN 0.6 "
                "WHEN \"kind\"='sea' THEN 0.4 ELSE 0 END",
            QgsPalLayerSettings.Property.BufferDraw: "\"kind\" = 'lake'",
            QgsPalLayerSettings.Property.BufferSize: "0.5",
        })
    L["names"] = names

    # Locator layers
    L["sa"] = vlayer(ne, "South America", "sa_countries")
    L["sa"].setRenderer(QgsCategorizedSymbolRenderer("ADM0_A3", [
        QgsRendererCategory("PER", fill("#9a9a9a", "#ffffff", 0.1), "Peru"),
        QgsRendererCategory(None, fill("#dcdcdc", "#ffffff", 0.1), "other")]))

    # Legend-only layers (never drawn in a map)
    L["lg_catch"] = QgsVectorLayer("Polygon?crs=EPSG:4326", "Catchment (Andean-GC)", "memory")
    L["lg_catch"].setRenderer(QgsSingleSymbolRenderer(fill("#8c8c8c", "#555555", 0.22, opacity=0.6)))
    L["lg_peru"] = QgsVectorLayer("LineString?crs=EPSG:4326", "Peru boundary", "memory")
    L["lg_peru"].setRenderer(QgsSingleSymbolRenderer(line("#2b2b2b", 0.45)))
    L["lg_int"] = QgsVectorLayer("LineString?crs=EPSG:4326", "Other international boundary", "memory")
    L["lg_int"].setRenderer(QgsSingleSymbolRenderer(line("#7a7a7a", 0.22)))
    L["lg_riv"] = QgsVectorLayer("LineString?crs=EPSG:4326", "River / lake", "memory")
    L["lg_riv"].setRenderer(QgsSingleSymbolRenderer(line(C_WATER_LINE, 0.3)))


    for k in ["ocean", "relief", "relief_cb", "relief_cl", "veil", "borders", "peru", "rivers", "lakes", "catch", "gauges",
              "names", "sa", "lg_catch", "lg_peru", "lg_int", "lg_riv"]:
        project.addMapLayer(L[k], False)
        project.layerTreeRoot().addLayer(L[k])
    return L


# --------------------------------------------------------------------------
# Layout
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


def fit(rect: QgsRectangle, w: float, h: float) -> QgsRectangle:
    """Grow rect so that its aspect equals w/h (keep centre)."""
    cx, cy = rect.center().x(), rect.center().y()
    rw, rh = rect.width(), rect.height()
    if rw / rh < w / h:
        rw = rh * w / h
    else:
        rh = rw * h / w
    return QgsRectangle(cx - rw / 2, cy - rh / 2, cx + rw / 2, cy + rh / 2)


def add_map(layout, mid, x, y, w, h, extent, layers, crs=MAP_CRS, frame=0.3, bg="#ffffff"):
    m = QgsLayoutItemMap(layout)
    m.setId(mid)
    m.attemptMove(QgsLayoutPoint(x, y, Qgis.LayoutUnit.Millimeters))
    m.attemptResize(QgsLayoutSize(w, h, Qgis.LayoutUnit.Millimeters))
    m.setCrs(crs)
    m.setLayers(layers)
    m.setKeepLayerSet(True)
    m.setExtent(fit(extent, w, h))
    m.setFrameEnabled(frame > 0)
    m.setFrameStrokeWidth(QgsLayoutMeasurementFromMM(frame))
    m.setFrameStrokeColor(QColor("#333333"))
    m.setBackgroundColor(QColor(bg))
    layout.addLayoutItem(m)
    return m


def QgsLayoutMeasurementFromMM(v):
    from qgis.core import QgsLayoutMeasurement
    return QgsLayoutMeasurement(v, Qgis.LayoutUnit.Millimeters)


def add_label(layout, text, x, y, w, h, fmt, halign=Qt.AlignmentFlag.AlignLeft,
              valign=Qt.AlignmentFlag.AlignTop, bg=None):
    lab = QgsLayoutItemLabel(layout)
    lab.setText(text)
    lab.setTextFormat(fmt)
    lab.setHAlign(halign)
    lab.setVAlign(valign)
    lab.attemptMove(QgsLayoutPoint(x, y, Qgis.LayoutUnit.Millimeters))
    lab.attemptResize(QgsLayoutSize(w, h, Qgis.LayoutUnit.Millimeters))
    if bg:
        lab.setBackgroundEnabled(True)
        lab.setBackgroundColor(QColor(bg))
    layout.addLayoutItem(lab)
    return lab


def add_overview(host, linked, color="#1a1a1a", width=0.35):
    ov = QgsLayoutItemMapOverview(f"ov_{linked.id()}", host)
    ov.setLinkedMap(linked)
    ov.setFrameSymbol(fill("transparent", color, width))
    host.overviews().addOverview(ov)
    return ov


def geo_to_page(m: QgsLayoutItemMap, lon, lat):
    tr = QgsCoordinateTransform(WGS84, m.crs(), QgsProject.instance())
    p = tr.transform(QgsPointXY(lon, lat))
    ext = m.extent()
    pos = m.positionWithUnits()
    sz = m.sizeWithUnits()
    x = pos.x() + (p.x() - ext.xMinimum()) / ext.width() * sz.width()
    y = pos.y() + (ext.yMaximum() - p.y()) / ext.height() * sz.height()
    return x, y


def add_leader(layout, pts, color="#1a1a1a", width=0.25):
    poly = QPolygonF([QPointF(x, y) for x, y in pts])
    pl = QgsLayoutItemPolyline(poly, layout)
    pl.setSymbol(line(color, width, dash="1.0;0.6"))
    layout.addLayoutItem(pl)
    return pl


def style_grid(m, interval_deg, sides, size=5.5, lines=True):
    grid = QgsLayoutItemMapGrid("graticule", m)
    grid.setCrs(WGS84)
    grid.setIntervalX(interval_deg)
    grid.setIntervalY(interval_deg)
    grid.setStyle(QgsLayoutItemMapGrid.GridStyle.Solid if lines else QgsLayoutItemMapGrid.GridStyle.FrameAnnotationsOnly)
    grid.setLineSymbol(line("#ffffff", 0.12, opacity=0.7))
    grid.setAnnotationEnabled(True)
    grid.setAnnotationFormat(QgsLayoutItemMapGrid.AnnotationFormat.DegreeMinuteNoSuffix)
    grid.setAnnotationFormat(QgsLayoutItemMapGrid.AnnotationFormat.CustomFormat)
    grid.setAnnotationExpression(
        "CASE WHEN @grid_axis = 'x' THEN to_string(abs(@grid_number)) || '°W' "
        "ELSE to_string(abs(@grid_number)) || '°S' END")
    grid.setAnnotationTextFormat(tfmt(size, "#333333"))
    grid.setAnnotationFrameDistance(0.8)
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
    grid.setFrameWidth(1.2)
    grid.setFramePenSize(0.25)
    grid.setFramePenColor(QColor("#333333"))
    m.grids().addGrid(grid)
    return grid


def inset_scalebar(layout, m, km, x, y):
    sb = QgsLayoutItemScaleBar(layout)
    sb.setStyle("Line Ticks Up")
    sb.setLinkedMap(m)
    sb.setUnits(Qgis.DistanceUnit.Kilometers)
    sb.setUnitLabel("km")
    sb.setUnitsPerSegment(km)
    sb.setNumberOfSegments(1)
    sb.setNumberOfSegmentsLeft(0)
    sb.setHeight(0.9)
    sb.setLineWidth(0.25)
    sb.setTextFormat(tfmt(4.6, "#333333", buffer=0.4))
    sb.setLabelBarSpace(0.5)
    sb.setBoxContentSpace(0.0)
    sb.setSegmentSizeMode(Qgis.ScaleBarSegmentSizeMode.Fixed)
    sb.attemptMove(QgsLayoutPoint(x, y, Qgis.LayoutUnit.Millimeters))
    layout.addLayoutItem(sb)
    sb.update()
    return sb


def elevation_bar(layout, x, y, w=24.0, h=2.0):
    """Horizontal colour bar matching the relief tint (legend for the hypsometry)."""
    from qgis.core import QgsGradientColorRamp, QgsGradientFillSymbolLayer, QgsGradientStop, QgsLayoutItemShape
    stops_m = [0, 300, 1000, 2000, 3000, 3800, 4500, 5200, 6000]
    cols = [(214, 226, 204), (222, 230, 205), (233, 232, 207), (236, 226, 199), (229, 212, 186),
            (219, 203, 180), (208, 197, 184), (224, 220, 216), (248, 248, 248)]
    ramp = QgsGradientColorRamp(QColor(*cols[0]), QColor(*cols[-1]), False,
                                [QgsGradientStop(v / 6000.0, QColor(*c))
                                 for v, c in zip(stops_m[1:-1], cols[1:-1])])
    gl = QgsGradientFillSymbolLayer()
    gl.setGradientColorType(Qgis.GradientColorSource.ColorRamp)
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
    sh.attemptMove(QgsLayoutPoint(x, y + 3.6, Qgis.LayoutUnit.Millimeters))
    sh.attemptResize(QgsLayoutSize(w, h, Qgis.LayoutUnit.Millimeters))
    layout.addLayoutItem(sh)
    add_label(layout, "Elevation (m a.s.l.)", x - 0.2, y, w + 10, 3.4, tfmt(6.2, C_TEXT, bold=True))
    for v in (0, 2000, 4000, 6000):
        xx = x + w * v / 6000.0
        add_label(layout, f"{v:,}".replace(",", " "), xx - 5, y + 3.6 + h + 0.3, 10, 2.8,
                  tfmt(5.2, "#333333"), halign=Qt.AlignmentFlag.AlignHCenter)
    add_label(layout, "tint × multidirectional hillshade", x - 0.2, y + 3.6 + h + 3.0, w + 12, 2.8,
              tfmt(4.8, "#666666", italic=True))


def build_layout(project: QgsProject, L: dict) -> QgsPrintLayout:
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName("fig00")
    page = layout.pageCollection().page(0)
    page.setPageSize(QgsLayoutSize(PAGE_W, PAGE_H, Qgis.LayoutUnit.Millimeters))

    base = [L["names"], L["gauges"], L["catch"], L["lakes"], L["rivers"], L["peru"], L["borders"],
            L["veil"], L["ocean"], L["relief"]]
    base_cb = base[:-1] + [L["relief_cb"], L["relief"]]
    base_cl = [x for x in base[:-1] if x is not L["veil"]] + [L["relief_cl"], L["relief"]]

    # ---- (a) main map
    main = add_map(layout, "main", MAIN_X, MAIN_Y, MAIN_W, MAIN_H,
                   extent_lcc(MAIN_LON[0], MAIN_LON[1], MAIN_LAT[0], MAIN_LAT[1]), base,
                   bg=C_WATER)
    style_grid(main, 2.0, ("left", "bottom"))

    # ---- (b) Cordillera Blanca inset (Pacific, west of the cluster)
    cb_w, cb_h = 30.0, 45.0
    cb_x, cb_y = MAIN_X + 1.6, MAIN_Y + 32.5
    cb = add_map(layout, "cb", cb_x, cb_y, cb_w, cb_h,
                 extent_lcc(CB_EXT[0], CB_EXT[1], CB_EXT[3], CB_EXT[2]), base_cb, frame=0.35)
    # ---- (c) Chilean Altiplano inset (top-right, over the Amazon lowlands: no gauges there)
    cl_w, cl_h = 33.0, 44.0
    cl_x, cl_y = MAIN_X + MAIN_W - cl_w - 1.6, MAIN_Y + 1.6
    cl = add_map(layout, "cl", cl_x, cl_y, cl_w, cl_h,
                 extent_lcc(CL_EXT[0], CL_EXT[1], CL_EXT[3], CL_EXT[2]), base_cl, frame=0.35)

    add_overview(main, cb)
    add_overview(main, cl)

    tr = QgsCoordinateTransform(MAP_CRS, WGS84, project)

    def corner(mapitem, which):
        e = mapitem.extent()
        x = e.xMinimum() if "l" in which else e.xMaximum()
        y = e.yMaximum() if "t" in which else e.yMinimum()
        p = tr.transform(QgsPointXY(x, y))
        return geo_to_page(main, p.x(), p.y())


    for m, txt, sub in [(cb, "b", "Cordillera Blanca"), (cl, "c", "Chilean Altiplano")]:
        p = m.positionWithUnits()
        add_label(layout, f"({txt}) {sub}", p.x() + 0.35, p.y() + 0.35, m.sizeWithUnits().width() - 0.7,
                  3.3, tfmt(5.6, C_TEXT, bold=True), bg=QColor(255, 255, 255, 215))
    inset_scalebar(layout, cb, 20, cb_x + 1.5, cb_y + cb_h - 5.0)
    inset_scalebar(layout, cl, 10, cl_x + 1.5, cl_y + cl_h - 5.0)
    add_label(layout, "(a)", MAIN_X + 1.0, MAIN_Y + 0.8, 8, 4, tfmt(7.0, C_TEXT, bold=True))
    for m, txt in [(cb, "b"), (cl, "c")]:
        x, y = corner(m, "br")
        add_label(layout, txt, x + 0.3, y - 3.0, 3, 3, tfmt(6.5, C_TEXT, bold=True, buffer=0.5))

    # ---- locator (South America), Pacific south of the coast
    loc_w, loc_h = 20.0, 25.0
    loc_x, loc_y = MAIN_X + 38.0, MAIN_Y + MAIN_H - loc_h - 1.6
    loc_crs = QgsCoordinateReferenceSystem.fromProj(
        "+proj=laea +lat_0=-18 +lon_0=-60 +datum=WGS84 +units=m +no_defs")
    tr_loc = QgsCoordinateTransform(WGS84, loc_crs, project)
    r = QgsRectangle()
    for lo, la in [(-82, 13), (-34, 13), (-82, -56), (-34, -56), (-60, 13), (-60, -56), (-35, -8)]:
        p = tr_loc.transform(QgsPointXY(lo, la))
        r.combineExtentWith(p.x(), p.y())
    loc = add_map(layout, "loc", loc_x, loc_y, loc_w, loc_h, r, [L["sa"]], crs=loc_crs, frame=0.3,
                  bg="#eef4f8")
    add_overview(loc, main, color=C_FOCUS, width=0.4)
    add_label(layout, "South\nAmerica", loc_x + 0.8, loc_y + loc_h - 5.6, 12, 5.4,
              tfmt(4.6, "#444444", italic=True))

    # ---- north arrow + scale bar (bottom-left, in the Pacific)
    na = QgsLayoutItemPicture(layout)
    na.setPicturePath(str(SVG_NORTH))
    na.attemptMove(QgsLayoutPoint(MAIN_X + 4.0, MAIN_Y + MAIN_H - 20.0, Qgis.LayoutUnit.Millimeters))
    na.attemptResize(QgsLayoutSize(5.0, 7.5, Qgis.LayoutUnit.Millimeters))
    na.setSvgFillColor(QColor("#333333"))
    na.setSvgStrokeColor(QColor("#333333"))
    layout.addLayoutItem(na)

    sb = QgsLayoutItemScaleBar(layout)
    sb.setStyle("Single Box")
    sb.setLinkedMap(main)
    sb.setUnits(Qgis.DistanceUnit.Kilometers)
    sb.setUnitLabel("km")
    sb.setUnitsPerSegment(100)
    sb.setNumberOfSegments(2)
    sb.setNumberOfSegmentsLeft(0)
    sb.setHeight(1.1)
    sb.setLineWidth(0.2)
    sb.setTextFormat(tfmt(5.2, "#333333"))
    sb.setLabelBarSpace(0.8)
    sb.setBoxContentSpace(0.0)
    sb.setSegmentSizeMode(Qgis.ScaleBarSegmentSizeMode.Fixed)
    sb.attemptMove(QgsLayoutPoint(MAIN_X + 4.0, MAIN_Y + MAIN_H - 9.0, Qgis.LayoutUnit.Millimeters))
    layout.addLayoutItem(sb)
    sb.update()

    # ---- legend (below the map)
    leg_y = MAIN_Y + MAIN_H + 5.2
    leg = QgsLayoutItemLegend(layout)
    leg.setTitle("")
    leg.setLinkedMap(main)
    leg.setAutoUpdateModel(False)
    root = leg.model().rootGroup()
    root.removeAllChildren()
    gnode = root.addLayer(L["gauges"])
    gnode.setUseLayerName(False)
    gnode.setName("Stream gauges (by region)")
    for key in ["lg_catch", "lg_riv", "lg_peru", "lg_int"]:
        root.addLayer(L[key])
    leg.setColumnCount(2)
    leg.setSplitLayer(True)
    leg.setEqualColumnWidth(False)
    leg.setSymbolWidth(3.6)
    leg.setSymbolHeight(2.4)
    leg.setColumnSpace(3.0)
    leg.rstyle(QgsLegendStyle.Style.SymbolLabel).setTextFormat(tfmt(6.0, C_TEXT))
    leg.rstyle(QgsLegendStyle.Style.Subgroup).setTextFormat(tfmt(6.2, C_TEXT, bold=True))
    leg.rstyle(QgsLegendStyle.Style.Group).setTextFormat(tfmt(6.2, C_TEXT, bold=True))
    leg.rstyle(QgsLegendStyle.Style.Symbol).setMargin(QgsLegendStyle.Side.Top, 0.8)
    leg.rstyle(QgsLegendStyle.Style.Subgroup).setMargin(QgsLegendStyle.Side.Bottom, 0.3)
    leg.setBoxSpace(0.0)
    leg.setBackgroundEnabled(False)
    leg.setFrameEnabled(False)
    leg.attemptMove(QgsLayoutPoint(MAIN_X - 1.0, leg_y, Qgis.LayoutUnit.Millimeters))
    layout.addLayoutItem(leg)
    leg.adjustBoxSize()
    leg.refresh()

    elevation_bar(layout, MAIN_X + MAIN_W - 26.0, leg_y + 0.2)

    add_label(layout,
              "Data: gauges and catchments from Andean-GC (CC BY 4.0; SENAMHI Peru, DGA Chile); "
              "relief from Copernicus GLO-90 DEM (© DLR e.V./Airbus, provided under COPERNICUS by the EU "
              "and ESA), averaged to ~830 m (insets ~170–280 m); boundaries, lakes and rivers from Natural Earth. "
              "Lambert conformal conic projection (standard parallels 9°S and 17°S).",
              MAIN_X - 1.0, PAGE_H - 7.2, MAIN_W + 1.0, 7.0, tfmt(4.8, "#555555"))
    return layout, leg, None


def main() -> int:
    for p in (STATIONS, CATCH, DEM):
        if not p.is_file():
            print(f"missing {p}\n{fetch_inputs_help()}", file=sys.stderr)
            return 1
    if not RELIEF.is_file() or RELIEF.stat().st_mtime < DEM.stat().st_mtime or "--rebuild" in sys.argv:
        print("building relief RGB ...")
        build_relief()
    for key in FINE:  # finer relief for the zoom insets
        fine_rel = DEM.parent / f"relief_rgb_inset_{key}.tif"
        if not fine_rel.is_file() or "--rebuild" in sys.argv:
            print(f"building inset relief {key} ...")
            build_relief(fetch_fine_dem(key), fine_rel)
    if not (NE_CLIP / "sa_countries.fgb").is_file() or "--rebuild" in sys.argv:
        print("clipping Natural Earth ...")
        build_ne_clip()

    QgsApplication.setPrefixPath(str(QGIS_APP), True)
    app = QgsApplication([], False)
    app.initQgis()
    project = QgsProject.instance()
    project.setCrs(MAP_CRS)
    L = make_layers(project)
    layout, leg, leg2 = build_layout(project, L)
    project.layoutManager().addLayout(layout)
    layout.refresh()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    ex = QgsLayoutExporter(layout)
    s = QgsLayoutExporter.ImageExportSettings()
    s.dpi = int(os.environ.get("FIG_DPI", "600"))
    res = ex.exportToImage(str(OUT) + ".png", s)
    print("png:", res)
    if "--no-pdf" not in sys.argv:
        p = QgsLayoutExporter.PdfExportSettings()
        p.dpi = 300
        p.rasterizeWholeImage = False
        p.forceVectorOutput = False
        p.textRenderFormat = Qgis.TextRenderFormat.AlwaysText
        p.exportMetadata = False
        p.simplifyGeometries = True
        res = ex.exportToPdf(str(OUT) + ".pdf", p)
        print("pdf:", res)
    project.write(str(QGZ))
    app.exitQgis()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
