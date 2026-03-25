import numpy as np
import rasterio
from shapely.geometry import shape
import pyogrio

def load_vector_file(file):
    """
    Lecture SHP ou GeoJSON via pyogrio.read_vector (PAS read_dataframe).
    Retourne un objet GeoJSON-like {features: [...]}
    compatible sans GeoPandas.
    """

    # Lecture sans GeoPandas
    data = pyogrio.read_vector(file)

    geometries = data["geometry"]
    crs = data["crs"]
    features = []

    # Reprojection éventuelle
    # -----------------------
    # pyogrio.read_vector donne toujours des géométries Shapely,
    # mais si la couche n’est pas en EPSG:4326, on doit la reprojeter.
    if crs is not None and crs != "EPSG:4326":
        # Reprojection Shapely SANS GeoPandas → via pyproj
        import pyproj
        from shapely.ops import transform

        src = pyproj.CRS.from_user_input(crs)
        dst = pyproj.CRS.from_epsg(4326)
        proj = pyproj.Transformer.from_crs(src, dst, always_xy=True).transform

        geometries = [transform(proj, geom) for geom in geometries]

    # Construction de la structure GeoJSON-like
    for geom in geometries:
        features.append({
            "geometry": geom.__geo_interface__,
            "properties": {}
        })

    return {"features": features}


def compute_ndvi(red_path, nir_path):
    """
    Calcule le NDVI
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
    Zonal statistics sans rasterstats (incompatible Streamlit Cloud).
    Échantillonne les pixels du NDVI dans chaque polygone.
    """
    height, width = ndvi_array.shape

    for feat in gdf["features"]:
        geom = shape(feat["geometry"])
        minx, miny, maxx, maxy = geom.bounds

        # Calcul indices pixels
        row_min, col_min = ~transform * (minx, maxy)
        row_max, col_max = ~transform * (maxx, miny)

        row_min = max(0, int(row_min))
        row_max = min(height - 1, int(row_max))
        col_min = max(0, int(col_min))
        col_max = min(width - 1, int(col_max))

        values = []

        for row in range(row_min, row_max + 1):
            for col in range(col_min, col_max + 1):
                x, y = transform * (col + 0.5, row + 0.5)
                if geom.contains(shape({"type": "Point", "coordinates": (x, y)})):
                    val = ndvi_array[row, col]
                    if not np.isnan(val):
                        values.append(val)

        feat["properties"]["NDVI"] = float(np.mean(values)) if values else None

    return gdf
