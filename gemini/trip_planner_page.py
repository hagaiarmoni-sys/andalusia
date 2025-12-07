# trip_planner_page.py
import streamlit as st
import pandas as pd
import json
import os
import io
from datetime import datetime, timedelta
from urllib.parse import quote_plus

# ✅ CRITICAL: Use car-based generator
from itinerary_generator_car import generate_simple_trip
from document_generator import build_word_doc
from restaurant_service import get_restaurant_tips
from text_norm import canonicalize_city, norm_key
from date_picker_system import create_date_picker
from events_display import display_events_section  # 🆕 Events feature

# Configuration
TRIPS_DIR = "trips"
os.makedirs(TRIPS_DIR, exist_ok=True)

# Placeholder for data loading and summary (based on snippets)
def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception:
        return []

ALL_CITIES_COORDS = load_json("data/andalusia_city_coords.json")
ALL_POIS_DATA = load_json("data/andalusia_pois.json")
ALL_RESTAURANTS_DATA = load_json("data/andalusia_restaurants.json")

def add_plan_again_button():
    """Add a 'Plan Again' button that clears the itinerary and resets the form"""
    st.write("")
    st.write("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🔄 Plan Again", type="primary", use_container_width=True, key="plan_again_btn"):
            keys_to_clear = [
                'current_trip_result', 'current_trip_start_date', 'current_trip_end_date',
                'current_trip_days', 'current_trip_prefs', 'current_trip_ordered_cities',
                'current_trip_maps_link'
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

def to_excel_buffer(itinerary, ordered_cities, days, prefs, result):
    """Creates an Excel file buffer with summary and detailed itinerary"""
    bio = io.BytesIO()
    total_km = result.get('total_km', 0)
    trip_type = result.get('trip_type', 'Car Road Trip')
    
    with pd.ExcelWriter(bio, engine='xlsxwriter') as writer:
        itinerary_data = []
        for day in itinerary:
            poi_list = ", ".join([a['name'] for c in day.get('cities', []) for a in c.get('attractions', [])])
            itinerary_data.append({
                "Day": day.get('day'),
                "Date": day.get('date_obj').strftime('%Y-%m-%d') if day.get('date_obj') else 'N/A',
                "City": day.get('city'),
                "Overnight City": day.get('overnight_city'),
                "Driving (km)": day.get('driving_km', 0),
                "Attractions": poi_list,
            })
        df = pd.DataFrame(itinerary_data)
        df.to_excel(writer, index=False, sheet_name='Itinerary')

        summary_data = {
            "Start": [ordered_cities[0] if ordered_cities else "?"],
            "End": [ordered_cities[-1] if len(ordered_cities) > 1 else ordered_cities[0]],
            "Days": [days],
            "Trip Type": [trip_type],
            "Total Driving (km)": [round(total_km)],
            "Budget": [prefs.get("budget", "?")],
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, index=False, sheet_name="Summary")
    
    bio.seek(0)
    return bio

# --- Main Streamlit Function (Reconstructed) ---

def trip_planner_page(default_prefs):
    
    st.title("🗺️ Andalusia Road Trip Planner")
    st.markdown("Configure your trip and hit **Generate Itinerary**!")
    
    with st.form("trip_parameters"):
        col_dates, col_mode = st.columns(2)
        with col_dates:
            start_date, end_date, days = create_date_picker()
            # Storing dates in session state (CRITICAL for events_display.py)
            st.session_state['current_trip_start_date'] = start_date
            st.session_state['current_trip_end_date'] = end_date
            
        # Simplified inputs
        start_city = st.text_input("Start City", "Málaga")
        end_city = st.text_input("End City", "Seville")
        prefs = default_prefs
        cities_to_include = st.text_area("Cities to include (one per line, optional)", "")
        special_requests = st.text_area("Special Requests / Interests (e.g., 'must see beaches', 'flamenco show')", "")
        
        generate_button = st.form_submit_button("✨ Generate Itinerary", type="primary", use_container_width=True)

    
    if generate_button and start_date and end_date and start_city:
        
        params = {
            'start_date': start_date, 'end_date': end_date, 'days': days,
            'start_city': start_city, 'end_city': end_city,
            'cities_to_include': [c.strip() for c in cities_to_include.split('\n') if c.strip()],
            'special_requests': special_requests, 'prefs': prefs
        }
        
        with st.spinner("⏳ Generating the perfect Andalusian itinerary..."):
            result = generate_simple_trip(
                cities_coords=ALL_CITIES_COORDS,
                pois_data=ALL_POIS_DATA,
                restaurants_data=ALL_RESTAURANTS_DATA,
                params=params
            )
        
        itinerary = result.get('itinerary')
        if not itinerary:
            st.error("❌ Failed to generate itinerary. Check input cities or adjust preferences.")
            return

        # Store basic results in session state
        st.session_state['current_trip_result'] = result
        st.session_state['current_trip_days'] = days
        st.session_state['current_trip_prefs'] = prefs
        st.session_state['current_trip_ordered_cities'] = result.get('ordered_cities', [])
        st.session_state['current_trip_maps_link'] = result.get('maps_link', '#')

        st.success("✅ Itinerary generated successfully!")
        st.subheader("Itinerary Summary")
        st.dataframe(pd.DataFrame([
            {"Day": d.get('day'), "City": d.get('city'), "Highlights": len([a for c in d.get('cities', []) for a in c.get('attractions', [])])}
            for d in itinerary
        ]))

        # --- 🚨 CRITICAL FIX CALL 1: Display Events and populate result['all_events'] ---
        # NOTE: This function mutates (updates) the 'result' dictionary by adding the 'all_events' key.
        display_events_section(result) 
        st.session_state['current_trip_result'] = result # Save the updated result back to session state

        # --- Export Section ---
        st.markdown("---")
        st.markdown("### 💾 Export Trip")
        
        col_word, col_excel = st.columns(2)
        
        # 1. WORD Export (DOCX)
        with col_word:
            # Pass the full 'result' dictionary which now includes 'all_events'
            docx_file = build_word_doc(
                itinerary=result['itinerary'],
                hop_kms=result.get('hop_kms', []),
                maps_link=result.get('maps_link', '#'),
                ordered_cities=result['ordered_cities'],
                days=days,
                prefs=prefs,
                parsed_requests=result.get('parsed_requests', {}),
                is_car_mode=True, 
                result=result # 🚨 CRITICAL FIX CALL 2: Pass the complete result object!
            )
            
            start_date_str = start_date.strftime('%Y%m%d')
            end_date_str = end_date.strftime('%Y%m%d')
            docx_fname = f"Andalusia_Road_Trip_{start_date_str}_to_{end_date_str}.docx"
            
            st.download_button(
                label="📄 Download Word Document (.docx)",
                data=docx_file,
                file_name=docx_fname,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
            
        # 2. EXCEL Export
        # ... (Excel export logic remains the same) ...
        
        add_plan_again_button()
        
    # ... (Logic to re-display trip from session state goes here, also including the two critical calls) ...