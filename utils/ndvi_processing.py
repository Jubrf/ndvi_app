import numpy as np
import rasterio
import tempfile
import os
from shapely.geometry import shape
from shapely.ops import transform
import pyogrio
import pyproj


def save_uploaded_file_to_temp(uploaded):
    """Enregistre un Streamlit UploadedFile dans un fichier temporaire et retourne son chemin."""
    suffix = ".zip" if uploaded.name.endswith(".zip") else ".geojson"
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp.write(uploaded.getbuffer())
    temp.close()
    return temp.name


def load_vector_file(file):
    """
    Lecture SHP ZIP ou GeoJSON via pyogrio.read_vector().
    Compatible Streamlit Cloud.
    """
    # 1) Enregistrer le fichier uploadé dans un fichier temporaire
    path = save_uploaded_file_to_temp(file)

    # 2) Lecture via pyogrio (retourne tableau + géométries)
    data = pyogrio.read_vector(path)

    geometries = data["geometry"]
    crs = data["crs"]

    # 3) Reprojection si nécessaire → EPSG:4326
    if crs is not None and crs != "EPSG:4326":
        src = pyproj.CRS.from_user_input(crs)
        dst = pyproj.CRS.from_epsg(4326)
        transformer = pyproj.Transformer.from_crs(src, dst, always_xy=True).transform

        geometries = [transform(transformer, g) for g in geometries]

    # 4) Construire structure GeoJSON-like
    features = []
    for geom in geometries:
        features.append({
            "geometry": geom.__geo_interface__,
            "properties": {}
        })

    return {"features": features}


def compute_ndvi(red_path, nir_path):
    """
    Calcul NDVI à partir des bandes Sentinel-2.
    """
    with rasterio.open(red_path) as red_src, rasterio.open(nir_path) as nir_src:
        red = red_src.read(1).astype("float32")
        nir = nir_src.read(1).astype("float32")

        ndvi = (nir - red) / (nir + red)
        ndvi[np.isinf(ndvi)] = np.nan

        transform = red_src.transform

    return ndvi, transform


def compute_zonal_stats(gdf, ndvi_array, transform):
    """
    Zonal statistics sans rasterstats.
    Calcule le NDVI moyen par polygone.
    """
    height, width = ndvi_array.shape

    for feat in gdf["features"]:
        geom = shape(feat["geometry"])

        minx, miny, maxx, maxy = geom.bounds

        # Convertir coordonnées en indices raster
        row_min, col_min = ~transform * (minx, maxy)
        row_max, col_max = ~transform * (maxx, miny)

        row_min = max(0, int(row_min))
        col_min = max(0, int(col_min))
        row_max = min(height - 1, int(row_max))
        col_max = min(width - 1, int(col_max))

        values = []

        for row in range(row_min, row_max + 1):
            for col in range(col_min, col_max + 1):
                x, y = transform * (col + 0.5, row + 0.5)

                if geom.contains(shape({
                    "type": "Point",
                    "coordinates": (x, y)
                })):
                    v = ndvi_array[row, col]
                    if not np.isnan(v):
                        values.append(v)

        feat["properties"]["NDVI"] = float(np.mean(values)) if values else None

    return gdf
