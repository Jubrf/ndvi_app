import numpy as np
import rasterio
import tempfile
from shapely.geometry import shape
from shapely.ops import transform
import pyogrio
import pyproj


def save_uploaded_file_to_temp(uploaded):
    """Sauvegarde un fichier UploadStreamlit dans un vrai fichier temporaire."""
    suffix = ".zip" if uploaded.name.endswith(".zip") else ".geojson"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded.getbuffer())
    tmp.close()
    return tmp.name


def load_vector_file(uploaded):
    """
    Lecture universelle SHP (ZIP) ou GeoJSON via pyogrio.
    Compatible Streamlit Cloud.
    """
    path = save_uploaded_file_to_temp(uploaded)

    # Cas GEOJSON direct → shapely convertit tout seul
    if path.endswith(".geojson"):
        import json
        with open(path, "r") as f:
            gj = json.load(f)

        features = []
        for feat in gj["features"]:
            geom = shape(feat["geometry"])
            features.append({
                "geometry": geom.__geo_interface__,
                "properties": {}
            })
        return {"features": features}

    # Cas ZIP SHP → pyogrio list_layers / read_features
    layers = pyogrio.list_layers(path)
    layer_name = layers[0][0]  # 1er layer du shapefile

    geoms = []
    crs = None

    for feat in pyogrio.read_features(path, layer=layer_name):
        geom = shape(feat["geometry"])
        geoms.append(geom)

        if crs is None:
            info = pyogrio.read_info(path, layer=layer_name)
            crs = info["crs"]

    # Reprojection vers EPSG:4326 si nécessaire
    if crs and crs != "EPSG:4326":
        src = pyproj.CRS.from_user_input(crs)
        dst = pyproj.CRS.from_epsg(4326)
        transformer = pyproj.Transformer.from_crs(src, dst, always_xy=True).transform
        geoms = [transform(transformer, g) for g in geoms]

    # Construire GeoJSON-like
    features = []
    for g in geoms:
        features.append({
            "geometry": g.__geo_interface__,
            "properties": {}
        })

    return {"features": features}


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
    Zonal stats minimaliste compatible Streamlit Cloud.
    """
    height, width = ndvi_array.shape

    for feat in gdf["features"]:
        geom = shape(feat["geometry"])
        minx, miny, maxx, maxy = geom.bounds

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
                if geom.contains(shape({"type": "Point", "coordinates": (x, y)})):
                    v = ndvi_array[row, col]
                    if not np.isnan(v):
                        values.append(v)

        feat["properties"]["NDVI"] = float(np.mean(values)) if values else None

    return gdf
