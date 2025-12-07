# pages/enroute_planner_page.py
import streamlit as st
import pandas as pd  # <-- ADDED

def show_enroute_planner(route_service, attractions_df):
    st.title("En-Route Planner")
    col1, col2 = st.columns(2)
    with col1:
        start = st.text_input("From")
    with col2:
        end = st.text_input("To")
    if st.button("Find Stops"):
        if not start or not end:
            st.error("Enter both cities.")
            return
        recs = route_service.get_recommendations(start, end, max_detour=100)
        if not recs:
            st.info("No recommendations.")
        else:
            for r in recs:
                attr = r['attraction_details']
                st.write(f"**{attr['name']}** ({attr['city']}) — {r['detour_km']}km detour")