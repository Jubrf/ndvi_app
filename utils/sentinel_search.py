import requests
import streamlit as st


def find_latest_s2_product(bbox):
    """
    Recherche la dernière image Sentinel‑2 correspondant à la BBOX.
    Retourne un dictionnaire de produit ou None.
    """

    minx, miny, maxx, maxy = bbox

    # Construction du POLYGON WKT pour l’API OData
    poly = (
        f"POLYGON(({minx} {miny}, "
        f"{maxx} {miny}, "
        f"{maxx} {maxy}, "
        f"{minx} {maxy}, "
        f"{minx} {miny}))"
    )

    # URL OData Copernicus
    url = (
        "https://catalogue.dataspace.copernicus.eu/odata/v1/Products?"
        f"$filter=Collection/Name eq 'SENTINEL-2' "
        f"and OData.CSC.Intersects(area=geometry'{poly}') "
        f"and Attributes/OData.CSC.DoubleAttribute/any(att: att/Name eq 'cloudCover' and att/Value lt 50)"
        "&$orderby=ContentDate/Start desc"
        "&$top=1"
    )

    # Auth via secrets Streamlit
    user = st.secrets.get("CDSE_USER")
    pwd = st.secrets.get("CDSE_PASS")

    if not user or not pwd:
        st.error("❌ Aucun identifiant CDSE_USER / CDSE_PASS n’est disponible dans les secrets.")
        return None

    r = requests.get(url, auth=(user, pwd))

    # Bloc diagnostic pour afficher les erreurs API
    try:
        data = r.json()
    except Exception:
        st.error("❌ L’API Copernicus n’a pas renvoyé du JSON (erreur d’API).")
        st.write("➡️ Code HTTP :", r.status_code)
        st.write("➡️ Réponse (début) :", r.text[:500])
        return None

    if "value" not in data or len(data["value"]) == 0:
        return None

    return data["value"][0]
