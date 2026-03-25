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

# ✅ TEST SECRETS
st.write("TEST USER =", st.secrets.get("CDSE_USER"))
st.write("TEST PASS LENGTH =", len(st.secrets.get("CDSE_PASS", "")))

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

    # Extraction géométries shapely
    geoms = [shape(feat["geometry"]) for feat in gdf["features"]]

    # -----------------------------
# Calcul BBOX robuste (évite les BBOX dégénérées)
xs = [g.bounds[0] for g in geoms] + [g.bounds[2] for g in geoms]
ys = [g.bounds[1] for g in geoms] + [g.bounds[3] for g in geoms]

minx = min(xs)
maxx = max(xs)
miny = min(ys)
maxy = max(ys)

# si la bbox est trop petite -> l’élargir
if abs(maxx - minx) < 0.0001:
    minx -= 0.0005
    maxx += 0.0005

if abs(maxy - miny) < 0.0001:
    miny -= 0.0005
    maxy += 0.0005

bbox = (minx, miny, maxx, maxy)

    # -----------------------------
    # 3 – Recherche Sentinel‑2
    # -----------------------------
    st.info("Recherche de la dernière image Sentinel‑2 L2A…")

    product = find_latest_s2_product(bbox)

    if product is None:
        st.error("❌ Aucun produit Sentinel‑2 trouvé.")
        st.stop()

    st.success("✅ Produit trouvé : " + product["Name"])
    product_id = product["Id"]

    # -----------------------------
    # 4 – Téléchargement bandes
    # -----------------------------
    st.info("Téléchargement des bandes B04 et B08…")
    red_path = download_s2_band(product_id, "B04")
    nir_path = download_s2_band(product_id, "B08")

    # -----------------------------
    # 5 – NDVI
    # -----------------------------
    st.info("Calcul du NDVI…")
    ndvi_array, transform = compute_ndvi(red_path, nir_path)
    st.success("✅ NDVI calculé")

    # -----------------------------
    # 6 – NDVI moyen par parcelle
    # -----------------------------
    st.info("Calcul NDVI moyen par parcelle…")
    gdf = compute_zonal_stats(gdf, ndvi_array, transform)
    st.success("✅ Terminé")

    # -----------------------------
    # 7 – Carte NDVI
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

    st_folium(m, height=600)

    # -----------------------------
    # 8 – Tableau NDVI
    # -----------------------------
    st.subheader("📊 Tableau NDVI")
    rows = [
        {"Parcelle": i + 1, "NDVI": feat["properties"]["NDVI"]}
        for i, feat in enumerate(gdf["features"])
    ]
    st.dataframe(rows)

    # -----------------------------
    # 9 – Export CSV
    # -----------------------------
    import pandas as pd
    df = pd.DataFrame(rows)

    st.download_button(
        "Télécharger NDVI (CSV)",
        df.to_csv(index=False).encode(),
        "ndvi.csv"
    )
