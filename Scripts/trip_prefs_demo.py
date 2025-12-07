import streamlit as st

# Basic page config
st.set_page_config(
    page_title="Trip Preferences Demo",
    page_icon="🧭",
    layout="centered",
)

st.title("🧭 Trip Preferences – Category Sliders")
st.write(
    "Move the sliders to tell us how much you enjoy each type of place. "
    "Later, these numbers can be fed into the itinerary generator."
)

# Global scale for all sliders
MIN_SCORE = 0
MAX_SCORE = 5
DEFAULT_SCORE = 3

st.markdown("### What do you enjoy on this trip?")

col1, col2 = st.columns(2)

with col1:
    museums = st.slider("Museums & History", MIN_SCORE, MAX_SCORE, DEFAULT_SCORE)
    architecture = st.slider("Architecture & Monuments", MIN_SCORE, MAX_SCORE, DEFAULT_SCORE)
    nature = st.slider("Nature, Parks & Viewpoints", MIN_SCORE, MAX_SCORE, DEFAULT_SCORE)
    beaches = st.slider("Beaches & Coastline", MIN_SCORE, MAX_SCORE, DEFAULT_SCORE)

with col2:
    food = st.slider("Food, Tapas & Wine", MIN_SCORE, MAX_SCORE, DEFAULT_SCORE + 1)
    nightlife = st.slider("Nightlife & Bars", MIN_SCORE, MAX_SCORE, DEFAULT_SCORE - 1)
    shopping = st.slider("Shopping & Markets", MIN_SCORE, MAX_SCORE, DEFAULT_SCORE)
    kids = st.slider("Family / Kids Activities", MIN_SCORE, MAX_SCORE, DEFAULT_SCORE)

st.markdown("### Trip pace")
pace = st.slider(
    "Overall pace (0 = very relaxed, 5 = packed full days)",
    MIN_SCORE,
    MAX_SCORE,
    3,
)

# Pack into a dict – this is what you’d pass into your real generator
category_prefs = {
    "museums": museums,
    "architecture": architecture,
    "nature": nature,
    "beaches": beaches,
    "food": food,
    "nightlife": nightlife,
    "shopping": shopping,
    "kids": kids,
    "pace": pace,
}

st.markdown("### Raw preference scores")
st.json(category_prefs)

# Normalized weights (0–1) – many algorithms like this form
total = sum(category_prefs.values()) or 1
normalized_prefs = {k: round(v / total, 3) for k, v in category_prefs.items()}

st.markdown("### Normalized weights (0–1)")
st.json(normalized_prefs)

st.markdown("---")
st.markdown(
    "These values are **just a demo**, but in your real app you’d pass "
    "`category_prefs` or `normalized_prefs` into your itinerary generator "
    "to decide which POIs to prioritize."
)
