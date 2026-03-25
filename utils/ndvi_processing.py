import numpy as np
import rasterio
import tempfile
import os
import shapefile  # pyshp
from shapely.geometry import shape
from shapely.ops import transform
import pyproj
import json
import zipfile


def save_uploaded_file_to_temp(uploaded):
    """Save uploaded file into a temporary location."""
    suffix = ".zip" if uploaded.name.endswith(".zip") else ".geojson"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded.getbuffer())
    tmp.close()
    return tmp.name


def load_vector_file(uploaded):
    """
    Universal loader for:
    - SHP inside ZIP (using pyshp)
    - GEOJSON
    Compatible Streamlit Cloud (no GDAL, no Fiona, no GeoPandas)
    """

    path = save_uploaded_file_to_temp(uploaded)

    # CASE 1 : GEOJSON
    if path.endswith(".geojson"):
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

    # CASE 2 : ZIP (contains SHP)
    if path.endswith(".zip"):
        with zipfile.ZipFile(path, "r") as z:
            extract_dir = tempfile.mkdtemp()
            z.extractall(extract_dir)

        # find .shp inside extracted folder
        shp_path = None
        for f in os.listdir(extract_dir):
            if f.endswith(".shp"):
                shp_path = os.path.join(extract_dir, f)
                break

        if shp_path is None:
            raise ValueError("ZIP uploaded but no .shp file inside")

        # Read shapefile (pyshp)
        sf = shapefile.Reader(shp_path)
        shapes = sf.shapes()

        geoms = [shape(s.__geo_interface__) for s in shapes]

        # Read projection if exists
        prj_path = shp_path.replace(".shp", ".prj")
        crs = None
        if os.path.exists(prj_path):
            with open(prj_path, "r") as f:
                wkt = f.read()
            try:
                crs = pyproj.CRS.from_wkt(wkt)
            except:
                crs = None

        # Reproject if needed
        if crs and crs.to_epsg() != 4326:
            dst = pyproj.CRS.from_epsg(4326)
            transformer = pyproj.Transformer.from_crs(crs, dst, always_xy=True).transform
            geoms = [transform(transformer, g) for g in geoms]

        # Build features
        features = []
        for g in geoms:
            features.append({
                "geometry": g.__geo_interface__,
                "properties": {}
            })

        return {"features": features}

    raise ValueError("Format de fichier non reconnu (doit être .geojson ou .zip contenant SHP)")


def compute_ndvi(red_path, nir_path):
    with rasterio.open(red_path) as red_src, rasterio.open(nir_path) as nir_src:
        red = red_src.read(1).astype("float32")
        nir = nir_src.read(1).astype("float32")

        ndvi = (nir - red) / (nir + red)
        ndvi[np.isinf(ndvi)] = np.nan

        transform = red_src.transform

    return ndvi, transform


def compute_zonal_stats(gdf, ndvi_array, transform):
    height, width = ndvi_array.shape

    for feat in gdf["features"]:
        geom = shape(feat["geometry"])
        minx, miny, maxx, maxy = geom.bounds

        # coords → raster indices
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
