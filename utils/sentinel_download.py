import requests
import tempfile
import streamlit as st

def download_s2_band(product_id, band):
    """
    Télécharge une bande Sentinel‑2 du produit choisi (JP2 10 m).
    Exemple : band="B04" ou "B08".
    """

    url = (
        f"https://dataspace.copernicus.eu/odata/v1/Products({product_id})/"
        f"$value/GRANULE/*/IMG_DATA/R10m/{band}.jp2"
    )

    r = requests.get(
        url,
        auth=(st.secrets["COPERNICUS_USER"], st.secrets["COPERNICUS_PASS"])
    )

    tmp = tempfile.NamedTemporaryFile(suffix=".jp2", delete=False)
    tmp.write(r.content)
    tmp.close()
    return tmp.name
