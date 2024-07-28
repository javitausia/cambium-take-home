from io import StringIO
from pathlib import Path

import geemap.foliumap as geemap
import streamlit as st

from src.config import STATIC_FILES_PATH, FILES_DATA_PATH
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
st.title("Earth Engine Web App")

st.markdown(
    """
    This multipage app template demonstrates various interactive web apps created using [streamlit](https://streamlit.io) and [geemap](https://geemap.org). It is an open-source project and you are very welcome to contribute to the [GitHub repository](https://github.com/giswqs/geemap-apps).
    """
)

st.header("Instructions")

markdown = """
1. For the [GitHub repository](https://github.com/giswqs/geemap-apps) or [use it as a template](https://github.com/new?template_name=geemap-apps&template_owner=giswqs) for your own project.
2. Customize the sidebar by changing the sidebar text and logo in each Python files.
3. Find your favorite emoji from https://emojipedia.org.
4. Add a new app to the `pages/` directory with an emoji in the file name, e.g., `1_🚀_Chart.py`.
"""

st.markdown(markdown)

uploaded_file = st.file_uploader("Choose a file")
if uploaded_file is not None:
    # To read file as bytes:
    bytes_data = uploaded_file.getvalue()
    filename = uploaded_file.name
    # st.write(bytes_data)
    # To convert to a string based IO:
    stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
    # st.write(stringio)
    # To read file as string:
    string_data = stringio.read()
    st.write(string_data)
    # Can be used wherever a "file-like" object is accepted:

cambium_challenge = CambiumTakeHomeChallenge(
    area_of_interest_geojson_filename=Path(FILES_DATA_PATH, "corrientes1", "corrientes1_area.geojson")
)
# st.write(dataframe)

# Plot different layers in geemap
m = geemap.Map()
m.add_basemap("SATELLITE")
vis_params = {
    "palette": "terrain"
}
m.add_layer(cambium_challenge.drainage_ee, vis_params=vis_params, name="Drainage")
# m.add_layer(cambium_challenge.land_usage_ee.first(), name="Land Usage")
m.add_geojson(cambium_challenge.argentina_protected_area.__geo_interface__, layer_name='Protected Areas')
elevation_dataset = cambium_challenge.elevation_xarray.assign_coords(time=('time', [0]))
geemap.xee_to_image(elevation_dataset, filenames=[Path(STATIC_FILES_PATH, "elevation.tif")])
for layer in [
    {"var": "elevation", "name": "Elevation"},
    # {"var": "slope", "name": "Slope"},
    # {"var": "binary_slope", "name": "Binary Slope (|slope| > 1)"}
]:
    var_raster = geemap.array_to_image(elevation_dataset[layer.get("var")],
                                       source=Path(STATIC_FILES_PATH, "elevation.tif"))
    m.add_raster(var_raster, colormap="dem", layer_name=layer.get("name"))
# geemap.xee_to_image(cambium_challenge.drainage_xarray, filenames=[Path(STATIC_FILES_PATH, "drainage.tif")])
# drainage_raster = geemap.array_to_image(cambium_challenge.drainage_xarray["b1"], source=Path(STATIC_FILES_PATH, "drainage.tif"))
# m.add_raster(drainage_raster, colormap="viridis", layer_name="Drainage")
m.to_streamlit(height=500)
