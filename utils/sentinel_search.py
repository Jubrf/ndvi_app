import requests
import streamlit as st


def find_latest_s2_product(bbox):
    """
    Recherche du dernier produit Sentinel‑2 L2A via Copernicus Data Space.
    BBOX : (minx, miny, maxx, maxy) en WGS84.
    Retourne un dictionnaire ou None.
    """

    minx, miny, maxx, maxy = bbox

    # ✅ Construction du POLYGON WKT (format strict accepté par CDS-E)
    poly = (
        f"SRID=4326;POLYGON(({minx} {miny}, "
        f"{maxx} {miny}, "
        f"{maxx} {maxy}, "
        f"{minx} {maxy}, "
        f"{minx} {miny}))"
    )

    # ✅ URL OData (cloudCover jusqu’à 80 → plus souple)
    url = (
        "https://catalogue.dataspace.copernicus.eu/odata/v1/Products?"
        "$filter="
        "Collection/Name eq 'SENTINEL-2' "
        f"and OData.CSC.Intersects(area=geography'{poly}') "
        "and Attributes/OData.CSC.DoubleAttribute/any(att: att/Name eq 'cloudCover' and att/Value lt 80)"
        "&$orderby=ContentDate/Start desc"
        "&$top=1"
    )

    # ✅ Lecture des secrets
    user = st.secrets.get("CDSE_USER")
    pwd = st.secrets.get("CDSE_PASS")

    if not user or not pwd:
        st.error("❌ Secrets API non trouvés (CDSE_USER / CDSE_PASS).")
        return None

    # ✅ Appel API
    r = requests.get(url, auth=(user, pwd))

    # ✅ TRAITEMENT DES ERREURS : on affiche la vraie réponse (utile pour debug)
    if r.status_code != 200:
        st.error("❌ L’API Copernicus a renvoyé une erreur.")
        st.write("➡️ Code HTTP :", r.status_code)
        st.write("➡️ Réponse brute (début) :", r.text[:500])
        return None

    # ✅ Tentative de lecture JSON
    try:
        data = r.json()
    except Exception:
        st.error("❌ Réponse non JSON. Erreur inattendue de l’API.")
        st.write("➡️ Code HTTP :", r.status_code)
        st.write("➡️ Réponse brute (début) :", r.text[:500])
        return None

    # ✅ Vérification du contenu
    if "value" not in data or len(data["value"]) == 0:
        st.warning("⚠️ Aucun produit Sentinel‑2 trouvé dans cette zone.")
        return None

    return data["value"][0]  # ✅ On retourne le produit trouvé
