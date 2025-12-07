# pages/by_city_page.py
import streamlit as st
import pandas as pd  # <-- ADDED

def show_by_city_page(attraction_service):
    st.title("Attractions by City")
    cities = attraction_service.get_cities()
    if not cities:
        st.info("No cities.")
        return
    city = st.selectbox("Choose city", sorted(cities))
    df = attraction_service.get_by_city(city)
    if df.empty:
        st.info(f"No attractions in {city}.")
        return
    for _, row in df.iterrows():
        st.write(f"**{row['name']}** — {row.get('category', '')}")
        if pd.notna(row.get('rating')):
            st.caption(f"Rating: {row['rating']}/10")