# force streamlit refresh
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

st.set_page_config(page_title="NDVI – Sentinel-2", layout="wide")

st.write("USER =", st.secrets.get("julien.brefie@sdea.fr"))
st.write("PASS LENGTH =", len(st.secrets.get("Jkp1!62Xq'81","")))

st.title("🌱 Analyse NDVI des parcelles agricoles – Sentinel‑2")

uploaded = st.file_uploader(
    "Uploader vos parcelles (ZIP SHP ou GeoJSON)",
    type=["zip", "geojson"]
)

if uploaded:

    # -----------------------------
    # 1 – Lecture du fichier vecteur
    # -----------------------------
    gdf = load_vector_file(uploaded)
    n_parcelles = len(gdf["features"])
    st.success(f"{n_parcelles} parcelles chargées ✅")

    # Extraire les géométries shapely
    geoms = [shape(feat["geometry"]) for feat in gdf["features"]]

    # -----------------------------
    # 2 – Calcul BBOX WGS84
    # -----------------------------
    minx = min(g.bounds[0] for g in geoms)
    miny = min(g.bounds[1] for g in geoms)
    maxx = max(g.bounds[2] for g in geoms)
    maxy = max(g.bounds[3] for g in geoms)

    bbox = (minx, miny, maxx, maxy)

    # -----------------------------
    # 3 – Recherche de la dernière image Sentinel‑2
    # -----------------------------
    st.info("Recherche de la dernière image Sentinel‑2 L2A…")
    product = find_latest_s2_product(bbox)

    if product is None:
        st.error("❌ Aucune image Sentinel-2 trouvée sur cette zone.")
        st.stop()

    st.success("✅ Produit trouvé : " + product["Name"])
    product_id = product["Id"]

    # -----------------------------
    # 4 – Téléchargement bandes B04 / B08
    # -----------------------------
    st.info("Téléchargement des bandes B04 et B08…")

    red_path = download_s2_band(product_id, "B04")
    nir_path = download_s2_band(product_id, "B08")

    # -----------------------------
    # 5 – Calcul NDVI
    # -----------------------------
    st.info("Calcul NDVI…")
    ndvi_array, transform = compute_ndvi(red_path, nir_path)
    st.success("✅ NDVI calculé")

    # -----------------------------
    # 6 – Zonal statistics
    # -----------------------------
    st.info("Calcul NDVI moyen par parcelle…")
    gdf = compute_zonal_stats(gdf, ndvi_array, transform)
    st.success("✅ Analyse NDVI terminée")

    # -----------------------------
    # 7 – Affichage carte
    # -----------------------------
    st.subheader("🗺️ Carte NDVI")

    def colorize(v):
        if v is None:
            return "#cccccc"
        r = int((1 - v) * 255)
        g = int(v * 255)
        return f"#{r:02x}{g:02x}00"

    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

    for feat in gdf["features"]:
        ndvi = feat["properties"]["NDVI"]
        geom = feat["geometry"]

        folium.GeoJson(
            geom,
            style_function=lambda x, ndvi=ndvi: {
                "fillColor": colorize(ndvi),
                "color": "black",
                "fillOpacity": 0.7,
                "weight": 1
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["NDVI"],
                aliases=["NDVI :"],
                localize=True
            ),
        ).add_to(m)

