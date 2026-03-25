import requests
import tempfile
import streamlit as st


def download_s2_band(asset_url):
    """
    Télécharge une bande Sentinel‑2 (B04, B08, etc.) depuis une URL STAC.
    
    ✅ asset_url : URL directe STAC de la bande (href)
    ✅ Retourne : chemin local du fichier JP2 téléchargé
    
    Compatible Streamlit Cloud.
    """

    user = st.secrets.get("CDSE_USER")
    pwd = st.secrets.get("CDSE_PASS")

    if not user or not pwd:
        st.error("❌ Identifiants API manquants (CDSE_USER / CDSE_PASS).")
        return None

    # Requête HTTP authentifiée
    r = requests.get(asset_url, auth=(user, pwd), stream=True)

    if r.status_code != 200:
        st.error(f"❌ Erreur lors du téléchargement de l’asset (HTTP {r.status_code})")
        st.write("➡️ URL :", asset_url)
        st.write("➡️ Réponse :", r.text[:300])
        return None

    # Enregistrer dans un fichier temporaire
    suffix = ".jp2"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)

    for chunk in r.iter_content(chunk_size=8192):
        if chunk:
            tmp.write(chunk)

    tmp.close()

    return tmp.name
