import requests
import streamlit as st

STAC_URL = "https://catalogue.dataspace.copernicus.eu/stac/search"

def find_latest_s2_product(bbox):
    minx, miny, maxx, maxy = bbox

    body = {
        "collections": ["sentinel-2-l2a"],
        "bbox": [minx, miny, maxx, maxy],
        "limit": 1,
        "sortby": [{"field": "properties.datetime", "direction": "desc"}]
    }

    user = st.secrets.get("CDSE_USER")
    pwd = st.secrets.get("CDSE_PASS")

    if not user or not pwd:
        st.error("❌ Identifiants API manquants (CDSE_USER / CDSE_PASS)")
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
        st.warning("⚠️ Aucun produit Sentinel‑2 trouvé pour cette zone.")
        return None

    return data["features"][0]
