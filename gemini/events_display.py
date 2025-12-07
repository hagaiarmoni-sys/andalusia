# events_display.py

# Events Display Module
# Handles displaying events section in the trip planner

import streamlit as st
import os
from events_service import get_events_for_trip


def display_events_section(result):
    """
    Display events happening during the trip
    
    Shows between itinerary and export options.
    Fetches events from multiple sources and displays them in expandable cards.
    
    Args:
        result: Trip generation result dict containing itinerary.
                This dict will be updated with 'all_events' key.
    """
    
    # Get trip dates from session (required by date_picker_system)
    start_date = st.session_state.get('current_trip_start_date')
    end_date = st.session_state.get('current_trip_end_date')
    
    if not start_date or not end_date:
        return  # No dates available
    
    st.markdown("---")
    st.markdown("### 🎉 Events During Your Trip")
    
    # Get all unique cities from itinerary
    cities = set()
    for day in result.get('itinerary', []):
        city = day.get('city', '')
        if city:
            cities.add(city)
    
    if not cities:
        st.info("No cities in the itinerary to check for events.")
        return
    
    # Fetch events for all cities
    all_events = []
    
    # Define a safe token if eventbrite is used (optional, but good practice)
    EVENTBRITE_TOKEN = os.environ.get("EVENTBRITE_TOKEN") 

    with st.spinner("🔍 Checking official listings and local events..."):
        for city in cities:
            try:
                # Get events from APIs (Junta, Eventbrite, Curated DB)
                events = get_events_for_trip(
                    city,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d'),
                    eventbrite_token=EVENTBRITE_TOKEN
                )
                all_events.extend(events)
            except Exception as e:
                # Use st.warning to continue if one city fails
                st.warning(f"Error fetching events for {city}: {e}")

    # 🚨 CRITICAL FIX: Save the fetched events back to the result dictionary!
    # This is the data source for document_generator.py
    result['all_events'] = all_events 
    
    if not all_events:
        st.info("No major public events found during your trip dates. Check local listings upon arrival.")
        return

    st.success(f"Found {len(all_events)} unique events for your trip!")
    st.caption("Showing the first 5 events for brevity. All found events are included in the exported DOCX.")

    # --- Display Logic ---
    icon_map = {
        'Festival': '🎊', 'Feria': '💃', 'Concert': '🎵', 'Sports': '⚽', 'Music': '🎭', 
        'Religious': '⛪', 'Cultural': '🎨', 'Flamenco': '💃', 'Carnival': '🎭', 
        'Art': '🎨', 'Theater': '🎭'
    }

    # Display top 5 events
    for event in all_events[:5]:
        event_name = event.get('name', 'N/A')
        event_date = event.get('date', 'TBD')
        event_location = event.get('location', event.get('city', ''))
        event_type = event.get('type', 'Event')
        event_desc = event.get('description', 'No description available.')
        event_source = event.get('source', 'Unknown')
        event_url = event.get('url')
        
        icon = icon_map.get(event_type, '🎉')
        
        # Display event in expander
        expander_title = f"{icon} **{event_date}** • {event_location} - {event_name}"
        
        with st.expander(expander_title, expanded=False):
            st.markdown(f"**{event_name}**")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.caption(f"📍 {event_location}")
            with col2:
                st.caption(f"🏷️ {event_type}")
            
            if event_desc:
                st.write(event_desc)
            
            if event_source:
                st.caption(f"📊 Source: {event_source}")
            
            if event_url:
                st.link_button(
                    "More Information",
                    event_url,
                    use_container_width=True
                )
    
    if len(all_events) > 5:
        st.caption(f"💡 Showing 5 of {len(all_events)} events found. All {len(all_events)} events are included in the exported DOCX.")
        st.markdown("---")