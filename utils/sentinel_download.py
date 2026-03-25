import requests
import tempfile
import streamlit as st

def download_s2_band(product_id, band):
    """
    Télécharge une bande (JP2) du produit Sentinel-2.
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
