import streamlit as st
import json
import folium
from shapely.geometry import shape
from streamlit_folium import st_folium

from utils.sentinel_search import find_latest_s2_product
from utils.sentinel_download import download_s2_band
from utils.ndvi_processing import (
    load_vector_file,
    compute_ndvi,
    compute_zonal_stats
)

# -----------------------------------------------------------
# CONFIG
# -----------------------------------------------------------
st.set_page_config(page_title="NDVI – Sentinel-2", layout="wide")

# ✅ TEST DES SECRETS (à retirer une fois que tout fonctionne)
st.write("TEST USER =", st.secrets.get("CDSE_USER"))
st.write("TEST PASS LENGTH =", len(st.secrets.get("CDSE_PASS", "")))

st.title("🌱 Analyse NDVI des parcelles agricoles – Sentinel‑2 (STAC API)")

uploaded = st.file_uploader(
    "Uploader vos parcelles (ZIP SHP ou GeoJSON)",
    type=["zip", "geojson"]
)

# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------

if uploaded:

    # -----------------------------
    # 1 – Lecture du fichier vecteur
    # -----------------------------
    gdf = load_vector_file(uploaded)
    n_parcelles = len(gdf["features"])
    st.success(f"{n_parcelles} parcelles chargées ✅")

    # Extraction géométries shapely
    geoms = [shape(feat["geometry"]) for feat in gdf["features"]]

    # -----------------------------
    # 2 – BBOX ROBUSTE
    # -----------------------------
    xs = []
    ys = []

    for g in geoms:
        minx_g, miny_g, maxx_g, maxy_g = g.bounds
        xs += [minx_g, maxx_g]
        ys += [miny_g, maxy_g]

    minx = min(xs)
    maxx = max(xs)
    miny = min(ys)
    maxy = max(ys)

    # ✅ Empêcher les BBOX trop petites (à l’origine des 403)
    if abs(maxx - minx) < 0.0005:
        minx -= 0.001
        maxx += 0.001

    if abs(maxy - miny) < 0.0005:
        miny -= 0.001
        maxy += 0.001

    bbox = (minx, miny, maxx, maxy)
    st.write("✅ BBOX envoyée au STAC :", bbox)

    # -----------------------------
    # 3 – Recherche Sentinel‑2 via STAC
    # -----------------------------
