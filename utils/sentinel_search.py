import requests
import streamlit as st
from datetime import datetime, timedelta

STAC_URL = "https://catalogue.dataspace.copernicus.eu/stac/search"

def find_latest_s2_product(bbox):
    minx, miny, maxx, maxy = bbox

    # ✅ Stratégie Kermap : on teste plusieurs fenêtres temporelles décroissantes
    windows = [
        10,   # d’abord 10 jours
        20,   # puis 20
        30,   # puis 30
        60    # maximum 60 jours (pour garantir un produit NDVI)
    ]

    user = st.secrets.get("CDSE_USER")
    pwd = st.secrets.get("CDSE_PASS")

    if not user or not pwd:
        st.error("❌ Secrets API manquants (CDSE_USER / CDSE_PASS).")
        return None

    for w in windows:
        # ✅ Intervalle temporel dynamique
        today = datetime.utcnow()
        start = today - timedelta(days=w)

        time_range = f"{start.strftime('%Y-%m-%dT00:00:00Z')}/{today.strftime('%Y-%m-%dT23:59:59Z')}"

        st.write(f"🔎 Recherche d’images L2A sur les {w} derniers jours…")

        body = {
            "collections": ["sentinel-2-l2a"],
            "bbox": [minx, miny, maxx, maxy],
            "limit": 10,   # ✅ On récupère les 10 dernières images, Kermap-style
            "time": time_range,
            "sortby": [{"field": "properties.datetime", "direction": "desc"}]
        }

        r = requests.post(STAC_URL, json=body, auth=(user, pwd))

        if r.status_code != 200:
            st.write(f"⚠️ Erreur HTTP {r.status_code} pour fenêtre {w} jours :")
            st.write(r.text[:300])
            continue

        try:
            data = r.json()
        except:
            st.write("⚠️ Réponse STAC non JSON")
            continue

        if "features" not in data or len(data["features"]) == 0:
            st.write(f"⚠️ Aucune image dans les {w} derniers jours.")
            continue

        # ✅ Stratégie Kermap : ne garder QUE les tuiles qui ont B04 & B08
        for feat in data["features"]:
            assets = feat.get("assets", {})
            if "B04" in assets and "B08" in assets:
                st.write(f"✅ Tuile valide trouvée ({w} jours max)")
                return feat

        st.write(f"⚠️ Images trouvées mais sans bandes B04/B08 pour {w} jours.")

    # ✅ Si rien trouvé même sur 60 jours
    st.warning("❌ Aucune tuile NDVI exploitable (L2A avec B04/B08) trouvée sur 60 jours.")
    return None
