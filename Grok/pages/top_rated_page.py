# pages/top_rated_page.py
import streamlit as st
import pandas as pd  # <-- ADDED

def show_top_rated_page(attraction_service):
    st.title("Top Rated Attractions")
    df = attraction_service.get_top_rated(20)
    if df.empty:
        st.info("No attractions.")
        return
    for _, row in df.iterrows():
        with st.expander(f"{row['name']} — {row['rating']}/10"):
            st.write(f"**City:** {row['city']}")
            if pd.notna(row.get('description')):
                st.write(row['description'])