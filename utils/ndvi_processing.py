import numpy as np
import rasterio
from shapely.geometry import shape
import pyogrio

def load_vector_file(file):
    """
    Lecture SHP ou GeoJSON via pyogrio.
    Retourne un dict {features: [...]} structure GeoJSON-like.
    """
    gdf = pyogrio.read_dataframe(file)

    # Forcer WGS84 si possible
    if gdf.crs is not None:
        if gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(4326)

    features = []
    for _, row in gdf.iterrows():
        geom = shape(row.geometry)
        features.append({
            "geometry": geom.__geo_interface__,
            "properties": {}
        })

    return {"features": features, "geometry": gdf.geometry}

def compute_ndvi(red_path, nir_path):
    with rasterio.open(red_path) as red_src, rasterio.open(nir_path) as nir_src:
        red = red_src.read(1).astype("float32")
        nir = nir_src.read(1).astype("float32")

        ndvi = (nir - red) / (nir + red)
        ndvi[np.isinf(ndvi)] = np.nan

        transform = red_src.transform

    return ndvi, transform

def compute_zonal_stats(gdf, ndvi_array, transform):
    """
    Zonal stats manuel : NDVI moyen par polygone.
    On échantillonne les pixels intersectant le polygone.
    """

    height, width = ndvi_array.shape
    ndvi_results = []

    for feat in gdf["features"]:
        geom = shape(feat["geometry"])
        xs = []
        ys = []

        # On récupère toutes les coordonnées dans l’enveloppe du polygone
        minx, miny, maxx, maxy = geom.bounds

        # Calcul indices pixel
        row_min, col_min = ~transform * (minx, maxy)
        row_max, col_max = ~transform * (maxx, miny)

        row_min = max(0, int(row_min))
        row_max = min(height - 1, int(row_max))
        col_min = max(0, int(col_min))
        col_max = min(width - 1, int(col_max))

        values = []

        for row in range(row_min, row_max + 1):
            for col in range(col_min, col_max + 1):
                # coord du pixel
                x, y = transform * (col + 0.5, row + 0.5)
                if geom.contains(shape({"type": "Point", "coordinates": (x, y)})):
                    val = ndvi_array[row, col]
                    if not np.isnan(val):
                        values.append(val)

        ndvi_mean = float(np.mean(values)) if len(values) else None
        feat["properties"]["NDVI"] = ndvi_mean

        ndvi_results.append(ndvi_mean)

    return gdf
