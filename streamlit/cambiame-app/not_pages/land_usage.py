import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import cambium_challenge

import streamlit as st
import geemap.foliumap as geemap


def getLandImage(year):
    # Filter the collection by year.
    landcover = cambium_challenge.land_usage_ee.filterDate(f"{year}-01-01", f"{int(year) + 1}-01-01").first()
    return landcover


st.header("Google Dynamic World V1 Dataset")

# Create a layout containing two columns, one for the map and one for the layer dropdown list.
row1_col1, row1_col2 = st.columns([3, 1])

# Create an interactive map.
Map = geemap.Map()

# Select the year to show.
years = ["2020", "2021", "2022", "2023", "2024"]

# Add a dropdown list and checkbox to the second column.
with row1_col2:
    selected_year = st.multiselect("Select a year", years)

# Add selected image to the map based on the selected year.
if selected_year:
    for year in selected_year:
        try:
            Map.add_layer(getLandImage(year), name="DynamicWorld " + year)
        except Exception as e:
            print(f"Image not found for year {year}, with error: {e}")
    with row1_col1:
        Map.to_streamlit(height=600)

else:
    with row1_col1:
        Map.to_streamlit(height=600)
