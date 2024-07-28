from io import StringIO
from pathlib import Path

import geemap.foliumap as geemap
import streamlit as st

from src.config import STATIC_FILES_PATH
from src.main import CambiumTakeHomeChallenge

st.set_page_config(layout="wide")

# Customize the sidebar
markdown = """
Solution to Geospatial Data Developer Take Home Challenge: <https://github.com/cambium-earth/gdd-test>
"""

st.sidebar.title("About")
st.sidebar.info(markdown)
logo = "https://cdn.prod.website-files.com/665e55a84bd228945e1620d3/665e55a84bd228945e162108_02_Logo%20Cambium.png"
st.sidebar.image(logo)

# Customize page title
st.title("Dockerized Streamlit App to solve Cambium Areas Viability Problem")

st.markdown(
    """
    This is the [GitHub repository](https://github.com/javitausia/cambium-take-home) with all code and info ;)
    """
)

st.header("Instructions")

markdown = """
1. Load a .geojson file.
2. Play with the interactive map.
"""

st.markdown(markdown)

uploaded_file = st.file_uploader("Choose a file")
if uploaded_file is not None:
    # To read file as bytes:
    bytes_data = uploaded_file.getvalue()
    # st.write(bytes_data)
    # To convert to a string based IO:
    stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
    # st.write(stringio)
    # To read file as string:
    # string_data = stringio.read()
    # st.write(string_data)
    # Instantiate the main class to download and render all data
    cambium_challenge = CambiumTakeHomeChallenge(
        area_of_interest_geojson_filename=uploaded_file.name, area_of_interest_geojson_file=bytes_data
    )
    # Plot different layers in geemap
    m = geemap.Map()
    m.add_basemap("SATELLITE")
    m.add_layer(cambium_challenge.drainage_ee, name="Drainage", shown=False)
    m.add_layer(cambium_challenge.land_usage_ee.first(), name="Land Usage", shown=False)
    # m.add_geojson(cambium_challenge.argentina_protected_area.__geo_interface__, layer_name='Protected Areas')
    elevation_dataset = cambium_challenge.elevation_xarray.assign_coords(time=('time', [0]))
    geemap.xee_to_image(elevation_dataset, filenames=[Path(STATIC_FILES_PATH, "elevation.tif")])
    for layer in [
        {"var": "elevation", "name": "Elevation"},
        # {"var": "slope", "name": "Slope"},
        # {"var": "binary_slope", "name": "Binary Slope (|slope| > 1)"}
    ]:
        var_raster = geemap.array_to_image(elevation_dataset[layer.get("var")],
                                           source=Path(STATIC_FILES_PATH, "elevation.tif"))
        m.add_raster(var_raster, colormap="terrain", layer_name=layer.get("name"), shown=False)
    # m.add_geojson(cambium_challenge.area_of_interest_geojson_file.__geo_interface__,
    #               layer_name="Area of Interest",
    #               color="red")
    # Get areas with the study applied ;)
    areas_of_study = cambium_challenge.get_area_viability()
    m.add_geojson(areas_of_study.__geo_interface__,
                  layer_name="Studied Areas",
                  fill_colors=areas_of_study["color"],
                  fill_opacity=0.8)
    m.to_streamlit(height=500)
