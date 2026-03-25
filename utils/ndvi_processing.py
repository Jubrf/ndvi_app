import rasterio
import numpy as np
from rasterstats import zonal_stats

def compute_ndvi(red_path, nir_path):
    """
    Calcule le NDVI à partir des bandes B04 (rouge) et B08 (NIR)
    """

    with rasterio.open(red_path) as red_src, rasterio.open(nir_path) as nir_src:
        red = red_src.read(1).astype("float32")
        nir = nir_src.read(1).astype("float32")

        ndvi = (nir - red) / (nir + red)
        ndvi[np.isinf(ndvi)] = np.nan

        affine = red_src.transform

    return ndvi, affine


def compute_zonal_ndvi(gdf, ndvi_array, affine):
    """
    Calcule le NDVI moyen par parcelle via zonal statistics.
    """

    stats = zonal_stats(
        gdf,
        ndvi_array,
        affine=affine,
        stats=["mean"],
        nodata=np.nan
    )

    gdf["NDVI"] = [s["mean"] for s in stats]
    return gdf
