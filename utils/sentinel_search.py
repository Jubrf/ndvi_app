import requests
import streamlit as st
from datetime import datetime, timedelta

STAC_URL = "https://catalogue.dataspace.copernicus.eu/stac/search"

def find_latest_s2_product(bbox):
    minx, miny, maxx, maxy = bbox

    # Fenêtre temporelle : 10 jours
    today = datetime.utcnow()
    start = today - timedelta(days=10)

    time_range = f"{start.strftime('%Y-%m-%dT00:00:00Z')}/{today.strftime('%Y-%m-%dT23:59:59Z')}"

    body = {
        "collections": ["sentinel-2-l2a"],     # ✅ forcé à L2A
        "bbox": [minx, miny, maxx, maxy],
        "limit": 5,                             # ✅ on prend les 5 derniers produits
        "time": time_range,
        "sortby": [{"field": "properties.datetime", "direction": "desc"}]
    }

    user = st.secrets.get("CDSE_USER")
    pwd = st.secrets.get("CDSE_PASS")

    r = requests.post(STAC_URL, json=body, auth=(user, pwd))

    if r.status_code != 200:
        st.error(f"❌ Erreur API STAC (HTTP {r.status_code})")
        st.write(r.text[:500])
        return None

    try:
        data = r.json()
    except:
        st.error("❌ STAC a renvoyé un format non JSON")
        st.write(r.text[:300])
        return None

    if "features" not in data or len(data["features"]) == 0:
        st.warning("⚠️ Aucun Sentinel‑2 L2A trouvé.")
        return None

    # ✅ On boucle sur les produits les plus récents jusqu’à trouver un produit avec B04 et B08
    for feat in data["features"]:
        assets = feat.get("assets", {})
        if "B04" in assets and "B08" in assets:
            return feat  # ✅ produit complet trouvé

    # Si aucun produit n'a les bonnes bandes
    st.warning("⚠️ Aucune tuile récente ne contient B04/B08 dans cette zone.")
    return None
