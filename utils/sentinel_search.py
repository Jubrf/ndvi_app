import requests
import streamlit as st

def find_latest_s2_product(bbox):
    minx, miny, maxx, maxy = bbox

    poly = (
        f"POLYGON(({minx} {miny}, {maxx} {miny}, "
        f"{maxx} {maxy}, {minx} {maxy}, {minx} {miny}))"
    )

    url = (
        "https://catalogue.dataspace.copernicus.eu/odata/v1/Products?"
        f"$filter=Collection/Name eq 'SENTINEL-2' "
        f"and OData.CSC.Intersects(area=geometry'{poly}') "
        f"and Attributes/OData.CSC.DoubleAttribute/any(att: att/Name eq 'cloudCover' and att/Value lt 40)"
        "&$orderby=ContentDate/Start desc"
        "&$top=1"
    )

    r = requests.get(
        url,
        auth=(st.secrets["CDSE_USER"], st.secrets["CDSE_PASS"])
    )

    try:
    data = r.json()
    return data["value"][0] if data.get("value") else None
except Exception:
    st.error("❌ L’API Copernicus n’a pas renvoyé du JSON.")
    st.write("➡️ Code HTTP :", r.status_code)
    st.write("➡️ Réponse (début) :", r.text[:500])
    return None

    if "value" not in data or len(data["value"]) == 0:
        return None

    return data["value"][0]
