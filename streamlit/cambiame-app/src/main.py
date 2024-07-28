from pathlib import Path
from typing import IO

import ee
import geopandas as gpd
import xarray as xr

from .config import FILES_DATA_PATH
from .utils import load_geojson_file, download_elevation_and_slope_30m, download_drainage_30m, download_land_usage_30m


class CambiumTakeHomeChallenge:

    def __init__(self,
                 area_of_interest_geojson_filename: Path = None,
                 area_of_interest_geojson_file: IO = None):
        """

        :param area_of_interest_geojson_filename:
        :param area_of_interest_geojson_file:
        """

        ee.Initialize()  # This starts the ee engine

        # Load and save area of interest information
        if area_of_interest_geojson_filename:
            self.project_name: str = area_of_interest_geojson_filename.name.split("_")[0]
        else:
            self.project_name: str = "no_name_provided"
        if area_of_interest_geojson_file:
            area_of_interest_info: tuple = load_geojson_file(filename=area_of_interest_geojson_file)
            self.area_of_interest_geojson_file: gpd.GeoDataFrame = area_of_interest_info[0]
            self.area_of_interest_bounds: tuple = area_of_interest_info[1]
        elif area_of_interest_geojson_filename:
            area_of_interest_info: tuple = load_geojson_file(filename=area_of_interest_geojson_filename)
            self.area_of_interest_geojson_file: gpd.GeoDataFrame = area_of_interest_info[0]
            self.area_of_interest_bounds: tuple = area_of_interest_info[1]
        else:
            raise "No file nor filename provided, data will not be downloaded"

        # Create ee geometry based on bounds
        self.area_ee_geometry = ee.Geometry.Rectangle(*self.area_of_interest_bounds)
        # Based on file provided, create data structure and start downloading or re-using files
        self.files_project_path: Path = Path(FILES_DATA_PATH, self.project_name)
        self.files_project_path.mkdir(parents=True, exist_ok=True)

        # Define all xarray and ee datasets that will be downloaded
        self.elevation_raster: xr.Dataset = None
        self.elevation_xarray: xr.Dataset = None
        self.drainage_ee: ee.ImageCollection = None
        self.drainage_xarray: xr.Dataset = None
        self.land_usage_ee: ee.ImageCollection = None
        self.land_usage_xarray: xr.Dataset = None
        self.argentina_protected_area = gpd.read_file(filename=Path(FILES_DATA_PATH, "area_protegida.json"))

        # Download or load all data
        self.load_all_geospatial_data()

    def load_all_geospatial_data(self, exists=False):
        self.elevation_raster, self.elevation_xarray = download_elevation_and_slope_30m(
            bbox=self.area_of_interest_bounds
        )
        self.drainage_ee, self.drainage_xarray = download_drainage_30m(
            geometry=self.area_ee_geometry,
            path_to_xarray=Path(self.files_project_path, f"{self.project_name}_drainage.nc")
        )
        self.land_usage_ee, self.land_usage_xarray = download_land_usage_30m(
            geometry=self.area_ee_geometry,
            path_to_xarray=Path(self.files_project_path, f"{self.project_name}_land_usage.nc")
        )
