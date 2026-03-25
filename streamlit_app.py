import streamlit as st
import json
import folium
from streamlit_folium import st_folium

from utils.sentinel_search import find_latest_s2_product
from utils.sentinel_download import download_s2_band
from utils.ndvi_processing import (
    load_vector_file,
    compute_ndvi,
    compute_zonal_stats
)

st.set_page_config(page_title="NDVI – Sentinel-2", layout="wide")

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
    st.success(f"{len(gdf)} parcelles chargées ✅")

    # BBOX pour Sentinel
    minx = min(poly.bounds[0] for poly in gdf["geometry"])
    miny = min(poly.bounds[1] for poly in gdf["geometry"])
    maxx = max(poly.bounds[2] for poly in gdf["geometry"])
    maxy = max(poly.bounds[3] for poly in gdf["geometry"])

    bbox = (minx, miny, maxx, maxy)

    # -----------------------------
    # 2 – Trouver la dernière image Sentinel‑2
    # -----------------------------
    st.info("Recherche de la dernière image Sentinel‑2 L2A…")
    product = find_latest_s2_product(bbox)

    if product is None:
        st.error("❌ Aucune image Sentinel-2 trouvée.")
        st.stop()

    st.success("✅ Produit trouvé : " + product["Name"])
    product_id = product["Id"]

    # -----------------------------
    # 3 – Télécharger bandes B04 / B08
    # -----------------------------
    st.info("Téléchargement des bandes B04 et B08…")

    red_path = download_s2_band(product_id, "B04")
    nir_path = download_s2_band(product_id, "B08")

    # -----------------------------
    # 4 – Calcul NDVI
    # -----------------------------
    st.info("Calcul NDVI…")
    ndvi_array, transform = compute_ndvi(red_path, nir_path)
    st.success("✅ NDVI calculé")

    # -----------------------------
    # 5 – Zonal statistics NDVI
    # -----------------------------
    st.info("Calcul NDVI moyen par parcelle…")
    gdf = compute_zonal_stats(gdf, ndvi_array, transform)
    st.success("✅ Statistiques NDVI calculées")

    # -----------------------------
    # 6 – Affichage carte
    # -----------------------------
    st.subheader("🗺️ Carte NDVI")

    def colorize(v):
        if v is None:
            return "#cccccc"
        r = int((1 - v) * 255)
        g = int(v * 255)
        return f"#{r:02x}{g:02x}00"

    m = folium.Map(location=[(miny + maxy) / 2, (minx + maxx) / 2], zoom_start=12)

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
                aliases=["NDVI moyen :"],
                localize=True
            ),
        ).add_to(m)

    st_folium(m, height=600)

    # -----------------------------
    # 7 – Tableau NDVI
    # -----------------------------
    st.subheader("📊 Tableau NDVI")
    rows = [
        {"Parcelle": i + 1, "NDVI": feat["properties"]["NDVI"]}
        for i, feat in enumerate(gdf["features"])
    ]

    st.dataframe(rows)

    # -----------------------------
    # 8 – Export CSV
    # -----------------------------
    import pandas as pd
    df = pd.DataFrame(rows)

    st.download_button(
        "Télécharger NDVI (CSV)",
        df.to_csv().encode(),
        "ndvi.csv"
    )
