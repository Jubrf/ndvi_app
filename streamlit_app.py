import streamlit as st
import geopandas as gpd
from streamlit_folium import st_folium
import folium
import json

from utils.sentinel_search import find_latest_s2_product
from utils.sentinel_download import download_s2_band
from utils.ndvi_processing import compute_ndvi, compute_zonal_ndvi


st.set_page_config(page_title="Analyse NDVI – Sentinel‑2", layout="wide")

st.title("🌱 Analyse NDVI des parcelles agricoles – Sentinel‑2 (gratuit)")

uploaded = st.file_uploader(
    "Uploader votre fichier parcelles (ZIP contenant SHP ou GeoJSON)",
    type=["zip", "geojson"]
)

if uploaded:
    # ---- Lecture couche SIG ----
    if uploaded.name.endswith(".zip"):
        gdf = gpd.read_file(f"zip://{uploaded}")
    else:
        gdf = gpd.read_file(uploaded)

    st.success(f"{len(gdf)} parcelles chargées ✅")

    # Reprojection automatique
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)

    minx, miny, maxx, maxy = gdf.total_bounds
    bbox = (minx, miny, maxx, maxy)

    # ---- Recherche de l'image Sentinel-2 la plus récente ----
    st.info("Recherche de la dernière image Sentinel‑2 L2A…")
    product = find_latest_s2_product(bbox)

    if product is None:
        st.error("❌ Aucune image Sentinel‑2 trouvée pour cette zone.")
        st.stop()

    product_id = product["Id"]
    st.success("✅ Image trouvée : " + product["Name"])

    # ---- Téléchargement bandes ----
    st.info("Téléchargement des bandes B04 et B08…")

    red_path = download_s2_band(product_id, "B04")
    nir_path = download_s2_band(product_id, "B08")

    # ---- NDVI ----
    st.info("Calcul du NDVI en cours…")
    ndvi_arr, affine = compute_ndvi(red_path, nir_path)
    st.success("✅ NDVI calculé")

    # ---- Statistiques NDVI par parcelle ----
    st.info("Calcul du NDVI moyen par parcelle…")
    gdf = compute_zonal_ndvi(gdf, ndvi_arr, affine)

    # ---- Carte Folium ----
    st.subheader("🗺️ Carte NDVI")

    def ndvi_color(v):
        if v is None:
            return "#cccccc"
        r = int((1 - v) * 255)
        g = int(v * 255)
        return f"#{r:02x}{g:02x}00"

    m = folium.Map(
        location=[(miny + maxy) / 2, (minx + maxx) / 2],
        zoom_start=12
    )

    folium.GeoJson(
        json.loads(gdf.to_json()),
        style_function=lambda feat: {
            "fillColor": ndvi_color(feat["properties"]["NDVI"]),
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.7,
        },
        tooltip=folium.GeoJsonTooltip(fields=["NDVI"])
    ).add_to(m)

    st_folium(m, height=600)

    # ---- Tableau NDVI ----
    st.subheader("📊 Tableau des NDVI")
    st.dataframe(gdf[["NDVI"]])

    # ---- Export CSV ----
    st.download_button(
        "Télécharger NDVI (CSV)",
        gdf.to_csv().encode(),
        "ndvi.csv"
    )# Full code placeholder
