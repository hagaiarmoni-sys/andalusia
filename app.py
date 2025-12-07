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
        
        # Show file info
        st.success(f"✅ Loaded {filepath} ({len(data):,} records, {file_size / 1024:.1f} KB)")
        
        return data
        
    except json.JSONDecodeError as e:
        st.error(f"❌ JSON decode error in {filepath}: {str(e)}")
        return []
    except Exception as e:
        st.error(f"❌ Error loading {filepath}: {str(e)}")
        return []


# ✅ OPTIMIZED: Cache data loading to prevent reloading on every interaction
@st.cache_data(ttl=3600)  # Cache for 1 hour (3600 seconds)
def load_cached_json(filename):
    """
    Load JSON with caching to improve performance
    
    Benefits:
    - Loads data only once per hour (or until cache is cleared)
    - Reduces memory usage
    - Speeds up app considerably
    - Critical for cloud deployment (free tiers have limited RAM)
    
    Args:
        filename: Name of the JSON file to load
        
    Returns:
        List of data from JSON file
    """
    # Try current directory first, then data/ subdirectory
    if os.path.exists(filename):
        filepath = filename
    elif os.path.exists(f"data/{filename}"):
        filepath = f"data/{filename}"
    else:
        print(f"❌ File not found: {filename} (checked current dir and data/ subdir)")
        return []
    
    # Load the file
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        file_size = os.path.getsize(filepath)
        
        return data
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error in {filepath}: {str(e)}")
        return []
    except Exception as e:
        print(f"❌ Error loading {filepath}: {str(e)}")
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
    
    # ✅ OPTIMIZED: Load data using cache
    # This will only load once per hour instead of on every page interaction
    attractions_data = load_cached_json("andalusia_attractions_filtered.json")
    hotels_data = load_cached_json("andalusia_hotels_osm.json")
    restaurants_data = load_cached_json("restaurants_andalusia.json")
    
    # Validate critical data
    if not attractions_data:
        st.error("❌ CRITICAL: No attractions data loaded! Cannot generate trips.")
        st.info("💡 Make sure `andalusia_attractions_filtered.json` is in the current directory or in the `data/` folder")
        st.stop()
    
    # Route to appropriate page
    if page == "Plan a Trip":
        from trip_planner_page import show_trip_planner_full
        show_trip_planner_full(attractions_data, hotels_data, restaurants_data)
    
    elif page == "My Trips":
        st.title("📚 My Saved Trips")
        
        trips_dir = "trips"
        if not os.path.exists(trips_dir):
            st.info("No saved trips yet. Plan your first trip!")
        else:
            trip_files = [f for f in os.listdir(trips_dir) if f.endswith('.json')]
            
            if not trip_files:
                st.info("No saved trips yet. Plan your first trip!")
            else:
                st.write(f"Found {len(trip_files)} saved trip(s):")
                
                for trip_file in sorted(trip_files, reverse=True):
                    with st.expander(f"📄 {trip_file}"):
                        filepath = os.path.join(trips_dir, trip_file)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                trip_data = json.load(f)
                            
                            st.json(trip_data)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"🗑️ Delete", key=f"del_{trip_file}"):
                                    os.remove(filepath)
                                    st.success(f"Deleted {trip_file}")
                                    st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error loading trip: {str(e)}")
    
    elif page == "Preferences":
        st.title("⚙️ Preferences")
        st.write("_Coming soon: Save your travel preferences, favorite cities, budget settings, etc._")
        
        # Placeholder for future features
        st.markdown("### Future Features:")
        st.markdown("""
        - 💰 Default budget preferences
        - 🏨 Hotel star rating preferences
        - 🍽️ Cuisine preferences
        - 🚗 Daily driving limit preferences
        - 📅 Preferred travel seasons
        - 🎨 Interests and activity types
        """)
        
        # Add cache management
        st.markdown("---")
        st.markdown("### 🗑️ Cache Management")
        st.write("Clear cached data to force reload from disk:")
        
        if st.button("🔄 Clear Data Cache"):
            st.cache_data.clear()
            st.success("✅ Cache cleared! Data will be reloaded on next interaction.")
            st.info("💡 Use this if you've updated your JSON data files")


if __name__ == "__main__":
    main()
