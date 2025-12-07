# pages/explore_page.py
import streamlit as st
import pandas as pd  # <-- ADDED

def show_explore_page(attraction_service):
    st.title("Explore Attractions")
    df = attraction_service.get_all()
    if df.empty:
        st.info("No attractions found.")
        return

    st.dataframe(df[["name", "city", "category", "rating"]].head(20))

    st.subheader("All Attractions")
    for _, row in df.iterrows():
        with st.expander(f"{row['name']} ({row.get('category', 'Unknown')})"):
            st.write(f"**City:** {row['city']}")
            if pd.notna(row.get('rating')):
                st.write(f"**Rating:** {row['rating']}/10")
            if pd.notna(row.get('visit_duration_hours')):
                st.write(f"**Duration:** ~{row['visit_duration_hours']} hours")
            if pd.notna(row.get('entrance_fee')):
                st.write(f"**Fee:** {row['entrance_fee']}")
            if pd.notna(row.get('description')):
                st.write(row['description'])