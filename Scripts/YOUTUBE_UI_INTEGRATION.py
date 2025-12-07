"""
YOUTUBE VIDEO INTEGRATION INSTRUCTIONS FOR trip_planner_page.py
================================================================

This file shows how to add YouTube video previews to the trip planner UI.
"""

# ============================================================================
# STEP 1: ADD IMPORT AT TOP OF trip_planner_page.py (around line 15)
# ============================================================================

# Add this import after the other imports:
"""
# YouTube video display
try:
    from youtube_ui import display_city_video_card, display_video_expander
    YOUTUBE_UI_AVAILABLE = True
except ImportError:
    YOUTUBE_UI_AVAILABLE = False
    print("⚠️ youtube_ui not found - YouTube videos disabled in UI")
"""


# ============================================================================
# STEP 2: ADD YOUTUBE VIDEO IN CITY SECTION (around line 608)
# ============================================================================

# Find this section in display_itinerary() function (around line 600-610):
"""
        # Cities visited
        cities_list = day_data.get("cities", [])
        for city_stop in cities_list:
            city_name = city_stop.get("city", "Unknown")
            
            # POIs
            pois = city_stop.get("attractions", [])
            if pois:
                st.markdown(f"### 📍 {city_name} ({len(pois)} attractions)")
"""

# REPLACE WITH:
"""
        # Cities visited
        cities_list = day_data.get("cities", [])
        for city_stop in cities_list:
            city_name = city_stop.get("city", "Unknown")
            
            # POIs
            pois = city_stop.get("attractions", [])
            if pois:
                st.markdown(f"### 📍 {city_name} ({len(pois)} attractions)")
                
                # 🎬 YouTube Video Preview (collapsible)
                if YOUTUBE_UI_AVAILABLE:
                    display_video_expander(city_name, expanded=False)
"""


# ============================================================================
# ALTERNATIVE: SHOW VIDEO AS CARD (more prominent)
# ============================================================================

# If you prefer a more visible video card instead of expander:
"""
                # 🎬 YouTube Video Preview (card style)
                if YOUTUBE_UI_AVAILABLE:
                    display_city_video_card(city_name, show_title=True)
"""


# ============================================================================
# FULL MODIFIED SECTION (copy-paste ready)
# ============================================================================

# Here's the complete modified section from line ~600 to ~635:

MODIFIED_CODE = '''
        # Cities visited
        cities_list = day_data.get("cities", [])
        for city_stop in cities_list:
            city_name = city_stop.get("city", "Unknown")
            
            # POIs
            pois = city_stop.get("attractions", [])
            if pois:
                st.markdown(f"### 📍 {city_name} ({len(pois)} attractions)")
                
                # 🎬 YouTube Video Preview
                if YOUTUBE_UI_AVAILABLE:
                    display_video_expander(city_name, expanded=False)
                
                for idx, poi in enumerate(pois, 1):
                    with st.expander(f"**{idx}. {poi.get('name', 'Unknown')}**", expanded=False):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            desc = poi.get("description", "No description")
                            st.write(desc)
                            
                            if poi.get("insider_tip"):
                                st.info(f"💡 **Tip:** {poi['insider_tip']}")
                        
                        with col2:
                            if poi.get("rating"):
                                st.metric("⭐ Rating", f"{poi['rating']}/10")
                            if poi.get("duration"):
                                st.metric("⏱️ Duration", poi["duration"])
                            if poi.get("price"):
                                st.metric("💶 Price", poi["price"])
                            
                            category = poi.get("category", "")
                            if category:
                                st.caption(f"🏷️ {category}")
'''


# ============================================================================
# FILES NEEDED
# ============================================================================

"""
Make sure you have these files in your app folder:

andalusia-app/
├── app.py
├── trip_planner_page.py       ← Modified with YouTube integration
├── youtube_ui.py              ← NEW: YouTube UI helper
├── youtube_helper.py          ← For Word doc (already exists)
├── data/
│   └── youtube_videos_db.json ← YouTube videos database
"""


# ============================================================================
# OPTIONAL: ADD YOUTUBE SECTION IN ROUTE OVERVIEW
# ============================================================================

# If you want to show a "highlights" video section at the top of the itinerary:
# Add this around line 455 (after the route display):

ROUTE_VIDEO_SECTION = '''
    # 🎬 Video Highlights for your destinations
    if YOUTUBE_UI_AVAILABLE and ordered_cities:
        st.markdown("### 🎬 Destination Previews")
        
        # Show videos for first 3 unique cities
        shown_cities = set()
        video_cols = st.columns(min(3, len(ordered_cities)))
        
        col_idx = 0
        for city in ordered_cities:
            if city not in shown_cities and col_idx < 3:
                shown_cities.add(city)
                with video_cols[col_idx]:
                    from youtube_ui import get_videos_for_city
                    videos = get_videos_for_city(city, max_videos=1)
                    if videos:
                        st.markdown(f"**{city}**")
                        st.video(videos[0].get('watch_url', ''))
                        col_idx += 1
        
        st.markdown("---")
'''
