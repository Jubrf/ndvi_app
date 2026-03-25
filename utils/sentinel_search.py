import requests
import streamlit as st
from datetime import datetime, timedelta

STAC_URL = "https://catalogue.dataspace.copernicus.eu/stac/search"

def find_latest_s2_product(bbox):
    minx, miny, maxx, maxy = bbox

    # ✅ Fenêtre temporelle : 30 jours avant aujourd’hui
    today = datetime.utcnow()
    start = today - timedelta(days=30)

    time_range = f"{start.strftime('%Y-%m-%dT00:00:00Z')}/{today.strftime('%Y-%m-%dT23:59:59Z')}"

    body = {
        "collections": ["sentinel-2-l2a"],
        "bbox": [minx, miny, maxx, maxy],
        "limit": 1,
        "time": time_range,   # ✅ filtre temporel ajouté
        "sortby": [{"field": "properties.datetime", "direction": "desc"}]
    }

    user = st.secrets.get("CDSE_USER")
    pwd = st.secrets.get("CDSE_PASS")

    if not user or not pwd:
        st.error("❌ Identifiants API manquants.")
        return None

    r = requests.post(STAC_URL, json=body, auth=(user, pwd))

    if r.status_code != 200:
        st.error(f"❌ Erreur API STAC (HTTP {r.status_code})")
        st.write("Réponse :", r.text[:500])
        return None

    try:
        data = r.json()
    except:
        st.error("❌ Réponse STAC non JSON")
        st.write("Réponse brute :", r.text[:500])
        return None

    if "features" not in data or len(data["features"]) == 0:
        st.warning("⚠️ Aucun produit Sentinel‑2 trouvé dans les 30 derniers jours.")
        return None

    return data["features"][0]
