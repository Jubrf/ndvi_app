# 🌱 Application NDVI – Sentinel‑2 (gratuit)

Cette application Streamlit permet :

✅ Upload des parcelles (SHP/ZIP ou GeoJSON)  
✅ Reprojection automatique en WGS84  
✅ Recherche automatique de la dernière image Sentinel‑2 L2A  
✅ Téléchargement des bandes B04/B08  
✅ Calcul du NDVI  
✅ Statistiques NDVI par parcelle  
✅ Carte NDVI interactive  
✅ Export CSV des résultats  

---

# 🚀 Déploiement sur Streamlit Cloud

## 1. Configurer les secrets

Dans **Settings → Secrets** de Streamlit Cloud :

```toml
COPERNICUS_USER = "votre_email_copernicus"
COPERNICUS_PASS = "votre_mot_de_passe"
