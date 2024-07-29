from pathlib import Path
from typing import IO

import ee
import geopandas as gpd
import xarray as xr
from shapely.geometry import box
from shapely.geometry.polygon import Polygon

from .config import FILES_DATA_PATH, EARTHENGINE_PROJECT
from .utils import load_geojson_file, download_elevation_and_slope_30m, download_drainage_30m, \
    download_land_usage_30m


def get_final_score_for_area(row):
    if row["intersects_protected_area"]:
        return 0
    else:
        return (
                row["good_slopes_percentage"] + row["good_drainage_percentage"] + row["good_land_usage_percentage"]
        ) / 3.0


def get_final_label_for_area(row):
    if row["final_score"] < 30:
        return "Low"
    elif row["final_score"] < 70:
        return "Medium"
    else:
        return "High"


def get_final_color_for_area(row):
    if row["final_score"] < 30:
        return "red"
    elif row["final_score"] < 70:
        return "orange"
    else:
        return "green"


class CambiumTakeHomeChallenge:
    drainage_palette = [
        '#0000FF',  # Blue for water (0)
        '#00FF00',  # Green
        '#7FFF00',  # Chartreuse
        '#FFFF00',  # Yellow
        '#FFA500',  # Orange
        '#FF4500',  # OrangeRed
        '#FF0000'  # Red for highest values
    ]

    def __init__(self,
                 area_of_interest_geojson_filename: str = None,
                 area_of_interest_geojson_file: IO = None) -> None:
        """

        :param area_of_interest_geojson_filename:
        :param area_of_interest_geojson_file:
        """

        ee.Initialize(project=EARTHENGINE_PROJECT)  # This starts the ee engine

        # Load and save area of interest information
        if area_of_interest_geojson_filename:
            self.project_name: str = area_of_interest_geojson_filename.split("_")[0]
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
        self.drainage_params: dict = None
        self.land_usage_ee: ee.ImageCollection = None
        self.land_usage_xarray: xr.Dataset = None
        self.argentina_protected_area = gpd.read_file(filename=Path(FILES_DATA_PATH, "area_protegida.json"))

        # Download or load all data
        self.load_all_geospatial_data()

    def load_all_geospatial_data(self) -> None:
        self.elevation_raster, self.elevation_xarray = download_elevation_and_slope_30m(
            bbox=self.area_of_interest_bounds
        )
        self.drainage_ee, self.drainage_xarray = download_drainage_30m(
            geometry=self.area_ee_geometry,
            path_to_xarray=Path(self.files_project_path, f"{self.project_name}_drainage.nc")
        )
        self.drainage_params = {
            "min": self.drainage_xarray.min().values,
            "max": self.drainage_xarray.max().values
        }
        self.land_usage_ee, self.land_usage_xarray = download_land_usage_30m(
            geometry=self.area_ee_geometry,
            path_to_xarray=Path(self.files_project_path, f"{self.project_name}_land_usage.nc")
        )

    def get_random_subpolygons_from_polygon(self, bigger_polygon: Polygon = None) -> gpd.GeoDataFrame:
        if bigger_polygon is None:
            bigger_polygon = self.area_of_interest_geojson_file.geometry[0]
        # Get the bounding box of the polygon
        minx, miny, maxx, maxy = bigger_polygon.bounds
        # Define the number of rows and columns for the grid
        n_rows = 3
        n_cols = 3
        # Calculate the size of each grid cell
        cell_width = (maxx - minx) / n_cols
        cell_height = (maxy - miny) / n_rows
        # Create a list to store the grid cells
        cells = []
        # Generate the grid of rectangles
        for i in range(n_cols):
            for j in range(n_rows):
                # Create a rectangle for each cell in the grid
                cell = box(minx + i * cell_width, miny + j * cell_height,
                           minx + (i + 1) * cell_width, miny + (j + 1) * cell_height)
                # Clip the rectangle to the polygon
                intersection = cell.intersection(bigger_polygon)
                if not intersection.is_empty:
                    cells.append(intersection)
        # Create a GeoDataFrame for the cells
        cells_gdf = gpd.GeoDataFrame(geometry=cells)
        return cells_gdf

    def get_area_viability(self) -> gpd.GeoDataFrame:
        areas_to_study = self.get_random_subpolygons_from_polygon()
        intersections_with_protected_area = []
        percentage_of_good_slopes = []
        percentage_of_good_drainage = []
        percentage_of_good_land_usage = []
        for area_to_study in areas_to_study.geometry:
            minx, miny, maxx, maxy = area_to_study.bounds
            elevation_area = self.elevation_xarray.sel(x=slice(minx, maxx), y=slice(miny, maxy))
            drainage_area = self.drainage_xarray.sel(lon=slice(minx, maxx), lat=slice(miny, maxy))
            land_usage_area = self.land_usage_xarray.sel(lon=slice(minx, maxx), lat=slice(miny, maxy)).isel(time=1)
            # Check there is no protected area that intersects
            intersects_with_protected = any(
                area_to_study.intersects(protected_area) for protected_area in self.argentina_protected_area.geometry
            )
            intersections_with_protected_area.append(intersects_with_protected)
            # Check percentage of good slopes in area
            good_slope_percentage = elevation_area.binary_slope.sum().values / elevation_area.binary_slope.size * 100
            percentage_of_good_slopes.append(good_slope_percentage)
            # Check percentage of good drainage in area
            good_drainage_percentage = (drainage_area > 1).sum().values / drainage_area.size * 100
            percentage_of_good_drainage.append(good_drainage_percentage)
            # Check if the area contains wetland, etc
            good_land_usage_percentage = (
                                                 (land_usage_area.label != 1) & (land_usage_area.label != 4)
                                         ).sum().values / land_usage_area.label.size * 100
            percentage_of_good_land_usage.append(good_land_usage_percentage)
        areas_to_study["intersects_protected_area"] = intersections_with_protected_area
        areas_to_study["good_slopes_percentage"] = percentage_of_good_slopes
        areas_to_study["good_drainage_percentage"] = percentage_of_good_drainage
        areas_to_study["good_land_usage_percentage"] = percentage_of_good_land_usage
        areas_to_study["final_score"] = areas_to_study.apply(get_final_score_for_area, axis=1)
        areas_to_study["label"] = areas_to_study.apply(get_final_label_for_area, axis=1)
        areas_to_study["color"] = areas_to_study.apply(get_final_color_for_area, axis=1)
        return areas_to_study


if __name__ == "__main__":
    cambium_challenge = CambiumTakeHomeChallenge(
        area_of_interest_geojson_filename=Path(FILES_DATA_PATH, "corrientes1", "corrientes1_area.geojson")
    )
    areas_to_study = cambium_challenge.get_area_viability()
