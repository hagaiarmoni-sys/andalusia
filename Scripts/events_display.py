# Events Display Module
# Handles displaying events section in the trip planner

import streamlit as st
from events_service import get_events_for_trip


def display_events_section(result):
    """
    Display events happening during the trip
    
    Shows between itinerary and export options.
    Fetches events from multiple sources and displays them in expandable cards.
    
    Args:
        result: Trip generation result dict containing itinerary
    """
    
    # Get trip dates from session
    start_date = st.session_state.get('current_trip_start_date')
    end_date = st.session_state.get('current_trip_end_date')
    
    if not start_date or not end_date:
        return  # No dates available
    
    st.markdown("---")
    st.markdown("### 🎉 Events During Your Trip")
    
    # Get all cities from itinerary
    cities = set()
    for day in result.get('itinerary', []):
        city = day.get('city', '')
        if city:
            cities.add(city)
    
    if not cities:
        return  # No cities in itinerary
    
    # Fetch events for all cities
    all_events = []
    
    with st.spinner("🔍 Checking for events..."):
        for city in cities:
            try:
                # Get events from APIs (Junta, Eventbrite, Curated DB)
                events = get_events_for_trip(
                    city,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d'),
                    eventbrite_token=None  # Optional: Add your Eventbrite token
                )
                all_events.extend(events)
            except Exception as e:
                print(f"⚠️ Error fetching events for {city}: {e}")
                continue
    
    if not all_events:
        st.info("ℹ️ No major events found during your travel dates")
        return
    
    # Sort events by date
    all_events.sort(key=lambda x: x.get('date', ''))
    
    # Display up to 5 events
    events_to_show = all_events[:5]
    
    for event in events_to_show:
        event_date = event.get('date', '')
        event_name = event.get('name', 'Event')
        event_location = event.get('location', '')
        event_desc = event.get('description', '')
        event_type = event.get('type', '')
        event_url = event.get('url', '')
        event_source = event.get('source', '')
        
        # Truncate description
        if len(event_desc) > 150:
            event_desc = event_desc[:150] + '...'
        
        # Choose icon based on type
        icon_map = {
            'Festival': '🎊',
            'Concert': '🎵',
            'Sports': '⚽',
            'Music': '🎭',
            'Religious': '⛪',
            'Cultural': '🎨',
            'Flamenco': '💃',
            'Carnival': '🎭',
            'Art': '🎨',
            'Theater': '🎭'
        }
        icon = icon_map.get(event_type, '🎉')
        
        # Display event in expander
        expander_title = f"{icon} {event_date} • {event_location} - {event_name}"
        
        with st.expander(expander_title, expanded=False):
            st.markdown(f"**{event_name}**")
            
            # Event details
            col1, col2 = st.columns([2, 1])
            with col1:
                st.caption(f"📍 {event_location}")
            with col2:
                st.caption(f"🏷️ {event_type}")
            
            # Description
            if event_desc:
                st.write(event_desc)
            
            # Source attribution
            if event_source:
                st.caption(f"📊 Source: {event_source}")
            
            # Link button
            if event_url:
                st.link_button(
                    "More Information",
                    event_url,
                    use_container_width=True
                )
    
    # Show count if more events exist
    if len(all_events) > 5:
        remaining = len(all_events) - 5
        st.caption(f"💡 Showing 5 of {len(all_events)} events. {remaining} more events found!")
        st.caption("📝 Download Word/Excel document to see all events.")
