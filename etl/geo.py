"""Stage 5 — Geo. Build simplified Bundesland boundaries (BKG VG2500, dl-de/by-2-0) as GeoJSON
and TopoJSON keyed by ags_code, for the Power BI Shape Map and the Plotly preview.

Geo dependencies (geopandas, pyogrio, shapely, topojson) are an optional extra and are imported
lazily, so the test suite / CI need not install them.
"""

from __future__ import annotations

import hashlib
import json

import requests

from etl import bundeslaender
from etl.paths import DASHBOARD_GEO_DIR, RAW_DIR, ensure_dirs

GEO_URL = "https://daten.gdz.bkg.bund.de/produkte/vg/vg2500/aktuell/vg2500_12-31.utm32s.shape.zip"
GEO_ZIP = RAW_DIR / "vg2500.zip"
LAN_LAYER = "/vsizip/{zip}/vg2500/VG2500_LAN.shp"
SIMPLIFY_TOLERANCE_M = 500  # metres (UTM32) — keeps state shapes crisp but small
LICENSE = "Datenlizenz Deutschland – Namensnennung – Version 2.0 (BKG, VG2500)"


def download_geo(*, force: bool = False) -> None:
    ensure_dirs()
    if GEO_ZIP.exists() and not force:
        return
    resp = requests.get(
        GEO_URL, headers={"User-Agent": "german-hospital-capacity-etl/0.1"}, timeout=180
    )
    resp.raise_for_status()
    if resp.content[:2] != b"PK":
        raise ValueError(f"{GEO_URL} did not return a ZIP.")
    GEO_ZIP.write_bytes(resp.content)


def build_geo(*, force_download: bool = False) -> dict[str, int]:
    """Produce dashboard/geo/bundeslaender.{geojson,topojson} keyed by ags_code."""
    import geopandas as gpd
    import topojson as tp

    download_geo(force=force_download)
    DASHBOARD_GEO_DIR.mkdir(parents=True, exist_ok=True)

    gdf = gpd.read_file(LAN_LAYER.format(zip=GEO_ZIP))
    gdf = gdf[gdf["GF"] == 9].copy()  # GF=9 = land area (drops water-body polygons)

    name_en = {b.ags_code: b.name_en for b in bundeslaender.load_reference()}
    gdf["ags_code"] = gdf["GEN"].map(bundeslaender.normalize_name)
    gdf["name_de"] = gdf["GEN"]
    gdf["name_en"] = gdf["ags_code"].map(name_en)

    gdf = gdf.dissolve(by="ags_code", as_index=False, aggfunc="first")
    gdf["geometry"] = gdf.geometry.simplify(SIMPLIFY_TOLERANCE_M, preserve_topology=True)
    gdf = gdf[["ags_code", "name_de", "name_en", "geometry"]].sort_values("ags_code")
    gdf = gdf.to_crs(4326)

    if len(gdf) != 16:
        raise ValueError(f"Expected 16 Bundesländer, got {len(gdf)}.")

    geojson_path = DASHBOARD_GEO_DIR / "bundeslaender.geojson"
    topojson_path = DASHBOARD_GEO_DIR / "bundeslaender.topojson"
    geojson_path.write_text(gdf.to_json(), encoding="utf-8")
    tp.Topology(gdf, prequantize=True).to_json(topojson_path)

    _write_provenance()
    return {"features": len(gdf)}


def _write_provenance() -> None:
    sha = hashlib.sha256(GEO_ZIP.read_bytes()).hexdigest()
    (DASHBOARD_GEO_DIR / "geo_source.json").write_text(
        json.dumps(
            {
                "source": "BKG — Bundesamt für Kartographie und Geodäsie, VG2500",
                "layer": "VG2500_LAN (GF=9, land area)",
                "url": GEO_URL,
                "sha256": sha,
                "license": LICENSE,
                "crs_output": "EPSG:4326",
                "simplify_tolerance_m": SIMPLIFY_TOLERANCE_M,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
