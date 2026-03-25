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

# ✅ TEST DES SECRETS (à retirer plus tard)
st.write("DEBUG USER =", st.secrets.get("CDSE_USER"))
st.write("DEBUG PASS LENGTH =", len(st.secrets.get("CDSE_PASS", "")))

st.title("🌱 Analyse NDVI des parcelles agricoles – Sentinel‑2 (STAC API)")

uploaded = st.file_uploader(
    "Uploader vos parcelles (ZIP SHP ou GeoJSON)",
    type=["zip", "geojson"]
)

# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------
if uploaded:

    st.write("✅ DEBUG : fichier reçu")

    # -----------------------------
    # 1 – Lecture du fichier vecteur
    # -----------------------------
    try:
        gdf = load_vector_file(uploaded)
    except Exception as e:
        st.error("❌ Erreur lors de la lecture du fichier vecteur (load_vector_file).")
        st.write(str(e))
        st.stop()

    st.write("✅ DEBUG : vecteur chargé")

    n_parcelles = len(gdf["features"])
    st.success(f"{n_parcelles} parcelles chargées ✅")

    # Extraction géométries shapely
    try:
        geoms = [shape(feat["geometry"]) for feat in gdf["features"]]
    except Exception as e:
        st.error("❌ Erreur dans la conversion des géométries.")
        st.write(str(e))
        st.stop()

    st.write("✅ DEBUG : géométries shapely OK")

    # -----------------------------
    # 2 – BBOX ROBUSTE + padding
    # -----------------------------
    xs = []
    ys = []

    try:
        for g in geoms:
            minx_g, miny_g, maxx_g, maxy_g = g.bounds
            xs += [minx_g, maxx_g]
            ys += [miny_g, maxy_g]
    except Exception as e:
        st.error("❌ Erreur lors du calcul des bounds.")
        st.write(str(e))
        st.stop()

    minx = min(xs)
    maxx = max(xs)
    miny = min(ys)
    maxy = max(ys)

    # ✅ Étendre la bbox pour être sûr de capturer une tuile Sentinel
    padding = 0.002
    minx -= padding
    maxx += padding
    miny -= padding
    maxy += padding

    bbox = (minx, miny, maxx, maxy)
    st.write("✅ DEBUG : BBOX envoyée au STAC :", bbox)

    # Debug STAC
    st.write("✅ DEBUG : entrée dans la fonction STAC")

    # -----------------------------
    # 3 – Recherche Sentinel‑2 via STAC
    # -----------------------------
    product = find_latest_s2_product(bbox)

    st.write("✅ DEBUG : retour STAC =", product)

    if product is None:
        st.error("❌ Aucun produit Sentinel‑2 trouvé dans les 30 derniers jours.")
        st.stop()

    product_id = product["id"]
    product_date = product["properties"]["datetime"]

    st.success(f"✅ Produit trouvé : {product_id}")
    st.write("📅 Date :", product_date)

    # -------------------------------------------------------
    # RÉCUPÉRATION DES BANDES STAC
    # -------------------------------------------------------
    assets = product.get("assets", {})

    if "B04" not in assets:
        st.error("❌ Bande B04 absente")
        st.write("Assets :", list(assets.keys()))
        st.stop()

    if "B08" not in assets:
        st.error("❌ Bande B08 absente")
        st.write("Assets :", list(assets.keys()))
        st.stop()

    url_B04 = assets["B04"]["href"]
    url_B08 = assets["B08"]["href"]

    # -----------------------------
    # 4 – Téléchargement B04 / B08
    # -----------------------------
    st.info("Téléchargement des bandes B04 et B08…")

    try:
        red_path = download_s2_band(url_B04)
        nir_path = download_s2_band(url_B08)
    except Exception as e:
        st.error("❌ Erreur lors du téléchargement des bandes.")
        st.write(str(e))
        st.stop()

    st.write("✅ DEBUG : bandes téléchargées")

    # -----------------------------
    # 5 – NDVI
    # -----------------------------
    st.info("Calcul du NDVI…")

    try:
        ndvi_array, transform = compute_ndvi(red_path, nir_path)
    except Exception as e:
        st.error("❌ Erreur dans compute_ndvi.")
        st.write(str(e))
        st.stop()

    st.success("✅ NDVI calculé")

    # -----------------------------
    # 6 – NDVI moyen par parcelle
    # -----------------------------
    st.info("Calcul NDVI moyen par parcelle…")

    try:
        gdf = compute_zonal_stats(gdf, ndvi_array, transform)
    except Exception as e:
        st.error("❌ Erreur dans compute_zonal_stats.")
        st.write(str(e))
        st.stop()

    st.success("✅ Calcul NDVI terminé")

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
