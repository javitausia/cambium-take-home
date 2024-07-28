import ee
import geemap
import geopandas as gpd
import numpy as np
import planetary_computer
import rioxarray
import xarray as xr
from pystac_client import Client


def meters_to_degrees(lat, meters):
    """
    Convert meters to degrees of latitude and longitude at a given latitude.

    Parameters:
    lat (float): Latitude in degrees where the conversion is to be calculated.

    Returns:
    tuple: (degrees_lat_per_meter, degrees_lon_per_meter)
           Conversion factors for latitude and longitude.
    """
    # Earth radius in meters
    R = 6378137

    # Latitude conversion (constant value)
    degrees_lat_per_meter = 1 / 111320 * meters

    # Longitude conversion (varies with latitude)
    degrees_lon_per_meter = 1 / (111320 * np.cos(np.radians(lat))) * meters

    return degrees_lat_per_meter, degrees_lon_per_meter


def load_geojson_file(filename):
    geojson_df = gpd.read_file(filename=filename)
    return (
        geojson_df,
        geojson_df.iloc[0].geometry.bounds
    )


def get_elevation_and_slope_dataset(signed_asset_href):
    # Create rioxarray dataset based on link
    elevation = rioxarray.open_rasterio(signed_asset_href).isel(band=0)
    elevation = elevation.sortby(["x", "y"])
    # Calculate the gradient in the x and y directions
    dx, dy = np.gradient(elevation, axis=(1, 0))
    # Calculate the slope
    slope = np.sqrt(dx ** 2 + dy ** 2)
    # Convert the slope to degrees
    slope_degrees = np.arctan(slope) * (180 / np.pi)
    # Create a binary variable where 1 indicates abs(slope) > 1
    binary_slope = (np.abs(slope) > 1).astype(int)
    # Create xarray DataArrays for the calculated variables
    slope_da = xr.DataArray(slope, dims=elevation.dims, coords=elevation.coords, name='slope')
    slope_degrees_da = xr.DataArray(slope_degrees, dims=elevation.dims, coords=elevation.coords, name='slope_degrees')
    binary_slope_da = xr.DataArray(binary_slope, dims=elevation.dims, coords=elevation.coords, name='binary_slope')
    # Combine all variables into a single dataset
    combined_ds = xr.Dataset({
        'elevation': elevation,
        'slope': slope_da,
        'slope_degrees': slope_degrees_da,
        'binary_slope': binary_slope_da
    })
    return elevation, combined_ds


def download_elevation_and_slope_30m(bbox):
    # First, open a Client session
    client = Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        ignore_conformance=True,
    )
    search = client.search(
        collections=["alos-dem"],
        bbox=bbox
    )
    items = list(search.get_items())
    item = items[0]
    signed_asset = planetary_computer.sign(item.assets["data"])
    elevation, combined_dataset = get_elevation_and_slope_dataset(signed_asset_href=signed_asset.href)
    return elevation, combined_dataset


def download_drainage_30m(geometry, path_to_xarray=None):
    # TODO: check lat lon meters conversion
    centroid_lat = geometry.centroid().getInfo()["coordinates"][0]
    degrees_lat, degrees_lon = meters_to_degrees(lat=centroid_lat, meters=30)
    drainage_ee = ee.ImageCollection("users/gena/global-hand/hand-100").filterBounds(geometry).mosaic()
    if path_to_xarray.exists():
        drainage_xarray = xr.open_dataarray(path_to_xarray)
    else:
        drainage_xarray = geemap.ee_to_xarray(drainage_ee, geometry=geometry, scale=degrees_lat).drop_vars("time")
        drainage_xarray = drainage_xarray.sortby(["lon", "lat"])
        drainage_xarray.to_netcdf(path=path_to_xarray)
    return drainage_ee, drainage_xarray


def download_land_usage_30m(geometry, path_to_xarray=None):
    # TODO: check lat lon meters conversion
    centroid_lat = geometry.centroid().getInfo()["coordinates"][0]
    degrees_lat, degrees_lon = meters_to_degrees(lat=centroid_lat, meters=30)
    land_usage_ee = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
    land_usage_ee_filtered = land_usage_ee.select("label").filterBounds(geometry).filterDate("2019-12-01", "2020-01-01")
    if path_to_xarray.exists():
        land_usage_xarray = xr.open_dataset(path_to_xarray)
    else:
        land_usage_xarray = geemap.ee_to_xarray(land_usage_ee_filtered, geometry=geometry, scale=degrees_lat)
        land_usage_xarray = land_usage_xarray.sortby(["lon", "lat"])
        land_usage_xarray.to_netcdf(path=path_to_xarray)
    return land_usage_ee.filterBounds(geometry), land_usage_xarray
