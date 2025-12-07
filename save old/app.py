"""
Andalusia Road Trip Planner - Main Application
Optimized for car-based travel with base cities and day trips
"""

import streamlit as st
import json
import os

# Page configuration
st.set_page_config(
    page_title="Wanderlust - Andalusia Road Trip Planner",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)


def load_json(filepath):
    """Load JSON data from file with better error reporting"""
    try:
        if not os.path.exists(filepath):
            st.warning(f"⚠️ File not found: {filepath}")
            return []
        
        file_size = os.path.getsize(filepath)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            st.warning(f"⚠️ File is empty: {filepath}")
            return []
        
        if not isinstance(data, list):
            st.warning(f"⚠️ File data is not a list: {filepath}")
            return []
        
        # Success - show info
        st.success(f"✅ Loaded {len(data):,} items from {os.path.basename(filepath)} ({file_size/1024:.0f} KB)")
        return data
        
    except json.JSONDecodeError as e:
        st.error(f"❌ JSON decode error in {filepath}: {str(e)}")
        return []
    except Exception as e:
        st.error(f"❌ Error loading {filepath}: {str(e)}")
        return []


def main():
    """Main application entry point"""
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🌍 Wanderlust")
        st.markdown("_Your Personal Trip Planner_")
        st.markdown("---")
        
        # Navigation
        st.markdown("**Navigation**")
        page = st.radio(
            "Go to:",
            ["Plan a Trip", "My Trips", "Preferences"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.caption("Traveller - plan your perfect journey")
    
    # Show current directory for debugging
    # st.info(f"📁 Working directory: {os.getcwd()}")
    
    # Load data - try current directory first, then data/ subdirectory
    def try_load(filename):
        """Try loading from current dir first, then data/ subdir"""
        if os.path.exists(filename):
            return load_json(filename)
        elif os.path.exists(f"data/{filename}"):
            return load_json(f"data/{filename}")
        else:
            st.error(f"❌ File not found: {filename} (checked current dir and data/ subdir)")
            return []
    
    st.markdown("### 📂 Loading Data...")
    
    attractions_data = try_load("andalusia_attractions_filtered.json")
    hotels_data = try_load("andalusia_hotels_osm.json")
    restaurants_data = try_load("restaurants_andalusia.json")
    routes_data = try_load("andalusia_routes.json")
    
    st.markdown("---")
    
    # Validate critical data
    if not attractions_data:
        st.error("❌ CRITICAL: No attractions data loaded! Cannot generate trips.")
        st.stop()
    
    # Route to appropriate page
    if page == "Plan a Trip":
        from trip_planner_page import show_trip_planner_full
        show_trip_planner_full(attractions_data, hotels_data, restaurants_data)
    
    elif page == "My Trips":
        st.title("📚 My Saved Trips")
        show_my_trips()
    
    elif page == "Preferences":
        st.title("⚙️ Preferences")
        show_preferences()


def show_my_trips():
    """Display saved trips"""
    trips_dir = "trips"
    
    if not os.path.exists(trips_dir):
        st.info("🔭 No saved trips yet. Create your first road trip!")
        return
    
    trip_files = [f for f in os.listdir(trips_dir) if f.endswith('.json')]
    
    if not trip_files:
        st.info("🔭 No saved trips yet. Create your first road trip!")
        return
    
    st.write(f"Found {len(trip_files)} saved trips:")
    
    for trip_file in sorted(trip_files, reverse=True):
        try:
            with open(os.path.join(trips_dir, trip_file), 'r', encoding='utf-8') as f:
                trip_data = json.load(f)
            
            with st.expander(f"🚗 {trip_data.get('start_end_text', 'Unknown')} - {trip_data.get('created_at', 'Unknown date')}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Days", trip_data.get('days', '?'))
                with col2:
                    cities = trip_data.get('ordered_cities', [])
                    st.metric("Cities", len(cities))
                with col3:
                    st.metric("Budget", trip_data.get('preferences', {}).get('budget', '?'))
                
                st.write("**Route:**", " → ".join(trip_data.get('ordered_cities', [])))
                
                if st.button(f"Load Trip", key=trip_file):
                    st.info("🔄 Loading saved trip... (Feature coming soon)")
        
        except Exception as e:
            st.error(f"Error loading {trip_file}: {str(e)}")


def show_preferences():
    """Display and edit preferences"""
    
    prefs_file = "preferences.json"
    
    # Load existing preferences
    default_prefs = {
        "default_trip_type": "Point-to-point",  # Can be "Point-to-point", "Circular", or "Star/Hub"
        "default_budget": "mid-range",
        "default_pace": "medium",
        "max_km_per_day": 300,
        "poi_categories": ["history", "architecture", "museums", "nature"],
        "hotel_platform": "Any",
        "max_price_per_night": 150,
        "min_poi_rating": 0.0,
        "max_same_category_per_day": 2
    }
    
    if os.path.exists(prefs_file):
        try:
            with open(prefs_file, 'r', encoding='utf-8') as f:
                saved_prefs = json.load(f)
                default_prefs.update(saved_prefs)
        except:
            pass
    
    st.markdown("### 🚗 Road Trip Preferences")
    
    with st.form("preferences_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Default Settings**")
            
            trip_type_options = ["Point-to-point", "Circular", "Star/Hub"]
            default_trip = default_prefs.get("default_trip_type", "Point-to-point")
            
            trip_type = st.selectbox(
                "Trip Type",
                trip_type_options,
                index=trip_type_options.index(default_trip) if default_trip in trip_type_options else 0,
                help="Point-to-point: A→B | Circular: Loop back to start | Star/Hub: Day trips from one base ⭐"
            )
            
            budget = st.selectbox(
                "Budget",
                ["budget", "mid-range", "luxury"],
                index=["budget", "mid-range", "luxury"].index(default_prefs["default_budget"])
            )
            
            pace = st.selectbox(
                "Travel Pace",
                ["easy", "medium", "fast"],
                index=["easy", "medium", "fast"].index(default_prefs["default_pace"])
            )
            
            max_km = st.number_input(
                "Max driving km per day",
                min_value=100,
                max_value=500,
                value=default_prefs["max_km_per_day"],
                step=50
            )
        
        with col2:
            st.markdown("**Accommodation**")
            
            platform = st.selectbox(
                "Preferred Platform",
                ["Any", "Booking", "Airbnb"],
                index=["Any", "Booking", "Airbnb"].index(default_prefs["hotel_platform"])
            )
            
            max_price = st.number_input(
                "Max price per night (€)",
                min_value=0,
                max_value=500,
                value=default_prefs["max_price_per_night"],
                step=10,
                help="0 = no limit"
            )
            
            st.markdown("**Attractions**")
            
            min_rating = st.slider(
                "Minimum POI rating",
                min_value=0.0,
                max_value=10.0,
                value=default_prefs["min_poi_rating"],
                step=0.5
            )
            
            max_same = st.slider(
                "Max same category per day",
                min_value=1,
                max_value=4,
                value=default_prefs["max_same_category_per_day"]
            )
        
        st.markdown("**POI Categories**")
        categories = st.multiselect(
            "Preferred attraction types",
            ["art", "museums", "history", "architecture", "parks", "nature",
             "gardens", "beaches", "viewpoints", "markets", "religious", "castles",
             "palaces", "neighborhoods", "food & tapas", "wine & bodegas"],
            default=default_prefs["poi_categories"]
        )
        
        submitted = st.form_submit_button("💾 Save Preferences", use_container_width=True)
        
        if submitted:
            new_prefs = {
                "default_trip_type": trip_type,
                "default_budget": budget,
                "default_pace": pace,
                "max_km_per_day": max_km,
                "poi_categories": categories,
                "hotel_platform": platform,
                "max_price_per_night": max_price,
                "min_poi_rating": min_rating,
                "max_same_category_per_day": max_same
            }
            
            with open(prefs_file, 'w', encoding='utf-8') as f:
                json.dump(new_prefs, f, ensure_ascii=False, indent=2)
            
            st.success("✅ Preferences saved!")
            st.rerun()


if __name__ == "__main__":
    main()
