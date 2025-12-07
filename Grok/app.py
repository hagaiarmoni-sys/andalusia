# app.py
import streamlit as st
import pandas as pd
import json
import os

# ----------------------------------------------------------------------
# 1. Services
# ----------------------------------------------------------------------
from attraction_service import AttractionService
from filter_service import FilterService
from route_service import RouteService

# ----------------------------------------------------------------------
# 2. Load data (handles list **or** {"attractions": …} JSON)
# ----------------------------------------------------------------------
@st.cache_data
def load_attractions():
    p = "data/andalusia_attractions_enriched.json"
    if not os.path.exists(p):
        st.error(f"Missing {p}")
        return pd.DataFrame()
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return pd.DataFrame(data if isinstance(data, list) else data.get("attractions", []))

@st.cache_data
def load_hotels():
    p = "data/andalusia_hotels_full.json"
    if not os.path.exists(p):
        st.warning(f"Missing {p}")
        return []
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("hotels", [])

@st.cache_data
def load_routes():
    p = "data/andalusia_routes.json"
    if not os.path.exists(p):
        st.warning(f"Missing {p} – using empty routes.")
        return {"routes": []}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

attractions_df = load_attractions()
hotels_data      = load_hotels()
routes_data      = load_routes()

attraction_service = AttractionService(attractions_df)
filter_service     = FilterService(attraction_service)
route_service      = RouteService(routes_data, attraction_service)

# ----------------------------------------------------------------------
# 3. Page imports (only the two you need)
# ----------------------------------------------------------------------
try:
    from pages.preferences_page import show_preferences_page
except Exception as e:
    def show_preferences_page(*a): st.error(f"Preferences page error: {e}")

try:
    from pages.trip_planner_page import show_trip_planner_full
except Exception as e:
    def show_trip_planner_full(*a): st.error(f"Trip planner error: {e}")

# ----------------------------------------------------------------------
# 4. UI – ONLY two pages
# ----------------------------------------------------------------------
st.set_page_config(page_title="Andalusia Planner", layout="wide")

pages = ["Preferences", "Plan a Trip"]
page  = st.sidebar.selectbox("Navigate", pages)

if page == "Preferences":
    show_preferences_page()

elif page == "Plan a Trip":
    # give the page the data it needs
    show_trip_planner_full(
        attractions_df.to_dict('records'),
        hotels_data,
        route_service
    )