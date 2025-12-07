# pages/advanced_filter_page.py
import streamlit as st
import pandas as pd  # <-- ADDED

def show_advanced_filter_page(filter_service, attractions_df):
    st.title("Advanced Filter")
    criteria = {
        "min_rating": st.slider("Min Rating", 0.0, 10.0, 7.0),
        "free_only": st.checkbox("Free entrance only"),
        "city": st.text_input("City (optional)")
    }
    if criteria["city"]:
        criteria["city"] = criteria["city"].strip()
    df = filter_service.filter(criteria)
    if df.empty:
        st.info("No results.")
    else:
        st.dataframe(df[["name", "city", "rating", "entrance_fee"]])