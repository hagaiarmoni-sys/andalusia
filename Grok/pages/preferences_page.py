# pages/preferences_page.py
import streamlit as st
import json
import os

PREFS_FILE = "preferences.json"

def load_prefs():
    if os.path.exists(PREFS_FILE):
        with open(PREFS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "poi_categories": ["history", "architecture", "museums", "parks"],
        "min_poi_rating": 0.0,
        "max_same_category_per_day": 2,
        "max_daily_budget": 50.0
    }

def save_prefs(prefs):
    with open(PREFS_FILE, "w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=2)

def show_preferences_page():
    st.title("Preferences")
    prefs = load_prefs()

    with st.form("prefs_form"):
        cats = st.multiselect(
            "Preferred POI categories",
            ["history","architecture","museums","parks","nature","food","religious"],
            default=prefs.get("poi_categories", [])
        )
        min_r = st.slider("Minimum POI rating", 0.0, 10.0,
                          prefs.get("min_poi_rating", 0.0))
        max_cat = st.number_input("Max same category per day", 1, 10,
                                  prefs.get("max_same_category_per_day", 2))
        budget = st.number_input("Max daily budget (€)", 0, 500,
                                 int(prefs.get("max_daily_budget", 50)))

        if st.form_submit_button("Save Preferences"):
            new_prefs = {
                "poi_categories": cats,
                "min_poi_rating": min_r,
                "max_same_category_per_day": max_cat,
                "max_daily_budget": budget
            }
            save_prefs(new_prefs)
            st.success("Preferences saved!")